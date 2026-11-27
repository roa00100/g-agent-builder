# agent-builder-infra

에이전트 빌더의 기술 구성 — PostgreSQL·Redis·SeaweedFS(오브젝트 스토리지) 접속, 공통 서비스, 테이블 정의.
core 의 정의(예: `InputKind`)는 가져다 쓴다. infra 의 값을 계약에 맞추는 일(Repository)과 조립은 runtime 이 한다.

| 모듈 | 내용 |
|---|---|
| `settings.py` | 환경변수·`.env` 에서 읽는 설정. `.env` 는 실행한 폴더에서 위로 올라가며 찾는다(저장소 루트의 것). 비밀 값 암호화의 마스터 키 `SECRET_ENCRYPTION_KEY`. Postgres 는 `POSTGRES_USER`·`PASSWORD`·`HOST`·`PORT`·`DB` 를, Redis 는 `REDIS_HOST`·`PORT`·`DB`·`PASSWORD` 를 나눠 읽고 `database_url`·`redis_url` 로 조립한다 — docker compose 가 쓰는 값과 같은 것을 쓴다. `REDIS_PASSWORD` 를 비우면 비밀번호 없이, 적으면 compose 의 Redis 와 앱이 둘 다 그 비밀번호를 쓴다 |
| `providers/` | `PostgresProvider`, `RedisProvider`, `ObjectStorageProvider` — 연결 풀·클라이언트를 만들고 `ping()`·`close()` 한다 |
| `services/db.py` | `DbService` — `session_scope()`(트랜잭션), `cursor()`(psycopg 커서), `fetch_all`·`fetch_one`·`fetch_value`·`execute` |
| `services/redis.py` | `RedisService` — 문자열·JSON·Pydantic 모델·해시·카운터·키. 값을 쓰는 메서드는 `ttl` 이 필수다 |
| `services/object_storage.py` | `ObjectStorageService` — 버킷 하나 안에서 키로 `put_bytes`·`get_bytes`·`head`·`exists`·`delete`·`list_keys`. 없는 키는 `None`, 그 밖의 실패는 예외. S3 API(boto3)로만 말해 SeaweedFS 를 다른 S3 호환 스토리지로 바꿔도 그대로다 |
| `providers/openrouter.py` | `OpenRouterProvider` — OpenRouter 연결점. openai SDK 클라이언트를 OpenRouter 주소로 두고, `chat(payload)` 로 한 번 보내 응답 본문(dict)을 받는다. SDK 오류는 `OpenRouterCallError`(timeout·connection·http, 상태 코드·본문)로 넘긴다. 실패를 무엇으로 볼지는 runtime 이 정한다. SDK 의 자동 재시도는 끈다 |
| `services/cipher.py` | `FernetCipher` — 비밀 값(공급자 API 키 등)을 마스터 키(`SECRET_ENCRYPTION_KEY`)로 암호화·복호화. 키가 다르거나 암호문이 바뀌면 `CipherError` |
| `orm.py` | 테이블 모델의 부모 `Base` |
| `crud.py` | ORM 모델 공통 `find_by_id`·`find_all`·`count`·`create`·`update`·`delete`. 세션은 인자로 받는다 |
| `tables/model_provider.py` | `ModelProviderRow` — 공급자 프로필. 주소, API 키 암호문(`api_key_enc`, 평문 없음), 기본 대기 시간, 켜짐 |
| `tables/` | 테이블 정의(SQLAlchemy ORM 매핑 — 쿼리 매핑과 마이그레이션 생성의 기준, 실제 DDL 은 `migrations/`). `model_alias.py` 의 `ModelAliasRow` — 모델 논리 이름의 대응표. 검사 제약으로 `input_kinds` 를 text·image·file 로 막는다(core 의 `InputKind` 에서 만든다). 이 테이블을 core 의 계약에 맞추는 Repository 는 runtime 에 있다 |

프로바이더와 서비스를 조립하는 `container.py` 는 runtime 에 있다. infra 의 테스트는 프로바이더를 직접 만들어 서비스에 넣는다.

## 로컬 DB·Redis·오브젝트 스토리지

저장소 루트에서 띄운다. 설치는 루트 `AGENTS.md` 6절을 본다.

```powershell
docker compose up -d --wait
```

Redis 는 AOF 로 디스크에 써서 재시작해도 데이터가 남는다. SeaweedFS 는 `STORAGE_ACCESS_KEY`·`STORAGE_SECRET_KEY` 로 인증을 요구하고, 시작할 때 `STORAGE_BUCKET` 버킷을 만든다. 없는 버킷에 쓰면 새로 만들지 않고 오류를 낸다. 끌 때는 `docker compose down`, 데이터까지 지우려면 `docker compose down -v`.

## 마이그레이션과 테스트

이 폴더에서 실행한다. 테스트는 실제 PostgreSQL·Redis·SeaweedFS 에 붙는다.

```powershell
..\.venv\Scripts\alembic upgrade head
..\.venv\Scripts\python -m pytest
```

`alembic.ini` 에는 한글을 쓰지 않는다 — Windows 에서 alembic 이 이 파일을 cp949 로 읽어 모든 명령이 실패한다.

## 모델 대응표 고치기

명령줄 진입점은 `agent-builder-runtime` 에 있다. 그쪽 README 를 본다.

## 컨테이너

저장소 루트에서 실행한다. 빌드 맥락이 루트라 core 와 infra 가 같이 들어간다.

```powershell
docker compose run --rm --build app
```

컨테이너의 기본 명령은 infra·runtime 테스트다.
