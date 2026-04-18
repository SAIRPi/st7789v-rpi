#!/usr/bin/env python3
#
# Python script for TFT module 240x320 ST7789V GMT020-02-7P ver 1.3
#
# Exaga - 2026-04-16 - SAIRPi Project - https://sairpi.penthux.net
#
###
#
# TFT MODULE CONFIG:
# This script is intended for 2 inch TFT module 240x320 ST7789V GMT020-02:
# https://goldenmorninglcd.com/tft-display-module/2-inch-240x320-st7789v-gmt020-02/
#
# It may work on other non-touch TFT modules, but no guarantees!
#
# ST7789V module wiring on Raspberry Pi 40-pin GPIO header:
#
# CS  - pin 24 (GPIO8)
# DC  - pin 22 (GPIO25)
# RST - pin 18 (GPIO24)
# SDA - pin 19 (GPIO10)
# SCL - pin 23 (GPIO11)
# VCC - pin 17 (3v3)
# GND - pin 20 (Ground)
#
###
#
# USAGE:
# First install the required Python libraries:
#
#   python3 -m pip install --upgrade pillow spidev numpy lgpio rpi-lgpio
#
# Then create a 240 (W) x 320 (H) pixel image (.png, .jpg, .bmp) and run
# this script while referencing the image. For example:
#
#   python3 /root/tft/st7789v_display.py /root/tft/my_image.jpg
#
# You can enter this into /etc/rc.d/rc.local to run at boot time:
#
#   /usr/bin/python3 /root/tft/st7789v_display.py /root/tft/my_image.jpg & 
#
# Or enter in crontab and run as a cron job on reboot:
#
#   @reboot /usr/bin/python3 /root/tft/st7789v_display.py /root/tft/my_image.jpg &
#
# NB: Use your own PATHs and image files, of course. 
#
###
#
# LICENCE:
# This script is released under the MIT License. You are free to use, copy, 
# modify, merge, publish, distribute, sublicense, and/or sell copies of this 
# software, subject to the terms of the MIT License. If you reuse this work, 
# retain the original copyright notice and license text.
#
# Copyright (c) 2026 sairpi.penthux.net
#
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
###

# Import required libraries
import sys              # CLI arguments
import time             # Delays
import spidev           # SPI communication
import lgpio            # GPIO control
from PIL import Image   # Image loading and processing

# Display resolution
WIDTH = 240
HEIGHT = 320

# GPIO pin assignments (BCM numbering)
DC = 25    # Data Command pin
RST = 24   # Reset pin

# SPI configuration
SPI_BUS = 0
SPI_DEV = 0
SPI_SPEED = 40000000  # 40 MHz SPI speed (lower this if you have issues)

# Open GPIO chip (required for lgpio)
h = lgpio.gpiochip_open(0)

# Write HIGH/LOW to GPIO pin
def gpio_out(pin, value):
    lgpio.gpio_write(h, pin, value)

# Claim GPIO pins for output
lgpio.gpio_claim_output(h, DC)
lgpio.gpio_claim_output(h, RST)

# Send a command byte to the display
def cmd(spi, value):
    gpio_out(DC, 0)                # DC low = command mode
    spi.writebytes([value & 0xFF]) # send 1 byte

# Send data bytes to the display
def data(spi, values):
    gpio_out(DC, 1)                # DC high = data mode
    if isinstance(values, int):
        spi.writebytes([values & 0xFF])
    else:
        # Send in chunks to avoid buffer limits
        chunk = 4096
        for i in range(0, len(values), chunk):
            spi.writebytes(values[i:i+chunk])

# Hardware reset of the display
def reset():
    gpio_out(RST, 1)
    time.sleep(0.05)
    gpio_out(RST, 0)
    time.sleep(0.05)
    gpio_out(RST, 1)
    time.sleep(0.15)

# Define the rectangular area to write to
def set_window(spi, x0, y0, x1, y1):
    cmd(spi, 0x2A)  # Column address set
    data(spi, [x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])

    cmd(spi, 0x2B)  # Row address set
    data(spi, [y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])

    cmd(spi, 0x2C)  # Memory write for sending pixel data

# Initialise the ST7789 display
def init_display(spi):
    reset()

    cmd(spi, 0x36)      # Memory data access control rotation/orientation
    data(spi, 0x00)

    cmd(spi, 0x3A)      # Interface pixel format
    data(spi, 0x05)     # 16-bit colour (RGB565)

    cmd(spi, 0x21)      # Display inversion ON to improve colours
    cmd(spi, 0x11)      # Sleep OUT to wake display
    time.sleep(0.12)

    cmd(spi, 0x29)      # Display ON
    time.sleep(0.05)

# Convert image to RGB565 byte format - what this TFT module expects
def image_to_rgb565_bytes(img):
    img = img.convert("RGB")
    out = bytearray()

    for r, g, b in img.getdata():  # NB: will be deprecated in pillow 14!
  # for r, g, b in img.get_flattened_data(): # use this instead on latest pillow version        
        # Convert 24-bit RGB to 16-bit RGB565
        value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out.append((value >> 8) & 0xFF)
        out.append(value & 0xFF)

    return out

# Main program
def main():
    # Require exactly one argument for image path
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} IMAGE")
        sys.exit(1)

    # Setup SPI
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEV)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = 0

    try:
        # Initialise display
        init_display(spi)

        # Load and resize image to screen resolution
        img = Image.open(sys.argv[1]).resize((WIDTH, HEIGHT))

        # Convert image to display format
        fb = image_to_rgb565_bytes(img)

        # Set entire screen as drawing area
        set_window(spi, 0, 0, WIDTH - 1, HEIGHT - 1)

        # Send pixel data to display
        data(spi, fb)

        print("Image sent to display.")

    finally:
        # Clean up SPI and GPIO
        spi.close()
        lgpio.gpiochip_close(h)

# Entry point
if __name__ == "__main__":
    main()

# EOF<*>
