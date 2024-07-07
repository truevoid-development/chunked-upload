FROM python:3

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1
ENV POETRY_CACHE_DIR=/app/cache
ENV PIP_CACHE_DIR=/app/cache

WORKDIR /app

RUN pip3 install --cache-dir $PIP_CACHE_DIR poetry

COPY pyproject.toml .
COPY poetry.lock .
COPY README.md .

RUN poetry install --only main

COPY chunked_upload chunked_upload/

CMD ["gunicorn", "chunked_upload.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
