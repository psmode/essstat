#!/usr/bin/env python3
# coding: utf-8

__author__ = "Peter Smode"
__copyright__ = "Copyright 2025, Peter Smode"
__credits__ = "Peter Smode"
__license__ = "GPL 3.0"
__version__ = "1.2.0"
__maintainer__ = "Peter Smode"
__email__ = "psmode@kitsnet.us"
__status__ = "RC"

import argparse, pprint, re, requests, sys, json
from datetime import datetime
from bs4 import BeautifulSoup

# Numeric mappings
TPlinkStatus = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6}
TPstate = {'0': 0, '1': 1}

# String mappings
TPlinkStatusNames = {
    '0': "Link Down", '1': "LS 1", '2': "10M Half",
    '3': "10M Full", '4': "LS 4", '5': "100M Full", '6': "1000M Full"
}
TPstateNames = {'0': 'Disabled', '1': 'Enabled'}

def isnotebook():
    try:
        shell = get_ipython().__class__.__name__
        return shell == 'ZMQInteractiveShell'
    except NameError:
        return False

def encode_output(data, mode="text"):
    """
    Encode data into text, JSON, or Zabbix LLD.
    data can be dict (system info) or list of dicts (ports).
    """
    if mode == "lld":
        lld = {"data": []}
        if isinstance(data, dict):
            entry = {}
            for k, v in data.items():
                macro_name = "{#" + str(k).upper() + "}"
                entry[macro_name] = v
            lld["data"].append(entry)
        elif isinstance(data, list):
            for d in data:
                entry = {}
                for k, v in d.items():
                    macro_name = "{#" + str(k).upper() + "}"
                    entry[macro_name] = v
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

# ---------- Debug helpers (for any GET/POST) ----------

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

    # Full response body
    print("text (full):")
    print(r.text)
    print("content length:", len(r.content))
    print("===========================")

# ------------------ MAIN ------------------

if not isnotebook():
    parser = argparse.ArgumentParser(description='TP-Link Easy Smart Switch statistics.')
    parser.add_argument('target', metavar='TPhost', help='IP address or hostname of switch')
    parser.add_argument('-1', '--1line', action='store_true', help='output on a single line (CSV)')
    parser.add_argument('-d', '--debug', action='store_true', help='activate debugging output')
    parser.add_argument('-i', '--info', action='store_true', help='fetch system info instead of port statistics')
    parser.add_argument('-j', '--json', action='store_true', help='output as JSON')
    parser.add_argument('-l', '--lld', action='store_true', help='output in Zabbix LLD JSON format')
    parser.add_argument('-p', '--password', metavar='TPpswd', required=True, help='password for switch access')
    parser.add_argument('-u', '--username', metavar='TPuser', required=False, default='admin', help='username for switch access')
    parser.add_argument('-s', '--statsonly', action='store_true', help='output per-port statistics only (one line per port)')
    parser.add_argument('-P', '--port', type=int, help='specific port number to retrieve')
    parser.add_argument('-M', '--metric', help='metric name for specific port (state, link_status, TxGoodPkt, TxBadPkt, RxGoodPkt, RxBadPkt)')
    parser.add_argument('-v', '--Version', action='version',
                        version=f"%(prog)s {__version__}",
                        help="show program's version number and exit")
    args = vars(parser.parse_args())

    TPLuser = args['username']
    TPLpswd = args['password']
    BASE_URL = "http://" + args['target']
    TPLdebug = args['debug']
    TPLlld = args['lld']
    PORT = args['port']
    METRIC = args['metric']
    TPLone = args['1line']
    TPLstatsonly = args['statsonly']
    TPLjson = args['json']
    TPLinfo = args['info']

else:
    # Notebook defaults
    TPLuser = 'admin'
    TPLpswd = 'changeme'
    BASE_URL = "http://tpl-host"
    TPLdebug = True
    TPLlld = False
    PORT = None
    METRIC = None
    TPLone = False
    TPLstatsonly = False
    TPLjson = False
    TPLinfo = False

if TPLdebug:
    print(TPLuser, TPLpswd, BASE_URL)

# Create requests session
s = requests.Session()

# Wrap s.get/s.post so any request will dump when -d is on
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

