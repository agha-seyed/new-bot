.PHONY: setup test lint run compile-deps clean

setup:
	pip install pip-tools
	pip-compile requirements.in
	pip-compile dev-requirements.in
	pip install -r requirements.txt
	pip install -r dev-requirements.txt
	pre-commit install

compile-deps:
	pip-compile requirements.in
	pip-compile dev-requirements.in

test:
	pytest --cov=smartstudentbot tests/

lint:
	ruff check .
	black --check .
	isort --check-only .
	mypy smartstudentbot/

run:
	uvicorn smartstudentbot.main:app --reload

clean:
	rm -rf __pycache__ .pytest_cache .coverage
