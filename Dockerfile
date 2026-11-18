FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY app ./app

RUN useradd --create-home --uid 10001 bot \
    && mkdir -p /app/data /app/exports \
    && chown -R bot:bot /app

USER bot

EXPOSE 8080

CMD ["python", "-m", "app"]
