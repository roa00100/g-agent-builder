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

1. workflow 가 주인이고 AI 는 단계의 손님이다. ~~AI 가 없어도 workflow 는 사람 손으로 끝까지 돈다.~~ → 어느 칸이든 멈추고 사람이 그 칸의 출력을 넣어 이어 갈 수 있다 — AI·도구가 실패해도 사람이 채우고 다음 칸으로 간다 (2026-11-28 결정 점검에서 사용자가 고름).
2. AI 보조 단계는 모두 같은 틀이다. 단계마다 다른 것은 보조 프로필(데이터)뿐이다(T4).
3. ~~AI 의 결과는 제안이다. 다음 단계로 넘기는 것은 사람이다(R4).~~ → 사람에게는 주의가 필요한 칸에서만 묻고, 나머지는 이어서 돈다 (2026-11-28 사용자 결정으로 바뀜 — 5절 참고).
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
| 결정 | 구현 언어는 Python (2026-11-27 사용자 지시). 코드는 `agent-builder-core/`(계약)·`agent-builder-infra/`(기술 구성)·`agent-builder-runtime/`(계약 구현·조립·진입점)에 나눠 둔다 (2026-11-27 사용자가 고름) |
| 결정 | DB 는 PostgreSQL (2026-11-27 사용자 지시) |
| 결정 | LangGraph 를 쓴다 (2026-11-27 사용자 지시 — 처음의 말 「LangGraph, pgvector, 웹 프레임워크 사용안함」을 에이전트가 셋 다 쓰지 않는다로 잘못 읽어 「쓰지 않는다」로 적었고, 2026-11-28 사용자가 정정함. 쓰지 않는 것은 웹 프레임워크뿐이었다). pgvector 도 같은 정정으로 「쓰지 않는다」를 지웠다 — 아래 행에서 쓴다로 정함. 웹 프레임워크는 core·infra 에 두지 않고, REST 를 여는 진입 계층에서만 쓴다 (2026-11-27 사용자가 고름 — 처음의 「웹 프레임워크는 쓰지 않는다」를 1절의 REST 정정에 맞춰 바꿈) |
| 결정 | 모델은 프로바이더 형태로 공급자를 고른다. 첫 공급자는 OpenRouter (2026-11-27 사용자 지시) |
| 제안 — 설정됨, 사용자 확인 전 | 로컬 DB 는 docker compose, DB 접근은 SQLAlchemy 2 + psycopg 3(동기), 스키마 변경은 Alembic, 설정은 pydantic-settings + `.env`, 데이터 모양은 Pydantic v2 |
| 미정 | 첫 도구 2~3개, 첫 예시 조립 하나, 자료 위치(handoff Q5 — 검색 도구에 자료를 넣을 때 필요). handoff 의 Q1~Q3(대표 workflow·AI 보조 단계·두 번째 workflow)은 비개발자가 조립을 만드는 틀로 바뀌어 이것으로 대신한다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 결정 | 사용자가 직접 쓰는 것은 기본 구조 코드다. 밑바탕까지 전부 직접 쓰지 않으며, 쓸 수 있는 오픈소스는 적극 검토한다 (2026-11-27 사용자 지시) |
| 결정 | OpenRouter 는 `openai` SDK 로 부른다 — 주소만 바꿔 쓴다 (2026-11-27 사용자가 고름) |
| 결정 | 프로바이더 인터페이스 — core 계약 `ModelProvider`(name, complete(request, spec) → ModelResponse, 한 번만 보내고 실패는 ModelCallFailed)와 `UnknownProvider`. 호출 순서(대응표 찾기 → check_inputs → 공급자 고르기 → 보내기)는 core 서비스 `ModelGateway` 가 맡는다. infra 에는 OpenRouter 라이브러리와의 연결점(`OpenRouterClient` — 클라이언트, 보내고 받기, SDK 오류를 기술의 말로 넘기기)만 두고, 그 밖의 공급자 조립과 서비스(요청·응답 바꾸기, 실패를 계약의 말로 해석하기)는 runtime(`model_adapters/`, `OpenRouterAdapter`)에 둔다 (처음에는 infra 에 호출 서비스 `ChatCompletionService` 와 실패 분류를 두었다가 사용자가 정정함). 다시 보내기는 프로바이더·Gateway 가 하지 않고 나중에 보조 고리의 런타임이 정한다. 스트리밍은 나중. `StoredSource` 는 FileStore 가 생기기 전까지 Gateway 가 보내기 전에 막는다. 코드는 에이전트가 쓰고 사용자가 검토한다 (2026-11-27 사용자가 고름) |
| 결정 | 패키지는 개념별로 나누고, 각 개념 안에서 층을 나눈다. core 의 개념에는 schemas·service 만 두고, SQLAlchemy 테이블 정의는 infra 의 `tables/` 에 둔다. 개념 서비스는 세션이 아니라 core 의 계약을 생성자로 받는다 (2026-11-27 사용자가 고름 — 처음의 「models 도 개념 안에, 세션은 인자로」를 core 분리에 맞춰 바꿈) |
| 결정 | 개념은 `workflow`(정의), `run`(실행 상태), `assist`(AI 보조 단계) 셋으로 시작한다 (2026-11-27 사용자가 고름) |
| 결정 | Redis 를 더한다 (2026-11-27 사용자 지시). ~~체크포인트 같은 상태를 저장한다~~ → Redis 에는 고리 중간 값·잠금·취소 신호처럼 짧게 사는 것만 둔다. 체크포인트는 LangGraph 의 Postgres 체크포인터가 맡는다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 제안 — 설정됨 | Redis 8 을 AOF(`appendfsync always`)로 띄워 재시작해도 남게 한다. 클라이언트는 redis-py |
| 결정 | Postgres 가 기준이다. 단계 결과·채택 여부·기록처럼 남아야 하는 것은 Postgres 에 둔다. Redis 에는 보조 고리가 도는 동안의 중간 상태, 잠금·취소 신호처럼 짧게 사는 것만 둔다. Redis 가 비어도 Postgres 만으로 마지막 확정 단계부터 이어 갈 수 있어야 한다 (2026-11-27 사용자가 고름) |
| 결정 | 접속 프로바이더(`providers/`)와 공통 서비스(`services/`)를 나눈다. 서비스는 프로바이더를 생성자로 받고, 조립은 `container.py` 한 곳에서 한다. `crud.py` 는 세션만 받는 함수로 둔다 (2026-11-27 사용자가 고름). 프로바이더·서비스·crud 는 infra 에, 조립하는 `container.py` 는 runtime 에 있다 (2026-11-27 사용자가 고름 — 처음에는 infra 에 두었음) |
| 결정 | core 는 공통 계약 구조를 두는 커널 레벨이다. 특정 기술을 모르고, 의존성은 Pydantic 뿐이다. core 계약의 구현(Repository 등)은 runtime 에 둔다. runtime 이 core 와 infra 를 import 하고, infra 도 core 를 import 할 수 있다 (2026-11-27 사용자가 고름 — 처음에는 「구체 구현은 infra」였다. infra 를 「runtime 이 쓸 기술 구성」으로 정한 뒤, infra 의 값을 꺼내 계약에 맞추는 일은 infra 구성이 아니라 runtime 의 일로 바꿈. 클린 아키텍처의 Interface Adapters 와 같은 자리. 이때 에이전트가 「infra 는 core 를 모른다」를 덧붙여 사용자 결정처럼 적었으나 제안이었고, 사용자가 정정함 — 바깥 층이 안쪽 core 에 의존하는 것은 문제없다) |
| 제안 — 사용자 확인 전 | 이름은 core 를 유지한다(kernel 로 바꾸지 않음) |
| 결정 | 입구(cli·rest)에는 번역만 두고, 여러 계약 호출을 엮는 순서는 서비스에 둔다. cli 와 rest 는 같은 서비스를 부른다 (2026-11-27 사용자 지시) |
| 미정 | core 의 계약(`contracts/`) — 짧게 사는 값 저장소, 실행 상태 저장소, 모델 공급자 등. 사용자가 쓰는 구조 코드 |
| 결정 | 첫 계약은 모델 요청(`ModelRequest`)이다. 공급자 중립이고, 봉투 규칙(모르는 필드 거부·만든 뒤 불변)을 따른다 (2026-11-27 사용자가 고름) |
| 결정 | 모델 요청의 `model` 은 논리 이름(예: `fast`, `smart`)이다. infra 가 공급자와 실제 모델 이름으로 바꾼다 (2026-11-27 사용자가 고름) |
| 결정 | 모델 요청에 공급자 전용 옵션 칸을 두지 않는다 (2026-11-27 사용자가 고름) |
| 결정 | 모델 요청에 버전 필드를 둔다 (2026-11-27 사용자가 고름) |
| 결정 | 메시지 내용은 텍스트만이 아니라 이미지·파일도 담을 수 있는 구조로 지금 잡는다 (2026-11-27 사용자 지시) |
| 결정 | 메시지 내용에 문자열을 주면 텍스트 조각 하나로 바꿔 받는다(문자열 지름길) (2026-11-27 사용자가 고름) |
| 결정 | 이미지·파일 조각의 출처에 저장된 파일(`StoredSource(file_id)`)을 지금 넣는다. file_id 를 실제 내용으로 바꾸는 일은 `FileStore` 계약을 만들 때 붙인다 (2026-11-27 사용자 지시) |
| 결정 | 요청의 내용 조각이 모델이 받는 종류 안에 드는지는 core 의 `check_inputs(request, spec)` 가 검사한다 — 몰래 빼지 않고 오류 (2026-11-27 사용자가 고름) |
| 결정 | `media_type` 은 `종류/세부` 모양만 검사한다. 허용 목록은 두지 않는다 — 공급자마다 달라서 (2026-11-27 사용자가 고름) |
| 결정 | 모델 요청 계약 코드는 에이전트가 정리한 모양대로 쓰고 사용자가 검토한다 (2026-11-27 사용자가 고름) |
| 결정 | 모델 응답 `ModelResponse` — 본문은 요청의 `Message`(role=assistant)를 다시 쓴다. 종료 사유는 stop·length·tool_calls·content_filter·other 로 고정하고 공급자의 원래 값은 `finish_detail` 에 둔다. 실패는 응답이 아니라 예외 `ModelCallFailed`(종류·다시 시도할 만한지)로 낸다. 사용량에 비용(`cost`)을 선택 필드로 둔다. 코드는 에이전트가 쓰고 사용자가 검토한다 (2026-11-27 사용자가 고름) |
| 결정 | 오브젝트 스토리지를 도입한다. 메시지의 이미지·파일 조각이 저장된 파일을 가리킬 수 있게 한다 (2026-11-27 사용자 지시) |
| 결정 | 오브젝트 스토리지는 SeaweedFS 다 (2026-11-27 사용자가 고름) |
| 제안 — 사용자 확인 전 | infra 는 S3 API 로만 말한다(클라이언트 boto3). core 는 스토리지를 모르고, 파일은 우리 쪽 ID(`file_id`)로 가리킨다. 파일 정보는 Postgres, 내용은 SeaweedFS |
| 결정 | 모델 논리 이름의 대응표는 Postgres 에 두고 Redis 에 캐싱한다 (2026-11-27 사용자 지시) |
| 결정 | 대응표는 함수로 넣고 고친다(지금은 runtime 의 `ModelCatalogRepository`). 고칠 때 캐시도 같이 지운다 (2026-11-27 사용자가 고름). 지금 있는 진입점은 명령줄 하나다 — 호출 방법은 REST 또는 CLI 라는 1절에 따라 명령줄은 함수 위의 얇은 진입점일 뿐이다 |
| 결정 | 패키지는 셋이다. core 는 계약, infra 는 runtime 이 쓸 infra 구성, runtime(`agent_builder_runtime`)은 실행 진입점(CLI·REST)이고, core 계약의 구현과 조립도 맡는다. 명령줄 진입점은 runtime 에 둔다 (2026-11-27 사용자 지시) |
| 결정 | 모델 대응표의 계약은 core(`contracts/model/`)에 둔다 — `ModelSpec`(name·provider·provider_model·input_kinds·enabled), 계약 `ModelCatalog`(찾기·고치기를 함께 — 처음에는 읽기·고치기 둘로 나눴다가 사용자가 하나로 합침, 권한은 계약이 다루지 않고 필요해지면 부르는 쪽에서 정한다), 오류 `UnknownModel`·`DisabledModel`, 규칙 `resolve_model`. `InputKind` 는 core 한 곳에서 정의한다. runtime 의 `ModelCatalogRepository`(`repositories/model_catalog.py`)가 infra 의 테이블·캐시로 이 계약을 채운다 (구현 이름은 저장 기술을 드러내지 않는다, 사용자가 고름). 테이블 정의는 infra 의 `tables/model_alias.py` 에 있다. Repository 는 SQLAlchemy 를 직접 쓰지 않고 infra 의 DbService·crud·RedisService 만 쓴다(사용자가 고름). 테이블 `model_alias` 의 이름은 그대로 둔다(명령줄 묶음은 처음에 `model-alias` 로 두었다가 계약 이름에 맞춰 `model-catalog` 로 바꿈). 이번 코드는 에이전트가 기존 코드를 옮겨 작성하고 사용자가 검토한다 (2026-11-27 사용자가 고름) |
| 결정 | 공급자 설정(API 키·주소·대기 시간)은 환경변수가 아니라 공급자 프로필(테이블 `model_provider`)에 둔다. Postgres 가 기준이고 Redis 에 캐싱한다. 키는 모델 행이 아니라 공급자 행에 하나 둔다. 키는 `cryptography` 의 Fernet 으로 암호화해 저장하고(캐시에도 암호문), 마스터 키 하나만 환경변수에 둔다. 대기 시간은 공급자 기본값을 두고 모델별로 덮어쓸 수 있다(`ModelSpec.timeout_seconds`). core 는 키를 모른다 (2026-11-27 사용자가 고름) |
| 결정 | 이름 규칙: 기술을 감싸는 접속 계층은 기술 이름, core 계약을 채우는 구현은 역할 이름(`ModelCatalogRepository`·`OpenRouterAdapter` 등) (2026-11-27 사용자가 고름). 접속 계층은 다시 둘로 나눈다 — 저장소 접속(Postgres·Redis·오브젝트 스토리지)은 `~Provider`(infra `providers/`), 외부 API 접속(OpenRouter 등 모델 공급자)은 `~Client`(infra `clients/`) (2026-11-27 사용자가 고름 — 처음에는 OpenRouter 접속도 `OpenRouterProvider` 였다) |
| 결정 | core 계약 `ModelProvider` 를 공급자 모양과 맞바꾸는 runtime 구현은 Adapter 로 부른다 — `model_adapters/openrouter/`, `OpenRouterAdapter`. infra 의 접속 계층 이름과 낱말이 겹치지 않게 하려는 것이다 (2026-11-27 사용자가 고름). infra 의 OpenRouter 접속은 이어서 `OpenRouterClient` 로 바꿨다 — 위 이름 규칙 참고 |
| 결정 | runtime 의 실행 모드는 `__main__` 에서 프로필(cli / rest)로 고른다 (2026-11-27 사용자 지시) |
| 결정 | 관측 — 추적은 OpenTelemetry(업체 중립, 나중에 Datadog 으로도 보냄), 구조적 로그는 structlog. 로그 단계는 TRACE(5)·DEBUG·INFO·WARNING·ERROR — INFO 흐름 요약, DEBUG 갈림길과 모양, TRACE 오간 데이터 전체(기본 꺼짐). 비밀(API 키·Authorization·암호문)은 단계와 상관없이 지운다. core 에는 추적 코드를 넣지 않고 runtime 이 계약 구현과 Gateway 를 span 으로 감싼다. 로컬 추적 화면은 Jaeger(compose 선택 서비스) (2026-11-27 사용자가 고름) |
| 제안 — 설정됨, 사용자 확인 전 | 관측의 구현 모양. SQL span 은 공식 계측(opentelemetry-instrumentation-sqlalchemy 0.66b2) 대신 SQLAlchemy 이벤트로 직접 건다 — 공식 계측이 SQLAlchemy 2.1 을 받지 않고, 켜면 asyncio(greenlet)까지 불러와서. HTTP 는 `httpx2` 계측 — openai SDK 3.x 가 httpx2 로 보낸다. span 에는 넘긴 값(SQL 값·Redis 값·HTTP 헤더)과 오간 문장을 넣지 않고, 문장은 TRACE 로그에만 둔다. 계약 구현은 container 에서 `traced()` 로 메서드를 바꿔 끼워 감싼다(클래스가 그대로라 계약 isinstance 가 맞는다). Gateway 는 runtime `trace_gateway()` 가 감싸 INFO `model.call.done` 한 줄을 남긴다 |
| 결정 | 호출 기록 — 공급자에 보낸 호출 한 번마다 Postgres(테이블 `model_call`)에 한 줄을 남긴다. 보내기 전에 막힌 것은 남기지 않는다. ~~기록에 실패해도 응답은 그대로 돌려주고 ERROR 로그(`model.call.record_failed`)로 알린다. 숫자와 모양만 남기고 보낸 문장·받은 답은 남기지 않는다.~~ → 바뀜: 아래 「추적 가능성」 행들. `ModelResponse` 에 선택 필드 `upstream_provider`(OpenRouter 가 알려 주는 실제 공급사)를 더하고 기록에도 남긴다 (2026-11-27 사용자가 고름) |
| 제안 — 설정됨, 사용자 확인 전 | 호출 기록의 구현 모양. core 계약 `CallRecord`·`CallLog`(record·get·list — 고치기·지우기 없음). ~~`ModelGateway` 가 `CallLog` 와 기록 실패 알림 함수(`on_record_error`)를 생성자로 받는다~~ → `ModelGateway` 는 `CallLog` 만 받는다. 호출마다 `CallJournal` 을 만들어 공급자 구현에 넘긴다 — `ModelProvider.complete(request, spec, journal)`. 본문 넷: request(계약의 요청 + 그때의 ModelSpec, Gateway 가 보내기 전) · sending(실제 보낼 본문 + 공급자 설정 사본 — 주소·대기 시간·프로필 updated_at, 키 제외, 어댑터가 보내기 직전) · received(받은 원문·오류 본문, 어댑터가 바꾸기 전) · response(계약의 응답, Gateway). 본문은 `CallLog.save_body` 로 오브젝트 스토리지 `model_call/<request_id>/<이름>.json` 에, 위치는 `CallRecord.bodies`(model_call.bodies JSONB)에 둔다. 못 남기면 `CallNotRecorded(stage, sent)` — 보낸 뒤면 숫자 없는 실패 줄을 남겨 보고 그대로 올린다. 입구는 명령줄 종료 코드 4, REST 503(kind not_recorded), 로그 ERROR `model.call.not_recorded`. 본문 보기: `model call-show <id> --body`, `GET /model/calls/{id}/bodies/{name}`. 실패 기록의 걸린 시간은 Gateway 가 잰다. `ProviderMismatch` 는 보낸 것이라 실패(`unknown`)로 남기고 응답의 숫자는 줄에 넣지 않는다 — 받은 원문(received)이 본문으로 남는다. 요청의 `TraceContext` 를 run_id·step_id·attempt 로 옮겨 둔다. 비용 열은 정밀도 없는 NUMERIC. 입구는 `model calls`·`model call-show`, `GET /model/calls`·`GET /model/calls/{request_id}`. infra `crud` 의 앞 인자를 위치 전용으로 바꿨다 — 열 이름 `model` 이 인자 이름과 부딪혀서 |
| 결정 | 만드는 것은 「사용자(개발자)가 만든 도구를 비개발자가 조합해 쓰는 것」이다. 시스템은 특정 업무를 미리 알지 않는다 — 업무의 모양은 비개발자의 조립 정의(데이터)로 정해진다. 조합의 모양은 섞음 — 큰 틀은 비개발자가 잇는 순서형이고, AI 칸 안에서만 허용한 도구들 중에서 AI 가 골라 쓴다 (2026-11-28 사용자가 고름). 무엇을 섞을지·상태를 어떻게 유지할지·이어 갈지를 맡는 것이 LangGraph 다 (2026-11-28 사용자 설명) |
| 결정 | LangGraph 는 runtime 에 둔다 — core 는 조립 정의와 실행 상태의 계약만 갖고, runtime 이 조립 정의를 LangGraph 그래프로 바꿔 돌린다. infra 에는 SDK 연결점을, runtime 에는 계약에 맞추는 Adapter 를 둔다. 체크포인트는 LangGraph 의 Postgres 체크포인터를 쓴다 (2026-11-28 사용자가 고름) |
| 결정 | pgvector 를 쓴다 (2026-11-28 사용자 지시) |
| 결정 | **절대 전제 — 추적 가능성은 반드시 확보한다.** 어떤 결과든 무엇을 받아 누가(어느 칸·모델·도구) 어떻게 만들었는지 끝까지 따라갈 수 있어야 한다 (2026-11-28 사용자 지시) |
| 결정 | 고르기 기록에 사용자의 말을 남긴다 (2026-11-28 사용자가 고름) |
| 결정 | 추적 가능성 — 모델 호출의 요청·응답 본문을 오브젝트 스토리지에 남기고, 호출 기록에는 그 위치(키)를 둔다. 키(비밀)는 본문에 없다 (2026-11-28 결정 점검에서 사용자가 고름 — 어제의 「숫자와 모양만」을 바꿈) |
| 결정 | 추적 가능성 — 기록하지 못한 결과는 쓰지 않는다. 요청 본문은 보내기 전에 저장하고, 못 하면 보내지 않는다. 받은 뒤 응답 본문·기록을 못 남기면 그 호출을 실패로 본다 (2026-11-28 결정 점검에서 사용자가 고름 — 어제의 「기록에 실패해도 응답은 돌려준다」를 바꿈) |
| 결정 | 추적 가능성 — 호출마다 그때 쓴 설정의 사본(ModelSpec 과 공급자 주소·대기 시간, 키 제외)을 요청 본문과 같이 남긴다. 대응표·공급자 프로필에 이력 테이블은 두지 않는다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 결정 | 추적 가능성 — 조립 정의·AI 칸 프로필은 고치면 새 판이 생기고 옛 판은 지우지 않는다. 실행·고르기 기록에 판 번호를 남긴다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 결정 | 추적 가능성 — 한 번 넣은 저장 파일(file_id)의 내용은 바꾸지 않는다. 새 내용은 새 id 다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 결정 | 추적 가능성 — 검색 도구가 찾아 준 결과(조각·출처·점수)는 도구 호출 기록에 통째로 남긴다. 색인이 바뀌어도 그때 읽은 것이 남는다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 결정 | 추적 가능성 — 실행 상태는 우리 테이블(`run`·`step_result`)과 LangGraph 체크포인트 둘로 둔다. 사슬은 우리 테이블이고, 체크포인트는 이어 가기용이다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 결정 | 추적 가능성 — 남긴 본문은 지금은 지우지 않는다. 지워야 할 때가 오면 「지웠다」는 기록을 남기는 방식으로 그때 정한다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 결정 | 사람은 입구에서 이름으로 받는다(cli `--user`, REST 헤더). 인증이 붙으면 그 값으로 바꾼다 (2026-11-28 결정 점검에서 사용자가 고름) |
| 결정 | 추적 가능성 — 만들 때 지킬 것 (2026-11-28 결정 점검에서 사용자가 고름): ① 도구 호출 기록 — 도구 칸·AI 칸 안의 모든 도구 호출에 한 줄(도구 이름·입력·출력 본문 위치·결과·걸린 시간·run_id·step_id·attempt), 모델 호출 기록과 같은 꼴 ② 칸 결과는 주의 칸이 아니어도 늘 남긴다(칸 id·입력·출력·조립 판·끝난 방식: 자동·사람 확인·사람이 넣음·실패) ③ 사람의 손은 늘 남긴다(주의 칸 확인·고친 값·버림, 헷갈림·되묻기 답 — 누가·언제·무엇을) ④ 고르기 기록(말·그때의 후보와 판·결과·까닭·고르기 프로필 판·모델 request_id) ⑤ 모든 기록은 위쪽 하나로 이어진다: 고르기 → run_id → step_id·attempt → request_id(모델)·tool_call_id(도구) → 본문 위치 ⑥ 사슬을 한 번에 펼쳐 보는 입구(예: `run trace <run_id>`) — 남겼다가 아니라 따라가 봤다로 확인한다(E12) |
| 미정 | 1절 목표 문구 — 「사용자」가 개발자인지 비개발자인지, 「workflow 의 특정 단계에서 AI 보조」를 「개발자가 만든 도구를 비개발자가 조합」으로 바꿀지. 목표 문구라 사용자만 고친다(E15) |
| 결정 | 시스템의 입구는 미리 만들어 둔 조립들 가운데 하나를 고르는 진입점이다. 골랐으면 바로 시작하고, 후보가 헷갈릴 때만 사람에게 묻는다. 고르기는 AI 칸과 같은 틀(프로필 데이터)로 만들고, 후보 조립 목록만 시스템이 채운다 (2026-11-28 사용자가 고름) |
| 결정 | 실행 중에 사람에게 묻는 것은 주의가 필요한 칸에서만이다. 그 밖의 칸은 AI 칸이라도 결과를 그대로 다음 칸으로 넘긴다 — 4절 원칙 3(R4, 늘 사람이 넘긴다)을 바꿈 (2026-11-28 사용자 지시). 주의가 필요한 칸은 조립하는 비개발자가 칸마다 정한다 — 도구가 강제하지 않는다. 확인을 빼는 것도 의도한 결정일 수 있고, 사람이 고칠 수 있어서 (2026-11-28 사용자가 고름) |
| 결정 | 사내 지식 같은 자료 읽기는 검색 도구 하나로 통일한다 — 보조 프로필에 「읽을 자료」 칸을 따로 두지 않고, 검색 도구를 도구 칸(늘 먼저 찾기)이나 AI 칸의 허용 도구(필요할 때 찾기)로 끼운다 (2026-11-28 사용자가 고름) |
| 결정 | 실패 문장 — 사람이 읽는 실패 문장은 경우를 나눠 사실대로, 자세히 쓴다: 무엇을 했고(또는 하지 않았고) 왜인가, 보냈는가·비용이 들었을 수 있는가·무엇이 남았는가·원인, 다음에 할 일(실제 명령). 기계가 읽는 이름(REST 의 kind, 로그 이벤트)은 바꾸지 않는다 (2026-11-28 사용자가 고름) |
| 제안 — 설정됨, 사용자 확인 전 | 실패 문장의 구현 모양. runtime `failure_text.py` 한 곳이 실패 → (message·facts·next) 를 만들고, 명령줄은 여러 줄로 찍고 REST 는 본문에 그대로 넣는다(같은 문장). 문장에 필요한 사실을 담으려고 core 예외에 칸을 더했다 — `UnknownModel(name)`·`DisabledModel(name)`·`UnsupportedInput(model, unsupported, accepted)`·`UnknownProvider(name, reason: no_profile·disabled·not_assembled)`·`UnresolvedSource(file_ids)`·`ProviderMismatch(request_id, detail)`·`ModelCallFailed(..., sent=True)`(보내기 전에 막힌 것을 아는 곳만 False — 키 없음·보낼 본문으로 못 바꿈), runtime `MissingApiKey(provider)`·`MissingMasterKey`. 시간 초과·연결 실패는 「닿았는지 확실하지 않다」, 그 밖의 호출 실패는 「공급자가 실패로 답했다」로 쓴다. 입력값 오류는 Pydantic 의 검사 종류를 한국어로 옮기고, 모르는 종류는 원문을 쓴다. REST 에 500 `provider_mismatch` 를 더했고, 명령줄 종료 코드 1 에 설정 문제(마스터 키·API 키)를 넣었다 |
| 결정 | REST 진입 계층의 웹 프레임워크는 FastAPI 다. 자리는 runtime 의 `rest/` 다 (2026-11-27 사용자가 고름) |
| 결정 | 프로필을 주지 않으면 cli 모드로 돈다 (2026-11-27 사용자가 고름) |
| 결정 | 프로필은 `--profile` 인자와 환경변수 `RUNTIME_PROFILE` 둘 다로 받고, 인자가 환경변수를 이긴다 (2026-11-27 사용자가 고름) |
| 진행 단계 | W0 이전 — core 에 모델 계약(`contracts/model/` — 대응표·요청·응답·내용 조각), infra 에 기술 구성(설정, Postgres·Redis·오브젝트 스토리지의 프로바이더·서비스, CRUD, 테이블 정의 — 사용자 지시로 에이전트가 작성), runtime 에 모델 대응표 Repository·조립·명령줄이 있고, core 의 개념 패키지 셋은 비어 있다. 모델 호출 경로(ModelGateway → OpenRouterAdapter)와 공급자 프로필(DB, 키는 암호문)이 있다. 파일 계약(`FileStore`)과 보조 고리는 아직 없다. 모델 호출 입구(`model call`·`POST /model/call`)와 관측(로그·추적, 로컬 Jaeger)이 있다. 호출 기록(테이블 `model_call`, `model calls`)이 있다. 테이블은 셋이다(`model_alias`·`model_provider`·`model_call`). 2026-11-28 두 전제(추적 가능성·비개발자의 조합)로 결정을 점검했고, 호출 기록의 본문 저장과 「기록하지 못한 결과는 쓰지 않는다」는 코드에 옮겼다(마이그레이션 4개). 다음은 진입점(고르기) |

