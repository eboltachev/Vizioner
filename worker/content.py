from __future__ import annotations

import json
import logging
import mimetypes
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
from uuid import uuid4

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from common.config import get_state

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadedObject:
    bucket: str
    key: str
    public_url: str


class Content:
    def __init__(self) -> None:
        state = get_state()
        self._bucket = state.vizioner_content_bucket_name
        self._region = state.vizioner_content_region or "us-east-1"
        self._internal_endpoint = state.vizioner_content_internal_endpoint_url.rstrip("/")
        self._public_endpoint = state.vizioner_content_public_endpoint_url.rstrip("/")
        self._apply_public_policy = bool(state.vizioner_content_apply_public_policy)
        verify = bool(state.vizioner_content_certificate)
        self._client = boto3.client(
            "s3",
            endpoint_url=self._internal_endpoint,
            aws_access_key_id=state.vizioner_content_access_key,
            aws_secret_access_key=state.vizioner_content_secret_key,
            region_name=self._region,
            verify=verify,
            config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 10, "mode": "standard"}),
        )
        self._transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            multipart_chunksize=8 * 1024 * 1024,
            max_concurrency=10,
            use_threads=True,
        )
        self._ready_lock = threading.Lock()
        self._ready = False

    def upload_files(self, files: Iterable[str], *, prefix: str | None = None) -> list[str]:
        self._ensure_ready()
        return [self.upload_file(file, prefix=prefix).public_url for file in files]

    def upload_file(self, file_path: str, *, prefix: str | None = None) -> UploadedObject:
        self._ensure_ready()
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        key = self._build_key(path.name, prefix=prefix)
        content_type, _ = mimetypes.guess_type(path.name)
        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        try:
            self._client.upload_file(
                Filename=str(path),
                Bucket=self._bucket,
                Key=key,
                ExtraArgs=extra_args or None,
                Config=self._transfer_config,
            )
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            raise RuntimeError(f"S3 upload failed: bucket={self._bucket} key={key} code={code}. raw={error}") from error
        return UploadedObject(bucket=self._bucket, key=key, public_url=self.public_url(key))

    def delete_objects(self, keys: Iterable[str]) -> int:
        self._ensure_ready()
        batch: list[dict[str, str]] = []
        deleted = 0
        for key in keys:
            if not key:
                continue
            batch.append({"Key": key})
            if len(batch) >= 1000:
                deleted += self._delete_objects_batch(batch)
                batch = []
        if batch:
            deleted += self._delete_objects_batch(batch)
        return deleted

    def delete_prefix(self, prefix: str) -> int:
        self._ensure_ready()
        prefix = prefix.lstrip("/")
        deleted = 0
        token: str | None = None
        while True:
            params: dict[str, object] = {"Bucket": self._bucket, "Prefix": prefix, "MaxKeys": 1000}
            if token:
                params["ContinuationToken"] = token
            resp = self._client.list_objects_v2(**params)
            items = resp.get("Contents") or []
            keys = [item.get("Key") for item in items if item.get("Key")]
            if keys:
                deleted += self.delete_objects(keys)
            if resp.get("IsTruncated"):
                token = resp.get("NextContinuationToken")
                if not token:
                    break
            else:
                break
        return deleted

    def public_url(self, key: str) -> str:
        safe_key = quote(key, safe="/")
        return f"{self._public_endpoint}/{self._bucket}/{safe_key}"

    def _build_key(self, filename: str, *, prefix: str | None = None) -> str:
        now = datetime.now(timezone.utc)
        date_path = now.strftime("%Y/%m/%d")
        prefix_path = self._normalize_prefix(prefix or "misc")
        return f"generated/{prefix_path}/{date_path}/{uuid4().hex}_{filename}"

    @staticmethod
    def task_prefix(task_id: str) -> str:
        safe = Content._normalize_prefix(f"tasks/{task_id}")
        return f"generated/{safe}/"

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        parts = [p for p in prefix.strip("/").split("/") if p]
        safe_parts: list[str] = []
        for part in parts:
            part = re.sub(r"[^a-zA-Z0-9._-]+", "_", part.strip())
            part = part.strip("._-") or "x"
            safe_parts.append(part[:128])
        return "/".join(safe_parts) if safe_parts else "misc"

    def _ensure_ready(self) -> None:
        if self._ready:
            return
        with self._ready_lock:
            if self._ready:
                return
            self._ensure_bucket_lenient()
            if self._apply_public_policy:
                self._ensure_public_read_policy_best_effort()
            self._ready = True

    def _delete_objects_batch(self, batch: list[dict[str, str]]) -> int:
        try:
            resp = self._client.delete_objects(
                Bucket=self._bucket,
                Delete={"Objects": batch, "Quiet": True},
            )
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            raise RuntimeError(f"S3 delete_objects failed: bucket={self._bucket} code={code} err={error}") from error
        errors = resp.get("Errors") or []
        if errors:
            raise RuntimeError(f"S3 delete_objects returned errors: {errors[:3]} (total={len(errors)})")
        deleted_items = resp.get("Deleted") or []
        return len(deleted_items) if deleted_items else len(batch)

    def _ensure_bucket_lenient(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"403", "AccessDenied", "Forbidden"}:
                logger.warning("HeadBucket forbidden for bucket=%s (code=%s).", self._bucket, code)
                return
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise RuntimeError(f"S3 head_bucket failed: bucket={self._bucket} err={error}") from error
        try:
            if self._region and self._region != "us-east-1":
                self._client.create_bucket(
                    Bucket=self._bucket,
                    CreateBucketConfiguration={"LocationConstraint": self._region},
                )
            else:
                self._client.create_bucket(Bucket=self._bucket)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                return
            if code in {"403", "AccessDenied", "Forbidden"}:
                logger.warning("CreateBucket forbidden for bucket=%s (code=%s).", self._bucket, code)
                return
            raise RuntimeError(f"S3 create_bucket failed: bucket={self._bucket} err={error}") from error

    def _ensure_public_read_policy_best_effort(self) -> None:
        desired = self._public_read_policy_json(bucket=self._bucket)
        try:
            current = self._client.get_bucket_policy(Bucket=self._bucket).get("Policy", "")
            if current:
                try:
                    if json.loads(current) == json.loads(desired):
                        return
                except Exception:
                    pass
        except ClientError:
            pass
        try:
            self._client.put_bucket_policy(Bucket=self._bucket, Policy=desired)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            logger.warning("PutBucketPolicy failed for bucket=%s (code=%s). err=%s", self._bucket, code, error)

    @staticmethod
    def _public_read_policy_json(*, bucket: str) -> str:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        }
        return json.dumps(policy, ensure_ascii=False)
