# AGENTS.md

이 저장소에서 일하는 AI 에이전트가 따르는 작업 규칙이다.
[agent-handoff.md](agent-handoff.md) 는 **사용자가 과거 다른 프로젝트에서 겪은 경험**을 정리한 문서다. 이 프로젝트의 목표나 결정을 적은 문서가 아니다.
거기서 교훈과 설계 이론을 참고로 가져온다. 여기 적힌 ID(E·T·R·J·Q·W)는 그 문서의 것이다. 두 문서가 다르면 이 문서를 따른다.

## 1. 무엇을 만드는가

- 사용자가 자기만의 에이전트를 조립해서, 자신이 필요한 업무 단계에서 에이전트의 보조를 지원한다
- 목표는 **workflow 의 특정 단계에서 AI 의 보조를 받는 것**이다.
- UI 는 나중이다. 구조 설계가 먼저다.
- 호출은 기본적으로 REST 또는 CLI 로 한다. CLI 는 방법 중 하나일 뿐 고정값이 아니다 (2026-11-27 사용자 정정).
- ** 에이전트는 사용자의 설계를 보조하고, 사용자는 설계를 확인한다**

## 2. 일하는 방식

- 코드는 사용자가 요청할 때만 쓴다. 그 전에는 설계 논리와 결과물의 모양만 보인다.
- 검토·설명 요청에는 코드를 고치지 않는다.
- 「맞아?」「어때?」에는 결론과 근거를 준다. 「어떻게 할까?」에는 번호 붙은 2~3안과 추천 하나.
- 여러 단계 계획은 실행 전에 결과물의 모양을 먼저 보인다.
- 「된다」는 실물을 본 뒤에만 말한다 — 사용자가 하는 동작을 직접 해 본 뒤에만. 확인 못 한 것을 먼저 적는다. 시험 통과는 「켜져서 돈다」가 아니다(E12, E13).
- 안전판·호환 코드·폴백은 시키지 않으면 남기지 않는다.
- 같은 자리를 두 번 고치게 되면 멈추고 원인과 구조를 본다(E10).
- 고치기 전에 「모델이 무엇을 받았고 왜 그렇게 골랐나」부터 읽는다(E11).
- 커밋·push 는 시킬 때만.

## 3. 제안과 결정

- 「결정」은 사용자가 말한 것, 「제안」은 에이전트의 안이다. 적을 때 출처를 구분한다(E14).
- 사용자가 고른 것만 결정이다. 제안이 승인되어도 「사용자가 고름」으로 적지, 에이전트의 권고를 의도보다 위에 두지 않는다.
- 목표 문구는 사용자만 바꾼다. 일부만 했으면 「일부 — 무엇만」이라고 적는다(E15).
- 한 번 정한 것을 시험 한 번으로 뒤집지 않는다(E17).
- handoff 6절의 Q1~Q7 은 사용자 몫이다. 답이 나오기 전에 구조를 정하지 않는다.
- handoff 2절의 교훈을 어기는 방향이면 그 ID 를 대고 말한다.

## 4. 구조 원칙 (handoff 5절 — 아직 제안)

1. workflow 가 주인이고 AI 는 단계의 손님이다. AI 가 없어도 workflow 는 사람 손으로 끝까지 돈다.
2. AI 보조 단계는 모두 같은 틀이다. 단계마다 다른 것은 보조 프로필(데이터)뿐이다(T4).
3. AI 의 결과는 제안이다. 다음 단계로 넘기는 것은 사람이다(R4).
4. UI 가 없어도 돈다. 정의·상태·기록은 파일이나 작은 DB 에 있다.

코드를 볼 때 늘 확인하는 것.

- 의미 판단은 모델, 코드는 실행·검증만(E1). 모델의 「했다」는 다른 손이 확인한다(E9).
- 코드에 특정 문서·특정 업무의 말이 나오면 구조 결함이다(E3).
- 고리를 만들면 한도(횟수·기한·취소)를 같이 만든다(E5).
- 넓히기 전에 끝에서 끝까지 얇게 한 번 통과시킨다(E6).
- 값마다 왜 그 값인지 주석으로 남긴다(E18).

