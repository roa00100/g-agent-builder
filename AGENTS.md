# AGENTS.md

이 저장소에서 일하는 AI 에이전트가 따르는 작업 규칙이다.
[agent-handoff.md](agent-handoff.md) 는 **사용자가 과거 다른 프로젝트에서 겪은 경험**을 정리한 문서다. 이 프로젝트의 목표나 결정을 적은 문서가 아니다.
거기서 교훈과 설계 이론을 참고로 가져온다. 여기 적힌 ID(E·T·R·J·Q·W)는 그 문서의 것이다. 두 문서가 다르면 이 문서를 따른다.

## 1. 무엇을 만드는가

- 만드는 것은 **에이전트 빌더**다 — 개발자가 만든 부품(도구·AI 칸 틀·검증기)을 조립하는 사람이 칸으로 이어 자기만의 에이전트를 만들고, 시스템은 그 조립을 그대로 실행한다.
- 목표는 **업무 흐름의 필요한 칸에서 AI 의 보조를 받는 것**이다. 흐름은 사람이 정하고, AI 는 칸 안에서만 판단한다.
- 사람은 셋이다 — 부품을 만드는 개발자(이 문서의 「사용자」), 조립하는 사람(비개발자), 말로 시켜 쓰는 사람. 같은 사람이 여러 역할을 할 수 있다.
- 시스템은 특정 업무를 미리 알지 않는다. 업무의 모양은 조립 정의(데이터)로 정해진다.
- 어떤 결과든 무엇을 받아 누가 어떻게 만들었는지 끝까지 따라갈 수 있어야 한다(추적 가능성 — 절대 전제).
- UI 는 나중이다. 구조 설계가 먼저다.
- 호출은 기본적으로 REST 또는 CLI 로 한다. CLI 는 방법 중 하나일 뿐 고정값이 아니다 (2026-11-27 사용자 정정).
- **에이전트는 사용자의 설계를 보조하고, 사용자는 설계를 확인한다**

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
- 미정인 것은 사용자 몫이다. 5절의 「미정」 항목에 답이 나오기 전에 그 부분의 구조를 정하지 않는다. (handoff 6절의 Q1~Q7 은 답이 났거나 다른 것으로 대신했다 — 5절 참고.)
- handoff 2절의 교훈을 어기는 방향이면 그 ID 를 대고 말한다.

## 4. 구조 원칙 (handoff 5절에서 출발 — 1·3 은 사용자 결정으로 바뀌었고, 2·4 는 아직 제안)

낱말: 이 절의 「workflow」는 5절의 「조립」, 「단계」는 「칸」과 같은 것을 가리킨다.

1. workflow 가 주인이고 AI 는 단계의 손님이다. ~~AI 가 없어도 workflow 는 사람 손으로 끝까지 돈다.~~ → 어느 칸이든 멈추고 사람이 그 칸의 출력을 넣어 이어 갈 수 있다 — AI·도구가 실패해도 사람이 채우고 다음 칸으로 간다 (2026-11-28 결정 점검에서 사용자가 고름).
2. AI 칸은 모두 같은 실행 구조로 돈다. 칸마다 다른 것은 데이터(개발자가 만든 틀과 조립하는 사람이 채운 빈칸)뿐이다 — 새 AI 칸을 더할 때 실행 코드를 고치지 않는다(T4).
3. ~~AI 의 결과는 제안이다. 다음 단계로 넘기는 것은 사람이다(R4).~~ → 사람에게는 주의가 필요한 칸에서만 묻고, 나머지는 이어서 돈다 (2026-11-28 사용자 결정으로 바뀜 — 5절 참고).
4. UI 가 없어도 돈다. 정의·상태·기록은 PostgreSQL 과 오브젝트 스토리지에 있다(5절).

코드를 볼 때 늘 확인하는 것.

