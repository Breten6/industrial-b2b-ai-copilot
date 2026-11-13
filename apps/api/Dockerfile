FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY migrations ./migrations
COPY tests ./tests
COPY examples ./examples
COPY pyproject.toml ./
RUN mkdir -p /var/lib/copilot/pdfs && chown -R 10001:10001 /var/lib/copilot
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--no-access-log"]
