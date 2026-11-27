# g-agent-builder

에이전트 빌더 — 업무 흐름(workflow)의 특정 단계에서 AI 의 보조를 받도록, 사용자가 자기 에이전트를 조립한다.
작업 규칙과 결정은 [AGENTS.md](AGENTS.md), 패키지별 내용은 각 README 를 본다.

| 패키지 | 맡는 것 |
|---|---|
| [agent-builder-core](agent-builder-core/README.md) | 계약 — 특정 기술을 모른다 |
| [agent-builder-infra](agent-builder-infra/README.md) | 기술 구성 — Postgres·Redis·SeaweedFS 접속, 테이블, 로그·추적 |
| [agent-builder-runtime](agent-builder-runtime/README.md) | 계약 구현·조립·입구(cli·rest) |

## 실행 방법

명령은 모두 저장소 루트에서 PowerShell 로 실행한다.

### 1. 처음 한 번 — 설치

필요한 것: Python 3.13, Docker Desktop.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -e ".\agent-builder-core[dev]" -e ".\agent-builder-infra[dev]" -e ".\agent-builder-runtime[dev]"
Copy-Item .env.example .env
```

`.env` 에 마스터 키 `SECRET_ENCRYPTION_KEY` 를 넣는다. 공급자 API 키를 DB 에 암호문으로 두는 데 쓴다 — 잃으면 저장한 키를 풀 수 없다.

```powershell
.venv\Scripts\python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. 띄우기 — 저장소와 스키마

Postgres·Redis·SeaweedFS 를 띄우고 테이블을 만든다.

```powershell
docker compose up -d --wait
cd agent-builder-infra; ..\.venv\Scripts\alembic upgrade head; cd ..
```

### 3. 처음 한 번 — 공급자와 모델 등록

공급자 프로필(주소·기본 대기 시간)을 넣고 API 키를 넣는다. 키는 화면에 보이지 않게 묻고, 암호화해 저장한다.

```powershell
.venv\Scripts\python -m agent_builder_runtime model-provider set openrouter --base-url https://openrouter.ai/api/v1 --timeout 60
.venv\Scripts\python -m agent_builder_runtime model-provider set-key openrouter
```

모델 논리 이름(`fast` 등)을 공급자 쪽 모델에 잇는다.

```powershell
.venv\Scripts\python -m agent_builder_runtime model-catalog set fast --provider openrouter --model openai/gpt-4o-mini
.venv\Scripts\python -m agent_builder_runtime model-catalog list
```

`--inputs text,image,file` 로 받는 내용 종류를, `--timeout 120` 으로 이 모델만의 대기 시간을 정한다.

### 4. 모델 부르기 — cli 모드 (기본)

```powershell
.venv\Scripts\python -m agent_builder_runtime model call fast "한 단어로 인사해" --max-tokens 20
```

답은 stdout 에, 로그는 stderr 에 나온다. INFO 로그 `model.call.done` 한 줄에 실제 모델·토큰·비용·걸린 시간이 있다.

| 종료 코드 | 뜻 |
|---|---|
| 0 | 성공 |
| 1 | 없거나 꺼진 모델·공급자 |
| 2 | 입력값 오류 (예: `--max-tokens 0`) |
| 3 | 호출 실패 (시간 초과·인증·한도 등) |

돈이 들지 않는 실패 확인:

```powershell
.venv\Scripts\python -m agent_builder_runtime model call nosuch "hi" --max-tokens 10; $LASTEXITCODE
```

### 호출 기록 보기

공급자에 보낸 호출은 성공이든 실패든 한 줄씩 Postgres(`model_call`)에 남는다. 위의 `nosuch` 처럼 보내기 전에 막힌 것은 남지 않는다. 보낸 문장과 받은 답은 남기지 않는다.

```powershell
.venv\Scripts\python -m agent_builder_runtime model calls --limit 20
.venv\Scripts\python -m agent_builder_runtime model call-show <request_id>
```

`calls` 는 최근 것부터 한 줄씩 — 시각, request_id, 모델, 실제 모델, 결과(종료 사유 또는 `실패:종류`), 입력/출력 토큰, 비용, 걸린 시간. `call-show` 는 실제 공급사(`upstream_provider`)·실패 내용까지 전부 보인다. 기록에 실패해도 답은 그대로 받고, ERROR 로그 `model.call.record_failed` 에 빠진 줄의 숫자가 남는다.

