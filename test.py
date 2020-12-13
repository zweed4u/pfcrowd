#!/usr/bin/python3
import os
import json
import time
import datetime
import requests
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from typing import Optional
import numpy as np
import cv2
from pytz import timezone


def get_crowd_percentage(image):
    image = cv2.imread(image)
    # cv2.imshow('image',image)
    # define the list of boundaries
    boundaries = [
        # G   B    R     G   B    R
        # >=  >=   >=    <=  <=   <=
        ([190, 190, 190], [255, 255, 255])
    ]

    # loop over the boundaries
    for (lower, upper) in boundaries:
        # create NumPy arrays from the boundaries
        lower = np.array(lower, dtype="uint8")
        upper = np.array(upper, dtype="uint8")
        # find the colors within the specified boundaries and apply
        # the mask
        mask = cv2.inRange(image, lower, upper)
        output = cv2.bitwise_and(image, image, mask=mask)
        # show the images
        # cv2.imshow("images", output)
        # cv2.waitKey(0)
        height = len(output)
        length = len(output[int(height / 2)])
        progress = 0
        bar_offset = (
            7  # screenshot webelement has 7 pixels on the left before bars starts
        )
        # loop through the horizontal pixels on the midline
        # increment until the first not black pixel is found.
        for x_pixel_bgr in output[int(height / 2)]:
            if not np.any(x_pixel_bgr):
                progress += 1
            else:
                break
        total_x_pixels = length - bar_offset
        x_pixels_until_gray_bar = max(progress - bar_offset, 0)
        return x_pixels_until_gray_bar, total_x_pixels


eastern = timezone("US/Eastern")
print(f"[*] {datetime.datetime.now(eastern)} :: Parsing cli options")
parser = argparse.ArgumentParser()
parser.add_argument("--poll", type=int, default=3600)
parser.add_argument(
    "--image", help="path to the image", type=str, default="screen_shot.png"
)

args = parser.parse_args()
poll = args.poll
image_path = args.image


print(f"[*] {datetime.datetime.now(eastern)} :: Setting up webdriver options")
options = Options()
options.headless = True
# start-maximized flag doesnt work in headless - makes sense; instead explicitly set
# options.add_argument("--start-maximized")
options.add_argument("--window-size=1440x900")

total_bars = (
    20  # this is the total number of bars in the graphic. ie. each bar worth 5%
)

print(f"[*] {datetime.datetime.now(eastern)} :: Initializing webdriver")
driver = webdriver.Chrome(options=options)
# driver.delete_all_cookies()
url = "https://www.planetfitness.com/gyms/danvers-ma"
running = True
while running:
    try:
        print(f"[*] {datetime.datetime.now(eastern)} :: Visiting...")
        driver.get(url)
        try:
            # complete_capacity_div = driver.find_element_by_class_name("club-capacity")
            # complete_capacity_div.screenshot('screen_shot.png')
            capacity_meter_div = driver.find_element_by_class_name(
                "club-capacity-meter"
            )
            capacity_meter_div.screenshot("screen_shot.png")
            x_pixels_until_gray_bar, total_x_pixels = get_crowd_percentage(image_path)
            crowd_percentage = x_pixels_until_gray_bar / total_x_pixels
            print(
                f"[!] {datetime.datetime.now(eastern)} :: Current Crowd Percentage: ~{round(crowd_percentage*100,2)}% - Filled Bar to Total Pixels: {x_pixels_until_gray_bar}/{total_x_pixels} - Bars: [{int(round(crowd_percentage,2)*total_bars)}] out of {total_bars}"
            )
        except Exception as exc:
            print(
                f"[!] {datetime.datetime.now(eastern)} :: Error in finding element, screenshotting, or getting percentage: {exc}"
            )
        time.sleep(poll)
    except (Exception, KeyboardInterrupt) as exc:
        print(
            f"[*] {datetime.datetime.now(eastern)} :: SIGINT caught - closing browser"
        )
        running = False
        continue
# driver.close() #raises an exception for some reason? (Failed to establish a new connection)
