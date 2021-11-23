#!/usr/bin/env python3

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
import time
import sys
import os
import requests
import urllib3
import logging
import argparse

logger = logging.getLogger(__name__)

def retry_connection(url, component):
    logger.info("Waiting for {} container to start.".format(component))
    while True:
        try:
            rsp = requests.get(url, verify=False)
        except requests.exceptions.ConnectionError:
            pass
        except urllib3.exceptions.MaxRetryError:
            pass
        except urllib3.exceptions.NewConnectionError:
            pass
        else:
            if rsp.status_code == 200:
                break
        logger.info("container not up, sleeping 1s and trying again.")
        sys.stdout.flush()
        sys.stderr.flush()
        time.sleep(1)

def main():

    parser = argparse.ArgumentParser(description='Interactive Brokers auto-login.')
    parser.add_argument('--selenium-endpoint', action='store',
            default='http://firefox-standalone:4444', help='Address for selenium standalone node')
    parser.add_argument('--client-portal-endpoint', action='store',
            default='https://client-portal:5000/',
            help='Address for IBKR client portal')
    parser.add_argument('--username', action='store',
            default=os.environ.get("IBKR_USER", "NO_USERNAME_PROVIDED"), help='IBKR username')
    parser.add_argument('--password', action='store',
            default=os.environ.get("IBKR_PASSWORD", "NO_PASSWORD_PROVIDED"), help='IBKR password')
    parser.add_argument('--debug', action='store_const', const=logging.DEBUG, default=logging.INFO)
    
    args = parser.parse_args()

    logger.setLevel(args.debug)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    retry_connection(args.selenium_endpoint, "selenium")
    retry_connection(args.client_portal_endpoint, "client-portal")
    
    logger.info("Starting login procedure.")
    firefox_options = webdriver.FirefoxOptions()
    # https://developer.mozilla.org/en-US/docs/Web/WebDriver/Capabilities/acceptInsecureCerts
    firefox_options.set_capability("acceptInsecureCerts", True)
    driver = webdriver.Remote(
        command_executor=args.selenium_endpoint,
        options=firefox_options
    )
    
    try:
        driver.get(args.client_portal_endpoint)
        if args.debug == logging.DEBUG:
            driver.save_screenshot("01-initial-page-load.png")
        driver.find_element(By.NAME, "user_name").send_keys(args.username)
        if args.debug == logging.DEBUG:
            driver.save_screenshot("02-username-input.png")
        driver.find_element(By.NAME, "password").send_keys(args.password)
        if args.debug == logging.DEBUG:
            driver.save_screenshot("03-password-input.png")
        driver.find_element(By.ID, "submitForm").click()
        if args.debug == logging.DEBUG:
            driver.save_screenshot("04-submitted-form.png")
        # https://www.selenium.dev/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.webdriver.html#module-selenium.webdriver.remote.webdriver
        element = WebDriverWait(driver, timeout=20).until(lambda d: d.find_element(By.XPATH, "//*[text()='Client login succeeds']"))
        logger.info(element.text)
        if args.debug == logging.DEBUG:
            driver.save_screenshot("05-login-completed.png")
    except exceptions.InsecureCertificateException as e:
        logger.error("InsecureCertificateException {}".format(e))
    except exceptions.NoSuchElementException as e:
        logger.error("NoSuchElementException {}".format(e))
    except exceptions.TimeoutException as e:
        err_element = driver.find_element(By.ID, "ERRORMSG")
        logger.error("TimeoutException {}".format(err_element.text))
    finally:
        for img in [f for f in os.listdir() if f.endswith("png")]:
            with open(img, "rb") as input_file:
                with open(f"img/{img}", "xb") as output_file:
                  data = input_file.read()
                  output_file.write(data)

        driver.quit()
        logger.info("End of script, selenium driver stopped.")
    
    sys.stdout.flush()
    time.sleep(57600) # 16h, to not kill the container.
    # Above should maybe be 24h to automatically trigger a new login
    # in combination with docker-compose up --abort-on-container-exit
    # and a systemd unit file with restart-on-failure


if __name__ == "__main__":
    main()
