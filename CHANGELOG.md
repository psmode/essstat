# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).
 
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
 
