# essstat - TP-Link Easy Smart Switch port statistics

[TP-Link Easy Smart Switches](https://www.tp-link.com/us/business-networking/easy-smart-switch/) are a family of managed switches capable of supporting QoS, VLANs and Link Aggregation Groups (LAGs).
They are managed through a web based interface, giving access a number of functions, including basic packets counters per-port. 
Unfortunately, these switches do not implement SNMP for access to these counters, nor do they appear to implement a discrete URL for
direct access to this information. This project addresses this issue to produce per-port statistics from a single command line invocation 
with output that can be trivially parsed for formatted output, or entered into a monitoring system like Zabbix.

This project has been tested against TP-Link switch models TL-SG1016DE and TL-SG108E. It should also be compatible with the other 
members of this family, including the TL-SG105E and TL-SG1024DE.


## Major Components

*essstat.py* is a lightweight utility is used to pull port statistics from the switch and output in a readily parsable format. Additional 
code will be added to parse and either output or store these statistics.


### essstat.py

This lightweight Python application performs a quick login through the switch's web based administrative interface, and then queries the 
unit for the current port statistics. Credentials for accessing the unit are passed on the command line. The utility was coded with 
Python &nbsp;3.6 and uses the [Beautiful Soup](https://pypi.org/project/beautifulsoup4/) library.

#### Usage

    essstat.py [-h] [-1] [-d] -p TPpswd [-s] [-u TPuser] TPhost
    
#### Options

##### positional arguments:

    TPhost                IP address or hostname of switch

##### optional arguments:

    -h, --help            show this help message and exit
    -1, --1line           output in a single line
    -d, --debug           activate debugging output
    -p TPpswd, --password TPpswd
                          password for swtich access
    -s, --statsonly       output post statistics only
    -u TPuser, --username TPuser
                          username for swtich access

#### Example

    $ essstat.py myswitch -p ChangeMe
    2020-03-28 11:25:15
    max_port_num=8
    1;Enabled;Link Down;0,0,0,0
    2;Enabled;10M Full;3568644976,0,3144940915,0
    3;Enabled;1000M Full;237232286,0,66662515,0
    4;Enabled;1000M Full;4019260430,0,3721138807,0
    5;Enabled;1000M Full;1300360968,0,355032522,0
    6;Enabled;Link Down;0,0,0,0
    7;Enabled;1000M Full;2903398648,0,4293632425,5
    8;Enabled;Link Down;0,0,0,0


### Accumulate Data in CSV

The simplest way to accumulate data from the switches is to have *essstat.py* execute with the `--1line` option and
append the output to a CSV file. You can then pull down a copy of the CSV file and process the raw data through
this Excel workbook to produce a dynamic chart that will automatically rescale to the available data. 

The first step is to setup a directory where the CSV files will accumulate the data. I chose to run all this under the 
zabbix user that supports the monitoring application on this host. You may choose a different user, but just make sure 
that the group of the directory matches the group of the user you will use.

    $ ls -ald  /var/log/essstat
    drwxrwxr-x. 2 root zabbix 68 Mar 30 10:56 /var/log/essstat

Next, create the cron job(s) for periodic data collection. To do this, create the file `/etc/cron.d/essstat` and add
one schedule for each switch you will monitor. To make this reasonably self-maintaining, include the current year as
part of the CSV file specification.

    */10 * * * *    zabbix  /usr/local/bin/essstat.py -1 -p ChangeMe1 orange >> /var/log/essstat/essstat-orange-`date +\%G`.csv
    */10 * * * *    zabbix  /usr/local/bin/essstat.py -1 -p ChangeMe2 black >> /var/log/essstat/essstat-black-`date +\%G`.csv

In the above example, there are two switches being monitored, named `orange` and `black`. For each switch, data collection
will run every 10 minutes starting on each hour. The data for `orange` will be accumulated in the file
`/var/log/essstat/essstat-orange-2020.csv` during the calendar year 2020. 


### essstat-TPLhost.xlsx

This Excel workbook prototype can be used to process a copy of the raw `--1line` data output from *essstat.py* that has been
accumulated in a CSV file. Start by copying the file to a new name, incorporating the name of the switch being 
monitored. This will be the switch monitoring notebook. For example:

    C:\user\me\Documents> copy essstat-TPLhost.xlsx essstat-orange.xlsx

Next, download a copy of the [CSV data that has been accumulated on your monitoring host](#Accumulate-Data-in-CSV) and open it 
in Excel, as well as the switch monitoring workbook. At this stage, you will need to copy the data from the CSV to the RawData tab
of the switch monitoring notebook *by value*. To do this, go to the CSV file in Excel and select the top-left cell, `A1`. In Windows,
you can use the key sequence `Ctrl-Shift-End` to select all the data, then press `Ctrl-Insert` to copy all of it. Then go to the switch
monitoring workbook and select the first data cell in the **RawData** tab at `A2` (top-left cell, below the headings). Right click 
and choose the option to paste values. With the raw data in place, you should scroll down to make note of the last populated row. The 
original CSV file can now be closed.

Click on the **PPS Table** tab to extend the analysis table and select the metric to be charted. The key is to extend the structured 
table range to match the available **RawData**. Press `Ctrl-End` to locate the end of the table. Mouse over the tiny square at the 
lower left corner of the cell until your mouse pointer changes to a crosshair. Click and drag down to the same row number as the last 
populated row number in the **RawData** tab. All the formulae and ranges in **PPS Table** and **PPS Chart** will extend automatically.

There are four metrics that are being tracked for each port: Tx Good Packets, Tx Bad Packets, Rx Good Pkts, and Rx Bad Pkts. The 
dropdown at cell `B2` on the **PPS Table** tab is used to select which metric should be populated in the table and charted. 


### essstat.cgi

This CGI script is used to query the [CSV data that has been accumulated on your monitoring host](#Accumulate-Data-in-CSV) and return 
matching entries. The CGI is self-contained, relying only upon access to awk for execution of a simple inline script. There are three 
variables implmented in the CGI:

- esTPLhost: *(required)* The name of the switch as used to store the [accumulated CSV data](#Accumulate-Data-in-CSV).
- esFrom: Return statistics starting with this date/time in format *yyyy-mm-dd&nbsp;HH:MM:SS*. Default value is for January 1st of the 
current year.
- esTo: Return statistics ending with this date/time in format *yyyy-mm-dd&nbsp;HH:MM:SS*. Default value is for all data to the current 
date/time.

Note that partial date/time specifications are allowed, since the matching entries are determined by a simple string comparison. The
From and To dates are allowed to span across a year boundary (e.g. from 2019 to 2020). 

To query the monitoring server for port statistics for the switch known as orange for the time range from 2/23/2020&nbsp;00:00 to 
3/7/2020&nbsp;11:30, the URI would look like:

    http://monitoring.mydomain.com/cgi-bin/essstat.cgi?esTPLhost=orange&esTo=2020-03-07%2011:30&esFrom=2020-02-23


### Zabbix Integration

I am working on a configuration and supporting scripting to dump the stats into Zabbix for monitoring, reporting and event handling (e.g. alert or take action on Link Down events).


## Technical Background

The TP-Link Easy Smart Switch has more capabilities than a completely unmanaged switch. However, the management environment is relatively closed, with only a proprietary management client (Easy Smart Configuration Utility) or a web-based management page on the switch available. Furthermore, there is no support for monitoring the switch with SNMP. This means that our only entry into the switch will be via the protocol used by the proprietary client, or by scaping the web-based management interface on the switch.

First, a little background on the UDP-base Easy Smart Configuration Protocol (ESCP) that this project does ***not*** use. The Easy Smart Configuration Utility interacts with the switch over UDP with broadcasts. The client will send a UDP broadcast from port 29809 to 29808 of a specially encoded discovery packet. Compatible switches on the network will broadcast a response from port 29808 to 29809 than includes the name, model and IP address of the switch. From this point, it is up to the client to encode a login sequence and broadcast this on the network, with the expectation that the specific target switch will receive and process the instruction. This could be to send back information in another broadcast packet, modify the configuration of the switch, or take some other action. 

This design and implementation has a number of issues that should cause some concern which have been highlighted by security researchers ([@chrisdcmoore]( https://twitter.com/chrisdcmoore) in [Information disclosure vulnerability in TP-Link Easy Smart switches](https://www.chrisdcmoore.co.uk/post/tplink-easy-smart-switch-vulnerabilities/) and [@chmod7850](https://twitter.com/chmod750) in [Vulnerability disclosure TP-Link multiples CVEs](https://chmod750.wordpress.com/2017/04/23/vulnerability-disclosure-tp-link/)). While hacking into the ESCP would be easy enough, I really did not like the idea of literally broadcasting credentials across the network on a regular basis to grab statistics.

Using the web-based client is better, but by no means highly secure. Using TCP unicast connections is better, but SSL is not implemented by the switch. While it is possible to reconfigure the switch to use a different administrative username, there is only one username for accessing the switch. This precludes employing role-based access with a dedicated username for reading statistics only. The credential we use to grab the statistics could also be used to access the management interface allowing resetting of counters, reconfiguring the switch or even replacing the firmware. 


___

**Peter Smode**

`psmode [at] kitsnet.us`
