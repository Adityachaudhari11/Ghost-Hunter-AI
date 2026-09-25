FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY demo ./demo
ENV PYTHONPATH=/app/src:/app PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "ghost_hunter.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
