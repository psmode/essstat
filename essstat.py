#!/usr/bin/env python3
# coding: utf-8

__author__ = "Peter Smode"
__copyright__ = "Copyright 2020, Peter Smode"
__credits__ = "Peter Smode"
__license__ = "GPL 3.0"
__version__ = "0.8.0"
__maintainer__ = "Peter Smode"
__email__ = "psmode@kitsnet.us"
__status__ = "Beta"

import argparse, pprint, re, requests, sys, json
from datetime import datetime
from bs4 import BeautifulSoup

# Numeric mappings (kept from newer script)
TPlinkStatus = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6}
TPstate = {'0': 0, '1': 1}

# String mappings (for --statsonly readable output)
TPlinkStatusNames = {
    '0': "Link Down", '1': "LS 1", '2': "10M Half",
    '3': "10M Full", '4': "LS 4", '5': "100M Full", '6': "1000M Full"
}
TPstateNames = {'0': 'Disabled', '1': 'Enabled'}

def isnotebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True
        elif shell == 'TerminalInteractiveShell':
            return False
        else:
            return False
    except NameError:
        return False

if not isnotebook():
    parser = argparse.ArgumentParser(description='TP-Link Easy Smart Switch port statistics.')
    parser.add_argument('target', metavar='TPhost', help='IP address or hostname of switch')
    parser.add_argument('-1', '--1line', action='store_true', help='output on a single line (CSV)')
    parser.add_argument('-d', '--debug', action='store_true', help='activate debugging output')
    parser.add_argument('-j', '--json', action='store_true', help='output per-port statistics as JSON')
    parser.add_argument('-l', '--lld', action='store_true', help='output in Zabbix Low-Level Discovery JSON format')
    parser.add_argument('-p', '--password', metavar='TPpswd', required=True, help='password for switch access')
    parser.add_argument('-u', '--username', metavar='TPuser', required=False, default='admin', help='username for switch access')
    parser.add_argument('-s', '--statsonly', action='store_true', help='output per-port statistics only (one line per port)')
    parser.add_argument('--port', type=int, help='specific port number to retrieve')
    parser.add_argument('--metric', help='metric name for specific port (state, link_status, TxGoodPkt, TxBadPkt, RxGoodPkt, RxBadPkt)')
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

# Notebook defaults
if isnotebook():
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

if TPLdebug:
    print(TPLuser, TPLpswd, BASE_URL)

# Create requests session
s = requests.Session()

# Login
data = {"logon": "Login", "username": TPLuser, "password": TPLpswd}
headers = {'Referer': f'{BASE_URL}/Logout.htm'}
try:
    r = s.post(f'{BASE_URL}/logon.cgi', data=data, headers=headers, timeout=5)
except requests.exceptions.Timeout:
    sys.exit("ERROR: Timeout Error at login")
except requests.exceptions.RequestException as err:
    sys.exit("ERROR: General error at login: "+str(err))

# Port stats page
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

# Raw arrays from page (strings)
e3 = re.split(",", edict['state'])        # '0'/'1'
e4 = re.split(",", edict['link_status'])  # '0'..'6'
e5 = re.split(",", edict['pkts'])         # packet counters (strings)

# Build per-port dict (ints)
pdict = {}
for x in range(1, max_port_num+1):
    pdict[x] = {}
    pdict[x]['state'] = TPstate[e3[x-1]]
    pdict[x]['link_status'] = TPlinkStatus[e4[x-1]]
    pdict[x]['TxGoodPkt'] = int(e5[((x-1)*4)])
    pdict[x]['TxBadPkt'] = int(e5[((x-1)*4)+1])
    pdict[x]['RxGoodPkt'] = int(e5[((x-1)*4)+2])
    pdict[x]['RxBadPkt'] = int(e5[((x-1)*4)+3])

# Output modes (priority: LLD > specific metric > JSON > 1line > statsonly > default)
if TPLlld:
    # Unchanged LLD behavior
    lld_output = {"data": []}
    for x in range(1, max_port_num+1):
        lld_output["data"].append({
            "{#PORT}": str(x),
            "{#state}": pdict[x]['state'],
            "{#link_status}": pdict[x]['link_status'],
            "{#TxGoodPkt}": pdict[x]['TxGoodPkt'],
            "{#TxBadPkt}": pdict[x]['TxBadPkt'],
            "{#RxGoodPkt}": pdict[x]['RxGoodPkt'],
            "{#RxBadPkt}": pdict[x]['RxBadPkt']
        })
    print(json.dumps(lld_output, indent=2))

elif PORT and METRIC:
    if PORT < 1 or PORT > max_port_num:
        sys.exit("ERROR: Invalid port number")
    if METRIC not in pdict[PORT]:
        sys.exit("ERROR: Invalid metric name")
    print(pdict[PORT][METRIC])

elif TPLjson:
    # JSON array of per-port objects (ints for codes and counters)
    jlist = []
    for x in range(1, max_port_num+1):
        jlist.append({
            "port": x,
            "state": int(e3[x-1]),           # raw code as int (0/1)
            "link_status": int(e4[x-1]),     # raw code as int (0..6)
            "TxGoodPkt": pdict[x]['TxGoodPkt'],
            "TxBadPkt": pdict[x]['TxBadPkt'],
            "RxGoodPkt": pdict[x]['RxGoodPkt'],
            "RxBadPkt": pdict[x]['RxBadPkt']
        })
    print(json.dumps(jlist))

else:
    current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if TPLone:
        # Single-line CSV: timestamp,max_port_num, then per-port records (numeric codes & counters)
        print(f"{current_dt},{max_port_num},", end="")
        for x in range(1, max_port_num+1):
            end_char = "\n" if x == max_port_num else ","
            print("{0:d},{1:s},{2:s},{3:s},{4:s},{5:s},{6:s}".format(
                x,
                e3[x-1],               # raw state code
                e4[x-1],               # raw link status code
                e5[((x-1)*4)],
                e5[((x-1)*4)+1],
                e5[((x-1)*4)+2],
                e5[((x-1)*4)+3]
            ), end=end_char)

    elif TPLstatsonly:
        # One line per port (no timestamp/header), readable names
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
        # Default summary
        print(current_dt)
        print(f"max_port_num={max_port_num}")
        if TPLdebug:
            pprint.pprint(pdict)