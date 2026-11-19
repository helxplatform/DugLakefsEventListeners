FROM python:3.12-slim

# pick up Debian security fixes released after the base image was built
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app src/ .

# main.py resolves ./data/ and writes logs.log + last_commit_id relative to the cwd
WORKDIR /app/DugLakefsEventListeners
USER 10001
EXPOSE 8001
CMD ["python", "main.py"]
