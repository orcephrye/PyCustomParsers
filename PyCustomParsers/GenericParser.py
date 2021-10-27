#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson
# Description: This takes advantage to IndexList's ability to take any str output and index/table it. It acts
# like a interface and toolkit for taking bash command output and formatting it. You can use this to easily import data
# from any command. From here you can use methods to find meaningful data. If you need to turn that meaningful data
# into a nice format for printing then this class has the tools to make that easy.


# This accepts plugins for additional parsing by simple inheritance and a couple of setup methods.
# The plugin object should return the formatted results and update any other attributes required.
# It is expected that formatting of the strFormat, headers, and columns will always be run when the plugin is called.
#   It is also possible to allow these to dynamically generate and to not use them at all.
# All parameters to the plugin should be configured to be optional.
# Parameters passed will be:
#   lines: IndexList, output results
#   header: list, the header to use when printing
#   strFormat: str, base format for column width before calculating
#       Format (zero based, sequential digits, any length): '{0:<[0]}{1:<[1]}'
#           Each digit within square brackets should replaced with the column width for that column of output
# The columns (dict) argument is worth noting as well since it is important to the GenericInputParser.
#   Format (zero based, sequential digits, any length): {'HEAD': 0, 'HEADER': 1}
# The following methods from GenericInputParser should be called before super() in the plugin init method:
#   self.setParserPluginClass(ClassName)
#   self.setParserPlugin(ClassName.classMethod)
# Do not instantiate the class or pass the executed method. Instead use the uninstantiated objects name as shown.
# Only use self for the calls to the setup methods, not for the parameters passed in.

from __future__ import annotations

# import os, sys, inspect
# currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
# parentdir = os.path.dirname(currentdir)
# sys.path.insert(0, parentdir)

import gc
from typing import Any, Union, Optional, List, Iterable, Dict, AnyStr, Callable
try:
    from PyCustomCollections.CustomDataStructures import IndexList
except:
    from PyCustomCollections.PyCustomCollections.CustomDataStructures import IndexList
from collections import defaultdict
import logging


# logging.basicConfig(format='%(module)s %(funcName)s %(lineno)s %(message)s', level=logging.DEBUG)
log = logging.getLogger('GenericInputParser')