- 의미 판단은 모델, 코드는 실행·검증만(E1). 모델의 「했다」는 다른 손이 확인한다(E9).
- 코드에 특정 문서·특정 업무의 말이 나오면 구조 결함이다(E3).
- 고리를 만들면 한도(횟수·기한·취소)를 같이 만든다(E5).
- 넓히기 전에 끝에서 끝까지 얇게 한 번 통과시킨다(E6).
- 값마다 왜 그 값인지 주석으로 남긴다(E18).

## 5. 현재 상태

기록은 이 절 한 장으로 유지한다. 작업 일지를 쌓지 않는다(E16). 지금 유효한 것만 적고, 바뀐 경위는 git 이력에 맡긴다.
표시가 없는 줄은 사용자의 결정이다. 「제안」이 붙은 줄은 에이전트의 안이고 사용자 확인 전이다.

### 진행

- 조립의 설계는 정했고 구현은 아직이다. core 의 개념 패키지 셋은 비어 있고, 파일 계약(`FileStore`)·도구·칸·고리가 없다. 다음은 진입점(고르기).
- 있는 것: 모델 호출 경로(`ModelGateway` → `OpenRouterAdapter`), 모델 대응표와 공급자 프로필, 호출 기록과 본문 저장, 관측(로그·추적), 입구(`model call`·`POST /model/call` 등), cli 셸(말은 아직 받지 않는다). 테이블 셋(`model_alias`·`model_provider`·`model_call`), 마이그레이션 4개.

### 미정

- 첫 도구 2~3개, 첫 예시 조립 하나, 자료 위치(검색 도구에 자료를 넣을 때 필요).
- core 의 계약 가운데 아직 없는 것 — 짧게 사는 값 저장소, 실행 상태 저장소, 파일(`FileStore`), 조립·칸·도구의 계약.
- 구현 세션에서 정한다 — 조립을 적는 형식과 저장 방식, 조립 정의를 LangGraph 로 옮기는 방법(합치기 함수·기록을 남기는 층), 입구의 세부(맞는 조립이 없을 때의 문장·멈춘 실행을 찾는 명령), 한도와 대기 시간의 실제 값.
- 확인 전 — LangGraph 의 `defer`(길이가 다른 길·일부만 선택된 길에서 합류 노드가 한 번만 도는지)와 단계 수 상한(`recursion_limit`)의 기본값은 문서 요약으로만 봤다. 도입할 때 설치 버전에서 작은 그래프로 직접 돌려 본다(E12).

### 기술 구성

- 언어는 Python. DB 는 PostgreSQL 이고 Postgres 가 기준이다 — 남아야 하는 것(칸 결과·채택 여부·기록)은 Postgres 에 둔다.
- Redis 에는 짧게 사는 것만 둔다(고리 중간 값·잠금·취소 신호·캐시). Redis 가 비어도 Postgres 만으로 마지막 확정 칸부터 이어 갈 수 있어야 한다.
- 오브젝트 스토리지는 SeaweedFS. LangGraph 와 pgvector 를 쓴다. 체크포인트는 LangGraph 의 Postgres 체크포인터가 맡는다.
- 웹 프레임워크는 FastAPI 이고 runtime 의 `rest/` 에서만 쓴다.
- 모델은 프로바이더 형태로 공급자를 고른다. 첫 공급자는 OpenRouter 이고 `openai` SDK 로 부른다(주소만 바꿔 쓴다).
- 사용자가 직접 쓰는 것은 기본 구조 코드다. 밑바탕까지 전부 직접 쓰지 않으며, 쓸 수 있는 오픈소스는 적극 검토한다. 지금까지의 코드는 건마다 사용자가 골라 에이전트가 쓰고 사용자가 검토했다.
- 제안 — 로컬은 docker compose, DB 접근은 SQLAlchemy 2 + psycopg 3(동기), 스키마 변경은 Alembic, 설정은 pydantic-settings + `.env`, 데이터 모양은 Pydantic v2. Redis 8 은 AOF(`appendfsync always`), 클라이언트는 redis-py. 스토리지는 S3 API 로만 말하고(boto3), 파일 정보는 Postgres·내용은 SeaweedFS.

