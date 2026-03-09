# Adapted from:
# https://github.com/tstack/lnav/blob/master/demo/loggen.py
import datetime
import random
import sys

# random.seed(42)

MSGS = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
]

GLOG_DATE_FMT = "%Y%m%d %H:%M:%S"

START_TIME = datetime.datetime.fromtimestamp(1490191111)

PIDS = [
    "123",
    "123",
    "123",
    "121",
    "124",
    "123",
    "61456",
    "61456",
    "61457",
]

LOG_LOCS = [
    "hello.py:123",
    "hello.py:352",
    "isd_tester.py:13",
    "isd_tester.py:552",
    "some_other_bin:352",
    "some_other_bin:112",
    "some_other_bin:6782",
]

CURR_TIME = START_TIME
for _index in range(0, int(sys.argv[1])):
    CURR_TIME += datetime.timedelta(seconds=random.randrange(1, 22))
    print(
        "I%s.%06d %s %s] %s"
        % (
            CURR_TIME.strftime(GLOG_DATE_FMT),
            random.randrange(0, 100000),
            random.choice(PIDS),
            random.choice(LOG_LOCS),
            random.choice(MSGS),
        )
    )
