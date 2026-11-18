FROM python:3.13-slim
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt && useradd -m nova && mkdir /data && chown nova /data
COPY app ./app
USER nova
ENV DATABASE_URL=sqlite:////data/nova.db
EXPOSE 8000
CMD ["uvicorn","app.main:create_app","--factory","--host","0.0.0.0","--port","8000"]
