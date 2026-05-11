dev:
	python manage.py runserver

lint:
	ruff check .

fmt:
	ruff format .

test:
	python manage.py test gui --verbosity=2

migrate:
	python manage.py migrate

check:
	python manage.py migrate --check

build:
	docker build -t lndg .

# ── Frontend (React/Vite SPA – 6-F) ──────────────────────────────────────────

frontend-install:
	cd frontend && npm install

frontend-build: frontend-install
	cd frontend && npm run build

frontend-dev:
	cd frontend && npm run dev

frontend-lint:
	cd frontend && npm run lint --if-present
