from __future__ import annotations

import json
import logging
import mimetypes
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
    """
    S3/MinIO content store.

    Требование: вернуть URL, который начинается с VIZIONER_CONTENT_PUBLIC_ENDPOINT_URL
    и указывает на объект в bucket. Без presigned URL.
    """

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
            config=BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 10, "mode": "standard"},
            ),
        )

        self._transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            multipart_chunksize=8 * 1024 * 1024,
            max_concurrency=10,
            use_threads=True,
        )

        # Важно: никаких сетевых вызовов в __init__ (воркер не должен падать при старте).
        self._ready_lock = threading.Lock()
        self._ready = False

    def upload_files(self, files: Iterable[str], *, prefix: str | None = None) -> list[str]:
        self._ensure_ready()
        urls: list[str] = []
        for f in files:
            uploaded = self.upload_file(f, prefix=prefix)
            urls.append(uploaded.public_url)
        return urls

    def upload_file(self, file_path: str, *, prefix: str | None = None) -> UploadedObject:
        self._ensure_ready()

        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        key = self._build_key(p.name, prefix=prefix)

        content_type, _ = mimetypes.guess_type(p.name)
        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            self._client.upload_file(
                Filename=str(p),
                Bucket=self._bucket,
                Key=key,
                ExtraArgs=extra_args or None,
                Config=self._transfer_config,
            )
        except ClientError as e:
            code = str(e.response.get("Error", {}).get("Code", ""))
            # Классическая причина: неверные ключи / нет прав на PutObject.
            raise RuntimeError(
                "S3 upload failed. "
                f"bucket={self._bucket} key={key} code={code}. "
                "Проверь VIZIONER_CONTENT_ACCESS_KEY / VIZIONER_CONTENT_SECRET_KEY и права (PutObject). "
                f"raw={e}"
            ) from e

        return UploadedObject(bucket=self._bucket, key=key, public_url=self.public_url(key))

    def public_url(self, key: str) -> str:
        safe_key = quote(key, safe="/")
        return f"{self._public_endpoint}/{self._bucket}/{safe_key}"

    # -------------------- internal --------------------

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

    def _build_key(self, filename: str, *, prefix: str | None = None) -> str:
        now = datetime.now(timezone.utc)
        date_path = now.strftime("%Y/%m/%d")
        group = (prefix or "misc").replace(" ", "_").replace("/", "_")
        return f"generated/{group}/{date_path}/{uuid4().hex}_{filename}"

    def _ensure_bucket_lenient(self) -> None:
        """
        Не падаем на 403 для HeadBucket.

        HeadBucket требует s3:ListBucket и может быть запрещён,
        даже если PutObject разрешён (типичный кейс least-privilege). :contentReference[oaicite:2]{index=2}
        """
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return
        except ClientError as e:
            code = str(e.response.get("Error", {}).get("Code", ""))
            if code in {"403", "AccessDenied", "Forbidden"}:
                logger.warning(
                    "HeadBucket forbidden for bucket=%s (code=%s). "
                    "Continue without bucket existence check; will rely on PutObject errors if any.",
                    self._bucket,
                    code,
                )
                return
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                # Прочие ошибки — уже реально подозрительные.
                raise RuntimeError(f"S3 head_bucket failed: bucket={self._bucket} err={e}") from e

        # Bucket отсутствует — пробуем создать.
        try:
            if self._region and self._region != "us-east-1":
                self._client.create_bucket(
                    Bucket=self._bucket,
                    CreateBucketConfiguration={"LocationConstraint": self._region},
                )
            else:
                self._client.create_bucket(Bucket=self._bucket)
        except ClientError as e:
            code = str(e.response.get("Error", {}).get("Code", ""))
            if code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                return
            if code in {"403", "AccessDenied", "Forbidden"}:
                # Нет прав на создание — но bucket может существовать и быть доступным для PutObject.
                logger.warning(
                    "CreateBucket forbidden for bucket=%s (code=%s). "
                    "If bucket already exists and PutObject is allowed, uploads will still work.",
                    self._bucket,
                    code,
                )
                return
            raise RuntimeError(f"S3 create_bucket failed: bucket={self._bucket} err={e}") from e

    def _ensure_public_read_policy_best_effort(self) -> None:
        """
        Best-effort: если нет прав на PutBucketPolicy — не валим воркер.
        Policy можно выставить отдельно в MinIO (console/mc). :contentReference[oaicite:3]{index=3}
        """
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
        except ClientError as e:
            code = str(e.response.get("Error", {}).get("Code", ""))
            logger.warning(
                "PutBucketPolicy failed for bucket=%s (code=%s). "
                "Public download may not work until policy is set in MinIO. err=%s",
                self._bucket,
                code,
                e,
            )

    @staticmethod
    def _public_read_policy_json(*, bucket: str) -> str:
        # Совместимый формат Principal для S3/MinIO. :contentReference[oaicite:4]{index=4}
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
