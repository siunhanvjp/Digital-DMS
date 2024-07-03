FROM python:3.11-slim
# LABEL maintainer="digitaldms"

ENV PYTHONUNBUFFERED=1


EXPOSE 8000

# Install dependencies and Tesseract OCR
RUN apt-get update && apt-get install -y \
    python3-venv \
    postgresql-client \
    tesseract-ocr \
    tesseract-ocr-vie \
    ghostscript  \
    gcc \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Set up Python virtual environment and install Python dependencies
RUN pip install --upgrade pip
RUN pip install gunicorn
ADD ./requirements.txt /app/
RUN pip install -r requirements.txt

ADD ./DigitalDMS /app/DigitalDMS
ADD ./docker /app/docker

RUN chmod +x /app/docker/backend/server-entrypoint.sh
RUN chmod +x /app/docker/backend/worker-entrypoint.sh
