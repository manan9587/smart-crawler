FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && playwright install --with-deps chromium
EXPOSE 8000
CMD ["uvicorn","backend.main:app","--host","0.0.0.0","--port","8000"]
