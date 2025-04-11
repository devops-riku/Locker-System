from machine import Pin
import time

class Keypad:
    def __init__(self, keys, row_pins, col_pins):
        self.keys = keys
        self.row_pins = [Pin(pin, Pin.OUT) for pin in row_pins]
        self.col_pins = [Pin(pin, Pin.IN, Pin.PULL_DOWN) for pin in col_pins]
        self.last_key_time = 0
        self.debounce = 200  # ms

    def get_key(self):
        for row_num, row_pin in enumerate(self.row_pins):
            row_pin.value(1)
            for col_num, col_pin in enumerate(self.col_pins):
                if col_pin.value() == 1:
                    now = time.ticks_ms()
                    if time.ticks_diff(now, self.last_key_time) > self.debounce:
                        self.last_key_time = now
                        row_pin.value(0)
                        return self.keys[row_num][col_num]
            row_pin.value(0)
        return None
