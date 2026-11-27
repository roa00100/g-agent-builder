"""비밀 값 암호화(Fernet)."""

import base64
import os

import pytest

from agent_builder_infra.services import CipherError, FernetCipher


def new_key() -> str:
    # Fernet 키는 32바이트를 url-safe base64 로 적은 것이다.
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def test_round_trip_and_ciphertext_hides_plaintext():
    cipher = FernetCipher(new_key())

    token = cipher.encrypt("sk-or-secret")

    assert b"sk-or-secret" not in token
    assert cipher.decrypt(token) == "sk-or-secret"


def test_same_plaintext_gives_different_ciphertext():
    cipher = FernetCipher(new_key())

    assert cipher.encrypt("x") != cipher.encrypt("x")


def test_other_master_key_cannot_decrypt():
    token = FernetCipher(new_key()).encrypt("x")

    with pytest.raises(CipherError, match="마스터 키"):
        FernetCipher(new_key()).decrypt(token)


def test_tampered_ciphertext_is_rejected():
    cipher = FernetCipher(new_key())
    token = bytearray(cipher.encrypt("x"))
    token[-5] ^= 1

    with pytest.raises(CipherError):
        cipher.decrypt(bytes(token))


def test_malformed_master_key_is_rejected():
    with pytest.raises(ValueError):
        FernetCipher("not-a-fernet-key")
