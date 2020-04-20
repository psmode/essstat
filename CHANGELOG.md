# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).
 
## Unreleased

### Fixed

- [essstat.xlsm] Dynamic rescaling of X-axis labels and tickmarks


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
 
