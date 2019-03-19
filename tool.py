'''
to start this app: python -m tool.py
'''

import sys

from interface import TimeMonitor


def usage():
    print("Usage:", file=sys.stderr)
    print("Press p to Pause", file=sys.stderr)
    print("Press q to Quit", file=sys.stderr)
    print("Press e to Edit", file=sys.stderr)
    print("To query year data, enter 4 digits like 2019", file=sys.stderr)
    print("To query month data, enter 6 digits like 201903", file=sys.stderr)
    print("To query day data, enter 8 digits like 20190318", file=sys.stderr)


def main():
    tm = TimeMonitor()
    usage()
    tm.run()


if __name__ == '__main__':
    main()