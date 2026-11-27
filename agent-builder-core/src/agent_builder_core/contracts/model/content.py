"""모델에 보내는 내용 — 종류(InputKind), 조각(ContentPart), 조각의 출처(Source).

모델 요청의 내용 조각과 모델 명세의 input_kinds 가 InputKind 정의 하나를 같이 쓴다.
조각의 type 값은 InputKind 의 세 낱말과 같다.
"""

import base64
import binascii
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, field_validator

from agent_builder_core.contracts.envelope import Envelope

# 종류를 늘리면 조각 클래스도 하나 더 만들고, infra 의 model_alias 테이블 검사 제약과
# 마이그레이션도 같이 바꾼다.
InputKind = Literal["text", "image", "file"]

# media_type 은 「종류/세부」 모양만 본다(예: image/png, application/pdf).
# 허용 목록은 두지 않는다 — 공급자마다 받는 형식이 달라서,
# 목록을 두면 core 가 공급자를 알게 된다.
_MEDIA_TYPE = r"^[\w.+-]+/[\w.+-]+$"


# --- 출처: 이미지·파일의 내용이 어디 있는가 ---


class InlineSource(Envelope):
    """내용을 요청에 직접 담는다."""

    type: Literal["inline"] = "inline"
    # base64 로 적은 내용.
    data: str = Field(min_length=1)

    @field_validator("data")
    @classmethod
    def _must_be_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except binascii.Error as error:
            raise ValueError("data 는 base64 여야 한다") from error
        return value


class UrlSource(Envelope):
    """공급자가 받아 갈 수 있는 주소."""

    type: Literal["url"] = "url"
    url: HttpUrl


class StoredSource(Envelope):
    """우리 쪽 오브젝트 스토리지에 저장해 둔 파일.

    file_id 는 우리가 정한 ID 다 — 스토리지의 버킷·키가 아니다.
    보내기 전에 실제 내용으로 바꾸는 일은 FileStore 계약이 맡는다(아직 없음).
    """

    type: Literal["stored"] = "stored"
    file_id: str = Field(min_length=1)


# 출처 셋 중 하나. type 값으로 어느 것인지 골라 읽는다.
# 아래 조각 클래스가 쓰므로 그보다 위, 출처 클래스들보다 아래에 둔다.
# 파이썬은 위에서부터 읽어서, 정의되기 전의 이름을 쓰면 NameError 가 난다.
Source = Annotated[InlineSource | UrlSource | StoredSource, Field(discriminator="type")]


# --- 조각: 메시지 내용 한 덩어리 ---


class TextPart(Envelope):
    type: Literal["text"] = "text"
    text: str


class ImagePart(Envelope):
    type: Literal["image"] = "image"
    source: Source
    # 예: image/png
    media_type: str = Field(pattern=_MEDIA_TYPE)


class FilePart(Envelope):
    type: Literal["file"] = "file"
    source: Source
    # 예: application/pdf
    media_type: str = Field(pattern=_MEDIA_TYPE)
    filename: str | None = None


# 조각 셋 중 하나. 조각 클래스들이 모두 정의된 뒤에 둔다(위 Source 와 같은 까닭).
ContentPart = Annotated[TextPart | ImagePart | FilePart, Field(discriminator="type")]
