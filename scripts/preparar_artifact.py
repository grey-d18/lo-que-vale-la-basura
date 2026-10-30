"""Prepara los archivos que lee el tablero publicado como Artifact de Claude en artifact/datos/.

Cada archivo es una lista de filas JSON. Los mapas van como filas con su geometría,
y las cifras del trabajo de campo como una tabla aparte, para que cada número del tablero tenga su fuente.

Uso: uv run scripts/preparar_artifact.py   (después de procesar_datos.py)
"""

import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ORIGINALES = RAIZ / "datos" / "originales"
WEB = RAIZ / "web" / "data"
SALIDA = RAIZ / "artifact" / "datos"
SALIDA.mkdir(parents=True, exist_ok=True)


def redondear(coords, dec=3):
    """Menos decimales en las coordenadas: el mapa se ve igual y el archivo pesa menos."""
    if isinstance(coords[0], (int, float)):
        return [round(c, dec) for c in coords]
    return [redondear(c, dec) for c in coords]


def escribir(nombre, filas):
    texto = json.dumps(filas, ensure_ascii=False, separators=(",", ":"))
    (SALIDA / f"{nombre}.json").write_text(texto)
    print(f"{nombre}: {len(filas)} filas, {len(texto) / 1e3:.0f} KB")


# Tablas ya procesadas
for nombre in ["mundo_paises", "mundo_regiones", "peru_nacional", "peru_departamentos", "trujillo_distritos",
               "peru_comercio_reciclables", "precios_comparados"]:
    escribir(nombre, json.loads((WEB / f"{nombre}.json").read_text()))

# Mapa mundial: Natural Earth 1:110m (dominio público), una fila por país con su código ISO3
mundo = json.loads((ORIGINALES / "mundo_paises_110m.geojson").read_text())
CODIGOS_BANCO_MUNDIAL = {"KOS": "XKX", "PSX": "PSE"}  # Natural Earth usa otro código para estos dos
escribir("mundo_mapa", [
    {"iso3": CODIGOS_BANCO_MUNDIAL.get(f["properties"]["ADM0_A3"], f["properties"]["ADM0_A3"]),
     "nombre": f["properties"]["NAME_ES"],
     "geometria": {"type": f["geometry"]["type"], "coordinates": redondear(f["geometry"]["coordinates"], 2)}}
    for f in mundo["features"]
])

# Mapa del Perú por departamentos (juaneladio/peru-geojson, MPL-2.0)
peru = json.loads((WEB / "peru_departamentos.geojson").read_text())
escribir("peru_mapa", [
    {"departamento": f["properties"]["NOMBDEP"],
     "geometria": {"type": f["geometry"]["type"], "coordinates": redondear(f["geometry"]["coordinates"])}}
    for f in peru["features"]
])

# Cifras del trabajo de campo de la tesis
escribir("cifras_tesis", json.loads(pd.read_csv(ORIGINALES / "cifras_tesis.csv").to_json(orient="records",
                                                                                        force_ascii=False)))
