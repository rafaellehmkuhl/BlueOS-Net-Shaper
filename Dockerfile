FROM python:3.11-slim

# Install runtime and build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        iproute2 \
        iputils-ping \
        iptables \
        procps \
        net-tools \
        gcc \
        libc6-dev \
        make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app /app

# Install Python dependencies and clean up build tools
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get purge -y --auto-remove gcc libc6-dev make

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

