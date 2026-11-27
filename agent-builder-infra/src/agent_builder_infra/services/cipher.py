"""비밀 값 암호화 — cryptography 의 Fernet(대칭 키, 인증 포함)을 감싼다.

마스터 키 하나로 여러 비밀(공급자 API 키 등)을 암호문으로 바꿔 DB·캐시에 둔다.
마스터 키는 32바이트를 url-safe base64 로 적은 것이다.
만드는 명령은 저장소 루트의 .env.example 에 적어 두었다.
"""

from cryptography.fernet import Fernet, InvalidToken


class CipherError(Exception):
    """암호문을 풀지 못했다 — 마스터 키가 다르거나 암호문이 바뀌었다."""


class FernetCipher:
    def __init__(self, master_key: str) -> None:
        # 키 모양(32바이트 url-safe base64)이 틀리면 여기서 ValueError 가 난다.
        self._fernet = Fernet(master_key.encode())

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, token: bytes) -> str:
        try:
            return self._fernet.decrypt(token).decode()
        except InvalidToken as error:
            raise CipherError("암호문을 풀지 못했다 — 마스터 키를 확인한다") from error
