#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson
# Description: This takes advantage to IndexedTable's ability to take any str output and index/table it. It acts
# like a interface and toolkit for taking bash command output and formatting it. You can use this to easily import data
# from any command. From here you can use methods to find meaningful data. If you need to turn that meaningful data
# into a nice format for printing then this class has the tools to make that easy.


# This accepts plugins for additional parsing by simple inheritance and a couple of setup methods.
# The plugin object should return the formatted results and update any other attributes required.
# It is expected that formatting of the strFormat, headers, and columns will always be run when the plugin is called.
#   It is also possible to allow these to dynamically generate and to not use them at all.
# All parameters to the plugin should be configured to be optional.
# Parameters passed will be:
#   lines: IndexedTable, output results
#   header: list, the header to use when printing
#   strFormat: str, base format for column width before calculating
#       Format (zero based, sequential digits, any length): '{0:<[0]}{1:<[1]}'
#           Each digit within square brackets should replaced with the column width for that column of output
# The columns (dict) argument is worth noting as well since it is important to the GenericInputParser.
#   Format (zero based, sequential digits, any length): {'HEAD': 0, 'HEADER': 1}
# The following methods from GenericInputParser should be called before super() in the plugin init method:
#   self.set_parser_plugin_class(ClassName)
#   self.set_parser_plugin(ClassName.classMethod)
# Do not instantiate the class or pass the executed method. Instead use the uninstantiated objects name as shown.
# Only use self for the calls to the setup methods, not for the parameters passed in.

from __future__ import annotations


from functools import partial
from collections import defaultdict
try:
    from PyCustomCollections.CustomDataStructures import IndexedTable
except:
    from PyCustomCollections.PyCustomCollections.CustomDataStructures import IndexedTable
from typing import Any, Union, Optional, List, Iterable, Dict, AnyStr, Callable
import logging

# logging.basicConfig(format='%(module)s %(funcName)s %(lineno)s %(message)s', level=logging.DEBUG)
log = logging.getLogger('GenericInputParser')


def dummy_func(*args, **kwargs):
    return kwargs.get('_default', None)


