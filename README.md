# st7789v

Python scripts to drive a 240x320 ST7789V TFT display on Raspberry Pi over SPI.

## Overview

This repository contains Python scripts for a 2-inch 240x320 ST7789V TFT module.

Included scripts:

- `st7789v_display.py` — display a static image on the TFT
- `matrix_digital_rain.py` — Matrix-style digital rain animation with optional custom text and timestamp

## Hardware

Target display module:

- 2 inch TFT module 240x320 ST7789V GMT020-02 (example: https://goldenmorninglcd.com/tft-display-module/2-inch-240x320-st7789v-gmt020-02/)

These scripts may also work on other non-touch ST7789V-based TFT modules, but that is not guaranteed.

## TFT Module Wiring

ST7789V module wiring on the Raspberry Pi 40-pin GPIO header:

| TFT Pin | Raspberry Pi Pin | GPIO |
|--------|------------------|------|
| CS     | Pin 24           | GPIO8  |
| DC     | Pin 22           | GPIO25 |
| RST    | Pin 18           | GPIO24 |
| SDA    | Pin 19           | GPIO10 |
| SCL    | Pin 23           | GPIO11 |
| VCC    | Pin 17           | 3.3V   |
| GND    | Pin 20           | Ground |

## Requirements

Install dependencies:

    python3 -m pip install --upgrade pillow spidev numpy lgpio rpi-lgpio

## Usage

### Display a static image

Prepare a 240x320 image and run:

    python3 st7789v_display.py my_image.jpg

### Run Matrix digital rain

    python3 matrix_digital_rain.py

## Script Notes

### st7789v_display.py

- loads an image from the command line
- resizes it to 240x320
- converts it to RGB565
- sends it to the display over SPI

### matrix_digital_rain.py

- renders an animated digital rain effect
- supports optional top text
- supports optional timestamp display
- includes configurable colours, intensity, and FPS

## Configuration

Both scripts are configured for:

- resolution: 240x320
- SPI bus: 0
- SPI device: 0
- DC pin: GPIO25
- RST pin: GPIO24

Default SPI speed:

    40000000 (40 MHz)

If you see instability or corruption, try lowering SPI speed.

## Run at Boot

NB: use your own PATHs and images, of course.

Example with rc.local:

    /usr/bin/python3 /root/tft/st7789v_display.py /root/tft/my_image.jpg &
    /usr/bin/python3 /root/tft/matrix_digital_rain.py &

Example with cron:

    @reboot /usr/bin/python3 /root/tft/st7789v_display.py /root/tft/my_image.jpg &
    @reboot /usr/bin/python3 /root/tft/matrix_digital_rain.py &

## License

Released under the MIT License.

## Credits

SAIRPi Project
