.PHONY: install run test lint format docker

install:
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install pytest pytest-asyncio ruff

run:
	.venv/bin/python -m app

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/python -m ruff check .
	.venv/bin/python -m ruff format --check .

format:
	.venv/bin/python -m ruff format .

docker:
	docker build -t tg-lead-bot .
	docker run --rm --env-file .env -p 8080:8080 tg-lead-bot
