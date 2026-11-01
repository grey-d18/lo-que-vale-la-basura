"""Descarga las fuentes originales en datos/originales/.

Fuentes:
- Banco Mundial, What a Waste 3.0 (país): residuos, tratamiento, composición y recicladores.
- MINAM / SIGERSOL (Plataforma Nacional de Datos Abiertos): generación, valorización y disposición final por distrito.
- OEFA (Plataforma Nacional de Datos Abiertos): inventario nacional de botaderos.
- UN Comtrade: exportaciones e importaciones de material reciclable del Perú (anual) y exportaciones
  mensuales de plástico y papel recuperado del Japón, para ver cómo varían esos precios mes a mes.
- Banco Mundial, WDI: tipo de cambio oficial (soles por dólar) para comparar precios.
- Banco Mundial, Pink Sheet: precios internacionales mensuales del cobre, el aluminio y el mineral de hierro.

Uso: uv run scripts/obtener_datos.py
"""

import json
import re
import time
from pathlib import Path

import httpx

ORIGINALES = Path(__file__).resolve().parent.parent / "datos" / "originales"
ORIGINALES.mkdir(parents=True, exist_ok=True)

# El portal de datos abiertos rechaza pedidos sin un navegador conocido
CLIENTE = httpx.Client(headers={"User-Agent": "Mozilla/5.0"}, timeout=120, follow_redirects=True)

PORTAL = "https://www.datosabiertos.gob.pe/sites/default/files/"
ARCHIVOS = {
    "waw3_paises.xlsx": "https://datacatalogfiles.worldbank.org/ddh-published/0039597/DR0095901/"
                        "What_a_Waste_3.0_COUNTRY_Dataset_&_Codebook.xlsx",
    "minam_generacion.csv": PORTAL + "1.%20Dataset%20Generaci%C3%B3n%20anual%20de%20residuos%20s%C3%B3lidos"
                                     "%20domiciliarios%20y%20municipales.csv",
    "minam_valorizacion_inorganicos.csv": PORTAL + "1.1%20Dataset_Valorizaci%C3%B3n%20de%20Residuos%20S%C3%B3lidos"
                                                   "%20Inorg%C3%A1nicos%20a%20Nivel%20Distrital%202019-2024.csv",
    "minam_valorizacion_diccionario.xlsx": PORTAL + "3.%20Diccionario%20de%20datos_Valorizaci%C3%B3n%20de%20RRSS"
                                                    "%20org%C3%A1nicos-inorg%C3%A1nicos.xlsx",
    "minam_disposicion_final.csv": PORTAL + "1%20DataSet%20Disposici%C3%B3n%20final%20adecuada%20de"
                                            "%20residuos%20s%C3%B3lidos.csv",
    "minam_disposicion_diccionario.xlsx": PORTAL + "3.%20Formato_DiccionarioDatos_Disposici%C3%B3n%20final"
                                                   "%20adecuada%20de%20RRSS.xlsx",
    "oefa_botaderos.csv": PORTAL + "1_a_Inventario%20Nacional%20de%20areas%20degradadas%20por%20residuos"
                                   "%20solidos%20municipales.csv",
}

# Partidas del Sistema Armonizado (HS) de los materiales que compran los acopiadores
MATERIALES_HS = {
    "7204": "Hierro y acero",
    "7404": "Cobre",
    "7602": "Aluminio",
    "4707": "Papel y cartón",
    "3915": "Plástico",
    "7001": "Vidrio",
}
PERU_COMTRADE = 604
ANIOS_COMTRADE = range(2015, 2026)
# El Perú no publica en Comtrade datos mensuales recientes; el Japón sí, y es uno de los grandes exportadores
# de plástico y papel recuperado
JAPON_COMTRADE = 392
MESES_DESDE = 202401


