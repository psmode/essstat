#!/usr/bin/env python3
"""
essstat_exporter.py  –  Minimal Prometheus HTTP exporter for essstat
─────────────────────────────────────────────────────────────────────
Wraps essstat.py in an HTTP server so Prometheus can scrape /metrics directly.
Listens on 0.0.0.0:9101 by default.

Usage:
    ./essstat_exporter.py --host 192.168.1.1 --password secret
    ./essstat_exporter.py --host 192.168.1.1 --password secret --listen 0.0.0.0:9101

Then add to prometheus.yml:
    scrape_configs:
      - job_name: tplink_switch
        static_configs:
          - targets: ['localhost:9101']

For multiple switches, run one instance per switch on different ports:
    ./essstat_exporter.py --host switch-a --password secretA --listen 0.0.0.0:9101
    ./essstat_exporter.py --host switch-b --password secretB --listen 0.0.0.0:9102
"""

import argparse
import subprocess
import sys
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


# ── scrape helper ─────────────────────────────────────────────────────────────

def scrape(essstat_path: str, host: str, password: str, username: str):
    """
    Invoke essstat.py -P and return (http_status, body_text).
    Returns 200 + Prometheus text on success, 500 + error message on failure.
    """
    cmd = [
        sys.executable, essstat_path,
        '-P',
        '-p', password,
        '-u', username,
        host,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip() or 'essstat exited non-zero'
            return 500, f'# essstat error (exit {result.returncode}): {err}\n'
        return 200, result.stdout
    except subprocess.TimeoutExpired:
        return 500, '# essstat error: scrape timed out after 15s\n'
    except Exception as exc:
        return 500, f'# essstat error: {exc}\n'


# ── HTTP handler ──────────────────────────────────────────────────────────────

class MetricsHandler(BaseHTTPRequestHandler):
    essstat_path = './essstat.py'
    switch_host  = None
    password     = None
    username     = 'admin'

    def do_GET(self):
        if self.path not in ('/metrics', '/metrics/'):
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'404 Not Found - use /metrics\n')
            return

        status, body = scrape(
            self.essstat_path,
            self.switch_host,
            self.password,
            self.username,
        )
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def log_message(self, fmt, *args):
        print(f'[scrape] {self.address_string()} -> {args[1]}', flush=True)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    # Resolve the default essstat.py path relative to this script's directory
    script_dir   = os.path.dirname(os.path.realpath(__file__))
    default_path = os.path.join(script_dir, 'essstat.py')

    ap = argparse.ArgumentParser(
        description='Prometheus HTTP exporter for TP-Link Easy Smart Switch via essstat.py'
    )
    ap.add_argument('--host',     required=True,
                    help='Switch IP or hostname')
    ap.add_argument('--password', required=True,
                    help='Switch admin password')
    ap.add_argument('--username', default='admin',
                    help='Switch admin username (default: admin)')
    ap.add_argument('--listen',   default='0.0.0.0:9101',
                    help='Listen on this address:port (default: 0.0.0.0:9101)')
    ap.add_argument('--essstat',  default=default_path,
                    help=f'Path to essstat.py (default: {default_path})')
    args = ap.parse_args()

    # Validate essstat.py exists before binding the socket
    if not os.path.isfile(args.essstat):
        ap.error(f'essstat.py not found at: {args.essstat}  (use --essstat to specify path)')

    addr, port_str = args.listen.rsplit(':', 1)
    try:
        port = int(port_str)
    except ValueError:
        ap.error(f'Invalid listen port: {port_str!r}')

    MetricsHandler.essstat_path = args.essstat
    MetricsHandler.switch_host  = args.host
    MetricsHandler.password     = args.password
    MetricsHandler.username     = args.username

    print(f'essstat_exporter listening on http://{addr}:{port}/metrics')
    print(f'  switch  : {args.host}')
    print(f'  essstat : {args.essstat}')

    try:
        HTTPServer((addr, port), MetricsHandler).serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