## 6. 저장소 구성

```
agent-handoff.md        과거 다른 프로젝트의 경험 (교훈·설계 이론, 참고용)
AGENTS.md               이 문서
.gitignore · .gitattributes · .editorconfig
.github/workflows/ci.yml    push·PR 때 ruff, core 테스트, 마이그레이션, infra·runtime 테스트
ruff.toml               저장소 전체의 ruff 설정
.python-version         Python 버전 (CI 가 읽는다)
docker-compose.yml      로컬 PostgreSQL · Redis · SeaweedFS(오브젝트 스토리지), 컨테이너 테스트용 app, 선택 서비스 Jaeger(추적 화면, profile observability)
.env.example            환경변수 예시 — 복사해서 루트에 .env 를 만든다
.dockerignore           도커 빌드 맥락은 저장소 루트다
.venv/                  가상환경 하나에 core·infra·runtime 을 같이 설치한다
agent-builder-core/     계약 — 특정 기술을 모른다. DB 없이 테스트가 돈다
  src/agent_builder_core/
  tests/
agent-builder-infra/    기술 구성 — 접속·공통 서비스·테이블 정의. core 의 정의를 가져다 쓸 수 있다
  Dockerfile
  alembic.ini · migrations/ 스키마 변경 (마이그레이션 4개: model_alias, model_provider·모델별 대기 시간, model_call, model_call 본문 위치)
  src/agent_builder_infra/
  tests/                    실제 PostgreSQL·Redis·SeaweedFS 에 붙는다
agent-builder-runtime/  계약 구현·조립·진입점 — infra 의 값을 core 의 계약에 맞추고, CLI(지금)·REST(나중)로 돌린다
  src/agent_builder_runtime/
  tests/
```

