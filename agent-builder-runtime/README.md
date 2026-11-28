# agent-builder-runtime

에이전트 빌더의 계약 구현·조립·실행 진입점. infra 의 값을 꺼내 core 의 계약에 맞추고, 그것을 묶어 돌린다.
실행 모드는 프로필로 고른다 — `cli`(기본) 또는 `rest`(FastAPI 서버).

진입점은 얇게 둔다. 기능은 서비스 함수(계약)에 있고, 진입점은 그것을 부르기만 한다.

| 모듈 | 내용 |
|---|---|
| `repositories/` | core 계약의 구현. `ModelCatalogRepository` — 테이블 `model_alias`(Postgres)를 기준으로 Redis 에 5분 캐싱하고, 고칠 때 커밋 뒤 캐시를 지운다. SQLAlchemy 를 직접 쓰지 않고 infra 의 `DbService`·`crud`·`RedisService` 만 쓴다 |
| `repositories/provider_profile.py` | `ProviderProfileRepository` — 공급자 프로필(주소·API 키·기본 대기 시간·켜짐). Postgres 기준, Redis 5분 캐시. 키는 DB·캐시 어디에도 평문으로 두지 않고, 보낼 때만 푼다 |
| `model_adapters/connections.py` | `ProviderConnections` — 프로필로 연결점을 만들고, 프로필이 바뀌면 옛 연결을 닫고 새로 만든다 |
| `model_adapters/openrouter/` | core 의 `ModelProvider` 구현. 흐름은 `provider.py`, 요청 바꾸기 `request.py`, 응답 바꾸기 `response.py`, 실패 해석 `errors.py`. `OpenRouterAdapter` — `ModelRequest` 를 OpenRouter 본문으로, 응답 본문을 `ModelResponse` 로 바꾼다. 연결점의 오류(`OpenRouterCallError`)와 HTTP 200 본문 속 오류를 OpenRouter 문서 기준 표(`kind_for_status`)로 `ModelCallFailed` 에 맞춘다. 파일을 주소로 보내는 것은 OpenRouter 문서에 없어 거절 |
| `container.py` | 조립 — `get_db()`, `get_redis()`, `get_object_storage()`, `get_model_catalog()`, `get_provider_profiles()`, `get_provider_connections()`, `get_model_gateway()` 가 한 번씩 만들어 준다. 공급자 키는 보낼 때 프로필에서 읽고, 풀려면 `SECRET_ENCRYPTION_KEY` 가 있어야 한다. 끝낼 때 `close_all()` |
| `settings.py` | 실행 설정 — `RUNTIME_PROFILE`(cli·rest, 기본 cli), `REST_HOST`·`REST_PORT`(기본 127.0.0.1:8000) |
| `__main__.py` | 입구 — 프로필로 모드만 고른다. `--profile` 인자가 환경변수 `RUNTIME_PROFILE` 을 이긴다 |
| `cli/` | cli 모드. 묶음마다 모듈 하나(`register()`·`run()`) |
| `rest/` | rest 모드. FastAPI 앱(`create_app()`)과 묶음마다 라우터. 웹 프레임워크는 여기에만 둔다 |

## 실행

이 폴더에서 실행한다. 저장소 루트의 `.env` 를 읽고, 로컬 Postgres·Redis 가 떠 있어야 한다(`docker compose up -d --wait`).

### cli 모드 (기본)

```powershell
..\.venv\Scripts\python -m agent_builder_runtime --help
..\.venv\Scripts\python -m agent_builder_runtime model-catalog list
..\.venv\Scripts\python -m agent_builder_runtime model-catalog set fast --provider openrouter --model <공급자 쪽 이름> --inputs text,image
..\.venv\Scripts\python -m agent_builder_runtime model-catalog show fast
..\.venv\Scripts\python -m agent_builder_runtime model-catalog disable fast
..\.venv\Scripts\python -m agent_builder_runtime model-catalog delete fast
```

`--inputs` 는 그 모델이 받는 조각(text·image·file)이다. 기본은 `text` 다. 종료 코드는 0 성공, 1 없는 이름, 2 입력값 오류.

### 모델 부르기

```powershell
..\.venv\Scripts\python -m agent_builder_runtime model call fast "안녕" --max-tokens 50
```

답은 stdout 에 찍는다. 실제 모델·토큰·비용·걸린 시간은 stderr 의 INFO 로그 `model.call.done` 에 있다. 종료 코드는 0 성공, 1 없거나 꺼진 모델·공급자 또는 빠진 설정(마스터 키·API 키), 2 입력값 오류, 3 호출 실패(공급자 구현의 결함 포함), 4 기록을 남기지 못해 결과를 쓰지 않음. 실패 문장은 `failure_text.py` 가 만들고 REST 본문에도 같은 문장(`message`·`facts`·`next`)이 들어간다. REST 는 `POST /model/call`.

