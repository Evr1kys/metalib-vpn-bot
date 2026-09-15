# VPN Agent Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for VPN management
RUN apt-get update && apt-get install -y \
    wireguard-tools \
    openvpn \
    easy-rsa \
    openssl \
    iptables \
    ethtool \
    iproute2 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Copy and make optimization script executable
COPY scripts/optimize-network.sh /usr/local/bin/optimize-network.sh
RUN chmod +x /usr/local/bin/optimize-network.sh

# Expose port
EXPOSE 8444

# Run agent
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8444"]
