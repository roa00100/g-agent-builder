# agent-builder-runtime

에이전트 빌더의 계약 구현·조립·실행 진입점. infra 의 값을 꺼내 core 의 계약에 맞추고, 그것을 묶어 돌린다.
실행 모드는 프로필로 고른다 — `cli`(기본) 또는 `rest`(FastAPI 서버).

진입점은 얇게 둔다. 기능은 서비스 함수(계약)에 있고, 진입점은 그것을 부르기만 한다.

| 모듈 | 내용 |
|---|---|
| `repositories/` | core 계약의 구현. `ModelCatalogRepository` — 테이블 `model_alias`(Postgres)를 기준으로 Redis 에 5분 캐싱하고, 고칠 때 커밋 뒤 캐시를 지운다. SQLAlchemy 를 직접 쓰지 않고 infra 의 `DbService`·`crud`·`RedisService` 만 쓴다 |
| `container.py` | 조립 — `get_db()`, `get_redis()`, `get_object_storage()`, `get_model_catalog()` 가 한 번씩 만들어 준다. 끝낼 때 `close_all()` |
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

컨테이너 안에서(저장소 루트에서): `docker compose run --rm app python -m agent_builder_runtime model-catalog list`

## 테스트

```powershell
..\.venv\Scripts\python -m pytest
```
