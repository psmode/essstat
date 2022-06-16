#!/usr/bin/env python3
# coding: utf-8

# In[1]:


__author__ = "Peter Smode"
__copyright__ = "Copyright 2021, Peter Smode"
__credits__ = "Peter Smode"
__license__ = "GPL 3.0"
__version__ = "0.5.0"
__maintainer__ = "Peter Smode"
__email__ = "psmode@kitsnet.us"
__status__ = "Beta"


# In[2]:


import argparse, pprint, re, requests, sys, json
from datetime import datetime
from bs4 import BeautifulSoup


# In[3]:


TPlinkStatus = {'0': "Link Down", '1': "LS 1", '2': "10M Half", '3': "10M Full", '4': "LS 4", '5': "100M Full", '6': "1000M Full"}
TPstate = {'0': 'Disabled', '1': 'Enabled'}


# In[4]:


def isnotebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter


# In[5]:


if not isnotebook():
    parser = argparse.ArgumentParser(description='TP-Link Easy Smart Switch port statistics.')
    parser.add_argument('target', metavar='TPhost', help='IP address or hostname of switch')
    parser.add_argument('-1', '--1line', action='store_true', help='output in a single line')
    parser.add_argument('-d', '--debug', action='store_true', help='activate debugging output')
    parser.add_argument('-p', '--password', metavar='TPpswd', required=True, help='password for switch access')
    parser.add_argument('-s', '--statsonly', action='store_true', help='output post statistics only')
    parser.add_argument('-j', '--json', action='store_true', help='output in JSON format')
    parser.add_argument('-u', '--username', metavar='TPuser', required=False, default='admin', help='username for switch access')
    args = vars(parser.parse_args())

    TPLuser = args['username']
    TPLpswd = args['password']
    BASE_URL = "http://"+args['target']
    TPLstatsonly = args['statsonly']
    TPL1line = args['1line']
    TPLjson = args['json']
    TPLdebug = args['debug']


# In[6]:


if isnotebook():
    TPLuser = 'admin'
    TPLpswd = 'changeme'
    BASE_URL = "http://"+"tpl-host"
    TPLstatsonly = False
    TPL1line = False
    TPLdebug = True


# In[7]:


if TPLdebug:
    print(TPLuser)
    print(TPLpswd)
    print(BASE_URL)


# In[8]:


s = requests.Session()


# In[9]:


data = {"logon": "Login", "username": TPLuser, "password": TPLpswd}
headers = { 'Referer': f'{BASE_URL}/Logout.htm'}
try:
    r = s.post(f'{BASE_URL}/logon.cgi', data=data, headers=headers, timeout=5)
except requests.exceptions.Timeout as errt:
       sys.exit("ERROR: Timeout Error at login")
except requests.exceptions.RequestException as err:
       sys.exit("ERROR: General error at login: "+str(err))


# In[10]:


