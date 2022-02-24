Custom Parsers
==============

-----
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://choosealicense.com/licenses/gpl-3.0/)
[![Docs](https://readthedocs.org/projects/ansicolortags/badge/?version=latest)](https://orcephrye.github.io/PyCustomCustomParsers/)

### Requiremnets
```sh
# Install requirements (pip should point to a Python 3.7+ environment.)
pip install -r requirements.txt
```

## External Parsers

External Parsers is a package mostly dedicated to Json and XML parsing/searching and manipulation

## Generic Parser

Is a complementary package for the IndexList. It takes input from a command line/shell environment and attempts too 
parse that input. 

* NOTE: This package also contains the Class 'BashParser' which is specifically used to parse common BASH/SHELL commands.

## Date Parse Line

This tool is used to find and parse the date time stamp within a line without knowing what format the line uses. It also
saves how it parsed the text so that future parsing can be done quicker.

* NOTE: The dateParser requires the following python modules when being packaged: dateutil, pytz, six
