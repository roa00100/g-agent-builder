# agent-builder-core

에이전트 빌더의 코어. 사용자가 자기만의 에이전트를 조립해서, 필요한 업무 단계(workflow 의 특정 단계)에서 그 에이전트의 보조를 받는다.
작업 규칙은 저장소 루트의 `AGENTS.md` 를 본다. `agent-handoff.md` 는 과거 다른 프로젝트의 경험을 정리한 참고 문서다.

패키지에는 설정(`settings.py`)과 DB 연결(`db.py`)만 있다. 테이블과 구조는 대표 workflow 가 정해진 뒤에 만든다.

테스트는 실제 PostgreSQL 에 붙는다. 먼저 아래 「로컬 DB」로 DB 를 띄운다.

## 준비

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

## 로컬 DB

```powershell
docker compose up -d --wait
.venv\Scripts\alembic upgrade head
```

끌 때는 `docker compose down`. 데이터까지 지우려면 `docker compose down -v`.

## 확인

```powershell
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\python -m pytest
```

## 도커

```powershell
docker compose run --rm --build app
```

실행 진입점이 아직 없어 컨테이너의 기본 명령은 pytest 다. 테스트가 DB 에 붙으므로 compose 로 DB 와 함께 띄운다.
