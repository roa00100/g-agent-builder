# agent-builder-core

에이전트 빌더의 커널 — 공통 계약 구조를 둔다. 사용자가 자기만의 에이전트를 조립해서, 필요한 업무 단계(workflow 의 특정 단계)에서 그 에이전트의 보조를 받는다.

core 는 특정 기술(DB·Redis·모델 공급자)을 모른다. 의존성은 Pydantic 뿐이고, 구현은 `agent-builder-infra` 가 채운다.
작업 규칙은 저장소 루트의 `AGENTS.md` 를 본다. `agent-handoff.md` 는 과거 다른 프로젝트의 경험을 정리한 참고 문서다.

| 모듈 | 내용 |
|---|---|
| `contracts/` | 공통 계약(Protocol) 자리. 비어 있음 |
| `workflow/` | workflow 정의 — 단계의 순서, 단계마다 입력·출력, 누가 하는가. 비어 있음 |
| `run/` | 실행 상태 — 지금 어느 단계인가, 단계별 결과, 멈췄다 이어 가기. 비어 있음 |
| `assist/` | AI 보조 단계 — 보조 프로필에 따라 제안을 만든다. 비어 있음 |

## 테스트

DB·Redis 없이 돈다. 설치는 저장소 루트 `AGENTS.md` 6절을 본다.

```powershell
..\.venv\Scripts\python -m pytest
```

`tests/test_package.py` 는 core 가 infra 나 기술 패키지를 import 하지 않는지도 확인한다.
