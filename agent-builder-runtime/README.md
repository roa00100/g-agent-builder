# agent-builder-runtime

에이전트 빌더의 실행 진입점. core 의 계약과 infra 의 구성을 묶어 돌린다.
호출 방법은 REST 또는 CLI 다. 지금은 CLI 만 있고, REST 는 나중에 이 패키지의 `rest/` 에 둔다.

진입점은 얇게 둔다. 기능은 서비스 함수에 있고, 진입점은 그것을 부르기만 한다.

| 모듈 | 내용 |
|---|---|
| `container.py` | 조립 — `get_db()`, `get_redis()`, `get_object_storage()`, `get_model_alias_service()` 가 infra 의 프로바이더와 서비스를 한 번씩 만들어 준다. 끝낼 때 `close_all()` |
| `__main__.py` | 명령줄 — `python -m agent_builder_runtime <묶음> <명령>` |
| `cli/` | 묶음마다 모듈 하나. `register()` 로 달고 `run()` 으로 실행한다 |

```python
from agent_builder_runtime.container import get_db

rows = get_db().fetch_all("select ...")
```

## 명령줄

이 폴더에서 실행한다. 저장소 루트의 `.env` 를 읽고, 로컬 Postgres·Redis 가 떠 있어야 한다(`docker compose up -d --wait`).

```powershell
..\.venv\Scripts\python -m agent_builder_runtime --help
..\.venv\Scripts\python -m agent_builder_runtime model-alias list
..\.venv\Scripts\python -m agent_builder_runtime model-alias set fast --provider openrouter --model <공급자 쪽 이름> --inputs text,image
..\.venv\Scripts\python -m agent_builder_runtime model-alias show fast
..\.venv\Scripts\python -m agent_builder_runtime model-alias disable fast
..\.venv\Scripts\python -m agent_builder_runtime model-alias delete fast
```

`--inputs` 는 그 모델이 받는 조각(text·image·file)이다. 기본은 `text` 다. 종료 코드는 0 성공, 1 없는 이름, 2 입력값 오류.

컨테이너 안에서(저장소 루트에서): `docker compose run --rm app python -m agent_builder_runtime model-alias list`

## 테스트

```powershell
..\.venv\Scripts\python -m pytest
```
