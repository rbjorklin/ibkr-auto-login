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

def retry_connection(url, component, timeout):
    logger.info("Waiting for {} container to start".format(component))
    while True:
        try:
            rsp = requests.get(url, verify=False, timeout=timeout)
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"ConnectionError {e}")
            pass
        except requests.exceptions.ReadTimeout as e:
            logger.debug(f"ReadTimeout {e}")
            pass
        except urllib3.exceptions.MaxRetryError as e:
            logger.debug(f"MaxRetryError {e}")
            pass
        except urllib3.exceptions.NewConnectionError as e:
            logger.debug(f"NewConnectionError {e}")
            pass
        except urllib3.exceptions.ReadTimeoutError as e:
            logger.debug(f"ReadTimeoutError {e}")
            pass
        else:
            if rsp.status_code == 200:
                break
        logger.info("container not up, sleeping 1s and trying again")
        sys.stdout.flush()
        sys.stderr.flush()
        time.sleep(1)


def screenshot(driver, fname):
    if os.path.exists(fname):
        os.remove(fname)
    driver.save_screenshot(fname)
    logger.debug(f"Saved screenshot {fname}")


def ensure_logged_out(client_portal_endpoint, timeout):
    url = f"{client_portal_endpoint}/v1/api/logout"
    headers = { "Content-Length": "0" }
    try:
        rsp = requests.post(url, headers=headers, verify=False, timeout=timeout)
    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {e}")
        return 1
    except requests.exceptions.ReadTimeout as e:
        logger.error(f"ReadTimeout {e}")
        return 1
    except urllib3.exceptions.MaxRetryError as e:
        logger.error("MaxRetryError: {}".format(e))
        return 1
    except urllib3.exceptions.NewConnectionError as e:
        logger.error("NewConnectionError: {}".format(e))
        return 1
    except urllib3.exceptions.ReadTimeoutError as e:
        logger.error(f"ReadTimeoutError {e}")
        return 1
    if rsp.status_code != 200:
        logger.warning("Logout failed with status code: {}".format(rsp.status_code))
    if rsp.status_code == 200:
        logger.info("Logged out successfully")
    return 0


def do_login(selenium_endpoint, client_portal_endpoint, username, password, timeout, selenium_timeout):
    firefox_options = webdriver.FirefoxOptions()
    firefox_options.set_capability("timeouts", {"implicit":selenium_timeout, "pageLoad":selenium_timeout, "script":selenium_timeout})
    if not logger.isEnabledFor(logging.DEBUG):
        firefox_options.add_argument("--headless")
    # https://developer.mozilla.org/en-US/docs/Web/WebDriver/Capabilities/acceptInsecureCerts
    firefox_options.set_capability("acceptInsecureCerts", True)
    try:
        driver = webdriver.Remote(
            command_executor=selenium_endpoint,
            options=firefox_options
        )
        logger.debug("Selenium driver initialized")
    except exceptions.SessionNotCreatedException as e:
        logger.error("Failed to create Selenium session, starting over. {}".format(e))
        return 1

    try:
        driver.get(client_portal_endpoint)
        if logger.isEnabledFor(logging.DEBUG):
            screenshot(driver, "01-initial-page-load.png")
        driver.find_element(By.NAME, "user_name").send_keys(username)
        if logger.isEnabledFor(logging.DEBUG):
            screenshot(driver, "02-username-input.png")
        driver.find_element(By.NAME, "password").send_keys(password)
        if logger.isEnabledFor(logging.DEBUG):
            screenshot(driver, "03-password-input.png")
        driver.find_element(By.ID, "submitForm").click()
        if logger.isEnabledFor(logging.DEBUG):
            screenshot(driver, "04-submitted-form.png")
        # https://www.selenium.dev/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.webdriver.html#module-selenium.webdriver.remote.webdriver
        element = WebDriverWait(driver, timeout=20).until(lambda d: d.find_element(By.XPATH, "//*[text()='Client login succeeds']"))
        logger.info(element.text)
        if logger.isEnabledFor(logging.DEBUG):
            screenshot(driver, "05-login-completed.png")
    except exceptions.InsecureCertificateException as e:
        logger.error("InsecureCertificateException {}".format(e))
    except exceptions.NoSuchElementException as e:
        logger.error("NoSuchElementException: {}".format(e.msg))
    except exceptions.TimeoutException as e:
        #err_element = driver.find_element(By.ID, "ERRORMSG")
        logger.error(f"TimeoutException {e}")
        return 1
    finally:
        for img in [f for f in os.listdir() if f.endswith("png")]:
            with open(img, "rb") as input_file:
                with open(f"img/{img}", "wb") as output_file:
                  data = input_file.read()
                  output_file.write(data)

        driver.quit()
        logger.info("End of login procedure, current selenium session ended")
    return 0

