#!/usr/bin/env python3
#
# Python script for TFT module 240x320 ST7789V GMT020-02-7P ver 1.3
#
# System Monitor Edition for Raspberry Pi 5 (Slackware Linux)
#
# Exaga - 2026-04-18 - SAIRPi Project - https://sairpi.penthux.net
#
###
#
# TFT MODULE CONFIG:
# This script is intended for 2 inch TFT module 240x320 ST7789V GMT020-02:
# https://goldenmorninglcd.com/tft-display-module/2-inch-240x320-st7789v-gmt020-02/
#
# Optimised for Pi 5: Uses 'lgpio' to handle the RP1 southbridge chip.
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
#    python3 -m pip install --upgrade pillow spidev lgpio
#
# Run this script to display real-time system metrics:
#
#    python3 /root/stats/rpi_system_stats.py
#
# You can enter this into /etc/rc.d/rc.local to run at boot time:
#
#    /usr/bin/python3 /root/stats/rpi_system_stats.py & 
#
# You can enter this into crontab to run on reboot:
#
#    @reboot /usr/bin/python3 /root/stats/rpi_system_stats.py & 
#
# NB: Use your own PATHs, of course.
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
import os
import re
import glob
import time
import socket
import spidev
import lgpio
from PIL import Image, ImageDraw, ImageFont

# Physical dimensions of the GMT020-02 TFT panel
WIDTH = 240
HEIGHT = 320

# GPIO pin assignments (BCM numbering)
DC = 25
RST = 24

# SPI config - Bus 0, Device 0
SPI_BUS = 0
SPI_DEV = 0
SPI_SPEED = 40000000 # 40 MHz SPI speed (lower this if you have issues)
REFRESH = 0.5 # How often the display refreshes (in seconds)

# Configurable RGB Colours (R, G, B)
BACKGROUND = (0, 0, 0)           # Display background colour
STATS_TEXT = (235, 235, 235)     # System stats text colour
SUB_TEXT = (140, 140, 140)       # Sub-text categories colour
LINE_SEPS = (70, 70, 70)         # Line separators colour

