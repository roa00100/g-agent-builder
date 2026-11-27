"""오브젝트 스토리지 공통 동작 — 버킷 하나 안에서 키로 바이트를 넣고 꺼낸다.

키는 이 계층의 말이다. core 는 키를 모르고 우리 쪽 file_id 만 안다.
file_id 와 키를 잇는 일은 파일 정보 테이블(Postgres)이 생길 때 그쪽이 맡는다.
"""

from dataclasses import dataclass

from botocore.exceptions import ClientError

from agent_builder_infra.providers.object_storage import ObjectStorageProvider

# S3 가 「그런 키 없음」을 알리는 오류 코드.
# 다른 오류(권한·버킷 없음 등)는 그대로 올린다.
_NOT_FOUND = {"NoSuchKey", "404", "NotFound"}


@dataclass(frozen=True)
class ObjectInfo:
    key: str
    size: int
    content_type: str
    etag: str


class ObjectStorageService:
    def __init__(self, provider: ObjectStorageProvider) -> None:
        self._client = provider.client
        self._bucket = provider.bucket

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        """같은 키가 있으면 덮어쓴다. content_type 은 꺼낼 때 그대로 돌아온다."""
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )

    def get_bytes(self, key: str) -> bytes | None:
        """없으면 None. 그 밖의 실패(권한·연결 등)는 None 이 아니라 예외다."""
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as error:
            if _is_not_found(error):
                return None
            raise
        return response["Body"].read()

    def head(self, key: str) -> ObjectInfo | None:
        """내용을 받지 않고 정보만. 없으면 None."""
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as error:
            if _is_not_found(error):
                return None
            raise
        return ObjectInfo(
            key=key,
            size=response["ContentLength"],
            content_type=response["ContentType"],
            etag=response["ETag"].strip('"'),
        )

    def exists(self, key: str) -> bool:
        return self.head(key) is not None

    def delete(self, key: str) -> None:
        """없는 키를 지워도 오류가 아니다(S3 의 동작 그대로)."""
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def list_keys(self, prefix: str = "", *, limit: int = 100) -> list[str]:
        """prefix 로 시작하는 키를 limit 개까지, 키 이름 순으로.

        limit 기본값 100 은 들여다보기용으로 충분하고,
        실수로 큰 목록을 모으지 않게 한다.
        """
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                keys.append(item["Key"])
                if len(keys) >= limit:
                    return keys
        return keys


def _is_not_found(error: ClientError) -> bool:
    return error.response.get("Error", {}).get("Code") in _NOT_FOUND
