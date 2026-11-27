"""테이블 정의 — 테이블의 열과 Python 클래스를 짝짓는 ORM 매핑(SQLAlchemy 모델).

계약은 모른다. 테이블의 값을 core 의 계약에 맞추는 일(Repository)은 runtime 이 한다.
쿼리 매핑(조회·저장)과 마이그레이션 생성(alembic autogenerate)의 기준으로 쓰인다.
실제 DDL 은 migrations/ 에 있다.
새 테이블 모듈은 migrations/env.py 에서 import 해야 autogenerate 가 본다.
"""
