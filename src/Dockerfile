FROM python:3.11-slim
WORKDIR /app

# Install the Docker CLI so the Action Engine can run compose commands
RUN apt-get update && apt-get install -y docker.io docker-compose-v2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]