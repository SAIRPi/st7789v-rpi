# 2 inch TFT Module 240×320 ST7789V GMT020-02 Display

Python scripts to drive a 240x320 ST7789V TFT display on Raspberry Pi over SPI on Slackware Linux operating systems.

## Overview

This repository contains Python scripts for a 2-inch 240x320 ST7789V TFT module.

Included scripts:

- `st7789v_display.py` — display a static image on the TFT
- `matrix_digital_rain.py` — Matrix-style digital rain animation with optional custom text and timestamp

## Hardware

Target display module:

- 2 inch TFT module 240x320 ST7789V GMT020-02 (example: https://goldenmorninglcd.com/tft-display-module/2-inch-240x320-st7789v-gmt020-02/)

These scripts may also work on other non-touch ST7789V-based TFT modules, but no guarantees! Try them and see for yourselves.

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

### Run Matrix digital rain generator script

    python3 matrix_digital_rain.py

## Script Notes

**NB:** Complete notes are in the script headers. The scripts are also quite well commented in the code to make it easy for editing and personal adjustments.

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

If you see instability or image rendering issues/distortion, try lowering SPI speed.

## Run at Boot

**NB:** use your own PATHs and images, of course.

Example entry in /etc/rc.d/rc.local:

    /usr/bin/python3 /root/tft/st7789v_display.py /root/tft/my_image.jpg &
    /usr/bin/python3 /root/tft/matrix_digital_rain.py &

Example entry in crontab:

    @reboot /usr/bin/python3 /root/tft/st7789v_display.py /root/tft/my_image.jpg &
    @reboot /usr/bin/python3 /root/tft/matrix_digital_rain.py &

## Notes On ST7789V display behaviour

### Static image uploads

When using `st7789v_display.py`, the image is sent to the ST7789V display framebuffer as a one-time transfer.

After the image has been uploaded:

- it remains visible on the screen
- it is not continuously refreshed by the script
- it will stay displayed until another image is sent to the display, the display contents are changed by another program, or power is removed from the module

In other words, once the image has been written to the display, it will remain - even though the `st7789v_display.py` script exits cleanly.

This is not the same with `matrix_digital_rain.py` - when the script is exited (i.e. CTRL+C) the screen will freeze but still display the last frame in the buffer. The display will not continue to show the falling Matrix digital rain illusion because the script is no longer driving that process.

### Important note

The display will continue displaying the last written image even after the host system is rebooted or poweroff/shutdown command is used. For as long as the TFT module itself is  receiving power the image will be displayed on screen.

Only when all power to the display module is cut will the image disappear from the screen.

## License

Released under the MIT License.

## Credits

SAIRPi Project
