import threading

import RPIO
import subprocess
import sys
import time
from bisect import bisect_left
from threading import Timer

entrance_auth = 0.000
RFID_READER_LINE_LEN = 10  # TODO verify this
alarm_process = None
too_long_alarm_timer = None
door_open = 0

def index(container, x):
    """Locate the leftmost value exactly equal to x"""
    i = bisect_left(container, x)
    if i != len(container) and container[i] == x:
        return i
    return -1


def play_unauth_alarm():
    global alarm_process
    alarm_process = subprocess.Popen(['cvlc', '-L', 'buzzer.mp3'])


def play_toolong_alarm():
    # TODO: different sounds for different alarms
    global alarm_process
    alarm_process = subprocess.Popen(['cvlc', '-L', 'buzzer.mp3'])


def stop_alarms():
    global alarm_process
    try:
        alarm_process.terminate()
    except AttributeError:
        pass
    alarm_process = None


def door_open_callback(gpio_id, val):
    """
    Start alert playback if entrance isn't authorized.
    :param gpio_id:
    :param val:
    :return:
    """
    global door_open
    door_open = 0
    # Both parameters unused.
    del gpio_id, val
    # If door opening was unauth'd, sound alarm and return.
    if time.monotonic() < entrance_auth:
        play_unauth_alarm()
        return
    # Set a timer to sound an alarm if the door stays open too long.
    global too_long_alarm_timer
    if isinstance(too_long_alarm_timer, Timer):
        too_long_alarm_timer.cancel()
        too_long_alarm_timer = None
    too_long_alarm_timer = Timer(45.000, play_toolong_alarm)


def door_close_callback(gpio_id, val):
    """
    Reset door open authorization & stop any active alarm.
    :param gpio_id:
    :param val:
    :return:
    """
    global door_open
    door_open = 0
    # Both parameters unused.
    del gpio_id, val
    # Deauthorize door.
    global entrance_auth
    entrance_auth = 0.000
    # Un-schedule "door open for too long" alarm if it exists.
    global too_long_alarm_timer
    if isinstance(too_long_alarm_timer, Timer):
        too_long_alarm_timer.cancel()
        too_long_alarm_timer = None
    # Stop any running alarms.
    stop_alarms()


def main():
    # Populate the valid ID list.
    # Assumptions: list contains only legal strings (numbers), list is already ordered.
    with open('./valid_ids.txt') as valid_ids_file:
        valid_ids = list(map(int, valid_ids_file))

    # Main, endless loop.
    for line in sys.stdin:
        if len(line) != RFID_READER_LINE_LEN:
            print(f"Wrong input on STDIN:\n{line}")
            continue
        try:
            new_id = int(line)
        except ValueError:
            print("Wrong input on STDIN:\n{line}")
            continue
        # Validate access card token.
        if index(valid_ids, new_id) == -1:
            print(f'Invalid card # found: {new_id}')
            continue
        # Is the door open? Stop any running alarm & re-schedule "toolong" alarm
        if door_open:
            global too_long_alarm_timer
            if isinstance(too_long_alarm_timer, Timer):
                too_long_alarm_timer.cancel()
                too_long_alarm_timer = None
            too_long_alarm_timer = Timer(45.000, play_toolong_alarm)
            stop_alarms()
            continue
        # Grant door authorization & stop any active alarms.
        global entrance_auth
        entrance_auth = time.monotonic() + 20.000
