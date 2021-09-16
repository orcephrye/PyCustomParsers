#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Timothy Nodine, Ryan Henrichson
# Description: This keeps all the parsers that can be called by a user if required.
# This is mostly stand alone, save the imported _simpleParseResults() function used by the CommandRunner module.


import logging
from collections import OrderedDict
from collections.abc import Iterable
from copy import deepcopy
import operator
import re
import json
from ast import Num, Name, BinOp, Add, Sub, Expression, PyCF_ONLY_AST
from ast import Str as astStr
from ast import Tuple as astTuple
from ast import List as astList
from ast import Dict as astDict
from typing import AnyStr, Hashable, Any, Union, Dict, Optional, List


VERSION = '0.2'


# logging.basicConfig(format='%(module)s %(funcName)s %(lineno)s %(message)s', level=logging.DEBUG)
log = logging.getLogger('ExternalParsers')


singleTagXML = re.compile(r'<(.+?) (.+?)/>', flags=re.DOTALL)


def jsonHook(jsonInput: str) -> Dict:
    """ Decode properly formatted json in a robust way. Meant to be used as an object_hook for the Python json lib.
        Usage:  json.loads(json_string, object_hook=jsonHook)

    - :param jsonInput: Valid json object
    - :return: dict object
    """

    def _decode_str(data):
        tmpStr = data.lower()
        if tmpStr == 'true':
            return True
        elif tmpStr == 'false':
            return False
        elif tmpStr == 'none' or tmpStr == 'null':
            return None
        return data

    def _decode_list(data):
        rv = []
        for item in data:
            if isinstance(item, bytes):
                try:
                    item = _decode_str(item.decode())
                except:
                    item = item.decode(errors='ignore')
            elif isinstance(item, list):
                item = _decode_list(item)
            elif isinstance(item, dict):
                item = _decode_dict(item)
            rv.append(item)
        return rv

    def _decode_dict(data):
        rv = {}
        for key, value in data.items():
            if isinstance(key, bytes):
                key = key.decode()
            if isinstance(value, bytes):
                try:
                    value = _decode_str(value.decode())
                except:
                    value = value.decode(errors='ignore')
            elif isinstance(value, list):
                value = _decode_list(value)
            elif isinstance(value, dict):
                value = _decode_dict(value)
            rv[key] = value
        return rv

    return _decode_dict(jsonInput)


def literal_eval_include(node_or_string: Any) -> Any:
    """ Safely evaluate an expression node or a string containing a Python expression.  The string or node provided may
        only consist of the following Python literal structures: strings, numbers, tuples, lists, dicts, booleans,
        and None. Includes json values and adapted directly out of the ast source.

    - :param node_or_string: (string/ast node) Python expression or data
    - :return: (Any) evaluated expression
    """

    def _parse(source):
        return compile(source, '<unknown>', 'eval', PyCF_ONLY_AST)

    def _convert(node):
        if isinstance(node, astStr):
            return node.s
        elif isinstance(node, Num):
            return node.n
        elif isinstance(node, astTuple):
            return tuple(map(_convert, node.elts))
        elif isinstance(node, astList):
            return list(map(_convert, node.elts))
        elif isinstance(node, astDict):
            return dict((_convert(k), _convert(v)) for k, v
                        in zip(node.keys, node.values))
        elif isinstance(node, Name):
            if node.id in _safe_names:
                return _safe_names[node.id]
        elif isinstance(node, BinOp) and \
                isinstance(node.op, (Add, Sub)) and \
                isinstance(node.right, Num) and \
                isinstance(node.right.n, complex) and \
                isinstance(node.left, Num) and \
                isinstance(node.left.n, (int, float)):
            left = node.left.n
            right = node.right.n
            if isinstance(node.op, Add):
                return left + right
            else:
                return left - right
        raise ValueError('malformed string')

    _safe_names = {'None': None, 'True': True, 'False': False,
                   'null': None, 'true': True, 'false': False}

    if isinstance(node_or_string, str):
        node_or_string = _parse(node_or_string)
    if isinstance(node_or_string, Expression):
        node_or_string = node_or_string.body

    return _convert(node_or_string)


