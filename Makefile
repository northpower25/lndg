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
