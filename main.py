import RPIO
import subprocess
import sys
import time
from bisect import bisect_left
from threading import Timer

entrance_auth = 0.000
door_toolong_timer = None
RFID_READER_LINE_LEN = 10  # TODO verify this


def index(container, x):
    """Locate the leftmost value exactly equal to x"""
    i = bisect_left(container, x)
    if i != len(container) and container[i] == x:
        return i
    return -1


def play_alarm():
    subprocess.run('./alarm.sh')


def door_open_callback(gpio_id, val):
    """
    Start alert playback if entrance isn't authorized.
    :param gpio_id:
    :param val:
    :return:
    """
    # Both parameters unused.
    del gpio_id, val
    if time.monotonic() < entrance_auth:
        play_unauth_alarm()
    # Set a timer to sound an alarm if the door stays open too long.
    global door_toolong_timer
    door_toolong_timer = Timer(30.000, play_toolong_alarm)


def door_close_callback(gpio_id, val):
    """
    Reset door open authorization, stop any active alarm.
    :param gpio_id:
    :param val:
    :return:
    """
    # Both parameters unused.
    del gpio_id, val
    global entrance_auth
    entrance_auth = 0.000
    # Un-schedule "door open for too long" alarm
    door_toolong_timer.cancel()
    stop_alarms()


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
        global entrance_auth
        entrance_auth = time.monotonic() + 60.000  # Grant door authorization for the next minute.
        stop_alarms()

