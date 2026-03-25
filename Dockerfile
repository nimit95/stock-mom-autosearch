FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt kiteconnect requests

COPY . .

# Persist database and cache outside container
VOLUME ["/app/data", "/root/.cache/mom-autosearch"]

# Dashboard port
EXPOSE 8765

CMD ["python3", "dashboard.py"]