## 5. 현재 상태

기록은 이 절 한 장으로 유지한다. 작업 일지를 쌓지 않는다(E16).

| 항목 | 상태 |
|---|---|
| 결정 | 구현 언어는 Python (2026-11-27 사용자 지시). 코드는 `agent-builder-core/`(계약)와 `agent-builder-infra/`(구현)에 나눠 둔다 (2026-11-27 사용자가 고름) |
| 결정 | DB 는 PostgreSQL (2026-11-27 사용자 지시) |
| 결정 | LangGraph, pgvector 는 쓰지 않는다 (2026-11-27 사용자 지시). 웹 프레임워크는 core·infra 에 두지 않고, REST 를 여는 진입 계층에서만 쓴다 (2026-11-27 사용자가 고름 — 처음의 「웹 프레임워크는 쓰지 않는다」를 1절의 REST 정정에 맞춰 바꿈) |
| 결정 | 모델은 프로바이더 형태로 공급자를 고른다. 첫 공급자는 OpenRouter (2026-11-27 사용자 지시) |
| 제안 — 설정됨, 사용자 확인 전 | 로컬 DB 는 docker compose, DB 접근은 SQLAlchemy 2 + psycopg 3(동기), 스키마 변경은 Alembic, 설정은 pydantic-settings + `.env`, 데이터 모양은 Pydantic v2 |
| 미정 | Q1~Q3, Q5 (대표 workflow, AI 보조 단계, 두 번째 workflow, 자료 위치) |
| 결정 | 사용자가 직접 쓰는 것은 기본 구조 코드다. 밑바탕까지 전부 직접 쓰지 않으며, 쓸 수 있는 오픈소스는 적극 검토한다 (2026-11-27 사용자 지시) |
| 결정 | OpenRouter 는 `openai` SDK 로 부른다 — 주소만 바꿔 쓴다 (2026-11-27 사용자가 고름) |
| 미정 | 프로바이더 인터페이스의 모양 (사용자가 쓰는 구조 코드) |
| 결정 | 패키지는 개념별로 나누고, 각 개념 안에서 층을 나눈다. core 의 개념에는 schemas·service 만 두고, SQLAlchemy 테이블 모델은 infra 에 둔다. 개념 서비스는 세션이 아니라 core 의 계약을 생성자로 받는다 (2026-11-27 사용자가 고름 — 처음의 「models 도 개념 안에, 세션은 인자로」를 core 분리에 맞춰 바꿈) |
| 결정 | 개념은 `workflow`(정의), `run`(실행 상태), `assist`(AI 보조 단계) 셋으로 시작한다 (2026-11-27 사용자가 고름) |
| 결정 | Redis 를 더해 체크포인트 같은 상태를 저장한다 (2026-11-27 사용자 지시) |
| 제안 — 설정됨 | Redis 8 을 AOF(`appendfsync always`)로 띄워 재시작해도 남게 한다. 클라이언트는 redis-py |
| 결정 | Postgres 가 기준이다. 단계 결과·채택 여부·기록처럼 남아야 하는 것은 Postgres 에 둔다. Redis 에는 보조 고리가 도는 동안의 중간 상태, 잠금·취소 신호처럼 짧게 사는 것만 둔다. Redis 가 비어도 Postgres 만으로 마지막 확정 단계부터 이어 갈 수 있어야 한다 (2026-11-27 사용자가 고름) |
| 결정 | 접속 프로바이더(`providers/`)와 공통 서비스(`services/`)를 나눈다. 서비스는 프로바이더를 생성자로 받고, 조립은 `container.py` 한 곳에서 한다. `crud.py` 는 세션만 받는 함수로 둔다 (2026-11-27 사용자가 고름). 프로바이더·서비스·crud 는 infra 에, 조립하는 `container.py` 는 runtime 에 있다 (2026-11-27 사용자가 고름 — 처음에는 infra 에 두었음) |
| 결정 | core 는 공통 계약 구조를 두는 커널 레벨이다. 특정 기술을 모르고, 의존성은 Pydantic 뿐이다. 구체 구현은 `agent-builder-infra` 에 둔다. infra 가 core 를 import 하고, 반대는 없다 (2026-11-27 사용자가 고름) |
| 제안 — 사용자 확인 전 | 이름은 core 를 유지한다(kernel 로 바꾸지 않음) |
| 미정 | core 의 계약(`contracts/`) — 짧게 사는 값 저장소, 실행 상태 저장소, 모델 공급자 등. 사용자가 쓰는 구조 코드 |
| 결정 | 첫 계약은 모델 요청(`ModelRequest`)이다. 공급자 중립이고, 봉투 규칙(모르는 필드 거부·만든 뒤 불변)을 따른다 (2026-11-27 사용자가 고름) |
| 결정 | 모델 요청의 `model` 은 논리 이름(예: `fast`, `smart`)이다. infra 가 공급자와 실제 모델 이름으로 바꾼다 (2026-11-27 사용자가 고름) |
| 결정 | 모델 요청에 공급자 전용 옵션 칸을 두지 않는다 (2026-11-27 사용자가 고름) |
| 결정 | 모델 요청에 버전 필드를 둔다 (2026-11-27 사용자가 고름) |
| 결정 | 메시지 내용은 텍스트만이 아니라 이미지·파일도 담을 수 있는 구조로 지금 잡는다 (2026-11-27 사용자 지시) |
| 결정 | 메시지 내용에 문자열을 주면 텍스트 조각 하나로 바꿔 받는다(문자열 지름길) (2026-11-27 사용자가 고름) |
| 결정 | 오브젝트 스토리지를 도입한다. 메시지의 이미지·파일 조각이 저장된 파일을 가리킬 수 있게 한다 (2026-11-27 사용자 지시) |
| 결정 | 오브젝트 스토리지는 SeaweedFS 다 (2026-11-27 사용자가 고름) |
| 제안 — 사용자 확인 전 | infra 는 S3 API 로만 말한다(클라이언트 boto3). core 는 스토리지를 모르고, 파일은 우리 쪽 ID(`file_id`)로 가리킨다. 파일 정보는 Postgres, 내용은 SeaweedFS |
| 결정 | 모델 논리 이름의 대응표는 Postgres 에 두고 Redis 에 캐싱한다 (2026-11-27 사용자 지시) |
| 결정 | 대응표는 infra 의 함수로 넣고 고친다. 고칠 때 캐시도 같이 지운다 (2026-11-27 사용자가 고름). 지금 있는 진입점은 명령줄 하나다 — 호출 방법은 REST 또는 CLI 라는 1절에 따라 명령줄은 함수 위의 얇은 진입점일 뿐이다 |
| 결정 | 패키지는 셋이다. core 는 계약, infra 는 runtime 이 쓸 infra 구성, runtime(`agent_builder_runtime`)은 실행 진입점(CLI·REST)이다. 명령줄 진입점은 runtime 에 둔다 (2026-11-27 사용자 지시) |
| 미정 | REST 진입 계층에 쓸 웹 프레임워크 — 그 계층을 만들 때 고른다. 자리는 runtime 이다 |
| 진행 단계 | W0 이전 — infra 에 공통 기반(설정, Postgres·Redis·오브젝트 스토리지의 프로바이더·서비스, CRUD — 사용자 지시로 에이전트가 작성)이 있고, core 에는 빈 `contracts/` 와 빈 개념 패키지 셋만 있다. 테이블은 `model_alias`(모델 논리 이름 대응표) 하나, 모델을 부르는 코드는 없다 |

