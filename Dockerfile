FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.12.13

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY config ./config
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "--no-sync", "threatalert"]
