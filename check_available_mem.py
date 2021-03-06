#!/usr/bin/env python3

# This script will check the amount of available memory using /proc/meminfo

# For now, we're going to make the (probably wrong) assumption that all values are 
# using the same units (usually kB)

import argparse
import re
import sys

# Constants
meminfo_re = re.compile("^\s*([a-zA-Z0-9_\(\)]+):\s+([0-9]+)\s*?([a-zA-Z]*?)\s*?$")
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3

def main():
    args = parse_cli_args()
    meminfo = read_meminfo(args)
    output_response(args, meminfo)

def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='A nagios check that can pass/fail based on the amount of ' \
            'available memory on the host.'
    )

    parser.add_argument(
        '--warn', '-w',
        action='store',
        type=int,
        required=True,
        help="Warn level.  Available memory being less than this percentage will " \
            "constitute a failure"
    )

    parser.add_argument(
        '--critical', '-c',
        action='store',
        type=int,
        required=True,
        help="Critical level.  Available memory being less than this percentage will " \
            "constitute a failure"
    )

    args = parser.parse_args()

    if args.warn < args.critical:
        parser.exit(
            status=NAGIOS_UNKNOWN,
            message="Warn threshold must be higher than critical threshold"
        )

    return args

def read_meminfo(args):
    """
    Parse the /proc/meminfo file
    """

    meminfo = {}

    with open("/proc/meminfo", "r") as meminfo_fh:
        for line in meminfo_fh.readlines():
            line = line.strip()
            matches = meminfo_re.search(line)
            if matches:
                meminfo[matches.group(1).lower()] = {
                    'value': int(matches.group(2)),
                    'unit': matches.group(3),
                }

    return meminfo

def output_response(args, meminfo):
    message = "Mem: {} {}, Available: {} {}, Percent available: {:0.2f}%"
    normalized = normalize_mem_info(meminfo)
    percent_available = normalized['percent_available']['value']

    rendered = message.format(
        normalized['total']['value'],
        normalized['total']['unit'],
        normalized['available']['value'],
        normalized['available']['unit'],
        percent_available
    )

    if percent_available < args.critical:
        status = NAGIOS_CRITICAL
        output = "CRIT - {}".format(rendered)
    
    elif percent_available < args.warn:
        status = NAGIOS_WARNING
        output = "WARNING - {}".format(rendered)

    else:
        status = NAGIOS_OK
        output = "OK - {}".format(rendered)

    print(output)
    sys.exit(status)

def normalize_mem_info(meminfo):
    """
    Normalize the info available about the memory
    """

    normalized = {'total': meminfo['memtotal']}

    # If xenial or above, we can look at "memavailable"
    if 'memavailable' in meminfo:
        normalized['available'] = meminfo['memavailable']

    # Otherwise, we have to math it a little, and it won't be nearly as accurate
    else:
        available = \
           normalized['total']['value'] - \
           meminfo['cached']['value'] - \
           meminfo['buffers']['value']

        normalized['available'] = {
            'value': available,
            'unit': normalized['total']['unit']
        }

    normalized['percent_available'] = {'value':
        (
            float(normalized['available']['value']) /
            float(normalized['total']['value'])
        ) * 100.0
    }

    return normalized


if __name__ == '__main__':
    main()
