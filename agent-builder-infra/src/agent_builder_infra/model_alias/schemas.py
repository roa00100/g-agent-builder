from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 모델 요청의 내용 조각 종류와 같은 세 가지. 테이블의 검사 제약과도 같다.
InputKind = Literal["text", "image", "file"]


class ModelAlias(BaseModel):
    """대응표 한 줄의 모양. 캐시(Redis)에 담는 것도 이것이다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    provider_model: str = Field(min_length=1)
    input_kinds: tuple[InputKind, ...] = Field(min_length=1)
    enabled: bool = True
