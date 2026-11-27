# 빌드 맥락은 저장소 루트다 — core 와 infra 를 같이 넣는다.
#   docker build -f agent-builder-infra/Dockerfile .
# 루트 .python-version 과 같은 버전을 쓴다.
FROM python:3.13-slim

# .pyc 를 남기지 않고, 로그가 버퍼에 묶이지 않게 한다.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# root 로 돌지 않는다.
RUN useradd --create-home app
WORKDIR /app
RUN chown app:app /app
USER app

# 가상환경을 /app 밖에 둔다 — 소스를 /app 에 마운트해도 가려지지 않는다.
ENV VIRTUAL_ENV=/home/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python -m venv "$VIRTUAL_ENV"

COPY --chown=app:app agent-builder-core ./agent-builder-core
COPY --chown=app:app agent-builder-infra ./agent-builder-infra
COPY --chown=app:app agent-builder-runtime ./agent-builder-runtime
RUN pip install -e "./agent-builder-core[dev]" -e "./agent-builder-infra[dev]" \
    -e "./agent-builder-runtime[dev]"

# 기본 명령은 DB·Redis·스토리지가 있어야 하는 infra·runtime 테스트다.
# core 테스트는 DB 없이 돌므로 PC·CI 에서 돈다.
# 명령줄을 돌리려면: docker compose run --rm app python -m agent_builder_runtime --help
WORKDIR /app
CMD ["sh", "-c", "cd agent-builder-infra && python -m pytest && cd ../agent-builder-runtime && python -m pytest"]
