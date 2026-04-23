import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------------------------
# CONFIG
# -------------------------
URLS = {
    "penalidades": "https://portalapp.corpac.gob.pe/transparencia/portal-de-transparencia#14120",
    "ordenes": "https://portalapp.corpac.gob.pe/transparencia/portal-de-transparencia#14121",
    "viaticos": "https://portalapp.corpac.gob.pe/transparencia/portal-de-transparencia#14122"
}

OUTPUT_DIR = "data_corpac"

# -------------------------
# DRIVER
# -------------------------
def iniciar_driver():

    download_path = os.path.abspath("data_corpac")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("prefs", {
    "download.default_directory": download_path,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True,
    "plugins.always_open_pdf_externally": True
})

    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }

    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver


def cambiar_carpeta_descarga(driver, ruta):
    driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {
            "behavior": "allow",
            "downloadPath": ruta
        }
    )

# -------------------------
# DESCARGAR ARCHIVO
# -------------------------
def descargar_con_selenium(driver, url):

    main_window = driver.current_window_handle

    driver.execute_script("window.open(arguments[0]);", url)

    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)

    new_window = [w for w in driver.window_handles if w != main_window][0]
    driver.switch_to.window(new_window)

    time.sleep(3)

    driver.close()

    # 🔥 esperar que vuelva a 1 ventana
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) == 1)

    driver.switch_to.window(main_window)
# -------------------------
# SCRAPER PRINCIPAL
# -------------------------
def scrape_categoria(nombre, url):

    driver = iniciar_driver()
    wait = WebDriverWait(driver, 10)

    print(f"\n🔎 Scrapeando {nombre.upper()}...")
    driver.get(url)

    time.sleep(6)

    # obtener botones de años
    years = driver.find_elements(By.XPATH, "//*[contains(text(),'Año')]")
    year_texts = [y.text.strip() for y in years if y.text.strip()]

    print("Años encontrados:", len(year_texts))

    for year_text in year_texts:

        print(f"\n📂 Entrando a {year_text}")
        year = "".join(filter(str.isdigit, year_text))
        folder = os.path.join(OUTPUT_DIR, nombre, year)
        os.makedirs(folder, exist_ok=True)

        cambiar_carpeta_descarga(driver, os.path.abspath(folder))
        try:
            year_elem = driver.find_element(By.XPATH, f"//*[contains(text(),'{year_text}')]")
        except:
            print("No se encontró:", year_text)
            continue

        # scroll + click
        driver.execute_script("arguments[0].scrollIntoView();", year_elem)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", year_elem)

        # 🔥 esperar cambio de URL (clave)
        time.sleep(5)
        current_url = driver.current_url
        print("URL actual:", current_url)

        # 🔥 esperar que carguen links
        time.sleep(5)

        # buscar excels
        botones = driver.find_elements(By.XPATH, "//a[contains(@href,'download')]")

        print("Total botones encontrados:", len(botones))

        hrefs = []
        for i in range(len(botones)):
            try:
                botones = driver.find_elements(By.XPATH, "//a[contains(@href,'download')]")
                boton = botones[i]

                href = boton.get_attribute("href")

                if href:
                    print("📥 Descargando:", href)

                    driver.execute_script("arguments[0].scrollIntoView();", boton)
                    time.sleep(1)

                    boton.click()
                    time.sleep(4)

            except Exception as e:
                print("Error botón:", e)

        for href in hrefs:

            if ".xls" in href or ".xlsx" in href:

                print("📥 Excel encontrado:", href)

                year = "".join(filter(str.isdigit, year_text))
                folder = os.path.join(OUTPUT_DIR, nombre, year)
                os.makedirs(folder, exist_ok=True)

                descargar_archivo(href, folder)

def descargar_archivo(url, folder):

    try:
        filename = url.split("/")[-1].split("?")[0]
        path = os.path.join(folder, filename)

        r = requests.get(url, timeout=10)

        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            print("✅ Descargado:", filename)
        else:
            print("❌ Error descarga:", url)

    except Exception as e:
        print("❌ Error:", e)
# -------------------------
# MAIN
# -------------------------
def main():

    for categoria, url in URLS.items():
        scrape_categoria(categoria, url)

    print("\n✅ SCRAPING COMPLETADO")

if __name__ == "__main__":
    main()