### 5. 모델 부르기 — rest 모드

```powershell
.venv\Scripts\python -m agent_builder_runtime --profile rest
```

http://127.0.0.1:8000/docs 에서 경로를 보고 시험할 수 있다. 다른 창에서 부르려면:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/model/call -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes('{"model":"fast","messages":[{"role":"user","content":"안녕"}],"params":{"max_output_tokens":20}}'))
```

기록은 `GET /model/calls?limit=20`·`GET /model/calls/{request_id}` 로 본다. 실패는 404(없는 모델)·409(꺼진 모델)·422(요청 모양·받지 않는 내용)·503(공급자 없음)·502(호출 실패, 본문에 kind·retryable)로 돌려준다. 인증이 아직 없어 이 PC 에서만 붙는다.

### 6. 로그 보기

`.env` 에 적거나, 그 창에서만 `$env:` 로 바꾼다(창을 닫으면 사라진다).

| 설정 | 값 | 남는 것 |
|---|---|---|
| `LOG_LEVEL` | `INFO` (기본) | 호출 하나의 요약 `model.call.done`, 실패는 WARNING·ERROR |
| | `DEBUG` | + 캐시 적중, 연결 열기, 고른 대기 시간 |
| | `TRACE` | + 요청·응답 전체, 공급자에 보낸 본문과 받은 본문 — 보낸 문장이 그대로 남으니 필요할 때만 |
| `LOG_FORMAT` | `console` (기본) · `json` | 사람이 읽는 줄 · 수집기가 읽는 줄 |

```powershell
$env:LOG_LEVEL = "TRACE"
.venv\Scripts\python -m agent_builder_runtime model call fast "한 단어로 인사해" --max-tokens 20
Remove-Item Env:LOG_LEVEL
```

API 키·Authorization·암호문 같은 값은 어느 단계에서도 `[REDACTED]` 로 지운다. span 안에서 남긴 줄에는 `trace_id` 가 붙어, 추적 화면의 그 호출을 찾아갈 수 있다.

### 7. 추적 보기 — Jaeger

Jaeger 는 선택 서비스라 따로 띄운다.

```powershell
docker compose --profile observability up -d --wait jaeger
$env:OTEL_EXPORTER_OTLP_ENDPOINT = "http://127.0.0.1:4318"
.venv\Scripts\python -m agent_builder_runtime model call fast "한 단어로 인사해" --max-tokens 20
```

http://127.0.0.1:16686 → Service `agent-builder` → Find Traces. 호출 하나가 이렇게 보인다:

```
cli model call                         (rest 면 POST /model/call)
└ ModelGateway.complete                모델·request_id·토큰·비용·종료 사유
  ├ ModelCatalogRepository.get         → Redis GET (처음엔 + SQL SELECT + Redis SET)
  └ OpenRouterAdapter.complete
    ├ ProviderConnections.get
    │ ├ ProviderProfileRepository.get  → Redis GET (처음엔 + SQL)
    │ └ ProviderProfileRepository.api_key
    └ POST https://openrouter.ai/api/v1/chat/completions
```

span 에는 숫자와 모양만 있다 — 보낸 문장, SQL·Redis 에 넘긴 값, HTTP 헤더는 없다. 계속 보내려면 `.env` 에 `OTEL_EXPORTER_OTLP_ENDPOINT` 를 적는다. Jaeger 는 받은 추적을 메모리에만 두어, 끄면 사라진다.

### 8. 확인과 정리

```powershell
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
cd agent-builder-core; ..\.venv\Scripts\python -m pytest -q; cd ..
cd agent-builder-infra; ..\.venv\Scripts\python -m pytest -q; cd ..
cd agent-builder-runtime; ..\.venv\Scripts\python -m pytest -q; cd ..
```

infra·runtime 테스트는 2번의 저장소가 떠 있어야 한다. 모델을 실제로 부르는 테스트는 없다.

```powershell
docker compose --profile observability stop jaeger
docker compose down
```

데이터까지 지우려면 `docker compose down -v` — 등록한 공급자·모델도 사라진다.

### 컨테이너 안에서

```powershell
docker compose run --rm --build app
docker compose run --rm app python -m agent_builder_runtime model-catalog list
```

컨테이너는 추적을 보내지 않는다(`.env` 의 127.0.0.1 주소가 컨테이너 안에서는 맞지 않아서).