s.get = debug_get
s.post = debug_post

# Login
data = {"logon": "Login", "username": TPLuser, "password": TPLpswd}
headers = {'Referer': f'{BASE_URL}/Logout.htm'}
try:
    r = s.post(f'{BASE_URL}/logon.cgi', data=data, headers=headers, timeout=5)
except requests.exceptions.Timeout:
    sys.exit("ERROR: Timeout Error at login")
except requests.exceptions.RequestException as err:
    sys.exit("ERROR: General error at login: "+str(err))

# ------------------ SYSTEM INFO (from <script> var info_ds) ------------------
# ------------------ SYSTEM INFO (from <script> var info_ds) ------------------
if TPLinfo:
    r = s.get(f'{BASE_URL}/SystemInfoRpm.htm', headers={'Referer': BASE_URL}, timeout=6)
    if str(r) != "<Response [200]>":
        sys.exit("ERROR: Could not retrieve SystemInfoRpm.htm")

    soup = BeautifulSoup(r.text, 'html.parser')

    # Find the <script> that defines info_ds
    script_text = ""
    for sc in soup.find_all("script"):
        txt = sc.string if sc.string is not None else sc.text
        if txt and "var info_ds" in txt:
            script_text = txt
            break
    if not script_text:
        sys.exit("ERROR: Could not find info_ds in SystemInfoRpm.htm")

    # Helper: extract first string inside array for a given key
    def extract_first(name: str) -> str:
        # Matches: name:[ "value" ]  (with arbitrary whitespace/newlines)
        m = re.search(rf'{name}\s*:\s*\[\s*"([^"]*)"\s*\]', script_text, re.DOTALL)
        return m.group(1) if m else ""

    # Build sysinfo with the device's original keys, unwrapped to strings
    sysinfo = {
        "descriStr":   extract_first("descriStr"),
        "macStr":      extract_first("macStr"),
        "ipStr":       extract_first("ipStr"),
        "netmaskStr":  extract_first("netmaskStr"),
        "gatewayStr":  extract_first("gatewayStr"),
        "firmwareStr": extract_first("firmwareStr"),
        "hardwareStr": extract_first("hardwareStr"),
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

# ------------------ PORT STATISTICS ------------------

headers = {
    'Referer': f'{BASE_URL}/',
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    'Upgrade-Insecure-Requests': "1"
}
r = s.get(f'{BASE_URL}/PortStatisticsRpm.htm', headers=headers, timeout=6)

if str(r) != "<Response [200]>":
    sys.exit("ERROR: Login failure - bad credential?")

soup = BeautifulSoup(r.text, 'html.parser')
if TPLdebug:
    from bs4 import __version__ as bs4__version__
    print("BeautifulSoup4 version: " + bs4__version__)
    print(r)

convoluted = (soup.script == soup.head.script)     #TL-SG1016DE and TL-SG108E models have a script before the HEAD block
if TPLdebug:
    pprint.pprint(convoluted)
    if convoluted:
        # This is the 24 port TL-SG1024DE model with the stats in a different place (and convoluted coding)
        pprint.pprint(soup.head.find_all("script"))
        pprint.pprint(soup.body.script)
    else:
        # This should be a TL-SG1016DE or a TL-SG108E
        pprint.pprint(soup.script)    

if TPLdebug:
    if convoluted:
        print(pattern.search(str(soup.head.find_all("script"))).group(0))
        print(pattern.search(str(soup.head.find_all("script"))).group(1))
        print(pattern.search(str(soup.head.find_all("script"))).group(2))
    else:
        print(pattern.search(str(soup.script)).group(0))
        print(pattern.search(str(soup.script)).group(1))
        print(pattern.search(str(soup.script)).group(2))

# Extract max port number
pattern = re.compile(r"var (max_port_num) = (.*?);$", re.MULTILINE)
if convoluted:
    max_port_num = int(pattern.search(str(soup.head.find_all("script"))).group(2))
else:
    max_port_num = int(pattern.search(str(soup.script)).group(2))

# Extract all port information
#pattern2 = re.compile(r"var all_info = {\n?(.*?)\n?};$", re.MULTILINE | re.DOTALL)
if convoluted:
    i1 = re.compile(r'tmp_info = "(.*?)";$', re.MULTILINE | re.DOTALL).search(str(soup.body.script)).group(1)
    i2 = re.compile(r'tmp_info2 = "(.*?)";$', re.MULTILINE | re.DOTALL).search(str(soup.body.script)).group(1)
    # We simulate bug for bug the way the variables are loaded on the "normal" switch models. In those, each
    # data array has two extra 0 cells at the end. To remain compatible with the balance of the code here,
    # we need to add in these redundant entries so they can be removed later. (smh)
    script_vars = ('tmp_info:[' + i1.rstrip() + ' ' + i2.rstrip() + ',0,0]').replace(" ", ",")
else:
    script_vars = re.compile(r"var all_info = {\n?(.*?)\n?};$", re.MULTILINE | re.DOTALL).search(str(soup.script)).group(1)
if TPLdebug:
    print(script_vars)

#entries = re.split(",?\n+", pattern2.search(soup.script.text).group(1))
entries = re.split(",?\n+", script_vars)
if TPLdebug:
    pprint.pprint(entries)

edict = {}
drop2 = re.compile(r"\[(.*),0,0]")  # drop trailing zeros
for entry in entries:
    e2 = re.split(":", entry)
    edict[str(e2[0])] = drop2.search(e2[1]).group(1)

# Raw arrays
#e3 = re.split(",", edict['state'])
#e4 = re.split(",", edict['link_status'])
#e5 = re.split(",", edict['pkts'])
if convoluted:
    e3 = {}
    e4 = {}
    e5 = {}
    ee = re.split(",", edict['tmp_info'])
    for x in range (0, max_port_num):
        e3[x] = ee[(x*6)]
        e4[x] = ee[(x*6)+1]
        e5[(x*4)] = ee[(x*6)+2]
        e5[(x*4)+1] = ee[(x*6)+3]
        e5[(x*4)+2] = ee[(x*6)+4]
        e5[(x*4)+3] = ee[(x*6)+5]
else:
    e3 = re.split(",", edict['state'])
    e4 = re.split(",", edict['link_status'])
    e5 = re.split(",", edict['pkts'])

# Build per-port dict
pdict = {}
for x in range(1, max_port_num+1):
    pdict[x] = {
        'state': TPstate[e3[x-1]],
        'link_status': TPlinkStatus[e4[x-1]],
        'TxGoodPkt': int(e5[((x-1)*4)]),
        'TxBadPkt': int(e5[((x-1)*4)+1]),
        'RxGoodPkt': int(e5[((x-1)*4)+2]),
        'RxBadPkt': int(e5[((x-1)*4)+3])
    }

# Output modes
if TPLlld:
    jlist = []
    for x in range(1, max_port_num+1):
        jlist.append({
            "port": str(x),
            "state": pdict[x]['state'],
            "link_status": pdict[x]['link_status'],
            "TxGoodPkt": pdict[x]['TxGoodPkt'],
            "TxBadPkt": pdict[x]['TxBadPkt'],
            "RxGoodPkt": pdict[x]['RxGoodPkt'],
            "RxBadPkt": pdict[x]['RxBadPkt']
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
    for x in range(1, max_port_num+1):
        jlist.append({
            "port": x,
            "state": int(e3[x-1]),
            "link_status": int(e4[x-1]),
            "TxGoodPkt": pdict[x]['TxGoodPkt'],
            "TxBadPkt": pdict[x]['TxBadPkt'],
            "RxGoodPkt": pdict[x]['RxGoodPkt'],
            "RxBadPkt": pdict[x]['RxBadPkt']
        })
    print(encode_output(jlist, mode="json"))

else:
    current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if TPLone:
        print(f"{current_dt},{max_port_num},", end="")
        for x in range(1, max_port_num+1):
            end_char = "\n" if x == max_port_num else ","
            print("{0:d},{1:s},{2:s},{3:s},{4:s},{5:s},{6:s}".format(
                x, e3[x-1], e4[x-1],
                e5[((x-1)*4)],
                e5[((x-1)*4)+1],
                e5[((x-1)*4)+2],
                e5[((x-1)*4)+3]
            ), end=end_char)
    elif TPLstatsonly:
        for x in range(1, max_port_num+1):
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
