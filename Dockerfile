FROM python:3.11-slim

# Install runtime dependencies only (no build tools needed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        iproute2 \
        iputils-ping \
        iptables \
        procps \
        net-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app /app

# Install Python dependencies (all wheels available, no compilation needed)
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

