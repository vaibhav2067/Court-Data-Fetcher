from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

driver = None
TARGET_URL = "https://delhihighcourt.nic.in/app/get-case-type-status"
WAIT_SECONDS = 15


def extract_result_table_html(soup):
    container = soup.find("div", class_="table-responsive")
    if container:
        return str(container)

    table = soup.find("table")
    if table:
        return str(table)

    return None


def start_browser():
    global driver
    if driver is None:
        options = Options()

        # Headless mode keeps the browser invisible.
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--mute-audio")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(TARGET_URL)
        WebDriverWait(driver, WAIT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "case_type"))
        )
    return driver


def get_captcha():
    driver = start_browser()
    return WebDriverWait(driver, WAIT_SECONDS).until(
        EC.visibility_of_element_located((By.ID, "captcha-code"))
    ).text.strip()


def reload_captcha():
    driver = start_browser()
    try:
        reload_btn = WebDriverWait(driver, WAIT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "reload-captcha"))
        )
        driver.execute_script("arguments[0].click();", reload_btn)

        def captcha_changed(current_driver):
            raw_text = current_driver.find_element(By.ID, "captcha-code").text.strip()
            parts = raw_text.split()
            return parts[-1] if parts else ""

        new_captcha = WebDriverWait(driver, WAIT_SECONDS).until(captcha_changed)
        return new_captcha.strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def submit_form(case_type, case_number, case_year, captcha_input):
    driver = start_browser()
    driver.get(TARGET_URL)

    try:
        wait = WebDriverWait(driver, WAIT_SECONDS)
        wait.until(EC.presence_of_element_located((By.ID, "case_type")))

        Select(driver.find_element(By.ID, "case_type")).select_by_value(case_type)

        case_number_input = driver.find_element(By.ID, "case_number")
        case_number_input.clear()
        case_number_input.send_keys(case_number)

        Select(driver.find_element(By.ID, "case_year")).select_by_value(case_year)

        captcha_field = driver.find_element(By.ID, "captchaInput")
        captcha_field.clear()
        captcha_field.send_keys(captcha_input)

        search_button = wait.until(EC.element_to_be_clickable((By.ID, "search")))
        driver.execute_script("arguments[0].click();", search_button)

        wait.until(
            lambda current_driver: current_driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            or "invalid captcha" in current_driver.page_source.lower()
            or "record not found" in current_driver.page_source.lower()
            or "no record found" in current_driver.page_source.lower()
        )
    except Exception as exc:
        return {"error": f"Search request failed before results loaded: {exc}"}

    soup = BeautifulSoup(driver.page_source, "html.parser")
    lowered_text = soup.get_text(" ", strip=True).lower()

    raw_html = extract_result_table_html(soup)

    if "invalid captcha" in lowered_text:
        return {"error": "Invalid captcha. Please try again with the latest code."}
    if "record not found" in lowered_text or "no record found" in lowered_text:
        return {"error": "No case data found for the entered details."}

    tbody = soup.find("tbody")
    if not tbody:
        if raw_html:
            return {"raw_html": raw_html}
        return {"error": "No case data found. The court site may have changed its layout."}

    row = tbody.find("tr")
    if not row:
        if raw_html:
            return {"raw_html": raw_html}
        return {"error": "No case data found for the entered details."}

    cols = row.find_all("td")
    if len(cols) < 4:
        if raw_html:
            return {"raw_html": raw_html}
        return {"error": "Incomplete case data was returned by the court site."}

    case_block = cols[1]
    case_no_text = case_block.text.strip().split("\n")[0].strip()
    status_tag = case_block.find("font")
    status = status_tag.text.strip("[]") if status_tag else "UNKNOWN"

    links = case_block.find_all("a")
    orders_link = links[1]["href"] if len(links) > 1 else None
    judgment_link = links[2]["href"] if len(links) > 2 else None

    parties_block = cols[2].decode_contents().split("<br>")
    petitioner = parties_block[0].strip()
    respondent = parties_block[2].strip() if len(parties_block) > 2 else "N/A"

    dates = [part.strip() for part in cols[3].text.strip().split("\n") if part.strip()]
    next_date = dates[0].replace("NEXT DATE:", "").strip() if dates else "N/A"
    last_date = dates[1].replace("Last Date:", "").strip() if len(dates) > 1 else "N/A"
    court_no = dates[2].replace("COURT NO:", "").strip() if len(dates) > 2 else "N/A"

    return {
        "case_no": case_no_text,
        "status": status,
        "petitioner": petitioner,
        "respondent": respondent,
        "next_date": next_date,
        "last_date": last_date,
        "court_no": court_no,
        "orders_link": orders_link,
        "judgment_link": judgment_link,
        "raw_html": raw_html,
    }
