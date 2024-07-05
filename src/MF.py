import os
from time import sleep
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

if os.environ["DEBUG"] == "1":
    import chromedriver_binary

print("MF: Bot started")


def init():
    print("MF: init() started")

    userdata_dir = "selenium"
    os.makedirs(userdata_dir, exist_ok=True)

    options = Options()
    if os.environ["DEBUG"] != "1":
        options.add_argument("--user-data-dir=" + userdata_dir)
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1280")
        options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://moneyforward.com/")
        print(f"MF: driver.title: {driver.title}")
        sleep(5)
        if driver.title == "マネーフォワード ME":
            print("MF: init() already logged in")
            return driver

        driver.get(
            "https://id.moneyforward.com/sign_in?client_id=2WND7CAYV1NsJDBzk13JRtjuk5g9Jtz-4gkAoVzuS_k&nonce=b15bb2e54f3a7ecac84810e4b0de5d65&redirect_uri=https%3A%2F%2Fmoneyforward.com%3A443%2Fauth%2Fmfid%2Fcallback&response_type=code&scope=openid+email+profile+address&select_account=true&state=c143c1eea1734298f11c48387ec2405a"
        )
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
    sleep(5)
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
