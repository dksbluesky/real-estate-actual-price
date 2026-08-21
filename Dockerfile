FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY web.py ./

RUN pip install --no-cache-dir . \
    && python scripts/sync_data.py --current \
      --city 臺北市 --city 新北市 --city 桃園市 \
      --city 臺中市 --city 臺南市 --city 高雄市

CMD gunicorn web:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120