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
        x_pixels_until_gray_bar = progress - bar_offset
        print(
            f"[!] {datetime.datetime.now()} :: Crowd meter percentage: {x_pixels_until_gray_bar}/{total_x_pixels} ({100*x_pixels_until_gray_bar / total_x_pixels}%)"
        )
        return x_pixels_until_gray_bar / total_x_pixels


print(f"[*] {datetime.datetime.now()} :: Parsing cli options")
parser = argparse.ArgumentParser()
parser.add_argument("--poll", type=int, default=3600)
parser.add_argument(
    "--image", help="path to the image", type=str, default="screen_shot.png"
)

args = parser.parse_args()
poll = args.poll
image_path = args.image

print(f"[*] {datetime.datetime.now()} :: Reading config")
current_directory = os.path.dirname(os.path.realpath(__file__))
with open(f"{current_directory}/config.json") as json_file:
    config_data = json.load(json_file)
slack_webhook_url = config_data.get("webhook_url")
slack_requester = SlackRequester(slack_webhook_url)

slack_requester.send_message(
    f"<!channel> *{datetime.datetime.now()} UTC* - initializing pf crowd bot"
)

print(f"[*] {datetime.datetime.now()} :: Setting up webdriver options")
options = Options()
options.headless = True
# start-maximized flag doesnt work in headless - makes sense; instead explicitly set
# options.add_argument("--start-maximized")
options.add_argument("--window-size=1440x900")

print(f"[*] {datetime.datetime.now()} :: Initializing webdriver")
driver = webdriver.Chrome(options=options)
# driver.delete_all_cookies()
url = "https://www.planetfitness.com/gyms/danvers-ma"
running = True
while running:
    try:
        print(f"[*] {datetime.datetime.now()} :: Visiting...")
        driver.get(url)
        try:
            # complete_capacity_div = driver.find_element_by_class_name("club-capacity")
            # complete_capacity_div.screenshot('screen_shot.png')
            capacity_meter_div = driver.find_element_by_class_name(
                "club-capacity-meter"
            )
            capacity_meter_div.screenshot("screen_shot.png")
            crowd_percentage = get_crowd_percentage(image_path)
            slack_requester.send_message(
                f"<!channel> *{datetime.datetime.now()} UTC* - Current Crowd Percentage: {round(crowd_percentage*100,2)}%"
            )
        except Exception as exc:
            print(
                f"[!] {datetime.datetime.now()} :: Error in finding element, screenshotting, or getting percentage: {exc}"
            )
            slack_requester.send_message(
                f"<!channel> *{datetime.datetime.now()} UTC* - Exception was raised during runtime - pf crowd bot exiting"
            )
        time.sleep(poll)
    except (Exception, KeyboardInterrupt) as exc:
        print(f"[*] {datetime.datetime.now()} :: SIGINT caught - closing browser")
        slack_requester.send_message(
            f"<!channel> *{datetime.datetime.now()} UTC* - Exception was raised during runtime - pf crowd bot exiting"
        )
        running = False
        continue
# driver.close() #raises an exception for some reason? (Failed to establish a new connection)