## 6. 저장소 구성

```
agent-handoff.md        과거 다른 프로젝트의 경험 (교훈·설계 이론, 참고용)
AGENTS.md               이 문서
.gitignore · .gitattributes · .editorconfig
.github/workflows/ci.yml    push·PR 때 ruff, core 테스트, 마이그레이션, infra·runtime 테스트
ruff.toml               저장소 전체의 ruff 설정
.python-version         Python 버전 (CI 가 읽는다)
docker-compose.yml      로컬 PostgreSQL · Redis · SeaweedFS(오브젝트 스토리지), 컨테이너 테스트용 app
.env.example            환경변수 예시 — 복사해서 루트에 .env 를 만든다
.dockerignore           도커 빌드 맥락은 저장소 루트다
.venv/                  가상환경 하나에 core·infra·runtime 을 같이 설치한다
agent-builder-core/     계약 — 특정 기술을 모른다. DB 없이 테스트가 돈다
  src/agent_builder_core/
  tests/
agent-builder-infra/    구현 — core 의 계약을 Postgres·Redis·SeaweedFS·OpenRouter 로 채운다
  Dockerfile
  alembic.ini · migrations/ 스키마 변경 (마이그레이션 1개: model_alias)
  src/agent_builder_infra/
  tests/                    실제 PostgreSQL·Redis·SeaweedFS 에 붙는다
agent-builder-runtime/  실행 진입점 — CLI(지금)·REST(나중). core 의 계약과 infra 의 구성을 묶어 돌린다
  src/agent_builder_runtime/
  tests/
```

