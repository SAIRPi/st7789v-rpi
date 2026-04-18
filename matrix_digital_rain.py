#!/usr/bin/env python3
#
# Python script for TFT module 240x320 ST7789V GMT020-02-7P ver 1.3
#
# Matrix Digital Rain (optional timestamp and custom text)
#
# Exaga - 2026-04-18 - SAIRPi Project - https://sairpi.penthux.net
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
# Copy this script to a location where root can execute it. For example:
#
#   python3 /root/matrix_digital_rain.py &
#
# You can enter this into /etc/rc.d/rc.local to run at boot time:
#
#   /usr/bin/python3 /root/matrix_digital_rain.py &
#
# Or enter in crontab and run as a cron job on reboot:
#
#   @reboot /usr/bin/python3 /root/matrix_digital_rain.py &
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
import time
import random
import spidev
import lgpio
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from datetime import datetime

# Settings
# RGB values for colour settings
RAIN_RGB = (0, 255, 70)
TEXT_RGB = (0, 255, 255)
DATETIME_RGB = (255, 255, 255)

# Intensity of digital rain on screen [0 = none | 9 = max]
INTENSITY = 5

# Display FPS
FPS = 30

# Optional text at top of screen (leave blank "" for no text)
# MAX 24 chars per line!
TEXT_LINES = [
  "First Line",
  "Maximum Characters is 24", 
  "Third Line",
  "THIS IS THE FOURTH - 4TH"
  ]

# Display timestamp at bottom of screen (1 = show | 0 = hide it) 
SHOW_DATETIME = 1

# Display resolution
WIDTH = 240
HEIGHT = 320

# GPIO pin assignments (BCM numbering)
DC = 25
RST = 24

# SPI configuration
SPI_BUS = 0
SPI_DEV = 0
SPI_SPEED = 40000000  # 40 MHz SPI speed (lower this if you have issues)

# Open GPIO chip (required for lgpio)
gpio = lgpio.gpiochip_open(0)

# Claim GPIO pins for output
lgpio.gpio_claim_output(gpio, DC)
lgpio.gpio_claim_output(gpio, RST)

# Write HIGH/LOW to GPIO pin
def gpio_out(pin, value):
    lgpio.gpio_write(gpio, pin, value)

# Send a command byte to the display
def send_cmd(spi, value):
    gpio_out(DC, 0)
    spi.writebytes([value & 0xFF])

# Send bytes to display buffer
def send_data(spi, values):
    gpio_out(DC, 1)
    if isinstance(values, int):
        spi.writebytes([values & 0xFF])
    else:
        for i in range(0, len(values), 4096):
            spi.writebytes(values[i:i + 4096])

# Display controller reset sequence
def reset_display():
    gpio_out(RST, 1)
    time.sleep(0.05)
    gpio_out(RST, 0)
    time.sleep(0.05)
    gpio_out(RST, 1)
    time.sleep(0.15)

