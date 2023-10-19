#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson
# Description: This is a Date parser. It can take the date out of a string in a uniq way that can be used not only for
#   one offs where you need to pull a date out of a single string but also pull a date from log entries without having
#   to re-parse each line. (Its super effective!)
#
# !!!WARNING!!!: This is an extremely intensive on CPU and Memory usage. This code exceptionally consumes more
# resources the more spaces a line has. IE: The bigger the resulting list is from a 'string.split()'. It is not
# recommended for use with strings that are larger then around 200 or 300 spaces. IE: len(string.split()) < 300.


from itertools import combinations
from datetime import *
from dateutil import tz
from dateutil.parser import *
import traceback
import logging


# logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
#                     level=logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('DateParserLine')


class DateParseLine(object):
    """
        This is designed to parse a single line of text. It attempts to learn the most likely set of characters that is
        a valid date. It then saves the location of that text. It can then attempt to parse that same location in other
        lines which should reduce the amount of resources it takes to parse a whole log file or list of dates.

        !!!WARNING!!!: This is an extremely intensive on CPU and Memory usage. This code consumes more resources the
        more spaces a line has. IE: The bigger the resulting list is from a 'string.split()'. It is not recommended
        for use with strings that are larger then around 200 or 300 spaces. IE: len(string.split()) < 300.
    """

    dateTime = None
    dateSliceCoordinates = None
    dateStr = None
    tz = None
    providedTZ = None
    line = None
    lineSplit = None
    mode = None
    sliceNums = None
    checkPast = None
    checkFuture = None
    defaultPastThreshold = 215308800
    pastThreshold = 0
    defaultFutureThreshold = 86401
    futureThreshold = 0
    prioritizeLargest = True
    prioritizeAlignment = 'LEFT'
    __DEBUG__ = None

    def __init__(self, line, tzinfos=None, checkPast=True, checkFuture=True, mode='LOG', **kwargs):
        """ This setups the values for parsing a line of text. It splits the line using 'str' class method 'split' to
            generate a list of words. By default it will then call the 'parseLine' method.

        - :param line: (str, list, tuple). This is parsed by the private staticmethod '_boilerPlateLine'.
        - :param tzinfos: (pytz.reference.LocalTimezone) Provides tzinfo to append to locally generated date timestamps
                    to compare to the datetime parsed from the line (if any tzinfo is found)
        - :param checkPast: (bool) Controls wither or not to check too see if the timestamp is too far in the past to
                    be considered valid
        - :param checkFuture: (bool) Controls wither or not to check too see if the timestamp is too far in the future
                    to be considered valid.
        - :param mode: (Str) Default 'LOG'. Either LOG or SCAN. This changes the behavior slightly when attempting to
                    learn the string used for the date and/or time in the line.
        - :param sliceNums: (Tuple) Default '(None, None)' Used to ignore words in row buy slicing the row which at the
                    this point is a list of words.
        - :param pastThreshold: (int) Measured in seconds and the default value is 7 years.
        - :param futureThreshold: (int) Measured in seconds and the default value is 1 day + 1 second.
        - :param prioritizeLargest: (bool) If there is more then one valid date time in the line and this is true then
                    this will automatically pick one with the largest number of characters.
        - :param prioritizeAlignment: (str) Either 'LEFT' or 'RIGHT'. It there is more then one valid date time then
                    this is used to sort the list of possible options so that index 0 is either the date time that
                    starts furthest left or furthest right. If prioritizeLargest is true then 'max' is used and if there
                    is a tie then max will return the first object in the list if prioritizeLargest is false then the
                    method will just return the first object in the list after sorting.
        - :param debug: (bool) (False) This saves the results of each 'pass' method so that one can troubleshoot what
                    each method did.
        - :param autoparse: (bool) (True) This automatically runs parse after setting up the class.
        - :param kwargs: (dict) includes pastThreshold, futureThreshold, prioritizeLargest, prioritizeAlignment, debug,
                    and autoparse.
        """

        self.line, self.lineSplit = DateParseLine._boilerPlateLine(line)
        self.providedTZ = tzinfos
        self.checkPast = checkPast
        self.checkFuture = checkFuture
        self.mode = mode
        self.sliceNums = kwargs.get('sliceNums', (None, None))
        self.pastThreshold = kwargs.get('pastThreshold', DateParseLine.defaultPastThreshold)
        self.futureThreshold = kwargs.get('futureThreshold', DateParseLine.defaultFutureThreshold)
        self.prioritizeLargest = kwargs.get('prioritizeLargest', True)
        self.prioritizeAlignment = kwargs.get('prioritizeAlignment', 'LEFT')
        self.__DEBUG__ = kwargs.get('debug', False)
        if self.__DEBUG__ is True:
            self.firstPassResults = None
            self.secondPassResults = None
            self.thirdPassResults = None
            self.forthPassResults = None
        super().__init__()
        if kwargs.get('autoparse', True):
            self.parseLine()

    def __str__(self):
        return str(self.dateTime)

    def __sub__(self, other):
        return self.dateTime.__sub__(other)

    def __add__(self, other):
        return self.dateTime.__add__(other)

    def __cmp__(self, other):
        if type(other) is DateParseLine:
            other = other.dateTime
            me = self.dateTime
        elif type(other) is datetime:
            me = self.dateTime
        elif type(other) is str:
            me = self.dateStr
        else:
            return None
        if other == me:
            return 0
        elif me < other:
            return -1
        elif me > other:
            return 1
        return None

    def __eq__(self, other):
        if type(other) is DateParseLine:
            return other.dateTime == self.dateTime
        elif type(other) is datetime:
            return other == self.dateTime
        elif type(other) is str:
            return other == self.dateStr
        else:
            return None

    def __ne__(self, other):
        if type(other) is DateParseLine:
            return other.dateTime != self.dateTime
        elif type(other) is datetime:
            return other != self.dateTime
        elif type(other) is str:
            return other != self.dateStr
        else:
            return None

    def __lt__(self, other):
        if type(other) is DateParseLine:
            return self.dateTime < other.dateTime
        elif type(other) is datetime:
            return self.dateTime < other
        elif type(other) is str:
            return self.dateStr < other
        else:
            return None

    def __gt__(self, other):
        if type(other) is DateParseLine:
            return self.dateTime > other.dateTime
        elif type(other) is datetime:
            return self.dateTime > other
        elif type(other) is str:
            return self.dateStr > other
        else:
            return None

    def __le__(self, other):
        if type(other) is DateParseLine:
            return self.dateTime <= other.dateTime
        elif type(other) is datetime:
            return self.dateTime <= other
        elif type(other) is str:
            return self.dateStr <= other
        else:
            return None

    def __ge__(self, other):
        if type(other) is DateParseLine:
            return self.dateTime >= other.dateTime
        elif type(other) is datetime:
            return self.dateTime >= other
        elif type(other) is str:
            return self.dateStr >= other
        else:
            return None

    def parseLine(self):
        """ This function uses all the arguments setup in '__init__'. It calls upon four private staticmethods one after
            another. Each method has a particular task. 'firstPass', 'secondPass', 'thirdPass', 'forthPass'. If 'debug'
            is enabled this will save the output of each 'pass' method too 'firstPassResults'... and so on. Once
            forthPass is complete it will use the returned data to save the dateTime/tz/dateStr/dateSliceCoordinates
            info.

        - :return: (DateParseLine) (self)
        """

        if not self.lineSplit:
            return None

        kwargs = {'tzinfos': self.providedTZ, 'checkPast': self.checkPast, 'checkFuture': self.checkFuture,
                  'pastThreshold': self.pastThreshold, 'futureThreshold': self.futureThreshold,
                  'prioritizeLargest': self.prioritizeLargest, 'prioritizeAlignment': self.prioritizeAlignment}

        try:
            firstPassResults = DateParseLine._firstPass(self.lineSplit, mode=self.mode, sliceNums=self.sliceNums,
                                                        tzinfos=self.providedTZ)
            if self.__DEBUG__ is True:
                self.firstPassResults = firstPassResults
                log.debug(f'First Pass Results: {firstPassResults}')
            if not firstPassResults:
                return False

            secondPassResults = DateParseLine._secondPass(firstPassResults, self.lineSplit, **kwargs)
            if self.__DEBUG__ is True:
                self.secondPassResults = secondPassResults
                log.debug(f'Second Pass Results: {secondPassResults}')
            if not secondPassResults:
                return False

            thirdPassResults = DateParseLine._thirdPass(secondPassResults, self.lineSplit, self.sliceNums, **kwargs)
            if self.__DEBUG__ is True:
                self.thirdPassResults = thirdPassResults
                log.debug(f'Third Pass Results: {thirdPassResults}')
            if not thirdPassResults:
                return False

            forthPassResults = DateParseLine._forthPass(thirdPassResults, **kwargs)
            if self.__DEBUG__ is True:
                self.forthPassResults = forthPassResults
                log.debug(f'Forth Pass Results: {forthPassResults}')

            if forthPassResults is not None and len(forthPassResults) == 3:
                self.dateTime = forthPassResults[1]
                self.tz = self.dateTime.tzinfo
                self.dateSliceCoordinates = forthPassResults[0]
                self.dateStr = forthPassResults[-1]
                return self
            else:
                return False

        except Exception as e:
            log.error(f'parseLine failed: {e}')
            log.debug(f'[DEBUG]: trace for error: [{e}] - {traceback.format_exc()}')
            return False

    def parseOtherLine(self, otherLine, **kwargs):
        """ This will get another line and using the settings, unless specified otherwise, it will attempt to parse
            'otherLine' by slicing it using the 'dateSliceCoordinates' variable.

        - :param otherLine: (Str, List, Tuple) Just like with 'line' in '__init__' this will be handled by
                    '_boilerPlateLine' private staticmethod.
        - :param kwargs: (dict) This passes in all the control variables and by default this uses the settings saved in
                    this class.
        - :return: (bool/datetime)
        """

        if not self.dateSliceCoordinates:
            return False
        try:
            checkPast = kwargs.get('checkPast', self.checkPast)
            checkFuture = kwargs.get('checkFuture', self.checkFuture)
            pastThreshold = kwargs.get('pastThreshold', self.pastThreshold)
            futureThreshold = kwargs.get('futureThreshold', self.futureThreshold)
            tzinfos = kwargs.get('tzinfos', self.providedTZ)
            line, listOfWords = DateParseLine._boilerPlateLine(otherLine)
            dateStr = ''.join(listOfWords[self.dateSliceCoordinates[0]:self.dateSliceCoordinates[-1]]).strip()
            return DateParseLine.safeParse(dateStr, tzinfos=tzinfos, checkPast=checkPast, checkFuture=checkFuture,
                                           pastThreshold=pastThreshold, futureThreshold=futureThreshold)
        except Exception as e:
            log.error(f'parseOtherLine failed: {e}')
            log.debug(f'[DEBUG]: trace for error: [{e}] - {traceback.format_exc()}')
            return False

    @staticmethod
    def inPast(dateObject, threshold=None, tzinfos=None):
        """ A helper staticmethod that can be useful for other applications. This compares the datetime object with the
            current system time to determine if it is in the past. The threshold is measured in seconds. This can also
            handle tz data.

        - :param dateObject: (datetime)
        - :param threshold: (int) None
        - :param tzinfos: (pytz.reference.LocalTimezone)
        - :return: (bool)
        """

        if type(dateObject) is DateParseLine:
            dateObject = dateObject.dateTime
        if dateObject.tzinfo is not None and tzinfos is None:
            tzinfos = tz.gettz('/etc/localtime') or tz.gettz('UTC')
        elif tzinfos is not None and dateObject.tzinfo is None:
            tzinfos = None
        if threshold is None:
            return datetime.now(tz=tzinfos) > dateObject
        now = datetime.now(tz=tzinfos)
        if now > dateObject:
            return now - dateObject > timedelta(seconds=threshold)
        return False

    @staticmethod
    def inFuture(dateObject, threshold=None, tzinfos=None):
        """ A helper staticmethod that can be useful for other applications. This compares the datetime object with the
            current system time to determine if it is in the future. The threshold is measured in seconds. This can also
            handle tz data.

        - :param dateObject: (datetime)
        - :param threshold: (int) None
        - :param tzinfos: (pytz.reference.LocalTimezone)
        - :return: (bool)
        """

        if type(dateObject) is DateParseLine:
            dateObject = dateObject.dateTime
        if dateObject.tzinfo is not None and tzinfos is None:
            tzinfos = tz.gettz('/etc/localtime') or tz.gettz('UTC')
        elif tzinfos is not None and dateObject.tzinfo is None:
            tzinfos = None
        if threshold is None:
            return datetime.now(tz=tzinfos) < dateObject
        now = datetime.now(tz=tzinfos)
        if now < dateObject:
            return dateObject - now > timedelta(seconds=threshold)
        return False

    @staticmethod
    def safeParse(timeStr, tzinfos=None, checkPast=False, checkFuture=False, **kwargs):
        """ A helpful method that wraps the 'parse' function from 'dateutil.parser'. This also includes the ability to
            filter out dates that are from the past or future with customizable thresholds.

        - :param timeStr: (str)
        - :param tzinfos: (pytz.reference.LocalTimezone)
        - :param checkPast: (bool) (False)
        - :param checkFuture: (bool) (False)
        - :param kwargs: (dict) includes pastThreshold and futureThreshold
        - :return: (datetime/None)
        """

        try:
            if not checkPast and not checkFuture:
                parsedTime = parse(timeStr)
                if parsedTime.tzinfo:
                    return parsedTime
                return parsedTime.replace(tzinfo=tzinfos)
            parsedTime = parse(timeStr)
            if not parsedTime.tzinfo:
                parsedTime = parsedTime.replace(tzinfo=tzinfos)
            pastThreshold = kwargs.get('pastThreshold', DateParseLine.defaultPastThreshold)
            if checkPast and DateParseLine.inPast(parsedTime, threshold=pastThreshold, tzinfos=tzinfos):
                return None
            futureThreshold = kwargs.get('futureThreshold', DateParseLine.defaultFutureThreshold)
            if checkFuture and DateParseLine.inFuture(parsedTime, threshold=futureThreshold, tzinfos=tzinfos):
                return None
            return parsedTime
        except ValueError:
            if timeStr.endswith(':'):
                return DateParseLine.safeParse(timeStr.strip(':'), tzinfos=tzinfos, checkPast=checkPast,
                                               checkFuture=checkFuture, **kwargs)
        except Exception as e:
            log.error(f'safeParse failed: {e}')
            log.debug(f'[DEBUG]: trace for error: [{e}] - {traceback.format_exc()}')
            return None

    @staticmethod
    def slicer(listOfWords, start, end, default=''):
        return [default] * start + listOfWords[start:end] + [default] * (len(listOfWords) - end)

    @staticmethod
    def sliceNumParser(listOfWords, sliceNums):
        return 0 if sliceNums[0] is None else sliceNums[0], len(listOfWords) if sliceNums[1] is None else sliceNums[1]

    @staticmethod
    def _boilerPlateLine(line):
        """ Function used only for '__init__' and 'parseOtherLine'. This is used to make sure that the 'line' or
            'otherLine' parameters are formatted correctly. This returns a single 'Str' as the line stripped of any
            whitespace and a list of words with there whitespaces added.

        - :param line: (Str,List,Tuple)
        - :return: (tuple) Tuple length is 2, first item is a Str and second item a List
        """

        try:
            if isinstance(line, str):
                return line, [f'{i} ' for i in line.split()]
            elif isinstance(line, (tuple, list)):
                if not all([isinstance(item, str) for item in line]):
                    raise ValueError("The provided iterable for parameter 'line' contains value types other then str")
                lineList = [f'{i.strip()} ' for i in line]
                return ''.join(lineList).strip(), lineList
        except ValueError:
            pass
        except Exception as e:
            log.error(f'BoilerPlateLine failed for an unknown reason: {e}')
            log.debug(f'[DEBUG]: trace for error: [{e}] - {traceback.format_exc()}')
            pass

    @staticmethod
    def _firstPass(listOfWords, mode='LOG', sliceNums=(None, None), tzinfos=None):
        """ Quick pass of each word individually through the 'safeParse' method.

        - :param listOfWords: (list) assert each item in the list is a Str.
        - :param mode: (Str) 'LOG' either LOG or SCAN. LOG mode by default.
        - :return: (list)
        """
        start, end = DateParseLine.sliceNumParser(listOfWords, sliceNums)
        outputList = []
        if mode == 'LOG':
            success = False
            for word in listOfWords:
                if not start <= listOfWords.index(word) < end:
                    outputList.append(None)
                    continue
                outputList.append(DateParseLine.safeParse(word.strip(), tzinfos=tzinfos))
                if outputList[-1] is not None:
                    success = True
                elif success:
                    break
            [outputList.append(None) for i in range(len(listOfWords) - len(outputList))]
            return outputList
        else:
            for word in listOfWords:
                if not start <= listOfWords.index(word) < end:
                    outputList.append(None)
                    continue
                outputList.append(DateParseLine.safeParse(word.strip(), tzinfos=tzinfos))
        return outputList

    @staticmethod
    def _secondPass(firstPassResults, listOfWords, **kwargs):
        """ Group up all successfully parsed words from firstPass and then attempt to parse each group as a whole. The
            logic will try to parse each group as a whole string. If it fails it will keep shrinking the size of the
            group until it successfully parses a datetime.

        - :return: (dict)
        """

        tzinfos = kwargs.get('tzinfos', None)
        checkPast = kwargs.get('checkPast', True)
        checkFuture = kwargs.get('checkFuture', True)
        pastThreshold = kwargs.get('pastThreshold', DateParseLine.defaultPastThreshold)
        futureThreshold = kwargs.get('futureThreshold', DateParseLine.defaultFutureThreshold)

        def findGroups(tmpList, orgList):
            newGroups = []
            group = []
            for x in range(len(tmpList)):
                if tmpList[x] is not None:
                    group.append(orgList[x])
                elif len(group) > 0:
                    newGroups.append(group)
                    group = []
            if len(group) > 0:
                newGroups.append(group)
            return newGroups

        def genCombinationGroup(group):
            def _fltLen(tmpList):
                return len(tmpList) > 1

            if len(group) == 1:
                return group

            outputList = list(filter(_fltLen, [group[i:j] for i, j in combinations(range(len(group) + 1), 2)]))
            [outputList.append([item]) for item in group]

            return sorted(outputList, key=len, reverse=True)

        def parseGroup(group):
            for combo in group:
                comboStr = ''.join(combo).strip()
                tmpTime = DateParseLine.safeParse(comboStr, tzinfos=tzinfos, checkFuture=checkFuture,
                                                  checkPast=checkPast, pastThreshold=pastThreshold,
                                                  futureThreshold=futureThreshold)
                if tmpTime is not None:
                    if type(combo) is not list:
                        combo = [combo]
                    starting = group[0]
                    if type(starting) is not list:
                        starting = [starting]
                    return combo, starting, tmpTime

        def generateDictionaryOutput(pGroup):
            output = {}
            for group in pGroup:
                output.update({(listOfWords.index(group[0][0]), listOfWords.index(group[0][-1]) + 1):
                                   (group[-1], (listOfWords.index(group[1][0]), listOfWords.index(group[1][-1]) + 1))})
            return output

        # print(f'listOfWords = {listOfWords}')
        # print(f'First Pass Results = {firstPassResults}')
        groups = findGroups(firstPassResults, listOfWords)
        # print(f'groups = {groups}')
        combGroup = [genCombinationGroup(group) for group in groups]
        # print(f'combGroup = {combGroup}')
        parsedGroups = list(filter(None, [parseGroup(group) for group in combGroup]))
        # print(f'parsedGroups ={parsedGroups}')
        if not parsedGroups:
            return {}
        return generateDictionaryOutput(parsedGroups)

    @staticmethod
    def _thirdPass(secondPassResults, listOfWords, sliceNums, **kwargs):
        """ Take each group of successfully parsed words and expand on them to see if neighboring words will now
            successfully parse into a datetime. This can happen because sometimes individual characters/words will not
            identify as a datetime without further context. This function is aware of any shrinking of groups done by
            'secondPass' and thus will not expand in the direction that has already failed.

        - :return: (list)
        """

        tzinfos = kwargs.get('tzinfos', None)
        checkPast = kwargs.get('checkPast', True)
        checkFuture = kwargs.get('checkFuture', True)
        pastThreshold = kwargs.get('pastThreshold', DateParseLine.defaultPastThreshold)
        futureThreshold = kwargs.get('futureThreshold', DateParseLine.defaultFutureThreshold)

        start, end = DateParseLine.sliceNumParser(listOfWords, sliceNums)

        def canGoRight(index, orgList):
            return index < len(orgList) and index < end

        def allowRight(k, v, orgList):
            orgCombo = v[-1]
            if k[-1] < orgCombo[-1]:
                return False
            return canGoRight(k[-1], orgList)

        def canGoLeft(index):
            return index > 0 and index > start

        def allowLeft(k, v):
            orgCombo = v[-1]
            if k[0] > orgCombo[0]:
                return False
            return canGoLeft(k[0])

        def parseGroup(k, v, orgList):
            right = allowRight(k, v, orgList)
            left = allowLeft(k, v)
            finialCombo = k
            currentParsed = v[0]
            while finialCombo[-1] - finialCombo[0] < len(orgList):
                passed = False
                if right and canGoRight(finialCombo[-1], orgList):
                    rightParse = DateParseLine.safeParse(''.join(orgList[finialCombo[0]:finialCombo[-1] + 1]).strip(),
                                                         tzinfos=tzinfos, checkFuture=checkFuture, checkPast=checkPast,
                                                         pastThreshold=pastThreshold, futureThreshold=futureThreshold)
                    if rightParse is not None:
                        finialCombo = (finialCombo[0], finialCombo[-1] + 1)
                        passed = True
                        currentParsed = rightParse
                    else:
                        right = False
                if left and canGoLeft(finialCombo[0]):
                    leftParse = DateParseLine.safeParse(''.join(orgList[finialCombo[0] - 1:finialCombo[-1]]).strip(),
                                                        tzinfos=tzinfos, checkFuture=checkFuture, checkPast=checkPast,
                                                        pastThreshold=pastThreshold, futureThreshold=futureThreshold)
                    if leftParse is not None:
                        finialCombo = (finialCombo[0] - 1, finialCombo[-1])
                        passed = True
                        currentParsed = leftParse
                    else:
                        left = False
                if passed is False:
                    break
            return finialCombo, currentParsed, ''.join(orgList[finialCombo[0]:finialCombo[-1]]).strip()

        return [parseGroup(k, v, listOfWords) for k, v in secondPassResults.items()]

    @staticmethod
    def _forthPass(thirdPassResults, **kwargs):
        """ This is designed to figure out which datetime in the output of the Third Pass too consider as the valid date
            of this line. If the third pass results only has one valid datetime then this is automatically chosen. If
            there are multiple possible date times within the line the largest one measured by character length is by
            default chosen. There is also left alignment and right alignment.

        - :param thirdPassResults: (dict)
        - :return: (tuple)
        """

        if len(thirdPassResults) == 1:
            return thirdPassResults[0]

        prioritizeAlignment = kwargs.get('prioritizeAlignment', DateParseLine.prioritizeAlignment)
        prioritizeLargest = kwargs.get('prioritizeLargest', DateParseLine.prioritizeLargest)

        def largestHelper(item):
            return len(item[-1])

        def alignmentHelper(item):
            return item[0][0]

        if isinstance(prioritizeAlignment, str):
            if prioritizeAlignment.upper() == 'LEFT':
                thirdPassResults.sort(key=alignmentHelper)
            elif prioritizeAlignment.upper() == 'RIGHT':
                thirdPassResults.sort(key=alignmentHelper, reverse=True)
        else:
            thirdPassResults.sort(key=alignmentHelper)

        if prioritizeLargest:
            return max(thirdPassResults, key=largestHelper)
        return thirdPassResults[0]
