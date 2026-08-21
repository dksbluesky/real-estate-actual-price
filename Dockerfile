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
      --season 112S3 --season 112S4 --season 113S1 --season 113S2 \
      --season 113S3 --season 113S4 --season 114S1 --season 114S2 \
      --season 114S3 --season 114S4 --season 115S1 --season 115S2 \
      --city 臺北市 --city 新北市 --city 桃園市 \
      --city 臺中市 --city 臺南市 --city 高雄市

CMD gunicorn web:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120