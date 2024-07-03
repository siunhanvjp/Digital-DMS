#!/bin/sh

until cd /app/DigitalDMS
do
    echo "Waiting for server volume..."
done

# run a worker :)
celery -A DigitalDMS worker --loglevel=info --concurrency 1 -E
