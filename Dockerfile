FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STREAMPROOF_DATA=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 streamproof && mkdir /data && chown streamproof /data
COPY streamproof ./streamproof
COPY static ./static
COPY samples ./samples
USER streamproof
EXPOSE 8080
VOLUME ["/data"]
CMD ["uvicorn", "streamproof.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
