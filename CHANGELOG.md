# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [1.1.0] - 2025-08-23

### Changed
- [Template_essstat.json] Replaced {$ESS_POLL_FAIL} as a counter based quantity with 
{$ESS_POLL_FAIL_INTERVAL} a time based quantity with default 180s.
- [Template_essstat.json] To better normalize and tidy template code, the template is
now imported, then exported to ensure consistent formatting and make tracking deltas
easier.

### Fixed
- [Template_essstat.json] Corrected error in number of ports handling not based on 
parameter from data return.
- [Template_essstat.json] Fixed trigger logic to alert on repeated polling failures.
Trigger is drive by the time based macro {$ESS_POLL_FAIL_INTERVAL}


## [1.0.0] - 2025-08-22

### Added
- [Template_essstat.json] Automatic population of Inventory fields.
- [Template_essstat.json] Trigger warning alarm on successive polling failures.
- [essstat.conf] UserParameter essstat.info[*] to support retrieval of data for Inventory
- [essstat.py] --debug to support diagnostic output including full dumps of returned data
- [essstat.py] --version to show script version 
- [essstat.py] --info to support return of system information for use with Zabbix Inventory

### Changed
- [Template_essstat.json] Modified all macros to use names starting with ESS_
instead of SWITCH_ and added a few more. This gives:
  - {$ESS_1LINE_INTERVAL} (default 60s) Interval between polls collecting all per-port metrics
  - {$ESS_INFO_INTERVAL} (default 1h) Interval between polls for inventory data
  - {$ESS_IP} (default {HOST.HOST}) The IP address or resolvable hostname of the switch
  - {$ESS_POLL_FAIL} (default 3) This many failures in a row for the 1line poll will trigger a warning
  - {$ESS_PWD} (default changeme) Password used to access the switch
  - {$ESS_USER} (default admin) Administrative username for switch management
- [essstat.py] Short forms of --port and --metric are now -I and -M respectively


## [0.8.1] - 2025-08-21

### Changed
- [Template_essstat.json] Modified template to collect all switch port metrics 
in a single poll, then break out the per-port metrics as dependent items in 
Zabbix.
- [essstat.conf] Additional UserParameter to support collecting all switch port
metrics with the --1line argument


## [0.8.0] - 2025-08-20

### Added
- [Template_essstat.json] Added Zabbix template for automated switch monitoring. When
linked to a suitably profiles Host definition in Zabbix, the template will support 
low level discovery (LLD) of the ports and metrics. The template will also create 
per-port graphs which will pull together all metrics for a given port in a single 
graph. Note that at this time, the method used to populate the port metrics is terribly
inefficient and will need to be improved, probably leveraging dependent items.
- [essstat.conf] Required to define UserParameter settings for execution of the script
by Zabbix Agent 2. This file needs to be placed in /etc/zabbix/zabbix_agent2.d/

### Changed
- [essstat.py] New processing options have been defined:
-- -l, --lld     output in Zabbix Low-Level Discovery JSON format
-- -m, --metric  metric name for specific port (state, link_status, TxGoodPkt, TxBadPkt, RxGoodPkt, RxBadPkt)
-- -p, --port    specific port number to retrieve


## [0.7.0] - 2023-06-13

### Added
- [requirements.txt] Added Dockerfile by [robrankin](https://github.com/robrankin)

## [0.6.0] - 2022-06-21

### Added
- [essstat.py] Added support for JSON output by [robrankin](https://github.com/robrankin)


## [0.5.0] - 2021-04-25

### Addeded
 - [essstat.py] Added proper support for TL-SG1024DE model as per Issue #4.
Many thanks to @FreedThx for his report and for providing the output from
that model that enabled the development of this code change.


## [0.4.1] - 2021-04-03

### Fixed

- [essstat.xlsm] Dynamic rescaling of X-axis labels and tickmarks
- [essstat.py] Fix for Issue #3 reported by jan-lukes, AttributeError: 'NoneType'
object has no attribute 'group'. The problem was a code compatibility issue
with newer versions of BeautifulSoup sometime after version 4.8.2. Changing
references to soup.script.text to soup.script.string fixes the problem and
is backwards compatible, at least to beautifulsoup4-4.8.2.


## [0.4.0] - 2020-04-01

### Added

- [essstat.xlsm] Macro-enabled Excel workbook will automatically construct 
a query and execute a web GET operation against the monitoring server using 
the `essstat2.cgi` script. It uses the returned data to plot charts of the
port statistics using dynaic chart ranges.
- [essstat2.cgi] This CGI script is designed to support operation of the essstat.xlsm
Excel workbook. This script will return the average packets per second rate since
the previous record.


## [0.3.2] - 2020-03-30

### Added
 - [essstat-TPLhost.xlsx] Excel workbook for charting statistics accumulated
 in a CSV file. See README.md for information about how to use this workbook
 as well as how to accumulate CSV data with a cron job.
 - [essstat.cgi] A cgi script to use with the Apache httpd to support remote
 query and retrieval from stored CSV files accumulating switch port
 statistics.

### Changed
 - [essstat.py] Modified --1line output to use only numeric codes for
 port state and link status. This is a preferred approach since it will use
 much less disk space when accumulating in a CSV file.


## [0.3.0] - 2020-03-29

### Added
 - [essstat.py] timestamp as first output line (yyyy-mm-dd HH:MM:SS format)
 - [essstat.py] --statsonly option to supress timestamp and max_port_count output
 - [essstat.py] --1line option for convenient accumulation ot a CSV file
 - [essstat.py] Implemented error handling. Errors in communicaitons with the
 switch will result in an error status return and output to stderr starting with
 `ERROR:`

### Changed
 - [essstat.py] Python3 shebang
 - [essstat.py] Updated TPlinkStatus dictionary
  
### Fixed
 - [essstat.py] Reverted funky quotes added around `__xxx__` documentation variables 
 
 
## [0.2.0] - 2020-03-27
  
Initial releasse to GitHub.
 
### Added

 - [essstat.py] Initial release.

### Changed
  

### Fixed
 