### 패키지와 층 (배치의 세부는 6절)

- 패키지는 셋이다. core 는 계약(커널 — 특정 기술을 모르고 의존성은 Pydantic 뿐), infra 는 runtime 이 쓸 기술 구성, runtime 은 core 계약의 구현·조립·진입점(CLI·REST)이다. runtime 이 core 와 infra 를, infra 가 core 를 import 할 수 있다.
- core 는 개념별로 나누고 개념 안에 schemas·service 를 둔다. 개념은 `workflow`(정의)·`run`(실행 상태)·`assist`(AI 칸) 셋으로 시작한다. 서비스는 세션이 아니라 core 의 계약을 생성자로 받는다. 테이블 정의는 infra 의 `tables/` 에 둔다.
- infra 는 접속(`providers/`·`clients/`)과 공통 서비스(`services/`)를 나누고, 조립은 runtime 의 `container.py` 한 곳에서 한다. `crud.py` 는 세션만 받는다.
- 이름: 기술을 감싸는 접속 계층은 기술 이름(저장소 접속 `~Provider`, 외부 API 접속 `~Client`), core 계약을 채우는 구현은 역할 이름(`~Repository`, 공급자 모양과 맞바꾸는 것은 `~Adapter`).
- 입구(cli·rest)에는 번역만 두고, 여러 계약 호출을 엮는 순서는 서비스에 둔다. 두 입구는 같은 서비스를 부른다.
- 실행 모드는 프로필(cli·rest)로 고른다 — `--profile` 이 환경변수 `RUNTIME_PROFILE` 을 이기고, 주지 않으면 cli 다.
- LangGraph 는 runtime 에 둔다. core 는 조립 정의와 실행 상태의 계약만 갖고, runtime 이 조립 정의를 그래프로 바꿔 돌린다.
- 제안 — 이름은 core 를 유지한다(kernel 로 바꾸지 않음).

### 모델 호출

- 요청 `ModelRequest` 는 공급자 중립이고 봉투 규칙(모르는 필드 거부·만든 뒤 불변)을 따른다. 버전 필드가 있고, 공급자 전용 옵션 칸은 없다. `model` 은 논리 이름(예: `fast`)이다.
- 메시지 내용은 텍스트·이미지·파일 조각을 담는다. 문자열을 주면 텍스트 조각 하나로 받는다. 조각의 출처에 저장된 파일(`StoredSource(file_id)`)이 있고, 실제 내용으로 바꾸는 일은 `FileStore` 를 만들 때 붙인다 — 그 전까지 Gateway 가 보내기 전에 막는다.
- 모델이 받지 못하는 종류의 조각은 `check_inputs` 가 오류로 낸다(몰래 빼지 않는다). `media_type` 은 `종류/세부` 모양만 검사한다.
- 응답 `ModelResponse` 의 본문은 요청의 `Message` 를 다시 쓴다. 종료 사유는 stop·length·tool_calls·content_filter·other 로 고정하고 원래 값은 `finish_detail` 에 둔다. 사용량에 비용, 실제 공급사(`upstream_provider`)를 둔다. 실패는 응답이 아니라 예외 `ModelCallFailed` 다.
- 호출 순서(대응표 찾기 → 입력 검사 → 공급자 고르기 → 보내기 → 기록)는 core 의 `ModelGateway` 가 맡는다. 프로바이더는 한 번만 보낸다 — 다시 보내기는 고리의 런타임이 정한다. 스트리밍은 나중.
- 대응표(`ModelCatalog`·`ModelSpec`)와 공급자 프로필(주소·API 키·대기 시간)은 Postgres 에 두고 Redis 에 캐싱한다. 고칠 때 캐시를 같이 지운다. API 키는 공급자 행에 하나, Fernet 으로 암호화해 두고(캐시에도 암호문) 마스터 키만 환경변수에 둔다. core 는 키를 모른다. 대기 시간은 공급자 기본값을 모델별로 덮어쓸 수 있다.
- 관측 — 추적은 OpenTelemetry, 로그는 structlog. 단계는 TRACE·DEBUG·INFO·WARNING·ERROR(INFO 흐름 요약, DEBUG 갈림길과 모양, TRACE 오간 데이터 전체·기본 꺼짐). 비밀은 어느 단계에서도 지운다. core 에는 추적 코드를 넣지 않는다. 로컬 추적 화면은 Jaeger.
- 실패 문장 — 사람이 읽는 문장은 경우를 나눠 사실대로 자세히 쓴다(무엇을 했고 왜인가, 보냈는가·비용이 들었을 수 있는가, 다음에 할 일). 기계가 읽는 이름(kind·로그 이벤트)은 바꾸지 않는다.
- 제안 — 관측·호출 기록·실패 문장·셸·출력 꾸밈의 구현 모양(코드에 있다: `observability/`, `contracts/model/record.py`, `failure_text.py`, `cli/shell.py`, `cli/render.py`).

