from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, List
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from common.config import get_state


class Content:
    _instance: "Content | None" = None

    def __new__(cls) -> "Content":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._state = get_state()
            cls._instance._upload_client = None
            cls._instance._public_client = None
        return cls._instance

    def publish_files(self, files: List[str], key_prefix: str) -> List[str]:
        upload_client, public_client = self._get_clients()
        bucket = self._state.vizioner_content_bucket_name
        ttl = int(self._state.vizioner_content_ttl)
        self._ensure_bucket(upload_client, bucket)
        urls: list[str] = []
        for local_path in files:
            p = Path(local_path)
            ext = p.suffix.lower()
            obj_key = f"{key_prefix}/{uuid4().hex}{ext}"
            content_type, _ = mimetypes.guess_type(str(p))
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            upload_client.upload_file(
                Filename=str(p),
                Bucket=bucket,
                Key=obj_key,
                ExtraArgs=extra_args or None,
            )
            url = public_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": obj_key},
                ExpiresIn=ttl,
            )
            urls.append(url)
        return urls

    def _get_clients(self) -> tuple[Any, Any]:
        if self._upload_client is not None and self._public_client is not None:
            return self._upload_client, self._public_client
        access_key = self._state.vizioner_content_access_key
        secret_key = self._state.vizioner_content_secret_key
        region = self._state.vizioner_content_region
        internal_endpoint = self._state.vizioner_content_internal_endpoint_url
        public_endpoint = self._state.vizioner_content_public_endpoint_url
        cfg = Config(signature_version="s3v4", s3={"addressing_style": "path"})
        self._upload_client = boto3.client(
            "s3",
            endpoint_url=internal_endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=cfg,
        )
        self._public_client = boto3.client(
            "s3",
            endpoint_url=public_endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=cfg,
        )

        return self._upload_client, self._public_client

    def _ensure_bucket(self, client: Any, bucket: str) -> None:
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchBucket", "NotFound"):
                try:
                    client.create_bucket(Bucket=bucket)
                except ClientError as create_error:
                    raise ConnectionError(f"{bucket=}") from create_error
            else:
                raise ConnectionError(f"{bucket=}") from error