def validate_authenticated(client_portal_endpoint, timeout):
    # IBKR api is incredibly slow at acknowledging logged in sessions
    # so wait a bit before starting the validation loop
    already_connected = False
    ret = 1 # assume failure if we wait 20s to successfully validate
    for _ in range(0, 20):
        try:
            url = f"{client_portal_endpoint}/v1/api/iserver/auth/status"
            headers = { "Content-Length": "0" }
            rsp = requests.post(url, headers=headers, verify=False, timeout=timeout)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"ConnectionError {e}")
            pass
        except requests.exceptions.ReadTimeout as e:
            logger.error(f"ReadTimeout {e}")
            pass
        except urllib3.exceptions.MaxRetryError as e:
            logger.error(f"MaxRetryError {e}")
            pass
        except urllib3.exceptions.NewConnectionError as e:
            logger.error(f"NewConnectionError {e}")
            pass
        except urllib3.exceptions.ReadTimeoutError as e:
            logger.error(f"ReadTimeoutError {e}")
            pass
        else:
            if rsp.status_code == 200 and rsp.json().get('connected', False) and not already_connected:
                logger.info("Connected, waiting for authenticated status")
                already_connected = True
            if rsp.status_code == 200 and rsp.json().get('authenticated', False):
                logger.info("Authenticated, moving on")
                ret = 0
                break
            if not already_connected:
                logger.info("Attempting to validate client-portal 'connected' status")
            time.sleep(1)
    return ret

