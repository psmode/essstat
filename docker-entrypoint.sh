#!/bin/sh
# docker-entrypoint.sh
# Supports two modes:
#
#   CLI mode (default) — original behaviour, passes all args straight to essstat.py:
#     docker run --rm essstat myswitch -p ChangeMe
#     docker run --rm essstat myswitch -p ChangeMe -P   # one-shot prometheus dump
#
#   Exporter mode — long-running HTTP /metrics server for Prometheus scraping:
#     docker run -e EXPORTER=1 -e ESS_HOST=myswitch -e ESS_PASSWORD=secret \
#                -p 9101:9101 essstat
#
#   Exporter env vars:
#     ESS_HOST      (required) switch IP or hostname
#     ESS_PASSWORD  (required) switch admin password
#     ESS_USERNAME  (default: admin)
#     ESS_LISTEN    (default: 0.0.0.0:9101)

set -e

if [ "${EXPORTER:-0}" = "1" ]; then
    # Validate required env vars
    if [ -z "${ESS_HOST}" ]; then
        echo "ERROR: ESS_HOST is required in exporter mode" >&2
        exit 1
    fi
    if [ -z "${ESS_PASSWORD}" ]; then
        echo "ERROR: ESS_PASSWORD is required in exporter mode" >&2
        exit 1
    fi

    exec python /app/essstat_exporter.py \
        --host     "${ESS_HOST}" \
        --password "${ESS_PASSWORD}" \
        --username "${ESS_USERNAME:-admin}" \
        --listen   "${ESS_LISTEN:-0.0.0.0:9101}" \
        --essstat  /app/essstat.py
else
    exec python /app/essstat.py "$@"
fi
