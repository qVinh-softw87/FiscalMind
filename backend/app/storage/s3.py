from __future__ import annotations

"""
S3 Storage — stub implementation for Phase 12.

Uncomment and complete when deploying to production with AWS S3.
"""

# from __future__ import annotations
#
# import boto3
# from botocore.exceptions import ClientError
# from app.core.config import settings
# from app.storage.base import StorageBackend
#
#
# class S3Storage(StorageBackend):
#     def __init__(self):
#         self._client = boto3.client(
#             "s3",
#             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#             region_name=settings.AWS_S3_REGION,
#         )
#         self._bucket = settings.AWS_S3_BUCKET
#
#     async def save(self, file_path: str, content: bytes) -> str:
#         self._client.put_object(Bucket=self._bucket, Key=file_path, Body=content)
#         return f"s3://{self._bucket}/{file_path}"
#
#     async def delete(self, file_path: str) -> None:
#         try:
#             self._client.delete_object(Bucket=self._bucket, Key=file_path)
#         except ClientError:
#             pass
#
#     async def exists(self, file_path: str) -> bool:
#         try:
#             self._client.head_object(Bucket=self._bucket, Key=file_path)
#             return True
#         except ClientError:
#             return False
#
#     async def read(self, file_path: str) -> bytes:
#         obj = self._client.get_object(Bucket=self._bucket, Key=file_path)
#         return obj["Body"].read()
#
#     async def get_url(self, file_path: str) -> str:
#         return self._client.generate_presigned_url(
#             "get_object",
#             Params={"Bucket": self._bucket, "Key": file_path},
#             ExpiresIn=3600,
#         )
