FROM python:3.12
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock .
RUN uv sync --frozen
COPY . . 
RUN apt-get update && apt-get install -y curl
HEALTHCHECK CMD ["curl", "--fail", "http://localhost:8000/healthz"]
CMD ["uv","run","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]


