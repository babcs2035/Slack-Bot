import os
from time import sleep
import chromedriver_binary
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler(
    executors={
        "threadpool": ThreadPoolExecutor(max_workers=1),
        "processpool": ProcessPoolExecutor(max_workers=1),
    }
)


print("MF: Bot started")


def init():
    print("MF: init() started")

    chromedriver_autoinstaller.install()

    userdata_dir = "selenium/mf"
    os.makedirs(userdata_dir, exist_ok=True)

    options = Options()
    if os.environ["DEBUG"] != "1":
        options.add_argument("--user-data-dir=" + userdata_dir)
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=640,480")
        options.add_argument("--no-sandbox")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36"
        )
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-desktop-notifications")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    wait = WebDriverWait(driver, 30)
    driver.implicitly_wait(30)

    try:
        driver.get("https://moneyforward.com/")
        wait.until(
            EC.visibility_of_element_located(
                (By.ID, "js-cf-manual-payment-entry-submit-button")
            )
        )
        if driver.title == "マネーフォワード ME":
            print("MF: init() already logged in")
            return driver

        driver.get("https://moneyforward.com/sign_in")

        input_id = wait.until(
            EC.visibility_of_element_located((By.NAME, "mfid_user[email]"))
        )
        print("MF: init() url: " + driver.current_url)
        input_id.send_keys(os.environ["MF_EMAIL"])
        print("MF: init() input MF_EMAIL")
        button_next = wait.until(EC.visibility_of_element_located((By.ID, "submitto")))
        button_next.click()
        print("MF: init() click submit button")
        wait.until(EC.visibility_of_element_located((By.ID, "submitto")))
        if str(driver.current_url).find("password") == -1:
            print("MF: init() failed to find password page")
            return None

        print("MF: init() url: " + driver.current_url)
        input_id = wait.until(
            EC.visibility_of_element_located((By.NAME, "mfid_user[password]"))
        )
        input_id.send_keys(os.environ["MF_PASSWORD"])
        print("MF: init() input MF_PASSWORD")
        button_next = wait.until(EC.visibility_of_element_located((By.ID, "submitto")))
        button_next.click()
        print("MF: init() click submit button")

        wait.until(
            EC.visibility_of_element_located(
                (By.ID, "js-cf-manual-payment-entry-submit-button")
            )
        )
        if driver.title != "マネーフォワード ME":
            input_id = wait.until(
                EC.visibility_of_element_located((By.NAME, "email_otp"))
            )
            otp = input("MF: init() input OTP here: ")
            input_id.send_keys(otp)
            print("MF: init() input OTP")
            button_next = wait.until(
                EC.visibility_of_element_located((By.ID, "submitto"))
            )
            button_next.click()
            print("MF: init() click submit button")

        wait.until(
            EC.visibility_of_element_located(
                (By.ID, "js-cf-manual-payment-entry-submit-button")
            )
        )
        if driver.title != "マネーフォワード ME":
            print("MF: init() failed to login")
            return None

        print("MF: init() logged in")
        return driver

    except Exception as e:
        print("MF: init() error: " + str(e))
        return None


def update_all(driver):
    print("MF: update_all() started")
    wait = WebDriverWait(driver, 30)

    driver.get("https://moneyforward.com/")
    wait.until(
        EC.visibility_of_element_located(
            (By.ID, "js-cf-manual-payment-entry-submit-button")
        )
    )
    a_elements = driver.find_elements(By.TAG_NAME, "a")
    for a_elem in a_elements:
        try:
            if a_elem.text == "更新":
                a_elem.click()
        except Exception as e:
            print("MF: update_all() error: " + str(e))

    print("MF: update_all() done")


if __name__ == "__main__":
    try:
        update_all(init())
    except Exception as e:
        print("MF: __main__ error: " + str(e))


@sched.scheduled_job(
    "cron", minute="20", hour="7", executor="threadpool", misfire_grace_time=60 * 60
)
def scheduled_job():
    print("MF: ----- update_all started -----")
    driver = init()
    if driver != None:
        update_all(driver)
        driver.quit()
    print("MF: ----- update_all done -----")


sched.start()
print("MF: Bot initialized")
