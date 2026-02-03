FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

RUN apt-get update && apt-get install -y curl

CMD ["python", "app.py"]
