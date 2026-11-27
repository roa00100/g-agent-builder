"""core 의 계약을 채우는 구현 — infra 의 값을 꺼내 계약의 모양으로 바꾼다.

DB 기술(SQLAlchemy 등)은 직접 쓰지 않고 infra 가 주는 것만 쓴다.
"""

from agent_builder_runtime.repositories.model_catalog import ModelCatalogRepository

__all__ = ["ModelCatalogRepository"]