패키지 배치 규칙 (결정).

```
agent_builder_core/                     계약
  contracts/                공통 계약 (Protocol). 특정 기술의 말을 쓰지 않는다
    envelope.py             Envelope — 봉투 규칙(모르는 필드 거부·만든 뒤 불변)의 부모
    model/                  content.py(InputKind·조각·출처) · request.py(ModelRequest) · response.py(ModelResponse·ModelCallFailed·parse_output) · provider.py(ModelProvider·UnknownProvider) · catalog.py(ModelSpec·ModelCatalog·resolve_model·check_inputs) · record.py(CallRecord·CallLog·CallJournal·CallNotRecorded)
  model/                    모델 호출 서비스 — ModelGateway (대응표 찾기 → check_inputs → 공급자 고르기 → 요청 본문 남기기 → 보내기 → 응답 본문·기록 남기기 — 못 남기면 결과를 버린다)
  workflow/ · run/ · assist/   개념 패키지
  <개념>/
    schemas.py              Pydantic 모델 — 주고받는 데이터의 모양
    service.py              업무 로직. 필요한 계약을 생성자로 받는다

agent_builder_infra/                    기술 구성
  settings.py               환경변수·.env 에서 읽는 설정
  providers/                접속 — 자원을 만들고, 확인(ping)하고, 닫는다
    postgres.py · redis.py · object_storage.py   저장소 접속 (~Provider)
  clients/                  외부 API 접속 (~Client)
    openrouter.py           OpenRouterClient — SDK 클라이언트, chat() 으로 한 번 보내고 받기, SDK 오류는 OpenRouterCallError 로 넘김. 자동 재시도 끔
  services/                 공통 동작 — 프로바이더를 생성자로 받는다
    db.py                   DbService: 트랜잭션·커서·SQL 직접 실행
    redis.py                RedisService: 문자열·JSON·모델·해시·카운터·키 (쓰기는 ttl 필수)
    object_storage.py       ObjectStorageService: 키로 바이트 넣기·꺼내기·정보·목록·삭제 (S3 API)
    cipher.py               FernetCipher: 비밀 값 암호화·복호화 (마스터 키 SECRET_ENCRYPTION_KEY)
  observability/            관측 — 입구가 맨 먼저 켠다
    logging.py              structlog 설정·get_logger (TRACE 단계, trace_id 붙이기, 비밀 지우기)
    tracing.py              OpenTelemetry 설정(OTLP 로 보내기는 주소가 있을 때만)·자동 계측(Redis·httpx2·botocore)·span·traced
    sql.py                  SQL 실행마다 span (SQLAlchemy 이벤트)
  orm.py                    테이블 모델의 부모 Base
  crud.py                   ORM 공통 CRUD — 세션만 받는다 (앞 인자는 위치 전용 — 열 이름과 부딪히지 않게)
  tables/                   테이블 정의 (SQLAlchemy ORM 매핑, Base 상속) — 테이블마다 파일 하나. 실제 DDL 은 migrations/
    model_alias.py          ModelAliasRow (모델별 대기 시간 덮어쓰기 timeout_seconds 포함)
    model_call.py           ModelCallRow — 호출 기록 (성공·실패 열 제약, started_at·run_id 색인)
    model_provider.py       ModelProviderRow — 공급자 프로필 (주소·API 키 암호문·기본 대기 시간·켜짐)

agent_builder_runtime/                  계약 구현·조립·진입점
  repositories/             core 계약의 구현 — infra 의 값 ↔ core 의 모양. SQLAlchemy 를 직접 쓰지 않는다
    model_catalog.py        ModelCatalogRepository (테이블 model_alias + Redis 캐시)
    call_log.py             CallLogRepository — 호출 기록 (테이블 model_call, 본문은 오브젝트 스토리지, 캐시 없음)
    provider_profile.py     ProviderProfileRepository — 공급자 프로필 (테이블 model_provider + Redis 캐시, 키는 어디서나 암호문)
  model_adapters/          core 의 ModelProvider 구현 — 공급자마다 하나. openai SDK 를 직접 쓰지 않는다
    connections.py          ProviderConnections — 프로필로 연결점을 만들고, 프로필이 바뀌면(updated_at) 새로 만든다
    openrouter/             OpenRouterAdapter — adapter.py(흐름: 연결 받기·대기 시간·보내기·시간 재기) · request.py(요청 → 본문) · response.py(본문 → 응답) · errors.py(오류 → 실패 종류)
  container.py              조립 — infra 의 프로바이더·서비스와 runtime 의 구현을 한 번씩 만든다 (get_model_catalog·get_model_gateway 등). 계약 구현은 traced() 로 감싸 내준다
  observability.py          setup_observability()(입구가 맨 먼저 부른다)·trace_gateway()(호출 하나 = span 하나 + INFO 한 줄)
  failure_text.py           실패 → 사람이 읽는 문장(message·facts·next). cli·rest 가 같이 쓴다
  settings.py               실행 설정 — RUNTIME_PROFILE(cli·rest, 기본 cli), REST_HOST·REST_PORT
  __main__.py               입구 — 프로필(--profile 또는 RUNTIME_PROFILE)로 모드만 고른다
  cli/                      cli 모드 — 명령 하나 실행하고 끝. __init__.run() 이 묶음 파서를 조립
    <묶음>.py               묶음마다 register()·run(). 계약을 부르기만 한다 (model.py · model_catalog.py · model_provider.py)
  rest/                     rest 모드 — FastAPI 서버. 웹 프레임워크는 여기에만
    __init__.py             create_app()·run() — /health 와 묶음별 라우터, FastAPI 계측(요청 하나 = 뿌리 span)
    <묶음>.py               묶음마다 APIRouter. cli 의 같은 묶음과 같은 일을 한다 (model.py · model_catalog.py · model_provider.py)
```

