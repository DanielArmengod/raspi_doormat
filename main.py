import subprocess
import sys
import time
from bisect import bisect_left
from threading import Timer

import gpiozero

entrance_auth = 0.000
RFID_READER_LINE_LEN = 10  # TODO verify this  - 9 digits + \n
alarm_process = None
too_long_alarm_timer = None
door_open = 0
door_sense_gpio = None  # Will be defined as Button in main()


def index(container, x):
    """Locate the leftmost value exactly equal to x"""
    i = bisect_left(container, x)
    if i != len(container) and container[i] == x:
        return i
    return -1


def play_unauth_alarm():
    global alarm_process
    print("play_unauth_alarm")
    alarm_process = subprocess.Popen(['sudo', '-ufiberparty', 'cvlc', '-L', 'buzzer.mp3'])


def play_toolong_alarm():
    # TODO: different sounds for different alarms
    global alarm_process
    print("play_toolong_alarm")
    alarm_process = subprocess.Popen(['sudo', '-ufiberparty', 'cvlc', '-L', 'buzzer.mp3'])


def stop_alarms():
    print("stop_alarms")
    global alarm_process
    try:
        alarm_process.send_signal(15)
        alarm_process.wait()
    except AttributeError as e:
        print(e)
        pass
    alarm_process = None


def door_open_handler():
    """
    Start alert playback if entrance isn't authorized.
    """
    print("door_open_handler")
    global door_open
    door_open = 0
    # If door opening was unauth'd, sound alarm and return.
    if time.monotonic() < entrance_auth:
        play_unauth_alarm()
        return
    # Set a timer to sound an alarm if the door stays open too long.
    global too_long_alarm_timer
    if isinstance(too_long_alarm_timer, Timer):
        too_long_alarm_timer.cancel()
        too_long_alarm_timer = None
    too_long_alarm_timer = Timer(5.000, play_toolong_alarm)
    too_long_alarm_timer.start()


def door_close_handler():
    """
    Reset door open authorization & stop any active alarm.
    """
    print("door_close_handler")
    global door_open
    door_open = 0
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
    # Configure door-sensing GPIO.
    global door_sense_gpio
    # GND pin is #39, bottom left of the pin header.
    door_sense_gpio = gpiozero.Button(
        21,  # Physical GPIO #40, bottom right near USB connectors.
        pull_up=True,  # pull_up=False would mean "enable pull-down resistor", pull_up=None is "leave it floating".
        bounce_time=0.20,
        hold_time=0
        )
    # TODO: VERIFY LOGIC -- This logic is valid for Normally Open door-sense switch.
    door_sense_gpio.when_pressed = door_open_handler
    door_sense_gpio.when_released = door_close_handler

    # Populate the valid ID list.
    # Assumptions: list contains only legal strings (numbers), list is already ordered.
    with open('./valid-ids.txt') as valid_ids_file:
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
            too_long_alarm_timer.start()
            stop_alarms()
            continue
        # Grant door authorization & stop any active alarms.
        global entrance_auth
        entrance_auth = time.monotonic() + 20.000



main()