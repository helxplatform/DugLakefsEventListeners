FROM python:3.12-slim

WORKDIR /app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .

# main.py resolves ./data/ and writes logs.log relative to the cwd
WORKDIR /app/DugLakefsEventListeners
EXPOSE 8001
CMD ["python", "main.py"]