패키지 배치 규칙 (결정).

```
agent_builder_core/                     계약
  contracts/                공통 계약 (Protocol). 특정 기술의 말을 쓰지 않는다
  workflow/ · run/ · assist/   개념 패키지
  <개념>/
    schemas.py              Pydantic 모델 — 주고받는 데이터의 모양
    service.py              업무 로직. 필요한 계약을 생성자로 받는다

agent_builder_infra/                    구현
  settings.py               환경변수·.env 에서 읽는 설정
  providers/                접속 — 자원을 만들고, 확인(ping)하고, 닫는다
    postgres.py · redis.py · object_storage.py
  services/                 공통 동작 — 프로바이더를 생성자로 받는다
    db.py                   DbService: 트랜잭션·커서·SQL 직접 실행
    redis.py                RedisService: 문자열·JSON·모델·해시·카운터·키 (쓰기는 ttl 필수)
    object_storage.py       ObjectStorageService: 키로 바이트 넣기·꺼내기·정보·목록·삭제 (S3 API)
  orm.py                    테이블 모델의 부모 Base
  crud.py                   ORM 공통 CRUD — 세션만 받는다
  model_alias/              모델 논리 이름 대응표 — models·schemas·service
  <개념>/models.py          SQLAlchemy 테이블 모델 (Base 상속) — 테이블이 생기면

agent_builder_runtime/                  실행 진입점
  container.py              조립 — infra 의 프로바이더·서비스를 한 번씩 만든다
  __main__.py               명령줄 — python -m agent_builder_runtime <묶음> <명령>
  cli/<묶음>.py             묶음마다 register()·run(). 서비스를 부르기만 한다
  (나중) rest/              REST 진입점 — 웹 프레임워크는 여기에만
```

- 의존 방향은 runtime → infra → core 한쪽뿐이다. core 는 infra·runtime 과 기술 패키지(sqlalchemy·psycopg·redis·openai·alembic·boto3)를, infra 는 runtime 을 import 하지 않는다. 각 패키지의 `test_package.py` 가 이것을 확인한다.
- 테이블 모델과 Pydantic 모델을 한 클래스로 합치지 않는다.
- 기능은 서비스 함수에 둔다. CLI·REST 는 그 함수를 부르기만 하는 얇은 진입점이고, 웹 프레임워크는 REST 진입 계층에만 둔다.
- 프로바이더는 runtime 의 `container.py` 만 만든다. 진입점은 container 에서 받고, 서비스는 생성자로 받는다.
- 새 테이블 모델 모듈은 `migrations/env.py` 에서 import 해야 autogenerate 가 본다.

설치와 확인. 저장소 루트에서 시작한다.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e ".\agent-builder-core[dev]" -e ".\agent-builder-infra[dev]" -e ".\agent-builder-runtime[dev]"
Copy-Item .env.example .env
docker compose up -d --wait
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
cd agent-builder-core; ..\.venv\Scripts\python -m pytest; cd ..
cd agent-builder-infra; ..\.venv\Scripts\alembic upgrade head; ..\.venv\Scripts\python -m pytest; cd ..
cd agent-builder-runtime; ..\.venv\Scripts\python -m pytest; cd ..
.venv\Scripts\python -m agent_builder_runtime --help
docker compose run --rm --build app
```
