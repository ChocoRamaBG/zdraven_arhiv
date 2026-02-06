import time
import os
import urllib.parse
import pandas as pd
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

output_filename = os.path.join(script_dir, "zdraven_arhiv_data.xlsx")
print(f"🎯 Базата данни: {output_filename}")

# --- ⚙️ НАСТРОЙКИ НА БРАУЗЪРА ЗА CLOUD ---
options = Options()
options.add_argument('--headless=new') 
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# --- 🚗 СТАРТИРАНЕ НА ДРАЙВЪРЧОВЦИ ---
print("⏳ Паля гумите на Chrome (Headless Mode)...")
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    print("✅ Драйвърът зареди. Cloud Ninja Mode.")
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
    # Малко логорея да има, да се знае, че работим
    print(f"   👉 Visiting: {url}")
    try:
        driver.get(url)
        time.sleep(1) 
        
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "elementor-heading-title")))
        except: pass

        # 1. ТЕЛЕФОНЧОВЦИ
        phones = []
        try:
            phone_widgets = driver.find_elements(By.XPATH, "//div[contains(@class, 'elementor-widget-icon-box')]//i[contains(@class, 'fa-phone-alt')]/ancestor::div[contains(@class, 'elementor-widget-icon-box')]//h3")
            for pw in phone_widgets:
                t = pw.text.strip()
                if t and t not in phones: phones.append(t)
        except: pass
        if not phones: 
            try:
                links = driver.find_elements(By.XPATH, "//a[contains(@href, 'tel:')]")
                for l in links: phones.append(l.text.strip())
            except: pass

        # 2. ИМЕЙЛЧОВЦИ
        emails = []
        try:
            email_widgets = driver.find_elements(By.XPATH, "//div[contains(@class, 'elementor-widget-icon-box')]//i[contains(@class, 'fa-mail-bulk')]/ancestor::div[contains(@class, 'elementor-widget-icon-box')]//h3")
            for ew in email_widgets:
                t = ew.text.strip()
                if t and t not in emails: emails.append(t)
        except: pass

        # 3. АДРЕСИ & MAPS
        text_address = "-"
        try:
            addr_widgets = driver.find_elements(By.XPATH, "//div[contains(@class, 'elementor-widget-icon-box')]//i[contains(@class, 'icon-checked1')]/ancestor::div[contains(@class, 'elementor-widget-icon-box')]//h3")
            if addr_widgets:
                text_address = addr_widgets[0].text.strip()
        except: pass

        map_pin_address = "-"
        clickable_map_link = "-"
        try:
            iframe = driver.find_element(By.XPATH, "//div[contains(@class, 'elementor-widget-google_maps')]//iframe")
            raw_address = iframe.get_attribute("title") or iframe.get_attribute("aria-label")
            
            if raw_address:
                map_pin_address = raw_address
                encoded_address = urllib.parse.quote(raw_address)
                clickable_map_link = f"https://www.google.com/maps/search/?api=1&query={encoded_address}"
            else:
                src = iframe.get_attribute("src")
                if src: clickable_map_link = src
        except Exception: pass

        # 4. БИОГРАФИЯ
        full_bio = "-"
        try:
            bio_elements = driver.find_elements(By.CSS_SELECTOR, ".jet-listing-dynamic-field__content")
            bio_texts = []
            for el in bio_elements:
                txt = el.text.strip()
                if len(txt) > 40: 
                    bio_texts.append(txt)
            if bio_texts:
                full_bio = " || ".join(bio_texts).replace('\n', ' ')
            elif bio_elements:
                full_bio = bio_elements[0].text.strip().replace('\n', ' ')
        except: pass

        # 5. BREADCRUMB
        breadcrumb_info = "-"
        try:
            breadcrumb_el = driver.find_element(By.CLASS_NAME, "breadcrumb_last")
            breadcrumb_info = breadcrumb_el.text.strip()
        except: 
            try:
                breadcrumb_el = driver.find_element(By.CSS_SELECTOR, "#breadcrumbs span.breadcrumb_last")
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
        print(f"💀 Грешка в профила: {e}")
        basic_info.update({"Note": "Profile Scrape Failed"})
    
    return basic_info

# --- 📜 MAIN LOOP (SIGMA GRINDSET EDITION) ---
page = 1
# max_pages... малини и къпини, все тая. Махаме го. 
# Сега сме на "while True" mode, no cap.

print("🚀 Стартиране на Scraping процеса...")

try:
    while True: # Infinite loop maxxing
        if page == 1:
            target_url = "https://zdraven-arhiv.com/doctors/"
        else:
            target_url = f"https://zdraven-arhiv.com/doctors/page/{page}/"
            
        print(f"\n📄 --- СТРАНИЦА {page} (докато свят светува) ---")
        driver.get(target_url)
        
        try:
            # Чакаме малко елементчовци да заредят
            # Намалих timeout-а малко, че да не висим като прани гащи
            wait_time = 10 if page == 1 else 5
            try:
                WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.CLASS_NAME, "jet-listing-grid__item")))
            except:
                # Ако timeout-не, вероятно няма елементи, но проверката долу ще го хване
                pass

            cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'jet-listing-grid__item')]")
            
            # ТОВА Е ВАЖНОТО, ЛЬОЛЬО:
            if not cards:
                print("⛔ Няма повече доктори. Край на мача. Game Over.")
                break # <-- Ето тук спираме цикъла

            print(f"🔎 Намерих {len(cards)} доктори. Lets gooo.")
            
            doctors_on_page = []
            for card in cards:
                try:
                    try:
                        link_el = card.find_element(By.XPATH, ".//a[contains(@class, 'jet-listing-dynamic-link__link')]")
                        url = link_el.get_attribute("href")
                        name = link_el.text.strip()
                        if not name:
                            name = card.find_element(By.XPATH, ".//span[contains(@class, 'jet-listing-dynamic-link__label')]").text.strip()
                    except: continue

                    desc_list = "-"
                    try:
                        fields = card.find_elements(By.XPATH, ".//div[contains(@class, 'jet-listing-dynamic-field__content')]")
                        if fields: desc_list = fields[0].text.strip()
                    except: pass

                    doc_data = {
                        "Име": name,
                        "URL": url,
                        "Описание (Лист)": desc_list
                    }
                    doctors_on_page.append(doc_data)
                except: continue

            for doc in doctors_on_page:
                if not doc['URL']: continue
                full_data = scrape_inner_profile(doc['URL'], doc)
                save_single_record(full_data)

            page += 1
            
        except Exception as e:
            # Ако гръмне нещо генерално, може би е 404
            print(f"🤬 ГРЕШКА на страница {page}: {e}")
            # Проверяваме дали не сме набили 404 страница
            if "404" in driver.title or "Страницата не е намерена" in driver.page_source:
                 print("⛔ Уцелихме 404. Спирам.")
                 break
            
            # Иначе пробваме следващата, барем стане нещо
            page += 1
            continue

finally:
    try:
        driver.quit()
        print("🛑 Спрях колата.")
    except: pass
    print(f"\n🏁 Финито! (Приключихме на страница {page})")
