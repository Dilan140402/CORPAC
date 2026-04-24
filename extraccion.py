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
    options.add_argument("--window-size=1920,1080")

    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def cambiar_carpeta_descarga(driver, ruta):
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": os.path.abspath(ruta)
    })

def scrape_categoria(nombre, url):
    driver = iniciar_driver()
    wait = WebDriverWait(driver, 20) # Espera de hasta 20 segundos
    print(f"\n🚀 TRABAJANDO EN: {nombre.upper()}")
    
    try:
        # Entrar a la URL
        driver.get(url)
        time.sleep(10) # Tiempo generoso para carga inicial de scripts del portal

        # Esperar a que aparezca al menos un botón de "Año" para confirmar que cargó la sección
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Año')]")))

        # Obtener los años disponibles en ESTA categoría
        years = driver.find_elements(By.XPATH, "//*[contains(text(),'Año')]")
        year_texts = [y.text.strip() for y in years if y.text.strip()]
        print(f"📅 Años encontrados: {year_texts}")

        for year_text in year_texts:
            print(f"  📂 Procesando: {year_text}")
            year = "".join(filter(str.isdigit, year_text))
            folder = os.path.join(OUTPUT_DIR, nombre, year)
            os.makedirs(folder, exist_ok=True)

            cambiar_carpeta_descarga(driver, folder)

            try:
                # Click en el año usando JS para evitar que otros elementos lo tapen
                year_elem = driver.find_element(By.XPATH, f"//*[contains(text(),'{year_text}')]")
                driver.execute_script("arguments[0].scrollIntoView();", year_elem)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", year_elem)
                
                # Esperar a que la lista de archivos se actualice (IMPORTANTE)
                time.sleep(7) 

                # Buscar botones de descarga
                botones = driver.find_elements(By.XPATH, "//a[contains(@href,'download')]")
                print(f"     ✅ Archivos para {year_text}: {len(botones)}")

                for i in range(len(botones)):
                    try:
                        # Re-localizar botones para evitar StaleElement
                        btns_current = driver.find_elements(By.XPATH, "//a[contains(@href,'download')]")
                        boton = btns_current[i]
                        
                        driver.execute_script("arguments[0].scrollIntoView();", boton)
                        driver.execute_script("arguments[0].click();", boton)
                        
                        print(f"     📥 Descargando {i+1}/{len(botones)}...")
                        time.sleep(4) # Tiempo para que inicie y termine la descarga
                    except Exception as e:
                        print(f"     ⚠️ Error en archivo {i+1}: {e}")

            except Exception as e:
                print(f"   ❌ Error al abrir el año {year_text}: {e}")
    
    except Exception as e:
        print(f"💥 Error crítico en categoría {nombre}: {e}")
    
    finally:
        driver.quit() # Cerramos y abrimos uno nuevo para la siguiente categoría para limpiar caché
        print(f"🏁 Finalizada sección: {nombre}")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    for categoria, url in URLS.items():
        scrape_categoria(categoria, url)
        time.sleep(5) # Pausa entre categorías

    print("\n✅ PROCESO COMPLETADO TOTALMENTE")

if __name__ == "__main__":
    main()
