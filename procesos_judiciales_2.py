
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager  

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import capsolver
import pandas as pd

# Configuración de claves y perfil
#profile_path = r"C:\Users\Jordan\seleniumnodes-chrome-profile-2"
CAPSOLVER_API_KEY = "CAP-D81F24F2A7947936AD16CA4B19E64539"
capsolver.api_key = CAPSOLVER_API_KEY

# Configuración del task para resolver captcha
captcha_task = {
    "type": "ReCaptchaV2TaskProxyLess",
    "websiteURL": "https://procesosjudiciales.funcionjudicial.gob.ec",
    "websiteKey": "6LfjVAcUAAAAANT1V80aWoeJusJ9flay5wTKvr0i"
}

# Payload inicial para la solicitud
payload = {
    "numeroCausa": "",
    "actor": {
        "cedulaActor": "",
        "nombreActor": ""
    },
    "demandado": {
        "cedulaDemandado": "",
        "nombreDemandado": "Elizabeth tipan"
    },
    "provincia": "",
    "numeroFiscalia": "",
    "recaptcha": "verdad",
    "first": 2,
    "pageSize": 10
}

# Enviar solicitud inicial para obtener datos
try:
    req = requests.post(
        'https://api.funcionjudicial.gob.ec/EXPEL-CONSULTA-CAUSAS-SERVICE/api/consulta-causas/informacion/buscarCausas?page=1&size=200',
        json=payload
    )
    req.raise_for_status()
    response_list = req.json()[:2]  # Limitar la lista de respuestas a los primeros 10 elementos
except requests.RequestException as e:
    print(f"Error al realizar la solicitud: {e}")
    exit()
except json.JSONDecodeError as e:
    print(f"Error al procesar la respuesta JSON: {e}")
    exit()

# Configuración de Selenium y opciones del navegador
options = webdriver.ChromeOptions()
prefs = {
    'download.default_directory': r'/home/ubuntu/environment/frontera',
    "download.prompt_for_download": False
}
options.add_experimental_option('prefs', prefs)
#options.add_argument(f"--user-data-dir={profile_path}")
#options.add_argument("--profile-directory=Default")
options.add_argument("--headless")
options.add_argument('window-size=1920x1080')
options.add_extension(r"/home/ubuntu/environment/frontera/Captcha.crx")
# Inicializar el driver de Selenium
try:
    #service = Service('/usr/bin/chromedriver')  # Ruta al chromedriver
   
    driver = driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 50)
except Exception as e:
    print(f"Error al inicializar Selenium: {e}")
    exit()

# Crear un DataFrame para almacenar los resultados
data = []

# Recorrer los juicios y extraer los datos necesarios
for i, item in enumerate(response_list):
    try:
        id_juicio = item["idJuicio"]
        delitos = item["nombreDelito"]
        fecha = item["fechaIngreso"]
        estado = item["estadoActual"]

        print(f"Procesando Juicio {i + 1}: {id_juicio}, {delitos}, {fecha}, {estado}")

        # Abrir la página de búsqueda
        driver.get("https://procesosjudiciales.funcionjudicial.gob.ec/busqueda-filtros")

        # Ingresar ID del juicio
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "mat-input-0"))).send_keys(id_juicio)
        except Exception as e:
            print(f"Error al ingresar ID del juicio: {e}")
            data.append({"id_juicio": id_juicio, "descarga_exitosa": False})
            continue

        # Hacer clic en buscar
        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/app-root/app-expel-filtros-busqueda/expel-sidenav/mat-sidenav-container/mat-sidenav-content/section/form/div[6]/button[1]"))).click()
        except Exception as e:
            print(f"Error al hacer clic en buscar: {e}")
            data.append({"id_juicio": id_juicio, "descarga_exitosa": False})
            continue

        # Comprobar si aparece el captcha
        try:
            boton = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/app-root/app-expel-listado-juicios/expel-sidenav/mat-sidenav-container/mat-sidenav-content/section/header/section/p"))).get_attribute("disabled")
        except Exception:
            print("Captcha detectado.")
            boton = "Captcha"

        if boton is None:
            print("Sin captcha, continuando.")
        else:
            print("Resolviendo captcha.")
            try:
                result = capsolver.solve(captcha_task)
                token = result["gRecaptchaResponse"]

                # Inyectar el token del captcha resuelto
                #js_code = f"document.getElementById('g-recaptcha-response').value='{token}';"
                #driver.execute_script(js_code)
                time.sleep(5)  # Esperar antes de continuar

                # Hacer clic nuevamente en buscar
                wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/app-root/app-expel-filtros-busqueda/expel-sidenav/mat-sidenav-container/mat-sidenav-content/section/form/div[6]/button[1]"))).click()
            except Exception as e:
                print(f"Error al resolver captcha: {e}")
                data.append({"id_juicio": id_juicio, "descarga_exitosa": False})
                continue

        # Descargar el PDF asociado
        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/app-root/app-expel-listado-juicios/expel-sidenav/mat-sidenav-container/mat-sidenav-content/section/section/div[2]/div/div[5]/a"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/app-root/app-expel-listado-movimientos/expel-sidenav/mat-sidenav-container/mat-sidenav-content/section/section/div/div[2]/div/div[2]/div/div[5]/a"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/app-root/app-expel-listado-actuaciones/expel-sidenav/mat-sidenav-container/mat-sidenav-content/section/section[2]/header/section[1]/section[2]/div/button[3]"))).click()
            print(f"PDF descargado para el juicio {id_juicio}.")
            data.append({"id_juicio": id_juicio, "descarga_exitosa": True})
        except Exception as e:
            print(f"Error al descargar PDF para el juicio {id_juicio}: {e}")
            data.append({"id_juicio": id_juicio, "descarga_exitosa": False})

        time.sleep(5)

    except Exception as e:
        print(f"Error en el proceso del juicio {i + 1}: {e}")
        data.append({"id_juicio": id_juicio, "descarga_exitosa": False})

# Guardar los resultados en un DataFrame
results_df = pd.DataFrame(data)
results_df.to_csv(r'/home/ubuntu/environment/frontera/resultados_descarga.csv', index=False)

# Finalizar ejecución
print("Proceso completado.")
driver.quit()