def xmlToJsonDict(configString: AnyStr, configDict: Optional[Dict] = None) -> Dict:
    """  This is your all in one parser for XML to json. This created a nested dictionary based on the structure of the
        XML as passed in.
        (Note: This has multiple meta functions that are used to break up the logic)

    - :param configString: a string containing correctly formatted XML
    - :param configDict: (None) An already existing Dictionary to add the XML data too. Default is to make a new dict.
    - :return: (dict)
    """

    def _singleTagXMLHandler(output, stackheap, line):
        key, values = _parseSingleTAGXML(line)
        if type(values) is OrderedDict:
            _recursiveAdd(output, list(stackheap), OrderedDict([(key, OrderedDict([]))]))
            stackheap.append(key)
            for keyValues, item in values:
                _recursiveAdd(output, list(stackheap), OrderedDict([(keyValues, item)]))
        else:
            _recursiveAdd(output, list(stackheap), OrderedDict([(key, values)]))

    def _singleLineXMLHandler(output, stackheap, line):
        lines = list(map(operator.methodcaller('strip'), line.replace('>', '>\n').replace('</', "\n</").splitlines()))
        if len(lines) < 3 or lines[0] != lines[-1].replace('/', ''):
            raise Exception("Failed to handle single line XML tags")
        key = lines[0]
        lines = lines[1:-1]
        if len(lines) == 1:
            lines = lines.pop()
            values = lines.split("=")
            if len(values) == 1:
                _recursiveAdd(output, list(stackheap), OrderedDict([(key, values.pop())]))
            else:
                _recursiveAdd(output, list(stackheap), OrderedDict([(key, OrderedDict([]))]))
                stackheap.append(key)
                _recursiveAdd(output, list(stackheap), OrderedDict([(values[0], values[1])]))
                stackheap.pop()
        else:
            _recursiveAdd(output, list(stackheap), OrderedDict([(key, OrderedDict([]))]))
            stackheap.append(key)
            for items in lines:
                values = items.split('=')
                if len(values) == 1:
                    continue
                else:
                    _recursiveAdd(output, list(stackheap),
                                  OrderedDict([(values[0].strip(), '='.join(values[1:]).strip())]))
            stackheap.pop()

    def _parseSingleTAGXML(value):
        output = singleTagXML.findall(value)
        if not output:
            raise Exception("Unable to parse XML")
        output = output.pop()
        line = output[0].strip()
        values = output[1].split()
        if len(values) == 1:
            return line, values.pop()
        elif len(values) == 0:
            raise Exception("Unable to parse XML values")
        outputValues = OrderedDict()
        for item in values:
            if "=" not in item:
                continue
            valueitem = item.split("=")
            outputValues.update((valueitem[0].strip(), '='.join(valueitem[1:]).strip()))
        return line, outputValues

    def _recursiveAdd(output, stackheap, value):
        # if there is only one key in the stack than update that key in the dict with the value and return
        if len(stackheap) == 1:
            output[stackheap[-1]].update(value)
            return output
        # if there are multiple keys in the stack then get the new key and remove it from the stack
        # then proceed to update that key with the value and return
        elif len(stackheap) > 1:
            key = stackheap[0]
            stackheap.remove(stackheap[0])
            _recursiveAdd(output[key], stackheap, value)
        else:
            output.update(value)
        return output

    if not configString:
        return {}

    configDict = configDict or OrderedDict([])
    stack = []

    for line in map(operator.methodcaller('strip'), configString.splitlines()):
        # check for commented lines and prevent them from being added to the stack
        # add them as keys with no values
        if line.strip().startswith('#'):
            _recursiveAdd(configDict, list(stack), OrderedDict([(line, '')]))
        # make sure the line contains a key
        elif '<' in line and '>' in line:
            # remove the key from the stack if the stanza is closed
            if "/>" in line:
                _singleTagXMLHandler(configDict, stack, line)
            elif line.count("<") >= 2 and '</' in line:
                _singleLineXMLHandler(configDict, stack, line)
            elif "</" in line:
                try:
                    stack.pop()
                except:
                    continue
            else:
                # otherwise this is a new key that needs to be added to the stack, and populated to the dict
                _recursiveAdd(configDict, list(stack), OrderedDict([(line, OrderedDict([]))]))
                stack.append(line)
        elif '=' in line:
            # if the line contains a value then add it to the values for the current key
            values = line.split('=')
            _recursiveAdd(configDict, list(stack), OrderedDict([(values[0].strip(), '='.join(values[1:]).strip())]))
    return configDict


def jsonToXML(jsonDict: Union[AnyStr, Dict], layer: int = 0, indent: int = 3) -> AnyStr:
    """ Converts json/dict objects to XML.

    - :param jsonDict: (str/dict) If this is a string then it will be converted using 'loads' within the Python module
        json with the object_hook param using the jsonHook method found within this Package.
    - :param layer: (int) This determines the amount of tabs used to indicate a layer or indentation. Default 0.
    - :param indent: (int) This determines the amount of white space is used as a 'tab'. Default 3.
    - :return: (str)
    """

    output = ""
    if type(jsonDict) is str:
        jsonDict = json.loads(jsonDict, object_hook=jsonHook)

    def taber():
        tabs = ""

        def whiteSpaceGenerator():
            for _ in range(indent):
                yield " "

        for x in range(layer):
            tabs += ''.join(whiteSpaceGenerator())
        return tabs

    for key, items in jsonDict.items():
        output += taber()
        if "<" not in key or type(items) is str:
            if "<" in key:
                output += f"{key}{items}{key.replace('<', '</')}"
            else:
                output += f"{key} = {items}"
        else:
            output += f"{key}\n{jsonToXML(items, layer=layer + 1, indent=indent)}{taber()}{key.replace('<', '</')}"
        output += "\n"
    return output


