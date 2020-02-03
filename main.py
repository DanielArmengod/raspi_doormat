import subprocess
import sys
from bisect import bisect_left

import RPIO


def index(container, x):
    'Locate the leftmost value exactly equal to x'
    i = bisect_left(container, x)
    if i != len(container) and container[i] == x:
        return i
    return -1


entrance_auth = 0
RFID_READER_LINE_LEN = 10  # TODO verify this


def play_alarm():
    subprocess.run('./alarm.sh')


def door_callback(gpio_id, val):
    """
    Called when the door is opened. Start alert playback if entrance isn't authorized.
    :param gpio_id:
    :param val:
    :return:
    """
    # Both parameters unused
    del gpio_id, val
    global entrance_auth
    if not entrance_auth:
        play_alarm()


def main():
    # Populate the valid ID list.
    # Assumptions: list contains only legal strings (numbers), list is already ordered.
    with open('./valid_ids.txt') as valid_ids_file:
        valid_ids = map(int, valid_ids_file)

    # Main, endless loop.
    for line in sys.stdin:
        if len(line) != RFID_READER_LINE_LEN:
            raise ValueError(f"Wrong input on STDIN:\n{line}")
        try:
            new_id = int(line)
        except ValueError:
            raise ValueError(f"Wrong input on STDIN:\n{line}")

        if index(valid_ids, new_id) == -1:
            # invalid card # found.
            print(f'Invalid card # found: {new_id}')
            continue

