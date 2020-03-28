# essstat - TP-Link Easy Smart Switch port statistics

[TP-Link Easy Smart Switches](https://www.tp-link.com/us/business-networking/easy-smart-switch/) are a family of managed switches capable of supporting QoS, VLANs and Link Aggregation Groups (LAGs).
They are managed through a web based interface, giving access a number of functions, including basic packets counters per-port. 
Unfortunately, these switches do not implement SNMP for access to these counters, nor do they appear to implement a discrete URL for
direct access to this information. This utility addresses this issue to produce per-port statistics from a single command line invocation 
with output that can be trivially parsed for formatted output, or entered into a monitoring system like Zabbix.

This project has been tested against TP-Link switch models TL-SG1016DE and TL-SG108E. It should also be compatible with the other 
members of this family, including the TL-SG105E and TL-SG1024DE.


## Technical Background
tbd


## Major Components
*essstat.py* is a lightweight utility is used to pull port statistics from the switch and output in a readily parsable format. Additional 
code will be added to parse and either output or store these statistics.


### essstat.py
This lightweight Python application performs a quick login through the switch's web based administrative interface, and then queries the 
unit for the current port statistics. Credentials for accessing the unit are passed on the command line. The utility was coded with 
Python &nbsp;3.6 and uses the <a href=”https://pypi.org/project/beautifulsoup4/”>Beautiful Soup</a> library.

#### Usage
    essstat.py [-h] [-d] -p TPpswd [-s] [-u TPuser] TPhost
    
#### Options

##### positional arguments:

    TPhost                IP address or hostname of switch

##### optional arguments:

    -h, --help            show this help message and exit
    -d, --debug           activate debugging output
    -p TPpswd, --password TPpswd
                          password for swtich access
    -s, --statsonly       output post statistics only
    -u TPuser, --username TPuser
                          username for swtich access



### Zabbix Integration



___

**Peter Smode**

`psmode [at] kitsnet.us`