def tickle(client_portal_endpoint, timeout):
    retry_count = 0
    while True:
        if retry_count >= 5:
            logger.error("Retry failed 5 times in a row, starting over")
            return 1
        try:
            url = f"{client_portal_endpoint}/v1/api/iserver/auth/status"
            headers = { "Content-Length": "0" }
            rsp = requests.post(url, headers=headers, verify=False, timeout=timeout)
        except requests.exceptions.ConnectionError as e:
            logger.error("Status check ConnectionError: {}".format(e))
            return 1
        except requests.exceptions.ReadTimeout as e:
            logger.error(f"ReadTimeout {e}")
            return 1
        except urllib3.exceptions.MaxRetryError as e:
            logger.error("Status check MaxRetryError: {}".format(e))
            return 1
        except urllib3.exceptions.NewConnectionError as e:
            logger.error("Status check NewConnectionError: {}".format(e))
            return 1
        except urllib3.exceptions.ReadTimeoutError as e:
            logger.error(f"ReadTimeoutError {e}")
            return 1
        else:
            if rsp.status_code != 200:
                logger.warning("Status request failed with status code: {}, retrying".format(rsp.status_code))
                time.sleep(1)
                retry_count += 1
                continue
            if not rsp.json().get('connected', False):
                logger.error("Not connected, starting over")
                return 1
            if not rsp.json().get('authenticated', False):
                logger.warning("Client-portal reports not being authenticated")
                time.sleep(1)
                retry_count += 1
                continue
            if rsp.json().get('message', ""):
                logger.warning("Status message is non-empty: '{}'".format(rsp.json().get('message')))
            if rsp.json().get('competing', False):
                # https://github.com/Voyz/ibeam/issues/19#issuecomment-840917681
                logger.error("Client-portal is competing. Logout all other sessions, live and paper. If the problem persists try changing the Gateway 'proxyRemoteHost' then restart")
                return 1

        try:
            url = f"{client_portal_endpoint}/v1/api/tickle"
            rsp = requests.get(url, verify=False, timeout=timeout)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"ConnectionError: {e}")
            time.sleep(1)
            retry_count += 1
            continue
        except urllib3.exceptions.ReadTimeoutError as e:
            logger.error(f"ReadTimeoutError: {e}")
            time.sleep(1)
            retry_count += 1
            continue
        except requests.exceptions.ReadTimeout as e:
            logger.error(f"ReadTimeout {e}")
            time.sleep(1)
            retry_count += 1
            continue
        except urllib3.exceptions.MaxRetryError as e:
            logger.error(f"MaxRetryError: {e}")
            time.sleep(1)
            retry_count += 1
            continue
        except urllib3.exceptions.NewConnectionError as e:
            logger.error(f"NewConnectionError: {e}")
            time.sleep(1)
            retry_count += 1
            continue
        except urllib3.exceptions.ReadTimeoutError as e:
            logger.error(f"ReadTimeoutError {e}")
            time.sleep(1)
            retry_count += 1
            continue
        except:
            logger.warn("Session tickle failed, retrying next cycle")
        else:
            logger.info("Session successfully tickled")
        sys.stdout.flush()
        sys.stderr.flush()
        retry_count = 0
        time.sleep(30) # Keep-alive once a minute should be sufficient
    return 0


def main():
    parser = argparse.ArgumentParser(description='Interactive Brokers auto-login.')
    parser.add_argument('--selenium-endpoint', action='store',
            default='http://firefox-standalone:4444', help='Address for selenium standalone node')
    parser.add_argument('--client-portal-endpoint', action='store',
            default='https://client-portal:5000', help='Address for IBKR client portal')
    parser.add_argument('--username', action='store',
            default=os.environ.get("IBKR_USER", "NO_USERNAME_PROVIDED"), help='IBKR username')
    parser.add_argument('--password', action='store',
            default=os.environ.get("IBKR_PASSWORD", "NO_PASSWORD_PROVIDED"), help='IBKR password')
    parser.add_argument('--debug', action='store_const', const=logging.DEBUG, default=logging.INFO)
    parser.add_argument('--timeout', action='store', type=int,
            default=3, help='Default request timeout')
    parser.add_argument('--selenium-timeout', action='store', type=int,
            default=30000, help='Default selenium timeout in ms')

    args = parser.parse_args()

    logger.setLevel(args.debug)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    selenium_healthcheck = args.selenium_endpoint + "/readyz"
    client_portal_healthcheck = args.client_portal_endpoint + "/demo#/"
    retry_connection(selenium_healthcheck, "selenium", args.timeout)
    retry_connection(client_portal_healthcheck, "client-portal", args.timeout)

    # https://urllib3.readthedocs.io/en/1.26.x/advanced-usage.html#ssl-warnings
    urllib3.disable_warnings()
    logger.warning("Disabling TLS warnings from here on out to reduce log spam")

    ret = 0
    while True:
        ret = ensure_logged_out(args.client_portal_endpoint, args.timeout)
        if ret != 0:
            time.sleep(1)
            continue
        logger.info("Starting login procedure")
        ret = do_login(args.selenium_endpoint, args.client_portal_endpoint, args.username, args.password, args.timeout, args.selenium_timeout)
        if ret != 0:
            continue
        ret = validate_authenticated(args.client_portal_endpoint, args.timeout)
        if ret != 0:
            continue
        tickle(args.client_portal_endpoint, args.timeout)


if __name__ == "__main__":
    main()
