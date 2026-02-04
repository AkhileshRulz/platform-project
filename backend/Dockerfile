FROM python:3.11-slim
RUN echo "CACHE BUST v2"
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

RUN apt-get update && apt-get install -y curl

CMD ["python", "app.py"]
