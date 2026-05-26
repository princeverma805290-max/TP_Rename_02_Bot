FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face ke health check ke liye port 7860 expose karna
EXPOSE 7860

CMD ["python", "bot.py"]