def descargar_archivos():
    for nombre, url in ARCHIVOS.items():
        destino = ORIGINALES / nombre
        if destino.exists():
            print(f"ya existe {nombre}")
            continue
        r = CLIENTE.get(url)
        r.raise_for_status()
        destino.write_bytes(r.content)
        print(f"descargado {nombre} ({len(r.content) / 1e6:.1f} MB)")


def pedir_comtrade(url):
    """La API pública de prueba de Comtrade da un periodo por pedido y limita la frecuencia de pedidos."""
    for intento in range(6):
        datos = CLIENTE.get(url).json()
        if "data" in datos:
            time.sleep(2)
            return datos["data"]
        time.sleep(3 * (intento + 1))  # límite de pedidos: esperar y reintentar
    raise RuntimeError(f"Comtrade no respondió: {url} {datos}")


def descargar_comtrade():
    """Comercio anual del Perú. Si el archivo ya existe, solo se agregan los años que faltan."""
    destino = ORIGINALES / "comtrade_peru_reciclables.json"
    filas = json.loads(destino.read_text()) if destino.exists() else []
    tenidos = {int(f["period"]) for f in filas}
    for anio in ANIOS_COMTRADE:
        if anio in tenidos:
            continue
        for flujo in ["X", "M"]:
            filas += pedir_comtrade(f"https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode={PERU_COMTRADE}"
                                    f"&period={anio}&partnerCode=0&cmdCode={','.join(MATERIALES_HS)}&flowCode={flujo}")
        print(f"comtrade {anio}: ok")
    destino.write_text(json.dumps(filas, ensure_ascii=False, indent=1))


def descargar_comtrade_mensual():
    """Exportaciones mensuales de plástico (3915) y papel (4707) recuperados del Japón, desde MESES_DESDE."""
    destino = ORIGINALES / "comtrade_japon_mensual.json"
    disponibles = CLIENTE.get(f"https://comtradeapi.un.org/public/v1/getDA/C/M/HS?reporterCode={JAPON_COMTRADE}").json()
    periodos = sorted(int(r["period"]) for r in disponibles["data"] if int(r["period"]) >= MESES_DESDE)
    filas = []
    for periodo in periodos:
        filas += pedir_comtrade(f"https://comtradeapi.un.org/public/v1/preview/C/M/HS?reporterCode={JAPON_COMTRADE}"
                                f"&period={periodo}&partnerCode=0&cmdCode=3915,4707&flowCode=X")
    destino.write_text(json.dumps(filas, ensure_ascii=False, indent=1))
    print(f"comtrade Japón mensual: {periodos[0]} a {periodos[-1]}")


def descargar_pink_sheet():
    """Precios mensuales de materias primas del Banco Mundial (Pink Sheet). El enlace cambia cada mes:
    se toma el que publica la página de Commodity Markets."""
    pagina = CLIENTE.get("https://www.worldbank.org/en/research/commodity-markets").text
    url = re.search(r'https://thedocs\.worldbank\.org[^"]*CMO-Historical-Data-Monthly\.xlsx', pagina).group(0)
    r = CLIENTE.get(url)
    r.raise_for_status()
    (ORIGINALES / "wb_pink_sheet_mensual.xlsx").write_bytes(r.content)
    print(f"descargado Pink Sheet ({url})")


def descargar_tipo_de_cambio():
    """Tipo de cambio oficial del Perú (PA.NUS.FCRF, soles por US$, promedio anual) desde la API del Banco Mundial."""
    destino = ORIGINALES / "wdi_tipo_de_cambio_peru.json"
    url = "https://api.worldbank.org/v2/country/PER/indicator/PA.NUS.FCRF?format=json&date=2015:2025&per_page=100"
    datos = CLIENTE.get(url).json()
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1))
    print("descargado tipo de cambio")


if __name__ == "__main__":
    descargar_archivos()
    descargar_tipo_de_cambio()
    descargar_comtrade()
    descargar_comtrade_mensual()
    descargar_pink_sheet()
