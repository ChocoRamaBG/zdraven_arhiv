import time
import os
import urllib.parse
import pandas as pd
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- 📁 ДИНАМИЧЕН ПЪТ ---
script_dir = os.getcwd()
print(f"📂 Работна папка: {script_dir}")

output_filename = os.path.join(script_dir, "zdraven_arhiv_data_fixed.xlsx")
print(f"🎯 Базата данни: {output_filename}")

# --- ⚙️ НАСТРОЙКИ НА БРАУЗЪРА ---
options = Options()

# 👇 ТОВА ТРЯБВА ДА Е ВКЛЮЧЕНО, ЩОМ СИ НА СЪРВЪР, ЛЬОЛЬО!
options.add_argument('--headless=new') 

options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# --- 🚗 СТАРТИРАНЕ НА ДРАЙВЪРЧОВЦИ ---
print("⏳ Паля гумите на Chrome... андибул морков mode activated.")
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    print("✅ Драйвърът зареди. Давай да мачкаме.")
except Exception as e:
    print(f"💥 What the fuck? Грешка при стартиране: {e}")
    raise e

# --- 💾 ЗАПИСВАЧКАТА ---
def save_single_record(record):
    if not record: return
    try:
        new_df = pd.DataFrame([record])
        if os.path.exists(output_filename):
            try:
                existing_df = pd.read_excel(output_filename)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            except:
                time.sleep(1)
                existing_df = pd.read_excel(output_filename)
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            final_df = new_df

        final_df.to_excel(output_filename, index=False)
        print(f"💾 Saved: {record.get('Име')}")
    except Exception as e:
        print(f"❌ HELL ERROR saving: {e}")

# --- 🕵️‍♂️ AGENT 007: PROFILE SCRAPER ---
def scrape_inner_profile(url, basic_info):
    print(f"   👉 Visiting: {url}")
    try:
        driver.get(url)
        # Чакаме малко, да не получим 429 като някой аматьор
        time.sleep(1.5) 
        
        # Чакаме основния контейнер
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "elementor-widget-icon-box")))
        except: pass

        # --- СЪБИРАНЕ НА ВСИЧКИ ИКОН-БОКСЧОВЦИ ---
        # Вместо да гадаем иконите, дърпаме всички текстове от кутийките
        # и ги сортираме с regex. Това е *Gyatt level logic*.
        
        phones = []
        emails = []
        possible_addresses = []
        
        try:
            # Търсим всички заглавия в icon boxes
            box_titles = driver.find_elements(By.CSS_SELECTOR, ".elementor-widget-icon-box .elementor-icon-box-title span")
            
            for title_el in box_titles:
                text = title_el.text.strip()
                if not text: continue
                
                # Regex Logic - Brainrot style
                # Ако има @ - имейл
                if "@" in text:
                    if text not in emails: emails.append(text)
                # Ако има цифри и е сравнително кратко - телефон
                elif re.search(r"(\+359|08[789]|02)", text) and len(text) < 20:
                    if text not in phones: phones.append(text)
                # Всичко останало, което е дълго, вероятно е адрес (или глупости)
                elif len(text) > 10:
                    if text not in possible_addresses: possible_addresses.append(text)
                    
        except Exception as e:
            print(f"⚠️ Warning: Не мога да парсна боксчовците. {e}")

        # --- АДРЕС ОТ GOOGLE MAPS IFRAME (Най-сигурното, Гащник) ---
        map_pin_address = "-"
        clickable_map_link = "-"
        
        try:
            # Търсим iframe-а по по-умен начин
            iframe = driver.find_element(By.CSS_SELECTOR, "iframe[src*='maps.google.com']")
            raw_address = iframe.get_attribute("title") or iframe.get_attribute("aria-label")
            
            if raw_address:
                map_pin_address = raw_address
                encoded_address = urllib.parse.quote(raw_address)
                clickable_map_link = f"https://www.google.com/maps/search/?api=1&query={encoded_address}"
        except: 
            pass

        # Ако нямаме адрес от картите, взимаме първия възможен текст от кутийките
        text_address = map_pin_address if map_pin_address != "-" else (possible_addresses[0] if possible_addresses else "-")

        # --- БИОГРАФИЯ ---
        full_bio = "-"
        try:
            # Взимаме текста от главното описание
            bio_el = driver.find_element(By.XPATH, "//div[contains(@class, 'jet-listing-dynamic-field__content')]")
            full_bio = bio_el.get_attribute("innerText").strip().replace('\n', ' || ')
        except: pass

        # --- BREADCRUMB ---
        breadcrumb_info = "-"
        try:
            breadcrumb_el = driver.find_element(By.ID, "breadcrumbs")
            breadcrumb_info = breadcrumb_el.text.strip()
        except: pass

        basic_info.update({
            "Телефони": ", ".join(phones) if phones else "-",
            "Email": ", ".join(emails) if emails else "-",
            "Адрес (Текст)": text_address,
            "Адрес (Google Maps Pin)": map_pin_address,
            "Google Maps Link": clickable_map_link,
            "Breadcrumb (Текст)": breadcrumb_info,
            "Биография": full_bio,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        print(f"💀 Грешка в профила: {e}. Мамка му човече!")
        basic_info.update({"Note": "Profile Scrape Failed"})
    
    return basic_info

# --- 📜 MAIN LOOP (SIGMA GRINDSET EDITION) ---
page = 1
print("🚀 Стартиране на Scraping процеса...")

try:
    while True:
        if page == 1:
            target_url = "https://zdraven-arhiv.com/doctors/"
        else:
            target_url = f"https://zdraven-arhiv.com/doctors/page/{page}/"
            
        print(f"\n📄 --- СТРАНИЦА {page} ---")
        driver.get(target_url)
        
        try:
            # Проверка за 404 - ако няма такава страница, бием шута
            if "404" in driver.title or "Страницата не е намерена" in driver.page_source:
                 print("⛔ Уцелихме 404. Край на играта, льольо.")
                 break

            wait_time = 10 if page == 1 else 5
            try:
                WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.CLASS_NAME, "jet-listing-grid__item")))
            except:
                print("⛔ Няма елементи. Probably finished.")
                break

            cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'jet-listing-grid__item')]")
            if not cards: break

            print(f"🔎 Намерих {len(cards)} доктори.")
            
            doctors_on_page = []
            for card in cards:
                try:
                    link_el = card.find_element(By.CSS_SELECTOR, "a.jet-listing-dynamic-link__link")
                    url = link_el.get_attribute("href")
                    name = link_el.text.strip()
                    
                    # Малко safe check
                    if not url: continue
                    
                    doc_data = {
                        "Име": name,
                        "URL": url,
                        "Описание (Лист)": "-" # Мързи ме да го дърпам отвън, ще го вземем отвътре
                    }
                    doctors_on_page.append(doc_data)
                except: continue

            for doc in doctors_on_page:
                full_data = scrape_inner_profile(doc['URL'], doc)
                save_single_record(full_data)

            page += 1
            
        except Exception as e:
            print(f"🤬 ГРЕШКА на страница {page}: {e}")
            break

finally:
    try:
        driver.quit()
        print("🛑 Спрях колата.")
    except: pass
    print(f"\n🏁 Финито! Андбиул морков coding session finished.")
