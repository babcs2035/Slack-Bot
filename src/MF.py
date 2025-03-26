import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler(
    executors={
        "threadpool": ThreadPoolExecutor(max_workers=1),
        "processpool": ProcessPoolExecutor(max_workers=1),
    }
)
print("🟢 MF: started")


def setup_chrome_driver():
    """Set up and return the Chrome WebDriver."""
    userdata_dir = "selenium/mf"
    os.makedirs(userdata_dir, exist_ok=True)
    print(f"🔧 MF: Created userdata directory at {userdata_dir}")

    service = Service("/usr/bin/chromedriver")
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

    print("⚙️ MF: WebDriver options set")
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    driver.implicitly_wait(300)
    return driver


def login_to_moneyforward(driver):
    """Handles logging into the MoneyForward website."""
    wait = WebDriverWait(driver, 300)

    print("🌐 MF: Navigating to https://moneyforward.com/")
    driver.get("https://moneyforward.com/")

    if driver.title == "マネーフォワード ME":
        print("✅ MF: init() already logged in")
        return True

    print("🚪 MF: Not logged in, navigating to sign in page")
    driver.get("https://moneyforward.com/sign_in")

    input_id = wait.until(
        EC.visibility_of_element_located((By.NAME, "mfid_user[email]"))
    )
    print("🔑 MF: init() url: " + driver.current_url)
    input_id.send_keys(os.environ["MF_EMAIL"])
    print("💌 MF: init() input MF_EMAIL")

    input_id = wait.until(
        EC.visibility_of_element_located((By.NAME, "mfid_user[password]"))
    )
    input_id.send_keys(os.environ["MF_PASSWORD"])
    print("🔒 MF: init() input MF_PASSWORD")

    button_next = wait.until(EC.visibility_of_element_located((By.ID, "submitto")))
    button_next.click()
    print("📤 MF: init() click submit button")

    wait.until(
        EC.visibility_of_element_located(
            (By.ID, "js-cf-manual-payment-entry-submit-button")
        )
    )
    if driver.title != "マネーフォワード ME":
        input_id = wait.until(EC.visibility_of_element_located((By.NAME, "email_otp")))
        otp = input("💬 MF: init() input OTP here: ")
        input_id.send_keys(otp)
        print("🔑 MF: init() input OTP")
        button_next = wait.until(EC.visibility_of_element_located((By.ID, "submitto")))
        button_next.click()
        print("📤 MF: init() click submit button")

    wait.until(
        EC.visibility_of_element_located(
            (By.ID, "js-cf-manual-payment-entry-submit-button")
        )
    )
    if driver.title != "マネーフォワード ME":
        print("❌ MF: init() failed to login")
        return False

    print("✅ MF: init() logged in")
    return True


def init():
    print("🔵 MF: init() started")
    driver = setup_chrome_driver()

    if not login_to_moneyforward(driver):
        return None

    print("🟢 MF: WebDriver initialized")
    return driver


def update_all(driver):
    print("🔵 MF: update_all() started")
    wait = WebDriverWait(driver, 30)

    driver.get("https://moneyforward.com/")
    wait.until(
        EC.visibility_of_element_located(
            (By.ID, "js-cf-manual-payment-entry-submit-button")
        )
    )
    a_elements = driver.find_elements(By.TAG_NAME, "a")
    refreshed_cnt = 0
    for a_elem in a_elements:
        try:
            if a_elem.text == "更新":
                a_elem.click()
                refreshed_cnt += 1
        except Exception as e:
            print("⚠️ MF: update_all() error: " + str(e))
    print(f"🔄 MF: Refreshed {refreshed_cnt} elements")
    print("✅ MF: update_all() done")


if __name__ == "__main__":
    try:
        print("🚀 MF: Main execution started")
        update_all(init())
    except Exception as e:
        print("⚠️ MF: __main__ error: " + str(e))


@sched.scheduled_job(
    "cron", minute="15", hour="7", executor="threadpool", misfire_grace_time=60 * 60
)
def scheduled_job():
    print("📅 MF: ----- update_all started -----")
    driver = init()
    if driver != None:
        update_all(driver)
        driver.quit()
    print("✅ MF: ----- update_all done -----")


sched.start()
print("🟢 MF: initialized")
