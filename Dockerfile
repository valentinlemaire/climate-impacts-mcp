FROM python:3.11-slim AS builder

RUN pip install --no-cache-dir poetry==2.1.1

WORKDIR /app
COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

COPY src/ src/

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src src/

ENV PORT=8080

CMD ["climate-impacts-mcp"]
