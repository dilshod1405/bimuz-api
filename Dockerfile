FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System libs for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libcairo2 \
    libgirepository-1.0-1 \
    gir1.2-pango-1.0 \
    gir1.2-harfbuzz-0.0 \
    libgobject-2.0-0 \
    libffi-dev \
    libxml2 \
    libxslt1.1 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt /app/

RUN pip install --upgrade pip \
    && pip install --root-user-action=ignore -r requirements.txt

COPY . /app/

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
