"""계약의 봉투 규칙 — 모든 계약 모양이 이것을 상속한다.

- 모르는 필드는 거부한다(T11). 오타 난 필드가 조용히 무시되지 않는다.
- 만든 뒤에는 바꿀 수 없다. 기록해 둔 값과 실제로 쓴 값이 달라질 수 없다.
  목록은 tuple 로 둔다 — list 는 객체가 얼어 있어도 안쪽을 바꿀 수 있다.
"""

from pydantic import BaseModel, ConfigDict


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