# Set area that sent pixel data fills
def set_window(spi, x0, y0, x1, y1):
    send_cmd(spi, 0x2A)
    send_data(spi, [x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
    send_cmd(spi, 0x2B)
    send_data(spi, [y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
    send_cmd(spi, 0x2C)

# Initialise display with pixel format and state
def init_display(spi):
    reset_display()
    send_cmd(spi, 0x36)
    send_data(spi, 0x00)
    send_cmd(spi, 0x3A)
    send_data(spi, 0x05)
    send_cmd(spi, 0x21)
    send_cmd(spi, 0x11)
    time.sleep(0.12)
    send_cmd(spi, 0x29)
    time.sleep(0.05)

# Convert RGB image to RGB565
def image_to_rgb565(img):
    img = img.convert("RGB")
    out = bytearray()
    for r, g, b in img.getdata(): # NB: will be deprecated in pillow 14!
  # for r, g, b in img.get_flattened_data(): # use this instead on latest pillow version
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out.append((v >> 8) & 0xFF)
        out.append(v & 0xFF)
    return out

# Digital rain effects
# Clamp numeric value to RGB range
def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))

# Scale RGB colour by brightness factor
def scale_color(rgb, factor):
    return (
        clamp(rgb[0] * factor),
        clamp(rgb[1] * factor),
        clamp(rgb[2] * factor),
    )

# Blend two RGB colours
def blend(c1, c2, t):
    return (
        clamp(c1[0] * (1 - t) + c2[0] * t),
        clamp(c1[1] * (1 - t) + c2[1] * t),
        clamp(c1[2] * (1 - t) + c2[2] * t),
    )

# Map INTENSITY to normalised 0.0-1.0 range
def intensity_ratio():
    return max(0.0, min(1.0, (INTENSITY - 1) / 8.0))

# Control number of active streams on screen
def stream_density():
    r = intensity_ratio()
    return 0.03 + (r ** 1.8) * 0.94

# Digital rain generator
class Stream:
    def __init__(self, x, char_h, intensity, chars):
        self.x = x
        self.char_h = char_h
        self.intensity = intensity
        self.chars = chars
        self.reset(1)

    # Start stream with position and contents
    def reset(self, initial):
        density = stream_density()
        self.active = 1 if random.random() < density else 0

        if initial == 1:
            self.head_y = random.randint(-HEIGHT * 2, HEIGHT)
        else:
            self.head_y = random.randint(-HEIGHT * 4, -self.char_h)

        r = intensity_ratio()

        # Longer trails at higher intensity
        min_len = 16 + int(r * 8)
        max_len = 34 + int(r * 12)
        self.length = random.randint(min_len, max_len)

        # Per-frame pixel speed for smoother motion
        self.speed = random.uniform(2.2, 5.2)
        self.pause = 0
        self.buffer = [random.choice(self.chars) for _ in range(self.length)]

    def update(self):
        if self.active == 0:
            # Low-intensity is sparse - high intensity displays more
            if random.random() < (0.002 + stream_density() * 0.02):
                self.reset(0)
            return

        if self.pause > 0:
            self.pause -= 1
            return

        old_cell = int(self.head_y // self.char_h)
        self.head_y += self.speed
        new_cell = int(self.head_y // self.char_h)
        steps = new_cell - old_cell

        for _ in range(max(0, steps)):
            self.buffer.insert(0, random.choice(self.chars))
            self.buffer.pop()

        if random.random() < 0.008:
            self.pause = random.randint(1, 3)

        tail_y = self.head_y - (self.length * self.char_h)
        if tail_y > HEIGHT:
            self.reset(0)

    # Draw stream with glow layer
    def draw(self, draw_ctx, glow_ctx, font, base_color):
        if self.active == 0:
            return

        glow_outer = scale_color(base_color, 1.00)
        glow_inner = scale_color(base_color, 0.85)
        head_color = scale_color(base_color, 1.00)
        head2_color = scale_color(base_color, 0.80)
        head3_color = scale_color(base_color, 0.65)

        for i in range(self.length):
            y = self.head_y - (i * self.char_h)
            if y < -self.char_h or y >= HEIGHT:
                continue

            ch = self.buffer[i]

            if i == 0:
                glow_ctx.text((self.x, y), ch, font=font, fill=glow_outer)
                glow_ctx.text((self.x, y), ch, font=font, fill=glow_outer)
                draw_ctx.text((self.x, y), ch, font=font, fill=head_color)
            elif i == 1:
                glow_ctx.text((self.x, y), ch, font=font, fill=glow_inner)
                draw_ctx.text((self.x, y), ch, font=font, fill=head2_color)
            elif i == 2:
                draw_ctx.text((self.x, y), ch, font=font, fill=head3_color)
            else:
                fade = 1.0 - (i / self.length)
                fade = max(0.16, fade ** 0.70)
                color = scale_color(base_color, fade)
                draw_ctx.text((self.x, y), ch, font=font, fill=color)

# Matrix digital rain runtime
def main():
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEV)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = 0

    init_display(spi)

    # Load fixed-width font so chars align
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 12)
    except Exception:
        font = ImageFont.load_default()

    # Measure one char to size stream grid
    bbox = font.getbbox("A")
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]

    # Char set for digital rain effect
    rain_chars = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "@#$%&*+-=<>"
        "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿ"
        "ﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎ"
        "ﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜ"
    )

    # Create one stream per column
    cols = max(1, WIDTH // char_w)
    streams = []

    for i in range(cols):
        x = i * char_w
        streams.append(Stream(x, char_h, INTENSITY, rain_chars))

    frame_delay = 1.0 / FPS
    base = RAIN_RGB

    try:
        # Main render loop        
        while 1:
            t0 = time.time()

            # Build a fresh frame and a separate glow layer
            img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            glow = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

            draw = ImageDraw.Draw(img)
            glow_draw = ImageDraw.Draw(glow)

            for stream in streams:
                stream.update()
                stream.draw(draw, glow_draw, font, base)

            # Blur the glow layer
            glow = glow.filter(ImageFilter.GaussianBlur(radius=2.4))
            img = ImageChops.add(img, glow)

            draw = ImageDraw.Draw(img)

            # Draw optional custom text at top of screen
            for i, line in enumerate(TEXT_LINES):
                if line:
                    # Max 24 chars per custom text line
                    line = line[:24]
                    tb = font.getbbox(line)
                    tw = tb[2] - tb[0]
                    tx = (WIDTH - tw) // 2
                    ty = 10 + i * (char_h + 2)
                    draw.text((tx, ty), line, font=font, fill=TEXT_RGB)

            # Draw an optional timestamp at bottom of screen
            if SHOW_DATETIME == 1:
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db = font.getbbox(dt)
                dw = db[2] - db[0]
                dh = db[3] - db[1]
                dx = (WIDTH - dw) // 2
                dy = HEIGHT - dh - 6
                draw.rectangle((dx - 2, dy - 1, dx + dw + 2, dy + dh + 1), fill=(0, 0, 0))
                draw.text((dx, dy), dt, font=font, fill=DATETIME_RGB)

            # Convert frame buffer for display
            fb = image_to_rgb565(img)
            set_window(spi, 0, 0, WIDTH - 1, HEIGHT - 1)
            send_data(spi, fb)

            # Cap the loop to the configured frame rate
            elapsed = time.time() - t0
            sleep_time = frame_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    finally:
        # Release SPI and GPIO on exit
        spi.close()
        lgpio.gpiochip_close(gpio)

# Run the script
if __name__ == "__main__":
    main()

# EOF<*>
