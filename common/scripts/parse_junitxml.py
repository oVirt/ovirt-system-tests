#!/usr/bin/python3

import os
import os.path
import sys

import xml.etree.ElementTree as ET

if __name__ == '__main__':
    if len(sys.argv) != 3:
        basename = os.path.basename(sys.argv[0])
        print(f'usage: {basename} in_junitxml_file out_result_file')
        sys.exit(1)

    tree = ET.parse(sys.argv[1])
    suite = next(iter(tree.getroot()))

    if int(suite.get('failures')) > 0 or int(suite.get('errors')) > 0:
        test_case = tuple(suite.iter('testcase'))[-1]
        try:
            node = next(test_case.iter('failure'))
        except StopIteration:
            node = next(test_case.iter('error'))
        message = f'{test_case.get("name")} failed:\n\n{node.text}'
    else:
        message = 'Success!'

    with open(sys.argv[2], 'w') as result_file:
        result_file.write(message)