### 추적 가능성 — 절대 전제

어떤 결과든 무엇을 받아 누가(어느 칸·모델·도구) 어떻게 만들었는지 끝까지 따라갈 수 있어야 한다.

- 모델 호출 한 번마다 `model_call` 에 한 줄을 남기고, 요청·응답 본문은 오브젝트 스토리지에, 그 위치는 기록에 둔다. 그때 쓴 설정의 사본(ModelSpec, 공급자 주소·대기 시간 — 키 제외)을 같이 남긴다. 대응표·프로필에 이력 테이블은 두지 않는다.
- 기록하지 못한 결과는 쓰지 않는다. 요청 본문을 보내기 전에 저장하고, 못 하면 보내지 않는다. 받은 뒤 본문·기록을 못 남기면 그 호출은 실패다.
- 도구 호출도 같은 꼴로 한 줄씩 남긴다(도구 이름·판·입력·출력 본문 위치·결과·걸린 시간·run_id·step_id·attempt). 검색 도구가 찾아 준 결과(조각·출처·점수)는 통째로 남긴다.
- 칸 결과는 주의 표시가 없어도 늘 남긴다(칸 id·입력·출력·조립 판·끝난 방식: 자동·사람 확인·사람이 넣음·건너뜀·실패). 사람의 손(확인·고친 값·버림·되묻기 답 — 누가·언제·무엇을)도 늘 남긴다.
- 고르기 기록에는 사용자의 말, 그때의 후보와 판, 결과와 까닭, 뽑은 시작 입력, 모델 request_id 를 남긴다.
- 조립 정의·AI 칸 틀·도구는 고치면 새 판이 생기고 옛 판은 지우지 않는다. 실행·고르기·호출 기록에 판 번호를 남긴다. 저장 파일(`file_id`)의 내용은 바꾸지 않는다 — 새 내용은 새 id 다.
- 실행 상태는 우리 테이블(`run`·`step_result`)과 LangGraph 체크포인트 둘로 둔다. 사슬은 우리 테이블이고 체크포인트는 이어 가기용이다.
- 모든 기록은 하나로 이어진다: 고르기 → run_id → step_id·attempt → request_id(모델)·tool_call_id(도구) → 본문 위치. 사슬을 한 번에 펼쳐 보는 입구(예: `run trace <run_id>`)를 두고, 남겼다가 아니라 따라가 봤다로 확인한다(E12).
- 남긴 본문은 지금은 지우지 않는다. 사람은 입구에서 이름으로 받는다(cli `--user`, REST 헤더) — 인증이 붙으면 그 값으로 바꾼다.

### 조립 — 설계

