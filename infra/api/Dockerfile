FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY infra/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "recall_risk.serving.app:app", "--host", "0.0.0.0", "--port", "8000"]

