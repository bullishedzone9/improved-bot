FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY bridge_service/requirements.txt /app/bridge_service/requirements.txt
RUN pip install --no-cache-dir -r /app/bridge_service/requirements.txt
COPY mt4_bridge_validation.py /app/mt4_bridge_validation.py
COPY bridge_service/main.py /app/bridge_service/main.py
EXPOSE 8000
CMD ["uvicorn", "bridge_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
