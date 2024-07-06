import os
from time import sleep
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
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

    userdata_dir = "selenium/mf"
    os.makedirs(userdata_dir, exist_ok=True)

    options = Options()
    if os.environ["DEBUG"] != "1":
        options.add_argument("--user-data-dir=" + userdata_dir)
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1280")
        options.add_argument("--no-sandbox")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36"
        )
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    try:
        driver.get("https://moneyforward.com/")
        sleep(10)
        # print(f"MF: driver.title: {driver.title}")
        if driver.title == "マネーフォワード ME":
            print("MF: init() already logged in")
            return driver

        driver.get("https://moneyforward.com/sign_in")
        sleep(5)

        print("MF: init() input MF_EMAIL")
        print("MF: init() url: " + driver.current_url)
        input_id = driver.find_element(By.NAME, "mfid_user[email]")
        input_id.send_keys(os.environ["MF_EMAIL"])
        button_next = driver.find_element(By.ID, "submitto")
        button_next.click()
        sleep(5)

        print("MF: init() input MF_PASSWORD")
        input_id = driver.find_element(By.NAME, "mfid_user[password]")
        input_id.send_keys(os.environ["MF_PASSWORD"])
        button_next = driver.find_element(By.ID, "submitto")
        button_next.click()
        sleep(5)

        print("MF: init() logged in")
        return driver

    except Exception as e:
        print("MF: init() error: " + str(e))
        return None


def update_all(driver):
    print("MF: update_all() started")

    driver.get("https://moneyforward.com/")
    sleep(10)
    a_elements = driver.find_elements(By.TAG_NAME, "a")
    for a_elem in a_elements:
        try:
            if a_elem.text == "更新":
                a_elem.click()
        except Exception as e:
            print("MF: update_all() error: " + str(e))

    print("MF: update_all() done")


if __name__ == "__main__":
    update_all(init())


@sched.scheduled_job("cron", minute="0", hour="7", executor="threadpool")
def scheduled_job():
    print("MF: ----- update_all started -----")
    driver = init()
    if driver != None:
        update_all(driver)
        driver.quit()
    print("MF: ----- update_all done -----")


sched.start()
print("MF: Bot initialized")
