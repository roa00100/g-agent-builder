"""실제 오브젝트 스토리지(SeaweedFS)에 붙는다.

먼저 `docker compose up -d --wait` 로 띄운다.
"""

import hashlib
import uuid

import pytest


@pytest.fixture
def prefix(object_storage):
    """테스트마다 새 접두사를 쓰고, 끝나면 그 아래 키를 모두 지운다."""
    prefix = f"test/{uuid.uuid4()}/"
    yield prefix
    for key in object_storage.list_keys(prefix, limit=1000):
        object_storage.delete(key)


def test_put_and_get_bytes(object_storage, prefix):
    key = f"{prefix}hello.txt"
    object_storage.put_bytes(key, "안녕".encode(), content_type="text/plain")

    assert object_storage.get_bytes(key) == "안녕".encode()


def test_binary_round_trip_is_exact(object_storage, prefix):
    # 모든 바이트 값이 그대로 돌아오는지 — 이미지·PDF 같은 파일을 넣을 것이라서.
    data = bytes(range(256)) * 4096
    key = f"{prefix}blob.bin"
    object_storage.put_bytes(key, data, content_type="application/octet-stream")

    got = object_storage.get_bytes(key)

    assert hashlib.sha256(got).hexdigest() == hashlib.sha256(data).hexdigest()


def test_missing_key_is_none_not_error(object_storage, prefix):
    assert object_storage.get_bytes(f"{prefix}none") is None
    assert object_storage.head(f"{prefix}none") is None
    assert object_storage.exists(f"{prefix}none") is False


def test_head_returns_info(object_storage, prefix):
    key = f"{prefix}a.png"
    object_storage.put_bytes(key, b"\x89PNG....", content_type="image/png")

    info = object_storage.head(key)

    assert info.key == key
    assert info.size == 8
    assert info.content_type == "image/png"
    assert info.etag


def test_overwrite(object_storage, prefix):
    key = f"{prefix}k"
    object_storage.put_bytes(key, b"1", content_type="text/plain")
    object_storage.put_bytes(key, b"2", content_type="text/plain")

    assert object_storage.get_bytes(key) == b"2"


def test_list_and_delete(object_storage, prefix):
    for name in ["b", "a", "c"]:
        object_storage.put_bytes(f"{prefix}{name}", b"x", content_type="text/plain")

    assert object_storage.list_keys(prefix) == [
        f"{prefix}a",
        f"{prefix}b",
        f"{prefix}c",
    ]
    assert object_storage.list_keys(prefix, limit=2) == [f"{prefix}a", f"{prefix}b"]

    object_storage.delete(f"{prefix}a")
    object_storage.delete(f"{prefix}a")  # 두 번 지워도 오류가 아니다

    assert object_storage.list_keys(prefix) == [f"{prefix}b", f"{prefix}c"]
