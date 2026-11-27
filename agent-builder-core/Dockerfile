# pyproject.toml 의 requires-python 과 같은 버전을 쓴다.
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

COPY --chown=app:app . .
RUN pip install -e ".[dev]"

# 아직 실행 진입점이 없다. 진입점이 생기면 이 줄을 바꾼다.
CMD ["python", "-m", "pytest"]
