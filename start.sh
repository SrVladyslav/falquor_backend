#!/bin/bash

python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

# Init superuser 
python manage.py init_superuser

# populate groups
# python manage.py populate_groups --delete

# --reload  only in development
if [ "$ENVIRONMENT" = "dev" ]; then
    exec gunicorn --reload --workers 3 --bind 0.0.0.0:8000 core.wsgi:application
else
    exec gunicorn --workers 3 --bind 0.0.0.0:8000 core.wsgi:application
fi