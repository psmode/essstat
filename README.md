# essstat - TP-Link Easy Smart Switch port statistics

[TP-Link Easy Smart Switches](https://www.tp-link.com/us/business-networking/easy-smart-switch/) are a family of managed switches capable of supporting QoS, VLANs and Link Aggregation Groups (LAGs).
They are managed through a web based interface, giving access a number of functions, including basic packets counters per-port. 
Unfortunately, these switches do not implement SNMP for access to these counters, nor do they appear to implement a discrete URL for
direct access to this information. This project addresses this issue to produce per-port statistics from a single command line invocation 
with output that can be trivially parsed for formatted output, or entered into a monitoring system like Zabbix or Prometheus.

This project has been tested against TP-Link switch models TL-SG1016DE, TL-SG108E and TL-SG108PE. It should also be compatible with the other 
members of this family, including the TL-SG105E and TL-SG1024DE.

***
<p align="center">
<B>*** WARNING ***</B>
</p>

The Easy Smart Switch family has a number of unresolved vulnerabilities, including [CVE-2017-17746](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-17746). As described in [https://seclists.org/fulldisclosure/2017/Dec/67](https://seclists.org/fulldisclosure/2017/Dec/67), once a user from a given source IP address authenticates to the web-based management interface of the switch, any other user from that same source IP address is treated as authenticated. 

**The Python scripts in this project should be used only from a host that does not have general user access.**

***


## Major Components

*essstat.py* is a lightweight utility is used to pull port statistics from the switch and output in a readily parsable format. Additional 
code will be added to parse and either output or store these statistics.


### essstat.py

This lightweight Python application performs a quick login through the switch's web based administrative interface, and then queries the 
unit for the current port statistics. Credentials for accessing the unit are passed on the command line. The utility was coded with 
Python&nbsp;3.6 and uses the [Beautiful Soup](https://pypi.org/project/beautifulsoup4/) library.

#### Usage

    essstat.py [-h] [-1] [-d] [-j] [-l] [-P] -p TPpswd [-u TPuser] [-s] [-n PORT] [-M METRIC] TPhost
    
#### Options

##### positional arguments:
```
  TPhost                IP address or hostname of switch
```
##### optional arguments:
```
  -h, --help            show this help message and exit
  -1, --1line           output on a single line (CSV)
  -d, --debug           activate debugging output
  -i, --info            fetch system info instead of port statistics
  -j, --json            output as JSON
  -l, --lld             output in Zabbix LLD JSON format
  -P, --prometheus      output in Prometheus text exposition format (for /metrics scraping)
  -p TPpswd, --password TPpswd
                        password for switch access
  -u TPuser, --username TPuser
                        username for switch access
  -s, --statsonly       output per-port statistics only (one line per port)
  -n PORT, --port PORT  specific port number to retrieve
  -M METRIC, --metric METRIC
                        metric name for specific port (state, link_status, TxGoodPkt, TxBadPkt, RxGoodPkt, RxBadPkt)
  -v, --Version         show program's version number and exit
```

> **Note:** the short flag for `--port` was previously `-P`. It has been renamed to `-n` to free `-P` for `--prometheus`.
> If you have scripts or Zabbix `UserParameter` entries using `-P <number>`, update them to `-n <number>`.

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

#### Docker

The image supports two modes of operation controlled by environment variables.

##### Build

    $ docker build -t essstat .

##### CLI mode (default — original behaviour)

Pass any `essstat.py` arguments directly after the image name, exactly as on the command line:

    $ docker run --rm essstat myswitch -p ChangeMe
    $ docker run --rm essstat myswitch -p ChangeMe -j
    $ docker run --rm essstat myswitch -p ChangeMe -P    # one-shot Prometheus dump to stdout

##### Exporter mode — long-running Prometheus HTTP endpoint

Set `EXPORTER=1` to start a persistent `/metrics` HTTP server instead of running a one-shot scrape.
Credentials and connection details are passed via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EXPORTER` | yes | — | Set to `1` to enable exporter mode |
| `ESS_HOST` | yes | — | Switch IP address or hostname |
| `ESS_PASSWORD` | yes | — | Switch admin password |
| `ESS_USERNAME` | no | `admin` | Switch admin username |
| `ESS_LISTEN` | no | `0.0.0.0:9101` | Address and port to listen on |

    $ docker run -d \
        -e EXPORTER=1 \
        -e ESS_HOST=myswitch \
        -e ESS_PASSWORD=secret \
        -p 9101:9101 \
        essstat

Prometheus then scrapes `http://host:9101/metrics`. Add to `prometheus.yml`:

    scrape_configs:
      - job_name: tplink_switch
        static_configs:
          - targets: ['localhost:9101']

##### Multiple switches with Docker Compose

Run one container per switch, each on its own port:

```yaml
services:
  essstat-sw1:
    image: essstat
    environment:
      EXPORTER: "1"
      ESS_HOST: 192.168.1.10
      ESS_PASSWORD: secret1
    ports:
      - "9101:9101"
    restart: unless-stopped

  essstat-sw2:
    image: essstat
    environment:
      EXPORTER: "1"
      ESS_HOST: 192.168.1.11
      ESS_PASSWORD: secret2
      ESS_LISTEN: 0.0.0.0:9102
    ports:
      - "9102:9102"
    restart: unless-stopped
```

Then in `prometheus.yml`:

    scrape_configs:
      - job_name: tplink_switches
        static_configs:
          - targets:
              - 'localhost:9101'
              - 'localhost:9102'

### Zabbix Integration

Zabbix integration has been developed and tested with Zabbix 7.0 LTS. The approach used is to leverage the Zabbix Agent 2 
on the Zabbix server to execute the data retrieval from the switch. To support this, `Template_essstat.json` has been created
to facilitate discovery and automatic creation of monitored items, graphs and inventory field population. Multiple switches 
may be monitored under separate Zabbix host definitions. 

#### Import template
Import the JSON file to establish the template definition in Zabbix. In Zabbix 7.0, login with administrative privileges and navigate
to **Data Collection** → **Templates**, then click the **Import** button to start the process. See the 
[Templates](https://www.zabbix.com/documentation/current/en/manual/xml_export_import/templates) section in the Zabbix manual for more 
information.

#### Define `UserParameter` for Zabbix Agent2
Place the `essstat.conf` file in directory `/etc/zabbix/zabbix_agent2.d/` with protection so that the Zabbix Agent 2 process can read
it. Once it is in place, restart the zabbix-agent2 service so that the file will be read. 

#### Create a new switch host (repeat per switch)
1. Add host  
    - **Configuration** → **Hosts** → **Create host**  
        - Host name: use the switch name or IP (your choice)  
        - Groups: pick an appropriate host group (e.g., "Network/Switches")  

1. Interface (important)  
    - Add a Zabbix agent interface that points to the Zabbix server's agent, not the switch:  
        - DNS/IP: 127.0.0.1 (or the Zabbix server's IP)  
        - Port: 10050  
    - Rationale: the server polls its own agent, which runs your script and reaches the switch using the key parameters.  

1. Link the template  
    - **Templates** → **Select** → choose `Template ESS Switch`  

1. Set required host-level macros  
    - **Macros tab** → **Add:**  
        - `{$ESS_IP}` = _switch management IP_ or _FQDN_ 
          (If you prefer, you can leave `{$SWITCH_IP}` blank and set it to `{HOST.HOST}`, provided the host name is the switch's resolvable name/IP.)  
        - `{$ESS_PWD}` = •••••• (the real password)  

1. Set optional host-level macros (only if defaults need override)
    - **Macros tab** → **Add:**  
        - `{$ESS_USER}` (default admin) Administrative username for switch management
        - `{$ESS_1LINE_INTERVAL}`(default 60s) Interval between polls collecting all per-port metrics
        - `{$ESS_INFO_INTERVAL}` (default 1h) Interval between polls for inventory data
        - `{$ESS_POLL_FAIL_INTERVAL}` (default 180s) Consistent failures over this time interval for the 1line poll will trigger a warning

1. Save

It may take a few minutes for the LLD to fire and the items and graphs to be created. Multiple switches my be monitored by 
creating multiple hosts in Zabbix. Just be sure to set the Macros for each host correctly. 
![Sample Zabbix chart](./ESS%20Packets%20Zabbix%20Chart.png)


### Prometheus Integration

The `-P` / `--prometheus` flag outputs metrics in [Prometheus text exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/),
suitable for scraping with Prometheus. No additional libraries are required beyond those already used by `essstat.py`.

#### Exported metrics

| Metric | Type | Description |
|--------|------|-------------|
| `tplink_port_state` | gauge | Port administrative state: `1` = Enabled, `0` = Disabled |
| `tplink_port_link_speed_mbps` | gauge | Negotiated link speed in Mbps; `0` = link down or autoneg pending |
| `tplink_port_txgoodpkt_total` | gauge | Cumulative TX good packets (32-bit hardware counter) |
| `tplink_port_txbadpkt_total` | gauge | Cumulative TX bad/error packets (32-bit hardware counter) |
| `tplink_port_rxgoodpkt_total` | gauge | Cumulative RX good packets (32-bit hardware counter) |
| `tplink_port_rxbadpkt_total` | gauge | Cumulative RX bad/error packets (32-bit hardware counter) |

All metrics carry a `host` label set to the switch hostname/IP passed on the command line, and a `port` label with the port number.
`tplink_port_link_speed_mbps` also carries a `link_status` label with the raw status string (e.g. `"1000M Full"`).

> **Why `gauge` instead of `counter` for packet metrics?**  
> The switch hardware counters are 32-bit and wrap at 2³² (~4 billion packets). They also reset to zero on switch reboot.
> Prometheus `counter` type must be strictly monotonic — a wrap or reboot would appear to Prometheus as a massive negative
> delta and corrupt `rate()` calculations. Using `gauge` with `delta()` or `increase()` in Grafana queries is safer and
> more accurate for these counters.

#### Example output

    $ essstat.py myswitch -p ChangeMe -P
    # HELP tplink_port_state Port administrative state (1=Enabled, 0=Disabled)
    # TYPE tplink_port_state gauge
    tplink_port_state{host="myswitch",port="1"} 1 1711929600000
    tplink_port_state{host="myswitch",port="2"} 1 1711929600000
    ...
    
    # HELP tplink_port_link_speed_mbps Negotiated link speed in Mbps (0 = link down / autoneg pending)
    # TYPE tplink_port_link_speed_mbps gauge
    tplink_port_link_speed_mbps{host="myswitch",port="1",link_status="Link Down"} 0 1711929600000
    tplink_port_link_speed_mbps{host="myswitch",port="2",link_status="1000M Full"} 1000 1711929600000
    ...
    
    # HELP tplink_port_txgoodpkt_total Cumulative TX good packets (32-bit hardware counter, resets on reboot)
    # TYPE tplink_port_txgoodpkt_total gauge
    tplink_port_txgoodpkt_total{host="myswitch",port="2"} 3568644976 1711929600000
    ...

#### Option 1: node_exporter textfile collector (simplest)

The easiest way to get metrics into Prometheus is via the
[textfile collector](https://github.com/prometheus/node_exporter#textfile-collector) included in `node_exporter`.
Write the output to a `.prom` file in the collector directory and let `node_exporter` serve it on its `/metrics` endpoint.

Create `/etc/cron.d/essstat-prom` with one entry per switch:

    */1 * * * *  root  /usr/local/bin/essstat.py myswitch -p ChangeMe -P \
                       > /var/lib/node_exporter/textfile_collector/tplink_myswitch.prom.tmp \
                 && mv /var/lib/node_exporter/textfile_collector/tplink_myswitch.prom.tmp \
                       /var/lib/node_exporter/textfile_collector/tplink_myswitch.prom

The atomic `tmp` → final rename prevents Prometheus from scraping a partially written file.

Then add a scrape job to `prometheus.yml` if `node_exporter` is not already scraped:

    scrape_configs:
      - job_name: node
        static_configs:
          - targets: ['localhost:9100']

#### Option 2: standalone HTTP exporter

`essstat_exporter.py` wraps `essstat.py` in a minimal HTTP server so Prometheus can scrape it directly via pull,
without needing `node_exporter` or a cron job.

    $ python3 essstat_exporter.py --host myswitch --password ChangeMe
    Listening on http://0.0.0.0:9101/metrics  (switch: myswitch)

Add to `prometheus.yml`:

    scrape_configs:
      - job_name: tplink_switch
        static_configs:
          - targets: ['localhost:9101']

Run one exporter instance per switch, using different `--listen` ports:

    $ python3 essstat_exporter.py --host switch-a --password secretA --listen 0.0.0.0:9101
    $ python3 essstat_exporter.py --host switch-b --password secretB --listen 0.0.0.0:9102

#### Grafana queries

Once data is flowing into Prometheus, some useful PromQL expressions:

```promql
# TX throughput (packets/sec) per port
# delta() is correct here because these are gauge metrics (not counters)
delta(tplink_port_txgoodpkt_total{host="myswitch"}[1m]) / 60

# RX throughput (packets/sec) per port
delta(tplink_port_rxgoodpkt_total{host="myswitch"}[1m]) / 60

# Ports currently up
tplink_port_link_speed_mbps{host="myswitch"} > 0

# Any ports with TX errors in the last 5 minutes
delta(tplink_port_txbadpkt_total{host="myswitch"}[5m]) > 0

# Any ports with RX errors in the last 5 minutes
delta(tplink_port_rxbadpkt_total{host="myswitch"}[5m]) > 0
```


### Accumulate Data in CSV

A simple way to accumulate data from the switches is to have *essstat.py* execute with the `--1line` option and
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


### essstat.xlsm

This macro-enabled Excel workbook is a way to read and chart the port statistics. The workbook will automatically construct a query and execute a web GET operation against the monitoring server using the [`essstat2.cgi`](#essstat2cgi) script. To configure the workbook for your local installation, the defined name `essstatBaseURL` must be modified to point to the webserver operating on your monitoring host and the name of the CGI script. To make this update in Excel 2019 on Windows, click the Excel **Formulas** tab, then click the `Name Manager` button on the ribbon. Click on the entry for `essstatBaseURL` and modify the entry to suit. Be sure to click the button with the green checkmark to save the modification, close the dialog and save the updated workbook. This needs to be done only once.

When using the workbook, the name of the switch and the reporting from and to date/times are specified in the parameter table at the top left of the **WebData** tab. Click the `Update From Web` button to fetch the data into the table and dynamically update the plot on the **PPS Chart** tab. If the switch under study has only eight ports, the extra ports will be hidden automatically. 

The name of the switch and the metric plotted appears in the title of the chart. Once the metrics have been loaded into the table, the different metrics may be loaded into the chart by selecting from the choices in the dropdown cell next to the 'Chart metric` label. Moving between theses metrics for the same switch does *not* require doing another `Update From Web` operation.

The table on the **LocalPortNames* tab allows you to override the default port names shown in the chart. This table is entirely optional and defining entries for all ports on a given switch is *not* required (it is perfectly fine to define port name overrides for just a couple ports for a given switch). If you have multiple switches, you can add entries for all of them in a single table.


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


### essstat2.cgi

This CGI script is designed to support operation of the [`essstat.xlsm`](#essstatxlsm) Excel workbook. The script supports the same query parameters as `essstat.cgi` and returns data for the same metrics. However, instead of returning raw packets counts in each record, `essstat2.cgi` will return the average packets per second rate since the previous record. The script will calculate the actual delta time between the current and previous record to ensure the rate is accurate. The script also has handling for individual counters resetting to zero as they wrap the maximum integer size for the counter. In such a case, the packet per second rate from the previous interval will be returned for the affected statistic.



## Technical Background

The TP-Link Easy Smart Switch has more capabilities than a completely unmanaged switch. However, the management environment is relatively closed, with only a proprietary management client (Easy Smart Configuration Utility) or a web-based management page on the switch available. Furthermore, there is no support for monitoring the switch with SNMP. This means that our only entry into the switch will be via the protocol used by the proprietary client, or by scaping the web-based management interface on the switch.

First, a little background on the UDP-base Easy Smart Configuration Protocol (ESCP) that this project does ***not*** use. The Easy Smart Configuration Utility interacts with the switch over UDP with broadcasts. The client will send a UDP broadcast from port 29809 to 29808 of a specially encoded discovery packet. Compatible switches on the network will broadcast a response from port 29808 to 29809 than includes the name, model and IP address of the switch. From this point, it is up to the client to encode a login sequence and broadcast this on the network, with the expectation that the specific target switch will receive and process the instruction. This could be to send back information in another broadcast packet, modify the configuration of the switch, or take some other action. 

This design and implementation has a number of issues that should cause some concern which have been highlighted by security researchers ([@chrisdcmoore]( https://twitter.com/chrisdcmoore) in [Information disclosure vulnerability in TP-Link Easy Smart switches](https://www.chrisdcmoore.co.uk/post/tplink-easy-smart-switch-vulnerabilities/) and [@chmod7850](https://twitter.com/chmod750) in [Vulnerability disclosure TP-Link multiples CVEs](https://chmod750.wordpress.com/2017/04/23/vulnerability-disclosure-tp-link/)). While hacking into the ESCP would be easy enough, I really did not like the idea of literally broadcasting credentials across the network on a regular basis to grab statistics.

The approach that this project does use, the web-based client, is problematic as well. Using a TCP unicast connections is better, but SSL is not implemented by the switch. While it is possible to reconfigure the switch to use a different administrative username, there is only one username for accessing the switch. This precludes employing role-based access with a dedicated username for reading statistics only. The credential we use to grab the statistics could also be used to access the management interface allowing resetting of counters, reconfiguring the switch or even replacing the firmware. 

**Worse still are the vulnerabilities reported in [CVE-2017-17746](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-17746)**. As described in [https://seclists.org/fulldisclosure/2017/Dec/67](https://seclists.org/fulldisclosure/2017/Dec/67), once a user from a given source IP address authenticates to the web-based management interface of the switch, any other user from that same source IP address is treated as authenticated. This condition is created by the execution of the Python scripts in this project, where other users logged into or tunneling through the same host would then have unauthenticated access to the management interface of the switch. This problem can be mitigated by running the scripts from a dedicated management host. Use of a dedicated out-of-band management LAN could offer protection as well, but these switches are unlikely to be used in such an elaborately structured environment.

___

**Peter Smode**

`psmode [at] kitsnet.us`