- 출발 아이디어는 BPM 이다 — 흐름을 조립하면 에이전트가 그대로 실행한다. BPMN 규격을 따르는 것이 아니라 그 아이디어를 바탕으로 한 빌더다. 무엇을 섞고, 상태를 어떻게 유지하고, 어떻게 이어 갈지는 LangGraph 가 맡는다.
- 개발자가 만든 부품(도구·AI 칸 틀·검증기)을 조립하는 사람(비개발자)이 조합한다. 시스템은 특정 업무를 미리 알지 않는다 — 업무의 모양은 조립 정의(데이터)로 정해진다.
- 낱말 — 「칸」은 조립하는 사람이 보는 단위, 「노드」는 그것을 LangGraph 로 옮긴 단위다. 도구 칸·검증 칸은 노드 하나, AI 칸은 하위 그래프 하나다. 런타임이 끼워 넣는 노드(사람에게 묻기·기록)는 칸이 아니다.
- 칸의 종류는 AI 칸·도구 칸·검증 칸 셋이다. 갈림 전용 칸은 없다.
- AI 칸 — 개발자가 만든 틀 중에서 고른다. 출력 모양은 틀이 정하고, 조립하는 사람은 틀이 열어 둔 빈칸(예: 선택지 목록, 기준 문장)만 채운다. 칸 안에서만 AI 가 허용된 도구를 골라 쓴다.
- 검증 칸 — 개발자가 만든다(코드 검증기가 기본, AI 평가는 판정 기준이 틀에 명시된 경우에만). 대상 칸 바로 뒤에만 놓고, 출력은 통과(예/아니오)와 까닭(글)이다. 통과하지 못하면 까닭을 대상 칸에 돌려 다시 돌린다 — 되돌아가는 길은 런타임이 만든다.
- 주의 — 칸의 종류가 아니라 어느 칸에나 붙이는 표시다. 표시가 붙은 칸이 끝나면 사람에게 결과를 보이고 채택·고침·버림을 받는다. 어느 칸에 붙일지는 조립하는 사람이 정하고 도구가 강제하지 않는다. 표시가 없는 칸은 AI 칸이라도 결과를 그대로 넘긴다.
- 흐름 — 칸을 엣지로 잇고 엣지에 조건을 단다. 조건이 참인 엣지는 모두 간다(하나면 갈림, 여럿이면 동시에 돈다). 조건이 없는 엣지는 늘 간다. 조건은 「칸 X 의 값이 A 다」로 좁게 시작한다(값은 「고르기」 종류, 비교는 코드). 「그 밖의 경우」 엣지가 있는지 저장할 때 검사한다. 되돌아가기는 검증 칸의 다시 쓰기로만 한다. 동시에 도는 구간의 칸에는 처음에는 주의 표시를 붙일 수 없다.
- 합류 — 선택된 길이 모두 끝난 뒤 한 번 돈다. 조건이 거짓이라 가지 않은 칸은 「건너뜀」으로 기록만 남긴다.
- 상태 — 「칸마다 자기 자리」다. 상태는 칸 ID → 그 칸의 출력이고, 칸은 자기 자리에만 쓴다. 내부에 고정된 합치기 함수 하나를 둔다. 파일과 긴 본문은 `file_id` 만 넣는다.
- 입력 — 칸의 입력 하나하나는 앞 칸의 출력 한 칸·조립의 시작 입력·고정값·「이 칸들 중 실행된 것의 값」 가운데 하나를 가리킨다. 입력마다 「없어도 됨」 표시를 둘 수 있다.
- 값의 종류 — 글·숫자·예/아니오·고르기·목록(원소의 종류를 같이 적는다)·파일·묶음. AI 칸의 출력은 이름 붙은 값들의 묶음이고 전부 필수다.
- 도구의 계약 — 개발자가 선언한다: 이름·설명, 입력·출력 모양, 바깥을 바꾸는가, 되돌리기 어려운가, 다시 불러도 같은가, 대기 시간, 판 번호. 선언하지 않은 성질은 위험한 쪽으로 본다. 「바깥」은 우리 시스템 밖이다(메일, 외부 서비스에 쓰기). 모양은 MCP 의 도구 정의와 맞추되, 외부 MCP 도구의 성질 표시는 우리 쪽에서 다시 정한다.
- 자료 읽기는 검색 도구 하나로 통일한다 — 도구 칸(늘 먼저 찾기)이나 AI 칸의 허용 도구(필요할 때 찾기)로 끼운다.
- 부작용 — 바깥을 바꾸는 도구는 칸 하나에 하나만 두고 사람에게 묻는 노드와 분리한다. 부르기 전에 「부르려 한다」는 줄과 호출 ID 를 남기고, 못 남기면 부르지 않는다. 이어 갈 때 결과가 없으면 다시 불러도 같은 도구는 같은 호출 ID 로 다시 부르고, 아닌 도구는 멈추고 사람에게 묻는다. AI 칸의 허용 도구에는 처음에는 바깥을 바꾸지 않는 도구만 넣는다. 받아들인 약점: 동시에 도는 두 길의 부작용은 서로 되돌리지 않고, 도구의 성질은 개발자의 선언을 믿는다.
- 한도 — 틀: AI 칸 안의 모델 ↔ 도구 왕복 횟수(개발자). 조립: 검증의 다시 쓰기 횟수(조립하는 사람), 시간·비용은 시스템 값을 낮추는 것만. 시스템: 모든 실행의 상한(개발자).
- 사람에게 넘기기 — 어느 칸이든 멈추고 사람이 그 칸의 출력을 넣어 이어 갈 수 있다. 한도에 닿거나 검증 횟수를 다 쓰면 실패로 끝내지 않고 멈춰 사람에게 넘긴다.

