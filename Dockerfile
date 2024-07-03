FROM python:3.11-slim
LABEL maintainer="digitaldms"

ENV PYTHONUNBUFFERED=1

COPY ./requirements.txt /requirements.txt
COPY ./DigitalDMS /DigitalDMS
COPY ./scripts /scripts

WORKDIR /DigitalDMS
EXPOSE 8000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-vie \
    ghostscript \
    && python -m venv /py \
    && /py/bin/pip install --upgrade pip \
    && /py/bin/pip install -r /requirements.txt \
    # Clean up
    && apt-get remove -y build-essential libpq-dev \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --no-create-home digitaldms_user \
    && mkdir -p /vol/web/static \
    && mkdir -p /vol/web/media \
    && chown -R digitaldms_user:digitaldms_user /vol \
    && chown -R digitaldms_user:digitaldms_user /DigitalDMS \
    && chown -R digitaldms_user:digitaldms_user /py \
    && chmod -R 755 /vol \
    && chmod -R +x /scripts 
ENV PATH="/py/bin:$PATH"

USER digitaldms_user    

CMD ["sh", "-c", "set -e \
    && ls -la /vol/ \
    && ls -la /vol/web \
    && whoami \
    && python manage.py makemigrations \
    && python manage.py migrate \
    && uwsgi --socket :9000 --workers 4 --master --enable-threads --module DigitalDMS.wsgi"]
