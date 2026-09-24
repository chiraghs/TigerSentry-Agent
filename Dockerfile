FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY data/sample/ data/sample/
COPY cases/ cases/
COPY outputs/ outputs/
COPY gsql/ gsql/
COPY schema/ schema/
COPY screenshots/ screenshots/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
