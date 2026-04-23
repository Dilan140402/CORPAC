import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    options = Options()
    options.add_argument("--headless=new") # Obligatorio en GitHub Actions
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Configuración de descarga
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    # Uso de webdriver-manager para instalar el driver automáticamente
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
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
    print(f"\n🔎 Scrapeando {nombre.upper()}...")
    driver.get(url)

    time.sleep(6) # Esperar carga inicial

    years = driver.find_elements(By.XPATH, "//*[contains(text(),'Año')]")
    year_texts = [y.text.strip() for y in years if y.text.strip()]

    print("Años encontrados:", len(year_texts))

    for year_text in year_texts:
        print(f"\n📂 Entrando a {year_text}")
        year = "".join(filter(str.isdigit, year_text))
        folder = os.path.join(OUTPUT_DIR, nombre, year)
        os.makedirs(folder, exist_ok=True)

        try:
            year_elem = driver.find_element(By.XPATH, f"//*[contains(text(),'{year_text}')]")
            # Usar JavaScript para el click del año para evitar que se bloquee
            driver.execute_script("arguments[0].click();", year_elem)
            time.sleep(5) 
        except:
            print("No se encontró o no se pudo cliquear:", year_text)
            continue

        # BUSCAR LINKS DE DESCARGA
        botones = driver.find_elements(By.XPATH, "//a[contains(@href,'download')]")
        print(f"Total botones encontrados en {year_text}: {len(botones)}")

        for i in range(len(botones)):
            try:
                # Volvemos a buscar para evitar elementos caducados (StaleElement)
                btns = driver.find_elements(By.XPATH, "//a[contains(@href,'download')]")
                href = btns[i].get_attribute("href")

                if href:
                    # USAR REQUESTS DIRECTAMENTE (Ignoramos el click de Selenium)
                    descargar_archivo(href, folder)
                    time.sleep(1) # Pequeña pausa entre archivos

            except Exception as e:
                print(f"Error procesando link {i}: {e}")

    driver.quit() # Importante cerrar el driver al terminar cada categoría

def descargar_archivo(url, folder):
    # Headers para evitar que el servidor de Corpac bloquee a GitHub
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    try:
        # Generar un nombre basado en el ID del link para evitar duplicados
        if "i=" in url:
            file_id = url.split("i=")[-1].split("&")[0]
            filename = f"reporte_{file_id}.xlsx"
        else:
            filename = url.split("/")[-1].split("?")[0] or "archivo.xlsx"
            
        path = os.path.join(folder, filename)

        # Descarga con timeout más largo para GitHub
        r = requests.get(url, headers=headers, timeout=30, stream=True)

        if r.status_code == 200:
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  ✅ Guardado: {filename}")
        else:
            print(f"  ❌ Error HTTP {r.status_code} en: {url}")

    except Exception as e:
        print(f"  ❌ Error de conexión: {e}")
# -------------------------
# MAIN
# -------------------------
def main():

    for categoria, url in URLS.items():
        scrape_categoria(categoria, url)

    print("\n✅ SCRAPING COMPLETADO")

if __name__ == "__main__":
    main()