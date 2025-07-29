FROM python:3.12-slim

# 1. Install OS libs for Pillow (optional: libjpeg, zlib, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo-dev libwebp-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy source
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# 3. Expose port & run
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