호출 기록은 `model calls --limit 20`(최근 것부터)·`model call-show <request_id> [--body]` 로 본다. 본문은 오브젝트 스토리지 `model_call/<request_id>/` 아래에 있다.

### 공급자 프로필 (키는 어디에도 찍히지 않는다)

```powershell
..\.venv\Scripts\python -m agent_builder_runtime model-provider set openrouter --base-url https://openrouter.ai/api/v1 --timeout 60
..\.venv\Scripts\python -m agent_builder_runtime model-provider set-key openrouter
..\.venv\Scripts\python -m agent_builder_runtime model-provider list
```

키를 넣고 풀려면 `.env` 에 마스터 키 `SECRET_ENCRYPTION_KEY` 가 있어야 한다. 모델별 대기 시간은 `..\.venv\Scripts\python -m agent_builder_runtime model-catalog set <이름> ... --timeout 120` 처럼 덮어쓴다.

### rest 모드

```powershell
..\.venv\Scripts\python -m agent_builder_runtime --profile rest
```

`http://127.0.0.1:8000/docs` 에서 경로를 보고 시험할 수 있다. 인증이 아직 없으므로 기본 주소는 이 PC 에서만 붙는다.

| 경로 | 하는 일 |
|---|---|
| `GET /health` | 서버가 떠 있는지 |
| `GET /model-catalog` | 전부 (이름 순) |
| `GET /model-catalog/{name}` | 한 줄 — 없으면 404 |
| `PUT /model-catalog/{name}` | 넣거나 바꾸기. 본문은 `ModelSpec`, 이름은 경로와 같아야 한다(다르면 400) |
| `PATCH /model-catalog/{name}` | 켜고 끄기. 본문 `{"enabled": true}` — 없으면 404 |
| `DELETE /model-catalog/{name}` | 지우기 — 없으면 404 |
| `POST /model/call` | 모델 부르기. 본문은 `ModelRequest` |
| `GET /model/calls?limit=20` | 호출 기록, 최근 것부터 (limit 1~500) |
| `GET /model/calls/{request_id}` | 호출 기록 한 줄 — 없으면 404 |
| `GET /model/calls/{request_id}/bodies/{name}` | 남긴 본문 하나 (request·sending·received·response) — 없으면 404 |
| `GET /model-provider`, `GET /model-provider/{name}` | 공급자 프로필 (키는 `has_api_key` 로 있음·없음만) |
| `PUT /model-provider/{name}` | 주소·대기 시간 넣거나 바꾸기 |
| `PUT /model-provider/{name}/api-key` | API 키 넣기 — 응답에 키 없음(204) |
| `PATCH`·`DELETE /model-provider/{name}` | 켜고 끄기, 지우기 |

### 로그와 추적

입구(`__main__`·`create_app`)가 맨 먼저 관측을 켠다. 명령 하나·REST 요청 하나가 추적 하나의 뿌리 span 이고, 그 아래로 `ModelGateway.complete` → `ModelCatalogRepository.get` → `OpenRouterAdapter.complete` → `ProviderConnections.get` → `ProviderProfileRepository.get` 와 SQL·Redis·HTTP 호출이 붙는다.

```powershell
$env:LOG_LEVEL = "TRACE"; ..\.venv\Scripts\python -m agent_builder_runtime model call fast "안녕" --max-tokens 50
```

| 단계 | 남는 것 |
|---|---|
| INFO | `model.call.done` — 모델·실제 모델·종료 사유·토큰·비용·걸린 시간·request_id. 실패는 WARNING `model.call.failed`·`model.call.rejected` |
| DEBUG | 캐시 적중(`model_catalog.cache`·`provider_profile.cache`), 연결 열기(`provider.connection.open`), 고른 대기 시간(`openrouter.send`) |
| TRACE | 요청·응답 전체(`model.request`·`model.response`), 공급자에 보낸 본문과 받은 본문(`openrouter.payload`·`openrouter.body`) |

span 에는 숫자와 모양만 있고, 보낸 문장은 TRACE 로그에만 있다. 화면은 infra README 의 「로그와 추적」을 본다.

컨테이너 안에서(저장소 루트에서): `docker compose run --rm app python -m agent_builder_runtime model-catalog list`

## 테스트

```powershell
..\.venv\Scripts\python -m pytest
```