- 의존은 안쪽으로만 향한다: runtime → infra → core, runtime → core. core 는 infra·runtime 과 기술 패키지(sqlalchemy·psycopg·redis·openai·alembic·boto3)를, infra 는 runtime 을 import 하지 않는다. runtime 은 기술 패키지(sqlalchemy·psycopg·redis·boto3·openai)를 직접 import 하지 않는다. 각 패키지의 `test_package.py` 가 이것을 확인한다.
- 테이블 모델과 Pydantic 모델을 한 클래스로 합치지 않는다.
- 이름: 기술을 감싸는 접속 계층(providers·services)은 기술 이름으로, core 계약을 채우는 구현은 역할 이름으로 짓는다(예: `ModelCatalogRepository`). 저장 기술은 구현 이름에 드러내지 않는다.
- 입구(cli·rest)에는 번역만 둔다 — 인자·본문을 받아 계약이나 서비스를 부르고, 결과를 출력·응답(종료 코드·HTTP 상태)으로 바꾸는 데까지다. 둘 이상의 계약 호출을 엮는 순서는 서비스(core 개념의 `service.py`)에 두고, cli·rest 는 그 서비스를 부르기만 한다. 같은 로직을 두 입구에 각각 쓰지 않는다.
- 웹 프레임워크(fastapi·uvicorn)는 runtime 의 `rest/` 에만 둔다. runtime 의 `test_package.py` 가 이것을 확인한다.
- 관측 기술(opentelemetry·structlog)은 core 에 두지 않는다. runtime 은 infra 의 `observability` 를 거쳐 쓰고, 예외는 `rest/` 의 FastAPI 계측 하나다. 각 `test_package.py` 가 확인한다.
- span 에는 모양과 숫자만, 오간 문장은 TRACE 로그에만 둔다. 비밀은 어느 단계에서도 남기지 않는다.
- 사람이 읽는 실패 문장은 `failure_text.py` 에서만 만든다. 입구에서 예외의 문자열을 그대로 찍지 않는다.
- 프로바이더는 runtime 의 `container.py` 만 만든다. 진입점은 container 에서 받고, 서비스는 생성자로 받는다.
- 새 테이블 정의(`tables/<테이블>.py`)는 `migrations/env.py` 에서 import 해야 autogenerate 가 본다.

설치와 확인. 저장소 루트에서 시작한다.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e ".\agent-builder-core[dev]" -e ".\agent-builder-infra[dev]" -e ".\agent-builder-runtime[dev]"
Copy-Item .env.example .env
docker compose up -d --wait
docker compose --profile observability up -d --wait jaeger   # 추적 화면이 필요할 때만 (http://127.0.0.1:16686)
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
cd agent-builder-core; ..\.venv\Scripts\python -m pytest; cd ..
cd agent-builder-infra; ..\.venv\Scripts\alembic upgrade head; ..\.venv\Scripts\python -m pytest; cd ..
cd agent-builder-runtime; ..\.venv\Scripts\python -m pytest; cd ..
.venv\Scripts\python -m agent_builder_runtime --help
.venv\Scripts\python -m agent_builder_runtime --profile rest
docker compose run --rm --build app
```
