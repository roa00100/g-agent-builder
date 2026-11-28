"""core 의 CallLog 를 채운다 — 호출 기록은 테이블 model_call, 본문은 오브젝트 스토리지.

Postgres 가 기준이고 캐시는 두지 않는다. 기록은 쓰고 나면 바뀌지 않고, 읽는 일은
사람이 들여다볼 때뿐이라 캐시로 얻을 것이 없다.
본문은 JSON 한 덩이로 `model_call/<request_id>/<이름>.json` 에 둔다. 지우지 않는다.
DB·스토리지 기술은 직접 쓰지 않는다. infra 가 주는 것만 쓴다.
"""

import json

from agent_builder_core.contracts.model import BodyName, CallRecord
from agent_builder_infra import crud
from agent_builder_infra.services import DbService, ObjectStorageService
from agent_builder_infra.tables.model_call import ModelCallRow


class CallLogRepository:
    def __init__(self, db: DbService, storage: ObjectStorageService) -> None:
        self._db = db
        self._storage = storage

    def save_body(self, request_id: str, name: BodyName, content: dict) -> str:
        key = f"model_call/{request_id}/{name}.json"
        # 공급자 본문에는 JSON 으로 바로 못 적는 값이 섞일 수 있어(오류 본문 등)
        # 그런 값은 글자로 적는다.
        data = json.dumps(content, ensure_ascii=False, default=str).encode("utf-8")
        self._storage.put_bytes(key, data, content_type="application/json")
        return key

    def read_body(self, key: str) -> dict | None:
        data = self._storage.get_bytes(key)
        return None if data is None else json.loads(data)

    def record(self, record: CallRecord) -> None:
        # 같은 request_id 가 또 오면 기본 키 충돌로 실패한다 — 요청 하나에 기록 하나다.
        with self._db.session_scope() as session:
            crud.create(session, ModelCallRow, **_to_values(record))

    def get(self, request_id: str) -> CallRecord | None:
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelCallRow, request_id)
            return None if row is None else _to_record(row)

    def list(self, limit: int) -> list[CallRecord]:
        """최근 것부터. 정렬·개수 제한은 공통 CRUD 에 없어 SQL 로 읽는다."""
        rows = self._db.fetch_all(
            "select * from model_call order by started_at desc, request_id limit :n",
            {"n": limit},
        )
        return [CallRecord.model_validate(row) for row in rows]


def _to_values(record: CallRecord) -> dict:
    """CallRecord → 테이블 열 값. version 은 모양의 버전이라 열로 두지 않는다."""
    return record.model_dump(exclude={"version"})


def _to_record(row: ModelCallRow) -> CallRecord:
    # 계약의 필드 이름으로 행의 속성을 읽는다. 행에 없는 version 은 기본값(1)이다.
    return CallRecord.model_validate(row, from_attributes=True)
