FROM python:3.9-slim

# Set the working directory
WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./

RUN pip install --no-cache-dir uv==0.6.3 && \
    uv sync

COPY . .

CMD ["uv", "run", "python", "main.py"]
