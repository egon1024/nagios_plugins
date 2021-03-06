#!/usr/bin/env python3

# This script can be used with nagios to determine the size of a directory

import argparse
import os
import os.path
import re
import sys


# Constants
value_re = re.compile("^([0-9]+)([kKmMgG]?)$")
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3

KILOBYTE = 1024
MEGABYTE = 1024 ** 2
GIGABYTE = 1024 ** 3


def main():
    args = parse_cli_args()
    dir_size = find_dir_size(args)
    output_response(args, dir_size)


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description='A nagios check that can pass/fail based on the size of' \
          ' the contents of a directory.',
        epilog='Warn and crit can be either a single value (trigger if over) ' \
          'or a range in the form value:value and will trigger if outside of ' \
          'it.  Values can have a k, m, or g suffix (or no suffix).'
    )

    # What directory to scan
    parser.add_argument(
        '-d', '--dir',
        action='store',
        type=str,
        required=True,
        help='The directory to check'
    )

    # Restrict to the same filesystem
    parser.add_argument(
        '--xdev',
        action='store_true',
        default=False,
        help="Indicates the search should not cross filesystem devices"
    )

    # Warn range
    parser.add_argument(
        '--warn', '-w',
        action='store',
        type=str,
        required=True,
        help="Warn level (or range).  ie 512 or 1k:15k or 100M:2g"
    )

    # Critical range
    parser.add_argument(
        '--critical', '-c',
        action='store',
        type=str,
        required=True,
        help="Critical level (or range).  ie 768 or 512:20k or 50M:3g"
    )

    args = parser.parse_args()

    try:
        args.warn_min, args.warn_max = parse_range(args.warn)
    except ValueError:
        parser.exit(
            status=NAGIOS_UNKNOWN,
            message="Invalid value ({}) for warn\n".format(args.warn)
        )

    try:
        args.critical_min, args.critical_max = parse_range(args.critical)
    except ValueError:
        parser.exit(
            status=NAGIOS_UNKNOWN,
            message="Invalid value ({}) for critical\n".format(args.critical)
        )

    try:
        verify_range_validity(args)
    except ValueError as err:
        parser.exit(
            status=NAGIOS_UNKNOWN,
            message=str("{}\n".format(err))
        )

    return args


def parse_range(range_val):
    """
    Takes a range passed in from the cli, parses it, normalizes it to bytes
    """

    colon_count = range_val.count(':')
    
    if colon_count == 0:
        min_val = 0
        max_val = range_val

    elif colon_count == 1:
        min_val, max_val = range_val.split(':')

    else:
        raise ValueError('Too many colons')

    min_val = normalize_value(min_val)
    max_val = normalize_value(max_val)

    return min_val, max_val


def normalize_value(value):
    """
    Converts a value with a potential suffix of k/m/g to a full numeric value
    """

    value = str(value)

    match = value_re.fullmatch(value)

    if not match:
        raise ValueError('Does not match regex')

    if not match.group(2):
        normalized = int(match.group(1))
    
    elif match.group(2) in 'kK':
        normalized = int(match.group(1)) * KILOBYTE
    
    elif match.group(2) in 'mM':
        normalized = int(match.group(1)) * MEGABYTE
    
    elif match.group(2) in 'gG':
        normalized = int(match.group(1)) * GIGABYTE

    return normalized


def verify_range_validity(args):
    """
    Perform various checks 
    """

    # check for min > max
    if args.warn_min > args.warn_max:
        raise ValueError(
            "Warn minimum ({}) is greater than warn maximum ({})" \
                .format(args.warn_min, args.warn_max)
        )

    if args.critical_min > args.critical_max:
        raise ValueError(
            "Critical minimum ({}) is greater than critical maximum ({})" \
                .format(args.critical_min, args.critical_max)
        )

    if args.warn_min < args.critical_min:
        raise ValueError("Warning min must be higher than critical min")

    elif args.warn_max > args.critical_max:
        raise ValueError("Warning max must be lower than critical max")


def find_dir_size(args):

    total_bytes = 0

    if args.xdev:
        orig_dev = os.lstat(args.dir).st_dev

    for root, dirs, files in os.walk(args.dir, followlinks=False):
        if args.xdev:
            # If we've requested to stick to a single filesystem, filter out 
            # those files that are "elsewhere"
            if os.lstat(root).st_dev != orig_dev:
                files = []
            else:
                files = [
                    _ for _ in files
                    if os.lstat(os.path.join(root, _)).st_dev == orig_dev
                ]

        # Get the size of all files in the directory
        dir_bytes = sum(
            os.path.getsize(os.path.join(root, _))
            for _ in files
            if not os.path.islink(os.path.join(root, _))
        )
        total_bytes += dir_bytes
        #print(root, "consumes", end=" ")
        #print(dir_bytes, end=" ")
        #print("bytes in", len(files), "non-directory files")

    #print("Total bytes: ", str(total_bytes))
    return total_bytes


def output_response(args, dir_size):

    message = "{} size is {}".format(
        args.dir, prettify_number(dir_size)
    )
    status = NAGIOS_OK

    if dir_size > args.critical_max or dir_size < args.critical_min:
        status = NAGIOS_CRITICAL
        message = "CRIT - {}".format(message)

    elif dir_size > args.warn_max or dir_size < args.warn_min:
        status = NAGIOS_WARNING
        message = "WARNING - {}".format(message)

    else:
        status = NAGIOS_OK
        message = "OK - {}".format(message)

    print(message)
    sys.exit(status)


def prettify_number(number):
    """
    Take an integer and convert it to a units based string
    """

    if number > GIGABYTE:
        return "{:.3f}GB".format(number/float(GIGABYTE))
    elif number > MEGABYTE:
        return "{:.3f}MB".format(number/float(MEGABYTE))
    elif number > KILOBYTE:
        return "{:.3f}KB".format(number/float(KILOBYTE))
    else:
        return "{} bytes".format(str(number))


if __name__ == '__main__':
    main()