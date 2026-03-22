FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install pip requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot logic
COPY bot.py .

CMD ["python", "bot.py"]