headers = {'Referer': f'{BASE_URL}/',
           'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           'Upgrade-Insecure-Requests': "1" }
r = s.get(f'{BASE_URL}/PortStatisticsRpm.htm', headers=headers, timeout=6)


# In[11]:


soup = BeautifulSoup(r.text, 'html.parser')
if TPLdebug:
    from bs4 import __version__ as bs4__version__
    print("BeautifulSoup4 version: " + bs4__version__)
    print(r)


# In[12]:


convoluted = (soup.script == soup.head.script)     #TL-SG1016DE and TL-SG108E models have a script before the HEAD block
if TPLdebug:
    pprint.pprint(convoluted)


# In[13]:


if TPLdebug:
    if convoluted:
        # This is the 24 port TL-SG1024DE model with the stats in a different place (and convoluted coding)
        pprint.pprint(soup.head.find_all("script"))
        pprint.pprint(soup.body.script)
    else:
        # This should be a TL-SG1016DE or a TL-SG108E
        pprint.pprint(soup.script)


# In[14]:


if str(r) != "<Response [200]>":
    sys.exit("ERROR: Login failure - bad credential?")


# In[15]:


pattern = re.compile(r"var (max_port_num) = (.*?);$", re.MULTILINE)


# In[16]:


if TPLdebug:
    if convoluted:
        print(pattern.search(str(soup.head.find_all("script"))).group(0))
        print(pattern.search(str(soup.head.find_all("script"))).group(1))
        print(pattern.search(str(soup.head.find_all("script"))).group(2))
    else:
        print(pattern.search(str(soup.script)).group(0))
        print(pattern.search(str(soup.script)).group(1))
        print(pattern.search(str(soup.script)).group(2))


# In[17]:


current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
if convoluted:
    max_port_num = int(pattern.search(str(soup.head.find_all("script"))).group(2))
else:
    max_port_num = int(pattern.search(str(soup.script)).group(2))
if not (TPLstatsonly or TPL1line or TPLjson):
   print(current_dt)
   print("max_port_num={0:d}".format(max_port_num))


# In[18]:


if convoluted:
    i1 = re.compile(r'tmp_info = "(.*?)";$', re.MULTILINE | re.DOTALL).search(str(soup.body.script)).group(1)
    i2 = re.compile(r'tmp_info2 = "(.*?)";$', re.MULTILINE | re.DOTALL).search(str(soup.body.script)).group(1)
    # We simulate bug for bug the way the variables are loaded on the "normal" switch models. In those, each
    # data array has two extra 0 cells at the end. To remain compatible with the balance of the code here,
    # we need to add in these redundant entries so they can be removed later. (smh)
    script_vars = ('tmp_info:[' + i1.rstrip() + ' ' + i2.rstrip() + ',0,0]').replace(" ", ",")
else:
    script_vars = re.compile(r"var all_info = {\n?(.*?)\n?};$", re.MULTILINE | re.DOTALL).search(str(soup.script)).group(1)


# In[19]:


if TPLdebug:
    print(script_vars)


# In[20]:


entries = re.split(",?\n+", script_vars)


# In[21]:


if TPLdebug:
    pprint.pprint(entries)


# In[22]:


edict = {}
drop2 = re.compile(r"\[(.*),0,0]")
for entry in entries:
    e2 = re.split(":", entry)
    edict[str(e2[0])] = drop2.search(e2[1]).group(1)


# In[23]:


if TPLdebug:
    pprint.pprint(edict)


# In[24]:


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


# In[25]:

if not TPLjson:
    if TPL1line:
        print(current_dt+"," + str(max_port_num)+",", end="")
        output_format = "{0:d},{1:s},{2:s},{3:s},{4:s},{5:s},{6:s}"
        myend = ","
    else:
        output_format = "{0:d};{1:s};{2:s};{3:s},{4:s},{5:s},{6:s}"
        myend = "\n"

pdict = {}
jlist = []
for x in range(1, max_port_num+1):
    #print(x, ((x-1)*4), ((x-1)*4)+1, ((x-1)*4)+2, ((x-1)*4)+3 )
    pdict[x] = {}
    if (TPL1line or TPLjson):
        pdict[x]['state'] = e3[x-1]
        pdict[x]['link_status'] = e4[x-1]
    else:
        pdict[x]['state'] = TPstate[e3[x-1]]
        pdict[x]['link_status'] = TPlinkStatus[e4[x-1]]
    pdict[x]['TxGoodPkt'] = e5[((x-1)*4)]
    pdict[x]['TxBadPkt'] = e5[((x-1)*4)+1]
    pdict[x]['RxGoodPkt'] = e5[((x-1)*4)+2]
    pdict[x]['RxBadPkt'] = e5[((x-1)*4)+3]

    if (x == max_port_num):
        myend = "\n"

    if TPLjson:
        z = { **{"port": x}, **pdict[x] }
        jlist.append( z )
    else:
        print(output_format.format(x,
                                pdict[x]['state'],
                                pdict[x]['link_status'],
                                pdict[x]['TxGoodPkt'],
                                pdict[x]['TxBadPkt'],
                                pdict[x]['RxGoodPkt'],
                                pdict[x]['RxBadPkt']), end=myend)
if TPLjson:
    for dict in jlist:
        for key in dict:
            dict[key] = int(dict[key])
    json_object = json.dumps(jlist)
    print(json_object)

# In[26]:


if TPLdebug:
    pprint.pprint(pdict)
