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


class SlackRequester:
    def __init__(self, url: Optional[str]):
        self.url = url

    def send_message(self, message: str):
        slack_response = requests.request("POST", self.url, json={"text": message})


def get_crowd_percentage(image):
    image = cv2.imread(image)
    # cv2.imshow('image',image)
    # define the list of boundaries
    boundaries = [
        # G   B    R     G   B    R
        # >=  >=   >=    <=  <=   <=
        ([190, 190, 190], [254, 254, 254])  # white is 255 - in between
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
        bar_offset = 1  # EDIT THIS WAS 7 BUT SCREENSHOT OF ELEMENT WITH NEW SITE IS 1- screenshot webelement has 7 pixels on the left before bars starts
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

print(f"[*] {datetime.datetime.now(eastern)} :: Reading config")
current_directory = os.path.dirname(os.path.realpath(__file__))
with open(f"{current_directory}/config.json") as json_file:
    config_data = json.load(json_file)
slack_webhook_url = config_data.get("webhook_url")
slack_requester = SlackRequester(slack_webhook_url)

slack_requester.send_message(
    f"<!channel> *{datetime.datetime.now(eastern)} Eastern* - initializing pf crowd bot"
)

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
        day = datetime.date.today().strftime("%A")
        print(f"[*] {datetime.datetime.now(eastern)} :: Visiting...")
        driver.get(url)
        time.sleep(1)
        print(
            f"[*] {datetime.datetime.now(eastern)} :: Finding current day ({day}), clicking and screenshot whole div..."
        )
        try:
            day_btn = driver.find_element_by_id(day)
            day_btn.click()
            complete_crowd_div = driver.find_element_by_id("CrowdMeter")
            complete_crowd_div.screenshot("complete_crowd.png")
        except Exception as exc:
            print(
                f"[!] {datetime.datetime.now(eastern)} :: Error in finding specific day element and clicking, screenshotting the crowd div: {exc}"
            )
        try:
            # lol no opencv needed just grab number of masked bars
            crowd_bar_mask = driver.find_element_by_id("mask")
            cap_bars = crowd_bar_mask.find_elements_by_tag_name("path")
            print(
                f"[!] {datetime.datetime.now(eastern)} :: Bars found by counting masked completed-item elements: {len(cap_bars)}/20"
            )

            crowd_meter = driver.find_element_by_xpath(
                '//*[@id="CrowdMeter"]/div[1]/div[2]'
            )
            crowd_meter.screenshot("screen_shot.png")

            # complete_capacity_div = driver.find_element_by_class_name("club-capacity")
            # complete_capacity_div.screenshot('screen_shot.png')

            # Website redesign ~7PM EST December 16th, 2020
            # capacity_meter_div = driver.find_element_by_class_name(
            #     "club-capacity-meter"
            # )
            # capacity_meter_div.screenshot("screen_shot.png")
            x_pixels_until_gray_bar, total_x_pixels = get_crowd_percentage(image_path)
            crowd_percentage = x_pixels_until_gray_bar / total_x_pixels
            print(
                f"[!] {datetime.datetime.now(eastern)} :: Current Crowd Percentage: ~{round(crowd_percentage*100,2)}% - Filled Bar to Total Pixels: {x_pixels_until_gray_bar}/{total_x_pixels} - Bars: [{int(round(crowd_percentage,2)*total_bars)}] out of {total_bars}"
            )
            slack_requester.send_message(
                f"<!channel> *{datetime.datetime.now(eastern)} Eastern* - Current Crowd Percentage: ~{round(crowd_percentage*100,2)}% - Filled Bar to Total Pixels: {x_pixels_until_gray_bar}/{total_x_pixels} - Bars: [{int(round(crowd_percentage,2)*total_bars)}] out of {total_bars}"
            )
        except Exception as exc:
            print(
                f"[!] {datetime.datetime.now(eastern)} :: Error in finding element, screenshotting, or getting percentage: {exc}"
            )
            slack_requester.send_message(
                f"<!channel> *{datetime.datetime.now(eastern)} Eastern* - Exception was raised during runtime - pf crowd bot exiting"
            )
        time.sleep(poll)
    except (Exception, KeyboardInterrupt) as exc:
        print(
            f"[*] {datetime.datetime.now(eastern)} :: SIGINT caught - closing browser"
        )
        slack_requester.send_message(
            f"<!channel> *{datetime.datetime.now(eastern)} Eastern* - Exception was raised during runtime - pf crowd bot exiting"
        )
        running = False
        continue
# driver.close() #raises an exception for some reason? (Failed to establish a new connection)