### 입구

- 시스템의 입구는 미리 만들어 둔 조립 가운데 하나를 고르는 진입점이다. 골랐으면 바로 시작하고, 후보가 헷갈릴 때만 묻는다. 고르기는 AI 칸과 같은 틀로 만들고 후보 목록만 시스템이 채운다.
- 조립마다 시작 입력(이름·종류·필수 여부)을 선언한다. 고르기가 사람의 말에서 값을 채우고, 필수 입력을 못 채우면 시작하지 않고 되묻는다. 파일은 `file_id` 로 받는다.
- cli 모드는 명령 없이 실행하면 셸이 뜬다 — `/` 로 시작하면 명령, 그냥 말은 진입점으로 간다. 셸 세션에 세션 id 를 붙이고 사용자 이름은 `--user` 로 받거나 켤 때 묻는다. 입력은 prompt_toolkit.
- 셸·명령 출력 — 켤 때 GADI 로고와 사용자·세션 id, 프롬프트 `<사용자> › `, 목록은 화면이면 표·파이프면 탭 줄, `/help` 는 묶음별 명령과 설명, 실패 문장은 화면에서 색·들여쓰기, 셸 화면의 로그는 WARNING 위만(`LOG_LEVEL` 을 주면 그 값).

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
agent-builder-runtime/  계약 구현·조립·진입점 — infra 의 값을 core 의 계약에 맞추고, CLI·REST 로 돌린다
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
  cli/                      cli 모드 — 명령 하나 실행하고 끝(run) 또는 셸(shell.py). __init__ 이 묶음 파서를 조립하고 execute() 가 명령 하나를 돌린다
    <묶음>.py               묶음마다 register()·run(). 계약을 부르기만 하고 연결은 닫지 않는다 (model.py · model_catalog.py · model_provider.py)
    render.py               출력의 모양 — 화면이면 표·실패 문장의 색, 파이프면 지금까지의 모양 그대로. 문장은 만들지 않는다
    shell.py                셸 — 명령 없이 실행하면 뜬다. /명령은 cli 그대로, 그냥 말은 진입점으로(아직 없음). prompt_toolkit 은 여기에만
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
.venv\Scripts\python -m agent_builder_runtime --user <이름>   # 셸
.venv\Scripts\python -m agent_builder_runtime --profile rest
docker compose run --rm --build app
```
