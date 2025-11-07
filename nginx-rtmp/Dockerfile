# Dockerfile for nginx-rtmp server with dynamic configuration
FROM debian:bullseye-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcre3 \
    libpcre3-dev \
    libssl-dev \
    zlib1g-dev \
    wget \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and compile nginx with rtmp module
WORKDIR /tmp
RUN wget http://nginx.org/download/nginx-1.24.0.tar.gz && \
    tar -zxvf nginx-1.24.0.tar.gz && \
    git clone https://github.com/arut/nginx-rtmp-module.git

WORKDIR /tmp/nginx-1.24.0
RUN ./configure \
    --prefix=/usr/local/nginx \
    --with-http_ssl_module \
    --add-module=../nginx-rtmp-module \
    --with-debug && \
    make && \
    make install

# Install runtime dependencies (Python for config fetcher)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /tmp/hls /var/log/nginx /app

# Install Python dependencies for config fetcher
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copy config fetcher and startup script
COPY push_manager.py /app/push_manager.py
COPY nginx.conf.template /usr/local/nginx/conf/nginx.conf.template
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Expose ports
EXPOSE 1935 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run startup script (starts nginx + config updater)
CMD ["/start.sh"]