def findJsonStuff(keyGet: Optional[Hashable] = None, valueGet: Optional[Hashable] = None,
                  jsonStuff: Optional[Dict] = None, valueOnly: bool = True) -> Any:
    """ Find the value(s) for the key given in keyGet or the context {key(s): value(s)} for the value given in valueGet

    - :param keyGet: the key in the json dict you want the value for
    - :param valueGet: the value in the json dict you want the context for
    - :param jsonStuff: the json dict object
    - :param valueOnly: whether you want the dict including the key or just the value for that key
    - :return: dict value if using keyGet or dict if using valueGet
    """

    def _dataTypeHelper(jsonValue, jsonS):
        if isinstance(jsonValue, str):
            return jsonS.items()
        if type(jsonValue) is list:
            return dict(enumerate(jsonValue)).items()
        return jsonValue.items()

    saveKeyGet = keyGet
    if keyGet and valueGet:
        saveJson = deepcopy(jsonStuff.get(keyGet))
        if saveJson:
            if [vg for vg in saveJson if valueGet == vg]:
                if valueOnly:
                    return {vk: vv for vl in [saveJson.get(vg) for vg in saveJson if valueGet == vg] for vk, vv in
                            vl.items()}
                return {vg: saveJson.get(vg) for vg in saveJson if valueGet == vg}
            if [vg for vg in saveJson if valueGet in vg]:
                if valueOnly:
                    return {vk: vv for vl in [saveJson.get(vg) for vg in saveJson if valueGet in vg] for vk, vv in
                            vl.items()}
                return {vg: saveJson.get(vg) for vg in saveJson if valueGet in vg}
            jsonStuff = deepcopy(saveJson)
            keyGet = None
    elif keyGet:
        if keyGet in jsonStuff.keys():
            return jsonStuff.get(keyGet)
    elif valueGet:
        if [vg for vg in jsonStuff.values() if valueGet in vg]:
            return {kg: vg for kg, vg in jsonStuff.items() if valueGet in vg}
    try:
        return findJsonStuff(keyGet=keyGet, valueGet=valueGet, jsonStuff={jvk: jvv for jvalue in jsonStuff.values()
                                                                          for jvk, jvv in
                                                                          _dataTypeHelper(jvalue, jsonStuff)},
                             valueOnly=valueOnly)
    except:
        if valueOnly:
            return findJsonStuff(keyGet=saveKeyGet, valueGet=valueGet, jsonStuff=jsonStuff, valueOnly=False)
        return None
        # raise


def queryDict(dictToQuery: Union[Dict, Iterable], getkey: Hashable) -> Any:
    """ A generator that will keep yielding values from a key. Unlike a simple 'get' method this handles nested
        dictionaries and will return the values of every instance the key appears.

    :param dictToQuery: (dict) an instance of a dictionary object
    :param getkey: (hashable) The key to look for
    :return: yield (Any)
    """

    if isinstance(dictToQuery, dict):
        for key, item in dictToQuery.items():
            if key == getkey:
                yield item
            elif isinstance(item, dict):
                for results in queryDict(item, getkey):
                    yield results
            elif isinstance(item, Iterable):
                for results in queryDict(item, getkey):
                    yield results
    elif isinstance(dictToQuery, Iterable):
        if dictToQuery == getkey:
            yield dictToQuery
        else:
            for item in dictToQuery:
                for results in queryDict(item, getkey):
                    yield results


def findJsonValues(context: Hashable, key: Hashable, dictToQuery: Dict) -> Optional[List]:
    """ This uses the 'queryDict' function found within this package. It will search a nested dictionary and only return
        the values found within a 'context'. This context is just another key. In other words this will yield only
        values on a particular key found within the values of another key.

    :param context: (hashable) The parent key within a dict. This tool will search the values of this key only.
    :param key: (hashable) Return the values of this key
    :param dictToQuery: (dict) dictionary object o search
    :return: list
    """

    output = []
    for values in queryDict(dictToQuery, context):
        if isinstance(values, dict):
            output.append(values.get(key))
        elif isinstance(values, Iterable):
            for item in values:
                if key in item:
                    output.append(item)
    if not output:
        return None
    return list(filter(None, output))
