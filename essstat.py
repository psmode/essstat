#!/usr/bin/env python3
# coding: utf-8

__author__    = "Peter Smode"
__copyright__ = "Copyright 2020, Peter Smode"
__credits__   = "Peter Smode"
__license__   = "GPL 3.0"
__version__   = "1.0.0+prometheus"
__maintainer__ = "Peter Smode"
__email__     = "psmode@kitsnet.us"
__status__    = "RC"

# Patch: added -P / --prometheus output mode (Prometheus text exposition format)
# NOTE: the original -P short flag for --port has been renamed to -n to free up -P.

import argparse, pprint, re, requests, sys, json, time
from datetime import datetime
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Numeric mappings (used for JSON / --1line raw output)
# ---------------------------------------------------------------------------
TPlinkStatus = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6}
TPstate      = {'0': 0, '1': 1}

# String mappings (used for human-readable / Zabbix / Prometheus output)
TPlinkStatusNames = {
    '0': "Link Down", '1': "LS 1",      '2': "10M Half",
    '3': "10M Full",  '4': "LS 4",      '5': "100M Full", '6': "1000M Full"
}
TPstateNames = {'0': 'Disabled', '1': 'Enabled'}

# Speed lookup for Prometheus link-speed gauge (Mbps; 0 = link down)
_LINK_SPEED_MAP = {
    "link down":  0,
    "ls 1":       0,
    "ls 4":       0,
    "10m half":   10,
    "10m full":   10,
    "100m half":  100,
    "100m full":  100,
    "1000m half": 1000,
    "1000m full": 1000,
}


# ---------------------------------------------------------------------------
# Notebook detection
# ---------------------------------------------------------------------------
def isnotebook():
    try:
        shell = get_ipython().__class__.__name__
        return shell == 'ZMQInteractiveShell'
    except NameError:
        return False


# ---------------------------------------------------------------------------
# Encode output (text / JSON / Zabbix LLD)
# ---------------------------------------------------------------------------
def encode_output(data, mode="text"):
    """Encode data into text, JSON, or Zabbix LLD format."""
    if mode == "lld":
        lld = {"data": []}
        if isinstance(data, dict):
            entry = {"{#" + str(k).upper() + "}": v for k, v in data.items()}
            lld["data"].append(entry)
        elif isinstance(data, list):
            for d in data:
                entry = {"{#" + str(k).upper() + "}": v for k, v in d.items()}
                lld["data"].append(entry)
        return json.dumps(lld, indent=2)
    elif mode == "json":
        return json.dumps(data, indent=2)
    else:  # text
        if isinstance(data, dict):
            return "\n".join(f"{k}: {v}" for k, v in data.items())
        elif isinstance(data, list):
            return json.dumps(data, indent=2)
        else:
            return str(data)


# ---------------------------------------------------------------------------
# Debug helpers
# ---------------------------------------------------------------------------
def _mask(s, keep=4):
    if not isinstance(s, str) or len(s) <= keep:
        return s
    return s[:keep] + "..." + str(len(s) - keep) + "b"

def dump_response(r, label=""):
    print(f"=== Response Debug Dump {label} ===")
    print("status_code:", r.status_code)
    print("reason:", r.reason)
    print("url:", r.url)
    print("elapsed:", r.elapsed)
    print("encoding:", r.encoding)
    print("apparent_encoding:", r.apparent_encoding)
    masked_cookies = {k: _mask(v) for k, v in r.cookies.get_dict().items()}
    print("cookies:", masked_cookies)
    hdrs = dict(r.headers)
    if "Set-Cookie" in hdrs:
        hdrs["Set-Cookie"] = _mask(hdrs["Set-Cookie"])
    print("headers:", hdrs)
    print("history:", [h.url for h in r.history])
    print("is_redirect:", r.is_redirect, "is_permanent_redirect:", r.is_permanent_redirect)
    print("links:", r.links)
    print("text (full):")
    print(r.text)
    print("content length:", len(r.content))
    print("===========================")


# ---------------------------------------------------------------------------
# Prometheus output
# ---------------------------------------------------------------------------
def _prom_block(name, help_text, mtype, rows, ts_suffix):
    """Emit one Prometheus metric family: HELP + TYPE + all samples."""
    print(f"# HELP {name} {help_text}")
    print(f"# TYPE {name} {mtype}")
    for labels, value in rows:
        print(f"{name}{{{labels}}} {value}{ts_suffix}")
    print()


