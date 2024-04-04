import os
import json
import pickle
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler(
    executors={
        "threadpool": ThreadPoolExecutor(max_workers=5),
        "processpool": ProcessPoolExecutor(max_workers=1),
    }
)

print("UTOL: Bot started")


def init():
    print("UTOL: init() started")

    userdata_dir = "selenium"
    os.makedirs(userdata_dir, exist_ok=True)

    options = Options()
    options.add_argument("--user-data-dir=" + userdata_dir)
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1280")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://utol.ecc.u-tokyo.ac.jp/saml/login?disco=true")
        if driver.title != "時間割":
            sleep(5)

            print("UTOL: init() input UTOKYO_ID")
            input_id = driver.find_element(By.NAME, "loginfmt")
            input_id.send_keys(os.environ["UTOKYO_ID"])
            button_next = driver.find_element(By.ID, "idSIButton9")
            button_next.click()
            sleep(5)

            print("UTOL: init() input UTOKYO_ID & PASSWORD")
            input_password = driver.find_element(By.NAME, "Password")
            input_password.send_keys(os.environ["UTOKYO_PASSWORD"])
            button_login = driver.find_element(By.CLASS_NAME, "submit")
            button_login.click()
            sleep(5)

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
                print("UTOL: init() /appverify")
                onetime_code = driver.find_element(By.ID, "idRichContext_DisplaySign")
                print("UTOL: init() one-time code issued ", onetime_code.text)
                sleep(5)

            sleep(5)
            check_button = driver.find_element(By.ID, "KmsiCheckboxField")
            check_button.click()
            button_yes = driver.find_element(By.ID, "idSIButton9")
            button_yes.click()

        print("UTOL: init() done")
        return driver

    except Exception as e:
        print("UTOL: init() error... " + str(e))
        return None


def getTaskList(driver):
    driver.get("https://utol.ecc.u-tokyo.ac.jp/lms/task")
    sleep(5)
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
    return taskList


def getSpecificList(tasks, kind):
    res = []
    for task in tasks:
        if task["contents"] == kind:
            res.append(task)
    return res


def sendMessageToSlack(channel, message, attachments=json.dumps([])):
    try:
        client = WebClient(token=os.environ["SLACK_TOKEN"])
        client.chat_postMessage(channel=channel, text=message, attachments=attachments)
    except Exception as e:
        print("UTOL: sendMessageToSlack() error... " + str(e))
    else:
        print("UTOL: sendMessageToSlack() successfully sent message to " + channel)


def sendTasks(tasks):
    message = "未提出の課題: " + str(len(tasks)) + " 件"
    data = []
    for task in tasks:
        data.append(
            {
                "color": "good",
                "title": task["title"],
                "title_link": task["link"],
                "text": "・コース名: "
                + task["courseName"]
                + "\n・期限: "
                + task["deadline"],
            }
        )
    sendMessageToSlack("#utol-tasks", message, json.dumps(data))


def getUpdates(driver):
    driver.get(
        "https://utol.ecc.u-tokyo.ac.jp/updateinfo?openStatus=0&selectedUpdInfoButton=2"
    )
    sleep(5)
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
    return updateList


def sendUpdates(updates):
    data = []
    try:
        with open("data/UTOL/updates.pkl", "rb") as f:
            data = pickle.load(f)
    except:
        print("UTOL: sendUpdates() updates.pkl open error")

    sendLists = []
    for update in updates:
        if not (update in data):
            colorStr = "#f5f5f5"
            if update["content"] == "課題" or update["content"] == "テスト":
                colorStr = "danger"
            if (
                update["content"] == "お知らせ"
                or update["content"] == "担当教員へのメッセージ"
                or update["content"] == "アンケート"
                or update["content"] == "掲示板"
            ):
                colorStr = "warning"
            if update["content"] == "教材":
                colorStr = "good"
            sendLists.append(
                {
                    "color": colorStr,
                    "title": update["course"],
                    "title_link": update["link"],
                    "text": update["info"],
                }
            )
    if len(sendLists) > 0:
        sendMessageToSlack("#utol-updates", "", json.dumps(sendLists))

    data = updates
    os.makedirs("data/UTOL", exist_ok=True)
    with open("data/UTOL/updates.pkl", "wb") as f:
        pickle.dump(data, f)


@sched.scheduled_job("cron", minute="15", hour="8, 19", executor="threadpool")
def scheduled_job():
    print("UTOL: ----- sendTasks started -----")
    driver = init()
    if driver != None:
        sendTasks(getTaskList(driver))
        driver.quit()
    print("UTOL: ----- sendTasks done -----")


@sched.scheduled_job("cron", minute="0,10,20,30,40,50", executor="threadpool")
def scheduled_job():
    print("UTOL: ----- sendUpdates started -----")
    driver = init()
    if driver != None:
        sendUpdates(getUpdates(driver))
        driver.quit()
    print("UTOL: ----- sendUpdates done -----")


sched.start()
print("UTOL: Bot initialized")

init()