class GenericInputParser(IndexList):
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
            You may be asking why all the parameters if the function 'parseInput' has the same ones. The reason is
            simple. Making a class specific to an input format. This can be declared to be already setup to
            take input from a certain command such as 'ps' or 'df'. Then all that needs to happen is run: 'parseInput'.
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
            self.parseInput(refreshData=True)

    # NOTE: use with caution inside command modules: by default GenericCmdModule will override this
    def __call__(self, source: Optional[Any] = None, refreshData: bool = True, *args, **kwargs) -> GenericInputParser:
        if self._setup(source=source, **kwargs):
            self.parseInput(source=source, refreshData=refreshData, *args, **kwargs)
        return self

    def __str__(self) -> AnyStr:
        return self.formatOutput()

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
            return True
        return False

    def setStrFormat(self, strFormat: AnyStr) -> None:
        """

        - :param strFormat: (str)
        - :return:
        """

        self.strFormat = strFormat
        if not strFormat or '[0]' in strFormat:
            self.strFormatBackup = strFormat

    def setParserPlugin(self, plugin: Callable) -> GenericInputParser:
        """
            parserPlugin after the list has been format.
        - :param plugin:
        - :return:
        """

        self.parserPlugin = plugin
        return self

    def setParserPluginClass(self, klas: Any) -> GenericInputParser:
        """
            parserPluginClass is used instead of GenericInputParser if this is set
        - :param klas:
        - :return:
        """

        self.parserPluginClass = klas
        return self

    def parseInput(self, source: Optional[Any] = None, tail: Optional[int] = None, head: Optional[int] = None,
                   exclude: Optional[bool] = None, include: Optional[bool] = None, strFormat: Optional[AnyStr] = None,
                   header: Optional[List] = None, columns: Optional[Dict] = None,
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

        def _garbageCollector(*args, **kwargs):
            if gc.isenabled():
                gc.disable()  # just in case the parser plugin has some heavy lifting
            try:
                if self.parserPlugin:
                    return self.parserPlugin(*args, **kwargs)
                return
            finally:
                if not gc.isenabled():
                    gc.collect()  # run full collection then reenable
                    gc.enable()  # This re-enables Garbage Collection to deal with a bug in Python 2.7 and < 3.3.

        if strFormat is None:
            strFormat = self.strFormatBackup
        if not source:
            if not self.source:
                return _garbageCollector(self)
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

        gc.disable()    # This disabled Garbage Collection to deal with a bug in Python 2.7 and < 3.3.
        if isinstance(source, list):
            if isinstance(source[0], list):
                lines = source
            elif isinstance(source[0], str):
                lines = [l.split() for l in filter(None, source)]
            else:
                return _garbageCollector(self)
        elif isinstance(source, str):
            lines = [l.split() for l in filter(None, source.splitlines())]
        else:
            return _garbageCollector(self)

        # Below if statement creates the columns for IndexList
        if type(header) is int:
            header = lines[header]
            self.header = header
            if not columns:
                columns = {}
                for x in range(len(self.header)):
                    columns[self.header[x]] = x

        self.columns = columns
        lines = GenericInputParser._parseInput(lines[abs(head):len(lines) - abs(tail)],
                                               exclude=exclude, include=include)

        if not lines:
            return _garbageCollector(self)

        lines = _garbageCollector(self, lines, header, strFormat) or lines
        if refreshData:
            super(GenericInputParser, self).__init__(columns=self.columns)
        self.extend(lines)
        del lines   # This is done to more easily conserve memory.
        return

    def formatLines(self, lines: Iterable, header: Optional[Iterable] = None,
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

    def formatOutput(self, header: Optional[Iterable] = None, strFormat: Optional[AnyStr] = None) -> AnyStr:
        """

        - :param header: (Iterable/None)
        - :param strFormat: (Str/None)
        - :return: (Str)
        """

        return self.formatLines(lines=self, header=header, strFormat=strFormat)

    # The following 4 functions are overrides of functions from IndexList. They simply take the values returned from
    # IndexList and puts them in a new instance of GenericInputParser.
    def getCorrelation(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """
            Overrides 'getCorrelation' from IndexList. This takes the return value from IndexList and adds it to a new
            instance of GenericInputParser. Go to the IndexList object for documentation on this method.
        """

        return self._runParserClass(values=super(GenericInputParser, self).getCorrelation(*args, **kwargs))

    def getSearch(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """
            Overrides 'getSearch' from IndexList. This takes the return value from IndexList and adds it to a new
            instance of GenericInputParser. Go to the IndexList object for documentation on this method.
        """

        return self._runParserClass(values=super(GenericInputParser, self).getSearch(*args, **kwargs))

    def incompleteLineSearch(self, *args, **kwargs) -> Union[GenericInputParser, Any]:
        """
            Overrides 'incompleteLineSearch' from IndexList. This takes the return value from IndexList and adds it to
            a new instance of GenericInputParser. Go to the IndexList object for documentation on this method.
        """

        return self._runParserClass(values=super(GenericInputParser, self).incompleteLineSearch(*args, **kwargs))

    def _runParserClass(self, values: IndexList) -> Union[GenericInputParser, Any]:
        """

        - :param values: (IndexList)
        - :return: (GenericInputParser/Any)
        """

        newArgs = {'tail': self.tail, 'head': self.head, 'exclude': self.exclude, 'include': self.include,
                   'strFormat': self.strFormat, 'header': self.header, 'columns': self.columns, 'values': values}
        if self.parserPluginClass:
            return self.parserPluginClass(**newArgs
                                          ).setParserPluginClass(self.parserPluginClass
                                                                 ).setParserPlugin(self.parserPlugin)
        return GenericInputParser(**newArgs
                                  ).setParserPluginClass(self.parserPluginClass
                                                         ).setParserPlugin(self.parserPlugin)

    @staticmethod
    def _parseInput(lines: Iterable, exclude: bool = False, include: bool = False) -> Iterable:
        if exclude and not include:
            return [line for line in lines if exclude not in line]
        elif include and not exclude:
            return [line for line in lines if include in line]
        elif exclude and include:
            return [line for line in lines if include in line or exclude not in line]
        else:
            return lines

    @staticmethod
    def trimResultsToColumns(genericInput: GenericInputParser, columnList: Iterable) -> GenericInputParser:
        """ Trim the data so that only the requested columns are included
            NOTE: for command modules the genericInput will use the same parser as the main module
            this means that the update to the header update here may cause the main module to fail to print

        - :param genericInput: data structure object from GenericInputParser, usually self
            this object is required to have a columns in order to parse
        - :param columnList: columns to include in the results
        """

        genericInput.parseInput(source=map(list, zip(*[genericInput[c] for c in columnList])),
                                columns=dict(zip(columnList, range(len(columnList)))),
                                strFormat=''.join(['{%s:<[%s]}' % (s, s) for s in range(len(columnList))]),
                                header=columnList, refreshData=True)
        return genericInput

    @staticmethod
    def convertSpacesInResults(genericInput: GenericInputParser, replaceList: Optional[list] = None,
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
    def convertResultsToBytes(genericInput: GenericInputParser, columnList: list, convertSpaces: Optional[bool] = None,
                              _baseSize: Optional[list] = None) -> GenericInputParser:
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
            newColumn = [GenericInputParser.convertBytes(float(x), _baseSize=_baseSize).replace(' ', '_')
                         for x in genericInput[column] if x and str(x).isdigit()]
            for v in range(len(genericInput)):
                genericInput[v][genericInput.columns[column]] = newColumn[v]
        genericInput.parseInput(source=genericInput, refreshData=True)
        if not convertSpaces:
            return GenericInputParser.convertSpacesInResults(genericInput, columnList=columnList)
        return genericInput

    @staticmethod
    def convertBytes(num: Union[float, int], suffix: str = 'B', base: float = 1024.0, _baseSize: Optional[str] = None,
                     **kwargs) -> str:
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
    def revertBytes(num: Union[float, int], base: float = 1024.0, **kwargs) -> float:
        """  Reverts the converted measurement from convertBytes to its previous value  """

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


class BashParser(GenericInputParser, object):
    """

    """

    def __init__(self, *args, **kwargs):
        self.setParserPluginClass(BashParser)
        self.setParserPlugin(BashParser.bashParser)
        super(BashParser, self).__init__(*args, **kwargs)

    def bashParser(self, lines: Optional[Iterable] = None, header: Optional[List] = None,
                   strFormat: Optional[AnyStr] = None, columns: Optional[Dict] = None):
        """

        - :param lines:
        - :param header:
        - :param strFormat:
        - :param columns:
        - :return:
        """

        lines = lines or []
        header = header or self.header
        shortestLine = self._getShortestLine(lines, header)
        lines = self._reformatOutput(lines, shortestLine)
        self.header = header = self._formatHeader(shortestLine, header)
        columns = columns or self.columns
        self.columns.update(self._formatColumns(shortestLine, header, columns))
        strFormat = strFormat or self.strFormat or self._strFormatter(shortestLine)
        self.setStrFormat(strFormat)
        self.setStrFormat(self._updateStrFormat(strFormat, lines, shortestLine, header))
        return lines

    # Private Functions
    @staticmethod
    def _getShortestLine(sourcelines: Optional[Iterable] = None, sourceheader: Optional[List] = None) -> int:
        if sourcelines:
            return min(map(len, sourcelines))
        if sourceheader is not None:
            return len(sourceheader)
        return 1

    @staticmethod
    def _formatHeader(shortestLine: int, header: List) -> List:
        if header:
            headerLen = len(header)
            for headerItem in range(shortestLine - headerLen):
                header.append(str(headerItem + headerLen))
        return header

    @staticmethod
    def _formatColumns(shortestLine: int, header: List, columns: Dict) -> Dict:
        if columns:
            columnsLen = len(columns)
            for columnsItem in range(shortestLine - columnsLen):
                columns.update({columnsItem + columnsLen: columnsItem + columnsLen})
            return columns
        if header:
            return dict(zip(header, range(shortestLine)))
        return dict(enumerate(range(shortestLine)))

    @staticmethod
    def _strFormatter(shortestLine: int) -> AnyStr:
        return ''.join(['{%s:<[%s]}' % (s, s) for s in range(shortestLine - 1)]) + '{%s:<}' % (shortestLine - 1)

    @staticmethod
    def _updateStrFormat(sourceformat: AnyStr, sourcelines: List, shortestsource: int,
                         sourceheader: Optional[List] = None) -> AnyStr:
        for skey, svalue in BashParser._lineSizeInspection(sourcelines, shortestsource, sourceheader).items():
            sourceformat = sourceformat.replace('[%s]' % skey, str(svalue + 1))
        return sourceformat

    @staticmethod
    def _lineSizeInspection(lines: List, minLength: int, header: Optional[List] = None) -> Dict:
        if header:
            header = BashParser._reformatOutput([header], minLength).pop()
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
    def _reformatOutput(resultsList: List, shortestLine: int) -> List:
        shortestLine -= 1
        for resultsLine in range(len(resultsList)):
            if len(resultsList[resultsLine]) >= shortestLine:
                templine = resultsList[resultsLine][:shortestLine]
                templine.append(' '.join(resultsList[resultsLine][shortestLine:]))
                resultsList[resultsLine] = templine
        return resultsList
