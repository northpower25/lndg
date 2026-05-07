lint:
	ruff check .

test:
	python manage.py test gui --verbosity=2

migrate:
	python manage.py migrate

check:
	python manage.py migrate --check