# Standard font locations
FONT_PATHS = [
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

h = None

# Identify all available gpiochip devices
def find_gpiochip_numbers():
    chips = []
    for path in sorted(glob.glob("/dev/gpiochip*")):
        m = re.search(r"gpiochip(\d+)$", path)
        if m:
            chips.append(int(m.group(1)))
    return chips

# Pi 5 specific for RP1 chip
def open_working_gpiochip():
    chips = find_gpiochip_numbers()
    if not chips:
        raise RuntimeError("No /dev/gpiochip* devices found")
    for chip in reversed(chips):
        handle = None
        try:
            handle = lgpio.gpiochip_open(chip)
            lgpio.gpio_claim_output(handle, DC)
            lgpio.gpio_claim_output(handle, RST)
            return handle, chip
        except Exception:
            if handle is not None:
                lgpio.gpiochip_close(handle)
    raise RuntimeError("Could not find a working gpiochip")

# Write HIGH/LOW to GPIO pin
def gpio_out(pin, value):
    lgpio.gpio_write(h, pin, value)

# Send command to display
def cmd(spi, value):
    gpio_out(DC, 0)
    spi.writebytes([value & 0xFF])

# Send data to display
def data(spi, values):
    gpio_out(DC, 1)
    if isinstance(values, int):
        spi.writebytes([values & 0xFF])
    else:
        chunk = 4096
        for i in range(0, len(values), chunk):
            spi.writebytes(values[i:i + chunk])

# Hardware reset
def reset():
    gpio_out(RST, 1)
    time.sleep(0.05)
    gpio_out(RST, 0)
    time.sleep(0.05)
    gpio_out(RST, 1)
    time.sleep(0.15)

# Set memory window boundaries
def set_window(spi, x0, y0, x1, y1):
    cmd(spi, 0x2A)
    data(spi, [x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
    cmd(spi, 0x2B)
    data(spi, [y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
    cmd(spi, 0x2C)

# ST7789V init sequence
def init_display(spi):
    reset()
    cmd(spi, 0x11)
    time.sleep(0.12)
    cmd(spi, 0x36)
    data(spi, 0x00)
    cmd(spi, 0x3A)
    data(spi, 0x05)
    cmd(spi, 0x21)
    cmd(spi, 0x13)
    cmd(spi, 0x29)
    time.sleep(0.05)

# Convert RGB to RGB565
def image_to_rgb565_bytes(img):
    img = img.convert("RGB")
    out = bytearray()
    for r, g, b in img.getdata():
        value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out.append((value >> 8) & 0xFF)
        out.append(value & 0xFF)
    return out

# Font loader
def load_font(size):
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    return ImageFont.load_default()

# Get network IP
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "no network"

# System data collection
def get_stats():
    # Uptime
    try:
        with open("/proc/uptime", "r") as f:
            sec = int(float(f.read().split()[0]))
            up = f"{sec // 3600}h {(sec % 3600) // 60}m"
    except: up = "n/a"
    # CPU Temp
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = f"{float(f.read())/1000:.1f} C"
    except: temp = "n/a"
    # RAM Usage
    try:
        with open("/proc/meminfo", "r") as f:
            m = {l.split(':')[0]: int(l.split()[1]) for l in f.readlines()}
        total = m['MemTotal']
        avail = m.get('MemAvailable', m.get('MemFree'))
        used = (total - avail) // 1024
        mem = f"{used}/{total//1024}MB ({int((total-avail)*100/total)}%)"
    except: mem = "n/a"
    # Disk Usage
    try:
        st = os.statvfs("/")
        d_total = st.f_blocks * st.f_frsize
        d_free = st.f_bavail * st.f_frsize
        d_used = d_total - d_free
        d_perc = int(d_used * 100 / d_total)
        disk = f"{d_used/(1024**3):.1f}/{d_total/(1024**3):.1f}GB ({d_perc}%)"
    except: disk = "n/a"

    # Output system stat values
    return [
        ("HOST", socket.gethostname()),
        ("IP", get_ip()),
        ("UP", up),
        ("LOAD", f"{os.getloadavg()[0]:.2f}"),
        ("TEMP", temp),
        ("MEM", mem),
        ("DISK", disk),
    ]

# Main runtime
def main():
    global h
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEV)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = 0

    h, _ = open_working_gpiochip()
    
    title_f = load_font(18)
    norm_f = load_font(14)
    footer_f = load_font(15)
    small_f = load_font(11)

    try:
        # Initialise display
        init_display(spi)
        while True:
            # Load and resize image to screen resolution
            img = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
            draw = ImageDraw.Draw(img)
            
            # Header
            draw.text((15, 12), "SYSTEM STATUS", font=title_f, fill=STATS_TEXT)
            draw.line((15, 38, WIDTH-15, 38), fill=LINE_SEPS)

            # System metrics
            stats = get_stats()
            for i, (label, val) in enumerate(stats):
                y = 52 + (i * 34)
                draw.text((15, y), label, font=small_f, fill=SUB_TEXT)
                draw.text((75, y-2), val, font=norm_f, fill=STATS_TEXT)
                if i < len(stats) - 1:
                    draw.line((15, y+25, WIDTH-15, y+25), fill=LINE_SEPS)

            # Footer
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            bbox = draw.textbbox((0, 0), ts, font=footer_f)
            tx = (WIDTH - (bbox[2] - bbox[0])) // 2
            
            draw.line((15, HEIGHT-38, WIDTH-15, HEIGHT-38), fill=LINE_SEPS)
            draw.text((tx, HEIGHT-30), ts, font=footer_f, fill=STATS_TEXT)

            fb = image_to_rgb565_bytes(img)
            set_window(spi, 0, 0, WIDTH - 1, HEIGHT - 1)
            data(spi, fb)
            time.sleep(REFRESH)
    finally:
        spi.close()
        if h is not None:
            lgpio.gpiochip_close(h)

# Entry point
if __name__ == "__main__":
    main()

# EOF<*>
  
