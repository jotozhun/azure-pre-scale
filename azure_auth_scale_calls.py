import time

from azure_auth_scale import *
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service

from pynput.keyboard import Key, Controller

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


global driver


def portal_azure_login(email_credentials: str, smart_card_pin: str):
    global driver
    keyboard = Controller()
    chrome_options = Options()

    s = Service('../driver/chromedriver')
    capabilities = DesiredCapabilities.CHROME
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}
    driver = webdriver.Chrome(service=s, options=chrome_options, desired_capabilities=capabilities)#, seleniumwire_options=wire_options)
    driver.maximize_window()

    driver.get(PORTAL_AZURE_LINK)
    email_input = WebDriverWait(driver, WAIT_TIME) \
        .until(EC.element_to_be_clickable((By.XPATH,
                                           r'//*[@id="i0116"]')))

    email_input.send_keys(email_credentials)

    email_next_btn = WebDriverWait(driver, WAIT_TIME) \
        .until(EC.element_to_be_clickable((By.XPATH,
                                           r'//*[@id="idSIButton9"]')))

    email_next_btn.click()

    time.sleep(10)

    # Handle popup certificate

    keyboard.press(Key.enter)
    keyboard.release(Key.enter)
    time.sleep(7)

    # Smart card pin type and enter

    for char in smart_card_pin:
        keyboard.press(char)
        keyboard.release(char)

    keyboard.press(Key.enter)
    keyboard.release(Key.enter)

    no_stay_signed_btn = WebDriverWait(driver, WAIT_TIME) \
        .until(EC.element_to_be_clickable((By.XPATH,
                                           r'//*[@id="idBtn_Back"]')))

    no_stay_signed_btn.click()


microsoft_groups_token = ""
microsoft_create_apps_token = ""
windows_consent_app_token = ""
redirect_urls = ["https://yoda-cgqa.arubathena.com/oauth/reply",
                 "https://zodiac-dev.arubathena.com/oauth/reply",
                 "https://malshi-cgqa.arubathena.com/oauth/reply"]

azure_automation = AzureAuthScaleAutomation(microsoft_groups_token, microsoft_create_apps_token, windows_consent_app_token, redirect_urls)


# In this example it creates 5 groups that are called from 26500 to 26504 group
# Make sure to read the documentation of the method.

# To use this you only need the **microsoft_groups_token**
azure_automation.create_group_scale_threading(26500, 5)


# Creates and configures an application in azure, so make sure to read the documentation of the function.
# In this example, the first parameters stands for the active directory id,
# the second is the index of the app that will start creating: 300
# and the last parameter is the number of apps to be created: scale_app_300, scale_app_301

# To use this you need both tokens **microsoft_create_apps_token** and **windows_consent_app_token**
azure_automation.create_azure_app_registrations_apis("89f8652e-c99e-43a0-ab1f-9273081e5aaa", 300, 2)


# Assigns random groups to the users list, please read the function documentation before proceeding
# user_sample.csv and all_data_groups.csv has to have a format like:
#   <headers>
#   <data>
#   <one-empty-row>

#   If you have more than 5k of users, then please run this with a csv of 5k users, then wait at least 5 minutes, update the csv with other 6k users
#   and run it again and so on. If you have more than 10k users, then try to update the microsoft_groups_token after those 10k users run.

# To use this you only need the **microsoft_groups_token**
azure_automation.assign_groups_to_members_threading("user_sample.csv", "all_data_groups.csv")


# Modify the redirect urls of the apps
# In this case, will replace the redirect urls of the apps from the csv called object_id_test.csv
# Example:
#   You set the redirect_urls list with:                                               ["link_1", "link_2", "link_3"]
#   You have applications with redirect_urls like:                                     ["link_2", "link_3"]
#   When you execute the script the applications you selected will have the following: ["link_1", "link_2", "link_3"]

# To use this you only need the **microsoft_create_apps_token**
azure_automation.modify_redirect_urls_of_app_threading("azure_app_object_id.csv")


# Deletes the apps from the azure portal
# In this case, will delete all the apps from the csv called object_id_test.csv

# To use this you only need the **microsoft_create_apps_token**
azure_automation.delete_active_application_threading("objects_id_test.csv")