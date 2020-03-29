#!/usr/bin/env python3
# coding: utf-8

# In[ ]:


__author__ = "Peter Smode"
__copyright__ = "Copyright 2020, Peter Smode"
__credits__ = "Peter Smode"
__license__ = "GPL 3.0"
__version__ = "0.3.0"
__maintainer__ = "Peter Smode"
__email__ = "psmode@kitsnet.us"
__status__ = "Beta"


# In[3]:


import argparse, pprint, re, requests, sys
from datetime import datetime
from bs4 import BeautifulSoup


# In[4]:


TPlinkStatus = {'0': "Link Down", '1': "LS 1", '2': "10M Half", '3': "10M Full", '4': "LS 4", '5': "100M Full", '6': "1000M Full"}
TPstate = {'0': 'Disabled', '1': 'Enabled'}


# In[5]:


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


# In[6]:


if not isnotebook():
    parser = argparse.ArgumentParser(description='TP-Link Easy Smart Switch port statistics.')
    parser.add_argument('target', metavar='TPhost', help='IP address or hostname of switch')
    parser.add_argument('-1', '--1line', action='store_true', help='output in a single line')
    parser.add_argument('-d', '--debug', action='store_true', help='activate debugging output')
    parser.add_argument('-p', '--password', metavar='TPpswd', required=True, help='password for swtich access')
    parser.add_argument('-s', '--statsonly', action='store_true', help='output post statistics only')
    parser.add_argument('-u', '--username', metavar='TPuser', required=False, default='admin', help='username for swtich access')
    args = vars(parser.parse_args())

    TPLuser = args['username']
    TPLpswd = args['password']
    BASE_URL = "http://"+args['target']
    TPLstatsonly = args['statsonly']
    TPL1line = args['1line']
    TPLdebug = args['debug']


# In[7]:


if isnotebook():
    TPLuser = 'admin'
    TPLpswd = 'changeme'
    BASE_URL = "http://"+"tpl-host"
    TPLstatsonly = False
    TPL1line = False
    TPLdebug = True


# In[8]:


if TPLdebug:
    print(TPLuser)
    print(TPLpswd)
    print(BASE_URL)


# In[87]:


s = requests.Session()


# In[88]:


data = {"logon": "Login", "username": TPLuser, "password": TPLpswd}
headers = { 'Referer': f'{BASE_URL}/Logout.htm'}
try:
    r = s.post(f'{BASE_URL}/logon.cgi', data=data, headers=headers, timeout=5)
except requests.exceptions.Timeout as errt:
       sys.exit("ERROR: Timeout Error at login")
except requests.exceptions.RequestException as err:
       sys.exit("ERROR: General error at login: "+str(err))


# In[90]:


headers = {'Referer': f'{BASE_URL}/',
           'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           'Upgrade-Insecure-Requests': "1" }
r = s.get(f'{BASE_URL}/PortStatisticsRpm.htm', headers=headers, timeout=6)


# In[91]:


soup = BeautifulSoup(r.text, 'html.parser')
if TPLdebug:
    print(r)


# In[92]:


if TPLdebug:
    pprint.pprint(soup.script)


# In[93]:


if str(r) != "<Response [200]>":
    sys.exit("ERROR: Login failure - bad credential?")


# In[94]:

pattern = re.compile(r"var (max_port_num) = (.*?);$", re.MULTILINE)


# In[95]:


if TPLdebug:
    print(pattern.search(soup.script.text).group(0))
    print(pattern.search(soup.script.text).group(1))
    print(pattern.search(soup.script.text).group(2))


# In[117]:


current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
max_port_num = int(pattern.search(soup.script.text).group(2))
if not (TPLstatsonly or TPL1line):
   print(current_dt)
   print("max_port_num={0:d}".format(max_port_num))


# In[97]:


pattern2 = re.compile(r"var all_info = {\n?(.*?)\n?};$", re.MULTILINE | re.DOTALL)


# In[98]:


if TPLdebug:
    print(pattern2.search(soup.script.text).group(1))


# In[99]:


entries = re.split(",?\n+", pattern2.search(soup.script.text).group(1))


# In[100]:


if TPLdebug:
    pprint.pprint(entries)


# In[101]:


edict = {}
drop2 = re.compile(r"\[(.*),0,0]")
for entry in entries:
    e2 = re.split(":", entry)
    edict[str(e2[0])] = drop2.search(e2[1]).group(1)


# In[102]:


if TPLdebug:
    pprint.pprint(edict)


# In[103]:


e3 = re.split(",", edict['state'])
e4 = re.split(",", edict['link_status'])
e5 = re.split(",", edict['pkts'])


# In[122]:


if TPL1line:
	print(current_dt+"," + str(max_port_num)+",", end="")
	output_format = "{0:d},{1:s},{2:s},{3:s},{4:s},{5:s},{6:s}"
	myend = ","
else:
	output_format = "{0:d};{1:s};{2:s};{3:s},{4:s},{5:s},{6:s}"
	myend = "\n"

pdict = {}
for x in range(1, max_port_num+1):
    #print(x, ((x-1)*4), ((x-1)*4)+1, ((x-1)*4)+2, ((x-1)*4)+3 )
    pdict[x] = {}
    pdict[x]['state'] = TPstate[e3[x-1]]
    pdict[x]['link_status'] = TPlinkStatus[e4[x-1]]
    pdict[x]['TxGoodPkt'] = e5[((x-1)*4)]
    pdict[x]['TxBadPkt'] = e5[((x-1)*4)+1]
    pdict[x]['RxGoodPkt'] = e5[((x-1)*4)+2]
    pdict[x]['RxBadPkt'] = e5[((x-1)*4)+3]
	
    if (x == max_port_num):
    	myend = "\n"
    print(output_format.format(	x,
								pdict[x]['state'],
                                pdict[x]['link_status'],
                                pdict[x]['TxGoodPkt'],
                                pdict[x]['TxBadPkt'],
                                pdict[x]['RxGoodPkt'],
                                pdict[x]['RxBadPkt']), end=myend)


# In[120]:


if TPLdebug:
    pprint.pprint(pdict)