def output_prometheus(switch_host, port_data, timestamp_ms=None):
    """
    Print Prometheus text exposition format for all port metrics.

    port_data  – list of dicts with keys:
                   port (int), state (str 'Enabled'/'Disabled'),
                   link_status (str), TxGoodPkt, TxBadPkt, RxGoodPkt, RxBadPkt (int)
    timestamp_ms – Unix epoch milliseconds appended to each sample line.
                   Pass None to omit (Prometheus uses scrape time in pull mode).
    """
    ts = f" {timestamp_ms}" if timestamp_ms is not None else ""
    hl = f'host="{switch_host}"'

    # -- port_state (1 = Enabled, 0 = Disabled) ------------------------------
    _prom_block(
        name="tplink_port_state",
        help_text="Port administrative state (1=Enabled, 0=Disabled)",
        mtype="gauge",
        rows=[
            (f'{hl},port="{p["port"]}"',
             1 if str(p["state"]).strip().lower() == "enabled" else 0)
            for p in port_data
        ],
        ts_suffix=ts,
    )

    # -- link speed (Mbps; 0 = link down) ------------------------------------
    _prom_block(
        name="tplink_port_link_speed_mbps",
        help_text="Negotiated link speed in Mbps (0 = link down / autoneg pending)",
        mtype="gauge",
        rows=[
            (f'{hl},port="{p["port"]}",link_status="{p["link_status"]}"',
             _LINK_SPEED_MAP.get(p["link_status"].strip().lower(), 0))
            for p in port_data
        ],
        ts_suffix=ts,
    )

    # -- packet counters ------------------------------------------------------
    # The switch uses 32-bit hardware counters that wrap at 2^32 and reset on
    # reboot.  Prometheus 'counter' type must be strictly monotonic, so we use
    # 'gauge' to avoid confusing rate() on a counter-reset event.
    for field, help_text in (
        ("TxGoodPkt", "Cumulative TX good packets (32-bit hardware counter, resets on reboot)"),
        ("TxBadPkt",  "Cumulative TX bad/error packets (32-bit hardware counter, resets on reboot)"),
        ("RxGoodPkt", "Cumulative RX good packets (32-bit hardware counter, resets on reboot)"),
        ("RxBadPkt",  "Cumulative RX bad/error packets (32-bit hardware counter, resets on reboot)"),
    ):
        _prom_block(
            name=f"tplink_port_{field.lower()}_total",
            help_text=help_text,
            mtype="gauge",
            rows=[
                (f'{hl},port="{p["port"]}"', int(p[field]))
                for p in port_data
            ],
            ts_suffix=ts,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if not isnotebook():
    parser = argparse.ArgumentParser(description='TP-Link Easy Smart Switch statistics.')
    parser.add_argument('target',       metavar='TPhost', help='IP address or hostname of switch')
    parser.add_argument('-1', '--1line', action='store_true', help='output on a single line (CSV)')
    parser.add_argument('-d', '--debug', action='store_true', help='activate debugging output')
    parser.add_argument('-i', '--info',  action='store_true', help='fetch system info instead of port statistics')
    parser.add_argument('-j', '--json',  action='store_true', help='output as JSON')
    parser.add_argument('-l', '--lld',   action='store_true', help='output in Zabbix LLD JSON format')
    parser.add_argument('-p', '--password', metavar='TPpswd', required=True, help='password for switch access')
    parser.add_argument('-u', '--username', metavar='TPuser', required=False, default='admin', help='username for switch access')
    parser.add_argument('-s', '--statsonly', action='store_true', help='output per-port statistics only (one line per port)')
    # NOTE: original short flag was -P; renamed to -n to free -P for --prometheus
    parser.add_argument('-n', '--port',   type=int, help='specific port number to retrieve')
    parser.add_argument('-M', '--metric', help='metric name for specific port (state, link_status, TxGoodPkt, TxBadPkt, RxGoodPkt, RxBadPkt)')
    parser.add_argument('-P', '--prometheus', action='store_true',
                        help='output in Prometheus text exposition format (for /metrics scraping)')
    parser.add_argument('-v', '--Version', action='version',
                        version=f"%(prog)s {__version__}",
                        help="show program's version number and exit")

    args = vars(parser.parse_args())

    TPLuser      = args['username']
    TPLpswd      = args['password']
    BASE_URL     = "http://" + args['target']
    TPLdebug     = args['debug']
    TPLlld       = args['lld']
    PORT         = args['port']
    METRIC       = args['metric']
    TPLone       = args['1line']
    TPLstatsonly = args['statsonly']
    TPLjson      = args['json']
    TPLinfo      = args['info']
    TPLprometheus = args['prometheus']

else:
    # Notebook defaults
    TPLuser       = 'admin'
    TPLpswd       = 'changeme'
    BASE_URL      = "http://tpl-host"
    TPLdebug      = True
    TPLlld        = False
    PORT          = None
    METRIC        = None
    TPLone        = False
    TPLstatsonly  = False
    TPLjson       = False
    TPLinfo       = False
    TPLprometheus = False

if TPLdebug:
    print(TPLuser, TPLpswd, BASE_URL)

# Create requests session
s = requests.Session()

# Wrap s.get/s.post to dump when -d is on
_orig_get, _orig_post = s.get, s.post

def debug_get(*args, **kwargs):
    resp = _orig_get(*args, **kwargs)
    if TPLdebug:
        dump_response(resp, "GET")
    return resp

def debug_post(*args, **kwargs):
    resp = _orig_post(*args, **kwargs)
    if TPLdebug:
        dump_response(resp, "POST")
    return resp

s.get  = debug_get
s.post = debug_post

# Login
data    = {"logon": "Login", "username": TPLuser, "password": TPLpswd}
headers = {'Referer': f'{BASE_URL}/Logout.htm'}
try:
    r = s.post(f'{BASE_URL}/logon.cgi', data=data, headers=headers, timeout=5)
except requests.exceptions.Timeout:
    sys.exit("ERROR: Timeout Error at login")
except requests.exceptions.RequestException as err:
    sys.exit("ERROR: General error at login: " + str(err))


# ---------------------------------------------------------------------------
# SYSTEM INFO
# ---------------------------------------------------------------------------
if TPLinfo:
    r = s.get(f'{BASE_URL}/SystemInfoRpm.htm', headers={'Referer': BASE_URL}, timeout=6)
    if str(r) != "<Response [200]>":
        sys.exit("ERROR: Could not retrieve SystemInfoRpm.htm")

    soup = BeautifulSoup(r.text, 'html.parser')
    script_text = ""
    for sc in soup.find_all("script"):
        txt = sc.string if sc.string is not None else sc.text
        if txt and "var info_ds" in txt:
            script_text = txt
            break

    if not script_text:
        sys.exit("ERROR: Could not find info_ds in SystemInfoRpm.htm")

    def extract_first(name):
        m = re.search(rf'{name}\s*:\s*\[\s*"([^"]*)"\s*\]', script_text, re.DOTALL)
        return m.group(1) if m else ""

    sysinfo = {
        "descriStr":  extract_first("descriStr"),
        "macStr":     extract_first("macStr"),
        "ipStr":      extract_first("ipStr"),
        "netmaskStr": extract_first("netmaskStr"),
        "gatewayStr": extract_first("gatewayStr"),
        "firmwareStr":extract_first("firmwareStr"),
        "hardwareStr":extract_first("hardwareStr"),
    }

    if TPLlld:
        print(encode_output(sysinfo, mode="lld"))
    elif TPLjson:
        print(encode_output(sysinfo, mode="json"))
    elif TPLone:
        current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        oneline = [f"{k}={v}" for k, v in sysinfo.items()]
        print(f"{current_dt}," + ",".join(oneline))
    else:
        print(encode_output(sysinfo, mode="text"))
    sys.exit(0)


# ---------------------------------------------------------------------------
# PORT STATISTICS
# ---------------------------------------------------------------------------
headers = {
    'Referer': f'{BASE_URL}/',
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    'Upgrade-Insecure-Requests': "1"
}
r = s.get(f'{BASE_URL}/PortStatisticsRpm.htm', headers=headers, timeout=6)
if str(r) != "<Response [200]>":
    sys.exit("ERROR: Login failure - bad credential?")

soup = BeautifulSoup(r.text, 'html.parser')

# Extract max port number
pattern = re.compile(r"var (max_port_num) = (.*?);$", re.MULTILINE)
max_port_num = int(pattern.search(soup.script.text).group(2))

# Extract all port information
pattern2 = re.compile(r"var all_info = {\n?(.*?)\n?};$", re.MULTILINE | re.DOTALL)
entries = re.split(",?\n+", pattern2.search(soup.script.text).group(1))

edict = {}
drop2 = re.compile(r"\[(.*),0,0]")  # drop trailing zeros
for entry in entries:
    e2 = re.split(":", entry)
    edict[str(e2[0])] = drop2.search(e2[1]).group(1)

# Raw arrays
e3 = re.split(",", edict['state'])
e4 = re.split(",", edict['link_status'])
e5 = re.split(",", edict['pkts'])

# Build per-port dict
pdict = {}
for x in range(1, max_port_num + 1):
    pdict[x] = {
        'state':      TPstate[e3[x-1]],
        'link_status':TPlinkStatus[e4[x-1]],
        'TxGoodPkt':  int(e5[((x-1)*4)]),
        'TxBadPkt':   int(e5[((x-1)*4)+1]),
        'RxGoodPkt':  int(e5[((x-1)*4)+2]),
        'RxBadPkt':   int(e5[((x-1)*4)+3])
    }

# ---------------------------------------------------------------------------
# Output modes
# ---------------------------------------------------------------------------

if TPLprometheus:
    # Build a list of port dicts with string names (not numeric codes)
    prom_list = []
    for x in range(1, max_port_num + 1):
        prom_list.append({
            "port":        x,
            "state":       TPstateNames[e3[x-1]],
            "link_status": TPlinkStatusNames[e4[x-1]],
            "TxGoodPkt":   pdict[x]['TxGoodPkt'],
            "TxBadPkt":    pdict[x]['TxBadPkt'],
            "RxGoodPkt":   pdict[x]['RxGoodPkt'],
            "RxBadPkt":    pdict[x]['RxBadPkt'],
        })
    output_prometheus(args['target'], prom_list, int(time.time() * 1000))

elif TPLlld:
    jlist = []
    for x in range(1, max_port_num + 1):
        jlist.append({
            "port":       str(x),
            "state":      pdict[x]['state'],
            "link_status":pdict[x]['link_status'],
            "TxGoodPkt":  pdict[x]['TxGoodPkt'],
            "TxBadPkt":   pdict[x]['TxBadPkt'],
            "RxGoodPkt":  pdict[x]['RxGoodPkt'],
            "RxBadPkt":   pdict[x]['RxBadPkt'],
        })
    print(encode_output(jlist, mode="lld"))

elif PORT and METRIC:
    if PORT < 1 or PORT > max_port_num:
        sys.exit("ERROR: Invalid port number")
    if METRIC not in pdict[PORT]:
        sys.exit("ERROR: Invalid metric name")
    print(pdict[PORT][METRIC])

elif TPLjson:
    jlist = []
    for x in range(1, max_port_num + 1):
        jlist.append({
            "port":        x,
            "state":       int(e3[x-1]),
            "link_status": int(e4[x-1]),
            "TxGoodPkt":   pdict[x]['TxGoodPkt'],
            "TxBadPkt":    pdict[x]['TxBadPkt'],
            "RxGoodPkt":   pdict[x]['RxGoodPkt'],
            "RxBadPkt":    pdict[x]['RxBadPkt'],
        })
    print(encode_output(jlist, mode="json"))

else:
    current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if TPLone:
        print(f"{current_dt},{max_port_num},", end="")
        for x in range(1, max_port_num + 1):
            end_char = "\n" if x == max_port_num else ","
            print("{0:d},{1:s},{2:s},{3:s},{4:s},{5:s},{6:s}".format(
                x, e3[x-1], e4[x-1],
                e5[((x-1)*4)],
                e5[((x-1)*4)+1],
                e5[((x-1)*4)+2],
                e5[((x-1)*4)+3]
            ), end=end_char)

    elif TPLstatsonly:
        for x in range(1, max_port_num + 1):
            print("{0:d};{1:s};{2:s};{3:d},{4:d},{5:d},{6:d}".format(
                x,
                TPstateNames[e3[x-1]],
                TPlinkStatusNames[e4[x-1]],
                pdict[x]['TxGoodPkt'],
                pdict[x]['TxBadPkt'],
                pdict[x]['RxGoodPkt'],
                pdict[x]['RxBadPkt']
            ))

    else:
        print(current_dt)
        print(f"max_port_num={max_port_num}")
        if TPLdebug:
            pprint.pprint(pdict)
        for x in range(1, max_port_num + 1):
            print("{0:d};{1:s};{2:s};{3:d},{4:d},{5:d},{6:d}".format(
                x,
                TPstateNames[e3[x-1]],
                TPlinkStatusNames[e4[x-1]],
                pdict[x]['TxGoodPkt'],
                pdict[x]['TxBadPkt'],
                pdict[x]['RxGoodPkt'],
                pdict[x]['RxBadPkt']
            ))
