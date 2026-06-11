FROM python:3.11-slim as builder

WORKDIR /app

# تثبيت الاعتماديات
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# المرحلة النهائية
FROM python:3.11-slim

WORKDIR /app

# نسخ الاعتماديات من المرحلة السابقة
COPY --from=builder /root/.local /root/.local

# نسخ الكود
COPY . .

# إضافة المسار
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# مستخدم غير root للأمان
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# تشغيل البوت
CMD ["python", "-m", "bot.main"]
