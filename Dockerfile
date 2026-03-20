# ──────────────────────────────────────────────────────────────────────────────
# essstat — TP-Link Easy Smart Switch port statistics
# ──────────────────────────────────────────────────────────────────────────────
#
# Two modes of operation:
#
# 1. CLI mode (original behaviour) — run essstat.py with any args:
#
#      docker build -t essstat .
#      docker run --rm essstat myswitch -p ChangeMe
#      docker run --rm essstat myswitch -p ChangeMe -j
#      docker run --rm essstat myswitch -p ChangeMe -P   # one-shot prometheus
#
# 2. Exporter mode — long-running HTTP server for Prometheus pull scraping:
#
#      docker run -d \
#        -e EXPORTER=1 \
#        -e ESS_HOST=myswitch \
#        -e ESS_PASSWORD=secret \
#        -p 9101:9101 \
#        essstat
#
#   Then scrape http://localhost:9101/metrics from Prometheus.
#
#   Optional env vars for exporter mode:
#     ESS_USERNAME  (default: admin)
#     ESS_LISTEN    (default: 0.0.0.0:9101)
#
#   docker-compose example for multiple switches:
#
#     services:
#       essstat-sw1:
#         image: essstat
#         environment:
#           EXPORTER: "1"
#           ESS_HOST: 192.168.1.10
#           ESS_PASSWORD: secret1
#         ports: ["9101:9101"]
#       essstat-sw2:
#         image: essstat
#         environment:
#           EXPORTER: "1"
#           ESS_HOST: 192.168.1.11
#           ESS_PASSWORD: secret2
#           ESS_LISTEN: 0.0.0.0:9102
#         ports: ["9102:9102"]
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3-alpine

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY essstat.py           .
COPY essstat_exporter.py  .

# Copy and register the entrypoint
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose the Prometheus metrics port (only used in exporter mode)
EXPOSE 9101

ENTRYPOINT ["docker-entrypoint.sh"]
