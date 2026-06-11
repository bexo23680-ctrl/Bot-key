FROM python:3.11-slim

WORKDIR /app

# تثبيت الاعتماديات أولاً (لتحسين التخزين المؤقت)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY . .

# تشغيل البوت
CMD ["python", "main.py"]
