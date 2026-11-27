# agent-builder-infra

에이전트 빌더의 구현 — `agent-builder-core` 의 계약을 PostgreSQL·Redis·OpenRouter 로 채운다.
infra 가 core 를 import 하고, 반대는 없다.

| 모듈 | 내용 |
|---|---|
| `settings.py` | 환경변수·`.env` 에서 읽는 설정. `.env` 는 실행한 폴더에서 위로 올라가며 찾는다(저장소 루트의 것). Postgres 는 `POSTGRES_USER`·`PASSWORD`·`HOST`·`PORT`·`DB` 를, Redis 는 `REDIS_HOST`·`PORT`·`DB`·`PASSWORD` 를 나눠 읽고 `database_url`·`redis_url` 로 조립한다 — docker compose 가 쓰는 값과 같은 것을 쓴다. `REDIS_PASSWORD` 를 비우면 비밀번호 없이, 적으면 compose 의 Redis 와 앱이 둘 다 그 비밀번호를 쓴다 |
| `providers/` | `PostgresProvider`, `RedisProvider` — 연결 풀·클라이언트를 만들고 `ping()`·`close()` 한다 |
| `services/db.py` | `DbService` — `session_scope()`(트랜잭션), `cursor()`(psycopg 커서), `fetch_all`·`fetch_one`·`fetch_value`·`execute` |
| `services/redis.py` | `RedisService` — 문자열·JSON·Pydantic 모델·해시·카운터·키. 값을 쓰는 메서드는 `ttl` 이 필수다 |
| `orm.py` | 테이블 모델의 부모 `Base` |
| `crud.py` | ORM 모델 공통 `find_by_id`·`find_all`·`count`·`create`·`update`·`delete`. 세션은 인자로 받는다 |
| `container.py` | `get_db()`, `get_redis()` — 프로바이더와 서비스를 한 번씩 만들어 준다. 끝낼 때 `close_all()` |

```python
from agent_builder_infra.container import get_db, get_redis

rows = get_db().fetch_all("select ...")
```

## 로컬 DB·Redis

저장소 루트에서 띄운다. 설치는 루트 `AGENTS.md` 6절을 본다.

```powershell
docker compose up -d --wait
```

Redis 는 AOF 로 디스크에 써서 재시작해도 데이터가 남는다. 끌 때는 `docker compose down`, 데이터까지 지우려면 `docker compose down -v`.

## 마이그레이션과 테스트

이 폴더에서 실행한다. 테스트는 실제 PostgreSQL·Redis 에 붙는다.

```powershell
..\.venv\Scripts\alembic upgrade head
..\.venv\Scripts\python -m pytest
```

`alembic.ini` 에는 한글을 쓰지 않는다 — Windows 에서 alembic 이 이 파일을 cp949 로 읽어 모든 명령이 실패한다.

## 컨테이너

저장소 루트에서 실행한다. 빌드 맥락이 루트라 core 와 infra 가 같이 들어간다.

```powershell
docker compose run --rm --build app
```

실행 진입점이 아직 없어 컨테이너의 기본 명령은 infra 테스트다.