class GenericInputParser(IndexedTable):
    """ <a name="GenericInputParser"></a>

    """

    tail = None
    head = None
    exclude = None
    include = None
    source = None
    strFormat = None
    strFormatBackup = None
    header = None
    columns = None
    parserPlugin = None
    parserPluginClass = None
    _kwargList = ['source', 'tail', 'head', 'exclude', 'include', 'strFormat', 'header', 'columns']

    def __init__(self, source: Optional[Any] = None, tail: int = 0, head: int = 0, exclude: Optional[bool] = None,
                 include: Optional[bool] = None, strFormat: Optional[AnyStr] = None, header: Optional[List] = None,
                 columns: Optional[Dict] = None, **kwargs):
        """
            You may be asking why all the parameters if the function 'parse' has the same ones. The reason is
            simple. Making a class specific to an input format. This can be declared to be already setup to
            take input from a certain command such as 'ps' or 'df'. Then all that needs to happen is run: 'parse'.
        - :param source: The source 'str'. Needs to be a 'str'!
        - :param tail: The opposite of what a bash cmd 'tail' does. Instead of showing you only the number specified it
            removes that number from the bottom of the input.
        - :param head: Just like tail, this is opposite of what a bash cmd 'head' does. Instead of showing you only the
            number specified it removed that number of lines off the top of the input source.
        - :param exclude: This runs a very simple string 'in' comparison against each line before it is appended to the
            table. If the comparison returns True then it skips.
        - :param include: This overrides exclude. If something is in include then it will not exclude the item.
        - :param columns: This is based to the KeyedTable as its 'columns' parameter. However it also sames it here.
            The goal is so that it can later be used as a header when trying to print.
        - :param strFormat: This is a string that utilizes Python's '.format' str function. The goal here is to have
            custom format options.
        - :return:
        """
        log.debug("Creating GenericInputParser")
        super(GenericInputParser, self).__init__(columns=columns, **kwargs)
        if self._setup(source=source, tail=tail, head=head, exclude=exclude, include=include,
                       strFormat=strFormat, header=header, columns=columns, **kwargs):
            self.parse(refreshData=True)

    # NOTE: use with caution inside command modules: by default GenericCmdModule will override this
    def __call__(self, source: Optional[Any] = None, refreshData: bool = True, *args, **kwargs) -> GenericInputParser:
        if self._setup(source=source, **kwargs):
            self.parse(source=source, refreshData=refreshData, *args, **kwargs)
        return self

    def __str__(self) -> AnyStr:
        return self.format_output()

    def _setup(self, *args, **kwargs) -> bool:
        """
            This is used exclusively by init and call methods.

        - :param args: This is ignored
        - :param kwargs:
        - :return:
        """
        for kwarg in self._kwargList:
            setattr(self, kwarg, kwargs.get(kwarg))
        if self.columns is None:
            self.columns = {}
        if self.source is not None:
            if self.source:
                return True
        return False

    def set_str_format(self, strFormat: AnyStr) -> None:
        """

        - :param strFormat: (str)
        - :return:
        """

        self.strFormat = strFormat
        if not strFormat or '[0]' in strFormat:
            self.strFormatBackup = strFormat

    def set_parser_plugin(self, plugin: Callable) -> GenericInputParser:
        """
            parserPlugin after the list has been format.
        - :param plugin:
        - :return:
        """

        self.parserPlugin = partial(plugin, self)
        return self

    def set_parser_plugin_class(self, klas: Any) -> GenericInputParser:
        """
            parserPluginClass is used instead of GenericInputParser if this is set
        - :param klas:
        - :return:
        """

        self.parserPluginClass = klas
        return self

    def parse(self, source: Optional[Any] = None, tail: Optional[int] = None, head: Optional[int] = None,
              exclude: Optional[bool] = None, include: Optional[bool] = None, strFormat: Optional[AnyStr] = None,
              header: Optional[Iterable] = None, columns: Optional[Dict] = None,
              refreshData: bool = False, **kwargs) -> None:
        """

        - :param source:
        - :param tail:
        - :param head:
        - :param exclude:
        - :param include:
        - :param strFormat:
        - :param header:
        - :param columns:
        - :param refreshData:
        - :param kwargs:
        - :return:
        """

        if strFormat is None:
            strFormat = self.strFormatBackup
        if not source:
            if not self.source and self.parserPlugin:
                return self.parserPlugin()
            source = self.source
        if tail is not None:
            tail = int(tail)
        else:
            tail = self.tail
        if head is not None:
            head = int(head)
        else:
            head = self.head
        if not exclude:
            exclude = self.exclude
        if not include:
            include = self.include
        if header is None:
            header = self.header
        if columns is None:
            columns = self.columns

        lines = []
        if isinstance(source, list):
            if isinstance(source[0], list):
                lines = iter(source)
            elif isinstance(source[0], str):
                lines = (l.split() for l in filter(None, source))
            elif self.parserPlugin:
                return self.parserPlugin()
        elif isinstance(source, str):
            lines = (l.split() for l in filter(None, source.splitlines()))
        elif self.parserPlugin:
            return self.parserPlugin()

        # Below if statement creates the columns for IndexedTable
        if type(header) is int:
            for i, line in enumerate(lines):
                if i == header:
                    self.header = line
                    break

        if type(self.header) is list and not columns:
            self.columns = dict(((v, i) for i, v in enumerate(self.header)))

        lines = GenericInputParser._parse_lines(lines, exclude=exclude, include=include)

        if self.parserPlugin:
            lines = self.parserPlugin(lines, header, strFormat)
        if refreshData:
            self.clear()

        if head:
            for i, _ in enumerate(lines, start=1):
                if i == head:
                    break

        if tail:
            lines = list(lines)
            self.extend(lines[:len(lines) - abs(tail)])
            del lines
        else:
            self.extend(lines)
        del source 

    def format_lines(self, lines: Iterable, header: Optional[Iterable] = None,
                    strFormat: Optional[AnyStr] = None) -> AnyStr:
        """

        - :param lines: (Iterable)
        - :param header: (Iterable/None)
        - :param strFormat: (Str/None)
        - :return: Str
        """

        outputStr = ''
        if header is None:
            header = self.header
        if strFormat is None:
            strFormat = self.strFormat
        if strFormat:
            if header:
                outputStr = strFormat.format(*header)
            for line in lines:
                try:
                    outputStr += "\n" + strFormat.format(*line)
                except:
                    outputStr += '\n' + ' '.join(line)
        else:
            if header:
                outputStr = ' '.join(header)
            for line in lines:
                outputStr += '\n' + ' '.join(line)
        return outputStr

    def format_output(self, header: Optional[Iterable] = None, strFormat: Optional[AnyStr] = None) -> AnyStr:
        """

        - :param header: (Iterable/None)
        - :param strFormat: (Str/None)
        - :return: (Str)
        """

        return self.format_lines(lines=self, header=header, strFormat=strFormat)

    # The following functions are overrides of functions from IndexedTable. They simply take the values returned from
    # IndexedTable and puts them in a new instance of GenericInputParser.
    def search_by_column(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'search_by_column' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).search_by_column(*args, **kwargs))

    def search(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'search' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).search(*args, **kwargs))

    def correlation(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'correlation' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).correlation(*args, **kwargs))

    def incomplete_row_search(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'incomplete_row_search' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).incomplete_row_search(*args, **kwargs))

    def fuzzy_get_values(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'fuzzy_get_values' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).fuzzy_get_values(*args, **kwargs))

    def fuzzy_get_pairs(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'fuzzy_get_pairs' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).fuzzy_get_pairs(*args, **kwargs))

    def fuzzy_search(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'fuzzy_search' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).fuzzy_search(*args, **kwargs))

    def fuzzy_column(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'fuzzy_column' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).fuzzy_column(*args, **kwargs))

    def fuzzy_correlation(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """ Override 'fuzzy_correlation' to return a new GenericInputParser or a special parser class """
        kwargs['convert'] = False
        return self._run_parser_class(values=super(GenericInputParser, self).fuzzy_correlation(*args, **kwargs))

    def _run_parser_class(self, values: IndexedTable) -> Union[GenericInputParser, Any]:
        """

        - :param values: (IndexedTable)
        - :return: (GenericInputParser/Any)
        """
        newArgs = {'tail': self.tail, 'head': self.head, 'exclude': self.exclude, 'include': self.include,
                   'strFormat': self.strFormat, 'header': self.header, 'columns': self.columns}
        if self.parserPluginClass:
            newObj = self.parserPluginClass(values, **newArgs)
            getattr(newObj, 'set_parser_plugin_class', dummy_func)(self.parserPluginClass)
            getattr(newObj, 'set_parser_plugin', dummy_func)(self.parserPlugin)
            return newObj
        newObj = GenericInputParser(values, **newArgs)
        newObj.set_parser_plugin_class(self.parserPluginClass)
        newObj.set_parser_plugin(self.parserPlugin)
        return newObj

    @staticmethod
    def _parse_lines(lines: Iterable, exclude=False, include=False) -> Iterable:
        if exclude and not include:
            return (line for line in lines if exclude not in line)
        elif include and not exclude:
            return (line for line in lines if include in line)
        elif exclude and include:
            return (line for line in lines if include in line or exclude not in line)
        else:
            return iter(lines)

    @staticmethod
    def trim_to_Columns(genericInput: GenericInputParser, columnList: list) -> GenericInputParser:
        """ Trim the data so that only the requested columns are included
            NOTE: for command modules the genericInput will use the same parser as the main module
            this means that the update to the header update here may cause the main module to fail to print

        - :param genericInput: data structure object from GenericInputParser, usually self
            this object is required to have a columns in order to parse
        - :param columnList: columns to include in the results
        """

        genericInput.parse(source=map(list, zip(*[genericInput[c] for c in columnList])),
                                columns=dict(zip(columnList, range(len(columnList)))),
                                strFormat=''.join(['{%s:<[%s]}' % (s, s) for s in range(len(columnList))]),
                                header=columnList, refreshData=True)
        return genericInput

    @staticmethod
    def convert_spaces(genericInput: GenericInputParser, replaceList: Optional[list] = None,
                       columnList: Optional[list] = None) -> GenericInputParser:
        """ Convert characters in results from GenericInputParser usually used to convert to or from spaces to allow the
            data to be printed properly convert spaces to something else in columns to reparse the data convert
            characters back to spaces just before printing the data by default this will convert the default underscore
            back to a space.

        - :param genericInput: data structure object from GenericInputParser, usually self
            this object is required to have a columns in order to parse
        - :param replaceList: list to be used by str.replace(*[replace, with])
        - :param columnList: optional columns to specify where the replacement should happen for each value
        """

        if columnList:
            columnList = [genericInput.columns.get(c) for c in columnList]
        else:
            columnList = genericInput.columns.values()
        if not replaceList:
            replaceList = ['_', ' ']
        for d in range(len(genericInput)):
            for f in range(len(genericInput[d])):
                if f in columnList:
                    genericInput[d][f] = genericInput[d][f].replace(*replaceList)
        return genericInput

    @staticmethod
    def convert_results_to_bytes(genericInput: GenericInputParser, columnList: list,
                                 convertSpaces: Optional[bool] = None,
                                 _baseSize: str = None, default: int = 0) -> GenericInputParser:
        """
        Convert the results to byte notation appropriate for the value.
        You cannot undo this action and it may interfere with comparisons.
        Use only for the final printing of output.
        :param genericInput: data structure object from GenericInputParser, usually self
            this object is required to have a columns in order to parse
        :param columnList: list of column to convert
        :param convertSpaces: convert spaces to underscores so the data can still work with GenericInputParser
        :param _baseSize: smallest starting size for conversion
        """
        if not genericInput or not genericInput.columns or [c for c in columnList if genericInput[c][0][-1] == 'B']:
            return genericInput

        for column in columnList:
            newColumn = [GenericInputParser.convert_bytes(float(x), _baseSize=_baseSize).replace(' ', '_')
                         if x and str(x).isdigit() else f"{default}"
                         for x in genericInput[column]]
            for v in range(len(genericInput)):
                genericInput[v][genericInput.columns[column]] = newColumn[v]
        genericInput.parse(source=genericInput, refreshData=True)
        if not convertSpaces:
            return GenericInputParser.convert_spaces(genericInput, columnList=columnList)
        return genericInput

    @staticmethod
    def convert_bytes(num: Union[float, int], suffix: str = 'B', base: float = 1024.0,
                      _baseSize: Optional[str] = None, **kwargs) -> str:
        """  Converter for bytes to whatever larger measurement is appropriate for the size  """
        baseList = [' ', ' K', ' M', ' G', ' T', ' P', ' E', ' Z']
        if _baseSize:
            baseList = []
            for bl in reversed([' ', ' K', ' M', ' G', ' T', ' P', ' E', ' Z']):
                baseList.append(bl)
                if bl == ' ' + _baseSize.upper():
                    break
            baseList.reverse()
        for unit in baseList:
            if abs(float(num)) < base:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= base
        return "%.1f%s%s" % (num, ' Y', suffix)

    @staticmethod
    def revert_bytes(num: Union[float, int], base: float = 1024.0, **kwargs) -> float:
        """  Reverts the converted measurement from convert_bytes to its previous value  """

        def _getDigits(tmpNum):
            for aNum in str(tmpNum):
                try:
                    return float(tmpNum)
                except Exception:
                    tmpNum = tmpNum[:-1]

        def _getLetters(tmpNum):
            return tmpNum[len(str(_getDigits(tmpNum))):]

        baseList = ['B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
        numDigits = _getDigits(num)
        for unit in range(len(baseList) - 1, -1, -1):
            if _getLetters(num).count(baseList[unit]) == 1:
                if unit > 0:
                    for mult in range(unit):
                        numDigits *= base
                return numDigits


class BashParser(GenericInputParser):

    def __init__(self, *args, **kwargs):
        self.set_parser_plugin_class(BashParser)
        self.set_parser_plugin(BashParser.bash_parser)
        super(BashParser, self).__init__(*args, **kwargs)

    def bash_parser(self, lines: Optional[Iterable] = None, header: Optional[List] = None,
                   strFormat: Optional[AnyStr] = None, columns: Optional[Dict] = None):
        lines = lines or []
        if not isinstance(lines, list):
            lines = list(lines)
        header = header or self.header
        if type(header) is int:
            for i, line in enumerate(lines):
                if i == header:
                    header = line
                    break
        shortestLine = self._get_shortest_line(lines, header)
        lines = self._reformat_output(lines, shortestLine)
        self.header = header = self._format_header(shortestLine, header)
        columns = columns or self.columns
        self.columns.update(self._format_columns(shortestLine, header, columns))
        strFormat = strFormat or self.strFormat or self._str_formatter(shortestLine)
        self.set_str_format(strFormat)
        self.set_str_format(self._update_str_format(strFormat, lines, shortestLine, header))
        return iter(lines)

    # Private Functions
    @staticmethod
    def _get_shortest_line(sourcelines: Optional[Iterable] = None, sourceheader: Optional[List] = None) -> int:
        if sourcelines:
            return min(map(len, sourcelines))
        if sourceheader is not None:
            return len(sourceheader)
        return 1

    @staticmethod
    def _format_header(shortestLine: int, header: List) -> List:
        if header:
            headerLen = len(header)
            for headerItem in range(shortestLine - headerLen):
                header.append(str(headerItem + headerLen))
        return header

    @staticmethod
    def _format_columns(shortestLine: int, header: List, columns: Dict) -> Dict:
        if columns:
            columnsLen = len(columns)
            for columnsItem in range(shortestLine - columnsLen):
                columns.update({str(columnsItem + columnsLen): columnsItem + columnsLen})
            return columns
        if header:
            return dict(zip(header, range(shortestLine)))
        return dict(enumerate(range(shortestLine)))

    @staticmethod
    def _str_formatter(shortestLine: int) -> AnyStr:
        return ''.join(['{%s:<[%s]}' % (s, s) for s in range(shortestLine - 1)]) + '{%s:<}' % (shortestLine - 1)

    @staticmethod
    def _update_str_format(sourceformat: AnyStr, sourcelines: List, shortestsource: int,
                         sourceheader: Optional[List] = None) -> AnyStr:
        for skey, svalue in BashParser._line_size_inspection(sourcelines, shortestsource, sourceheader).items():
            sourceformat = sourceformat.replace('[%s]' % skey, str(svalue + 1))
        return sourceformat

    @staticmethod
    def _line_size_inspection(lines: List, minLength: int, header: Optional[List] = None) -> Dict:
        if header:
            header = BashParser._reformat_output([header], minLength).pop()
            lines.append(header)
        indexMap = [list(map(len, line)) for line in lines]
        columnSize = defaultdict(list)
        [columnSize[x].append(item[x]) for item in indexMap for x in range(minLength)]
        for key, value in columnSize.items():
            columnSize[key] = max(value)
        if header:
            lines.remove(header)
        return columnSize

    @staticmethod
    def _reformat_output(resultsList: List, shortestLine: int) -> List:
        shortestLine -= 1
        for resultsLine in range(len(resultsList)):
            if len(resultsList[resultsLine]) >= shortestLine:
                templine = resultsList[resultsLine][:shortestLine]
                templine.append(' '.join(resultsList[resultsLine][shortestLine:]))
                resultsList[resultsLine] = templine
        return resultsList
