#!/bin/python
"""
Remove 'include' fields from a .repo file
"""

import ConfigParser
import select
import sys

def main():
    rlist, _, _ = select.select([sys.stdin], [], [], 3)
    if not rlist:
        print('error: Failed to read from std-in')
        sys.exit(1)

    cp = ConfigParser.SafeConfigParser()
    cp.readfp(rlist.pop())
    for s in cp.sections():
        if cp.has_option(s, 'includepkgs'):
            cp.remove_option(s, 'includepkgs')

    cp.write(sys.stdout)

if __name__ == '__main__':
    main()
