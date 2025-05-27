import os
import json
import pickle
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler(
    executors={
        "threadpool": ThreadPoolExecutor(max_workers=5),
        "processpool": ProcessPoolExecutor(max_workers=1),
    }
)

print("🟢 UTOL: started")


def init():
    print("🔵 UTOL: init() started")

    userdata_dir = "selenium/utol"
    os.makedirs(userdata_dir, exist_ok=True)
    print(f"🔧 UTOL: Created userdata directory at {userdata_dir}")

    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--user-data-dir=" + userdata_dir)
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=640,480")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-desktop-notifications")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36"
    )
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    wait = WebDriverWait(driver, 300)
    driver.implicitly_wait(300)

    try:
        driver.get("https://utol.ecc.u-tokyo.ac.jp/saml/login?disco=true")
        wait.until(EC.visibility_of_element_located((By.ID, "pageContents")))
        if driver.title != "時間割":

            input_id = wait.until(
                EC.visibility_of_element_located((By.NAME, "loginfmt"))
            )
            input_id.send_keys(os.environ["UTOKYO_ID"])
            print("🔑 UTOL: init() input UTOKYO_ID")
            button_next = wait.until(
                EC.visibility_of_element_located((By.ID, "idSIButton9"))
            )
            button_next.click()

            input_password = wait.until(
                EC.visibility_of_element_located((By.NAME, "Password"))
            )
            input_password.send_keys(os.environ["UTOKYO_PASSWORD"])
            print("🔒 UTOL: init() input PASSWORD")
            button_login = wait.until(
                EC.visibility_of_element_located((By.CLASS_NAME, "submit"))
            )
            button_login.click()
            sleep(15)

            # if driver.current_url == "https://login.microsoftonline.com/login.srf":
            #     print("UTOL: init() /login.srf")
            #     button_yes = driver.find_element(By.ID, "idSIButton9")
            #     action = webdriver.common.action_chains.ActionChains(driver)
            #     action.move_to_element_with_offset(button_yes, 5, 5)
            #     action.click()
            #     action.perform()
            #     # button_yes.click()
            #     sleep(5)

            while driver.current_url == "https://login.microsoftonline.com/login.srf":
                print("🔄 UTOL: init() /appverify")
                onetime_code = wait.until(
                    EC.visibility_of_element_located(
                        (By.ID, "idRichContext_DisplaySign")
                    )
                )
                print("🔑 UTOL: init() one-time code issued ", onetime_code.text)
                sleep(5)

            check_button = wait.until(
                EC.visibility_of_element_located((By.ID, "KmsiCheckboxField"))
            )
            check_button.click()
            button_yes = wait.until(
                EC.visibility_of_element_located((By.ID, "idSIButton9"))
            )
            button_yes.click()

        print("✅ UTOL: init() done")
        return driver

    except Exception as e:
        print("⚠️ UTOL: init() error... " + str(e))
        return None


def getTaskList(driver):
    print("🔵 UTOL: getTaskList() started")
    driver.get("https://utol.ecc.u-tokyo.ac.jp/lms/task")
    wait = WebDriverWait(driver, 30)

    check_button = wait.until(EC.visibility_of_element_located((By.ID, "status_2")))
    check_button.click()
    check_button = wait.until(EC.visibility_of_element_located((By.ID, "status_3")))
    check_button.click()
    check_button = wait.until(EC.visibility_of_element_located((By.ID, "status_4")))
    check_button.click()
    sleep(15)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    tasks = soup.find_all("div", class_="result_list_line")

    taskList = []
    for task in tasks:
        taskList.append(
            {
                "courseName": task.contents[1].text.replace("\n", ""),
                "contents": task.contents[3].contents[1].text,
                "title": task.contents[5].contents[1].text.replace("\n", ""),
                "deadline": task.contents[7].contents[5].text,
                "link": "https://utol.ecc.u-tokyo.ac.jp"
                + task.contents[5].contents[1].attrs["href"],
            }
        )
    print(f"✅ UTOL: getTaskList() found {len(taskList)} tasks")
    return taskList


def getSpecificList(tasks, kind):
    print(f"🔵 UTOL: getSpecificList() started with kind: {kind}")
    res = [task for task in tasks if task["contents"] == kind]
    print(f"✅ UTOL: getSpecificList() found {len(res)} tasks of kind: {kind}")
    return res


