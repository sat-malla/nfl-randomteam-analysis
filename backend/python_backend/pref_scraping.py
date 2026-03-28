import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import pandas as pd
import time
from dotenv import load_dotenv
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["nfl_season_data"]

BASE_URL = "https://www.pro-football-reference.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3", 
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"}
YEARS = range(2015, 2026)

def create_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
   #  options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver = uc.Chrome(options=options)
    return driver

# BeatifulSoup
def fetch_table(url, table_id):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"id": table_id})
    if table is None:
        print(f"Table {table_id} not found at {url}")
        return pd.DataFrame()
    df = pd.read_html(str(table))[0]
    df.columns = [
        "_".join(c).strip("_") if isinstance(c, tuple) else c
        for c in df.columns
    ]

    for col in ["Player", "Tm", "Rk"]:
        if col in df.columns:
            df = df[df[col] != col]
            break
    
    return df

# Selenium
def fetch_table_selenium(driver, url, table_id):
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, table_id))
        )
    except:
        print(f"Table {table_id} not found at {url}")
        return pd.DataFrame()
    
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": table_id})
    if table is None:
        print(f"Table {table_id} not found at {url}")
        return pd.DataFrame()

    df = pd.read_html(str(table))[0]
    df.columns = [
        "_".join(c).strip("_") if isinstance(c, tuple) else c
        for c in df.columns
    ]

    for col in ["Player", "Tm", "Rk"]:
        if col in df.columns:
            df = df[df[col] != col]
            break
    
    return df

# Beautiful Soup
def scrape_standings(year):
    url = f"{BASE_URL}/years/{year}/"
    response = requests.get(url, headers=HEADERS)

    dfs = pd.read_html(response.text)
    afc = fetch_table(url, "AFC")
    nfc = fetch_table(url, "NFC")
    standings = pd.concat([afc, nfc], ignore_index=True)

    keep = ["Tm", "W", "L", "T", "W-L%", "PF", "PA", "PD", "MoV", "SoS", "SRS", "OSRS", "DSRS"]
    existing = [col for col in keep if col in standings.columns]
    standings = standings[existing].copy()

    standings = standings[~standings["Tm"].str.contains("AFC|NFC", na=True)]
    standings["made_playoffs"] = standings["Tm"].str.contains(r"[*+]", regex=True).astype(int)

    standings["Tm"] = standings["Tm"].str.replace(r"[*+]", "", regex=True).str.strip()
    standings["year"] = year

    return standings


def scrape_standings_selenium(driver, year, retries=3):
    url = f"{BASE_URL}/years/{year}/"

    driver.get(url)
    time.sleep(5)
    #   print(driver.page_source[:2000])
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    afc_table = soup.find("table", {"id": "AFC"})
    nfc_table = soup.find("table", {"id": "NFC"})

    if afc_table is None or nfc_table is None:
        print(f"  WARNING: standings tables not found for {year}")
        print(driver.page_source[:500])  # debug
        return pd.DataFrame()

    afc = pd.read_html(str(soup.find("table", {"id": "AFC"})))[0]
    nfc = pd.read_html(str(soup.find("table", {"id": "NFC"})))[0]
    standings = pd.concat([afc, nfc], ignore_index=True)

    keep = ["Tm", "W", "L", "T", "W-L%", "PF", "PA", "PD", "MoV", "SoS", "SRS", "OSRS", "DSRS"]
    existing = [col for col in keep if col in standings.columns]
    standings = standings[existing].copy()

    standings = standings[~standings["Tm"].str.contains("AFC|NFC", na=True)]
    standings["made_playoffs"] = standings["Tm"].str.contains(r"[*+]", regex=True).astype(int)

    standings["Tm"] = standings["Tm"].str.replace(r"[*+]", "", regex=True).str.strip()
    standings["year"] = year

    return standings
        


def store_collection(collection_name, df):
    if df.empty:
        print(f"No data to store for {collection_name}")
        return
    
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    collection = db[collection_name]
    collection.delete_many({})
    collection.insert_many(records)
    print(f"Stored {len(records)} records in {collection_name}")




driver = create_driver()

try:
    data = {
        "pfref_standings": []
    }
    standings = scrape_standings_selenium(driver, 2025)
    print(standings)
    # for year in YEARS:
    #     print(f"\n{'='*40}")
    #     print(f"Scraping {year}...")
    #     print(f"{'='*40}")

    #     data["pfref_standings"].append(scrape_standings_selenium(driver, year))
    #     time.sleep(8)


    # for collection_name, dfs in data.items():
    #     combined = pd.concat(dfs, ignore_index=True)
    #     store_collection(collection_name, combined)

    # print("\nAll data scraped and stored successfully!")
finally:
    driver.quit()



    