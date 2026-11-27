# agent-builder-core

에이전트 빌더의 코어. 사용자가 자기만의 에이전트를 조립해서, 필요한 업무 단계(workflow 의 특정 단계)에서 그 에이전트의 보조를 받는다.
작업 규칙은 저장소 루트의 `AGENTS.md` 를 본다. `agent-handoff.md` 는 과거 다른 프로젝트의 경험을 정리한 참고 문서다.

패키지는 비어 있다. 구조는 handoff 6절의 질문이 정해진 뒤에 만든다.

## 준비

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

## 확인

```powershell
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\python -m pytest
```

## 도커

```powershell
docker build -t agent-builder-core:dev .
docker run --rm agent-builder-core:dev
```

실행 진입점이 아직 없어 컨테이너의 기본 명령은 pytest 다.
