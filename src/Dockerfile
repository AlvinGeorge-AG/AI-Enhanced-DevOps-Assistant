FROM python:3.11-slim
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# 1. Install prerequisites for adding new repositories
RUN apt-get update && apt-get install -y ca-certificates curl gnupg

# 2. Add Docker's official GPG key and repository
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# 3. Install the official Docker CLI and Docker Compose plugin
RUN apt-get update && apt-get install -y docker-ce-cli docker-compose-plugin

# 4. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the code
COPY . .
CMD ["python", "main.py"]