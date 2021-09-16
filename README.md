# Custom Parsers

### Requiremnets
```shell
python3 -m pip install --upgrade pytz six
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
