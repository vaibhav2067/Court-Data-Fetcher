from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

driver = None

def start_browser():
    global driver
    if driver is None:
        options = Options()
        
        # ✅ Headless mode: invisible browser
        options.add_argument("--headless=new")   # 'new' avoids some bugs
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")

        # Optional: mute audio / suppress logs
        options.add_argument("--mute-audio")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Start Chrome
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://delhihighcourt.nic.in/app/get-case-type-status")
        time.sleep(3)
    return driver

def get_captcha():
    driver = start_browser()
    return driver.find_element(By.ID, "captcha-code").text

def submit_form(case_type, case_number, case_year, captcha_input):
    driver = start_browser()

    Select(driver.find_element(By.ID, "case_type")).select_by_value(case_type)
    driver.find_element(By.ID, "case_number").send_keys(case_number)
    Select(driver.find_element(By.ID, "case_year")).select_by_value(case_year)
    driver.find_element(By.ID, "captchaInput").send_keys(captcha_input)

    driver.find_element(By.ID, "search").click()
    time.sleep(5)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    result_div = soup.find("div", class_="table-responsive") or soup
    return str(result_div)
