import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

def iniciar_driver():
    download_path = os.path.abspath(OUTPUT_DIR)
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080") # Simular pantalla grande

    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def cambiar_carpeta_descarga(driver, ruta):
    # Esto es vital en headless para que Chrome permita descargar archivos
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": os.path.abspath(ruta)
    })

def scrape_categoria(nombre, url):
    driver = iniciar_driver()
    print(f"\n🔎 Iniciando: {nombre.upper()}")
    
    try:
        driver.get(url)
        time.sleep(8) # Esperar carga del portal

        years = driver.find_elements(By.XPATH, "//*[contains(text(),'Año')]")
        year_texts = [y.text.strip() for y in years if y.text.strip()]

        for year_text in year_texts:
            print(f"📂 Procesando: {year_text}")
            year = "".join(filter(str.isdigit, year_text))
            folder = os.path.join(OUTPUT_DIR, nombre, year)
            os.makedirs(folder, exist_ok=True)

            # Cambiamos la ruta de descarga para cada año
            cambiar_carpeta_descarga(driver, folder)

            try:
                # Localizar el botón del año
                year_elem = driver.find_element(By.XPATH, f"//*[contains(text(),'{year_text}')]")
                driver.execute_script("arguments[0].scrollIntoView();", year_elem)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", year_elem)
                
                time.sleep(6) # Esperar que cargue la lista de archivos del año

                # Buscar botones de descarga
                botones = driver.find_elements(By.XPATH, "//a[contains(@href,'download')]")
                print(f"   Encontrados {len(botones)} archivos.")

                for i in range(len(botones)):
                    try:
                        # Re-localizar para evitar StaleElementReferenceException
                        btns_current = driver.find_elements(By.XPATH, "//a[contains(@href,'download')]")
                        boton = btns_current[i]
                        
                        driver.execute_script("arguments[0].scrollIntoView();", boton)
                        driver.execute_script("arguments[0].click();", boton)
                        
                        print(f"   📥 Descargando archivo {i+1}...")
                        time.sleep(4) # Espera suficiente para que se complete la descarga
                    except Exception as e:
                        print(f"   ⚠️ Error en archivo {i+1}: {e}")

            except Exception as e:
                print(f"   ❌ No se pudo procesar el año {year_text}: {e}")
    
    finally:
        driver.quit()

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    for categoria, url in URLS.items():
        scrape_categoria(categoria, url)
    print("\n✅ PROCESO COMPLETADO")

if __name__ == "__main__":
    main()