def sendMessageToSlack(channel, message, attachments=json.dumps([])):
    try:
        client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        client.chat_postMessage(channel=channel, text=message, attachments=attachments)
        print(f"✅ UTOL: sendMessageToSlack() successfully sent message to {channel}")
    except Exception as e:
        print("⚠️ UTOL: sendMessageToSlack() error... " + str(e))


def sendTasks(tasks):
    print("🔵 UTOL: sendTasks() started")
    message = "未提出の課題: " + str(len(tasks)) + " 件"
    data = [
        {
            "color": "good",
            "title": task["title"],
            "title_link": task["link"],
            "text": f"・コース名: {task['courseName']}\n・期限: {task['deadline']}",
        }
        for task in tasks
    ]
    sendMessageToSlack("#utol-tasks", message, json.dumps(data))
    print("✅ UTOL: sendTasks() done")


def getUpdates(driver):
    print("🔵 UTOL: getUpdates() started")
    driver.get(
        "https://utol.ecc.u-tokyo.ac.jp/updateinfo?openStatus=0&selectedUpdInfoButton=2"
    )
    sleep(15)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    updates = soup.find_all(
        "div",
        class_="update-info-student contents-display-flex-exchange-sp update-info-cell",
    )

    updateList = []
    for update in updates:
        data = update.contents
        updateList.append(
            {
                "date": data[3].text.replace("\n", ""),
                "course": data[5].text.replace("\n", ""),
                "content": data[7].text.replace("\n", ""),
                "info": data[9].text.replace("\n", "")[1:-18],
                "link": "https://utol.ecc.u-tokyo.ac.jp"
                + data[9].contents[1].attrs["value"],
            }
        )
    print(f"✅ UTOL: getUpdates() found {len(updateList)} updates")
    return updateList


def sendUpdates(updates):
    print("🔵 UTOL: sendUpdates() started")
    data = []
    try:
        with open("data/UTOL/updates.pkl", "rb") as f:
            data = pickle.load(f)
        print("✅ UTOL: sendUpdates() loaded previous updates")
    except:
        print("⚠️ UTOL: sendUpdates() updates.pkl open error")

    sendLists = []
    for update in updates:
        if update not in data:
            colorStr = "#f5f5f5"
            if update["content"] == "課題" or update["content"] == "テスト":
                colorStr = "danger"
            elif update["content"] in [
                "お知らせ",
                "担当教員へのメッセージ",
                "アンケート",
                "掲示板",
            ]:
                colorStr = "warning"
            elif update["content"] == "教材":
                colorStr = "good"
            sendLists.append(
                {
                    "color": colorStr,
                    "title": update["course"],
                    "title_link": update["link"],
                    "text": update["info"],
                }
            )

    if sendLists:
        sendMessageToSlack("#utol-updates", "", json.dumps(sendLists))
        print(f"✅ UTOL: sendUpdates() sent {len(sendLists)} updates to Slack")

    data = updates
    os.makedirs("data/UTOL", exist_ok=True)
    with open("data/UTOL/updates.pkl", "wb") as f:
        pickle.dump(data, f)
    print("✅ UTOL: sendUpdates() saved updates")


@sched.scheduled_job(
    "cron", minute="45", hour="18", executor="threadpool", misfire_grace_time=60 * 60
)
def scheduled_job_sendTasks():
    print("📅 UTOL: ----- sendTasks started -----")
    driver = init()
    if driver:
        sendTasks(getTaskList(driver))
        driver.quit()
    print("✅ UTOL: ----- sendTasks done -----")


@sched.scheduled_job(
    "cron", minute="0,10,20,30,40,50", executor="threadpool", misfire_grace_time=60 * 60
)
def scheduled_job_sendUpdates():
    print("📅 UTOL: ----- sendUpdates started -----")
    driver = init()
    if driver:
        sendUpdates(getUpdates(driver))
        driver.quit()
    print("✅ UTOL: ----- sendUpdates done -----")


if __name__ == "__main__":
    try:
        print("🚀 UTOL: Main execution started")
        sendTasks(getTaskList(init()))
    except Exception as e:
        print("⚠️ UTOL: __main__ error: " + str(e))


sched.start()
print("🟢 UTOL: Execution completed")
