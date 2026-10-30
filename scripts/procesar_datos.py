"""Limpia las fuentes de datos/originales/ y genera tablas en datos/procesados/ y JSON para la web en web/data/.

Uso: uv run scripts/procesar_datos.py
"""

import json
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ORIGINALES = RAIZ / "datos" / "originales"
PROCESADOS = RAIZ / "datos" / "procesados"
WEB = RAIZ / "web" / "data"
PROCESADOS.mkdir(parents=True, exist_ok=True)
WEB.mkdir(parents=True, exist_ok=True)

ANIO_PRECIOS = 2024  # último año completo de Comtrade y del tipo de cambio


def sin_tildes(texto):
    """'Áncash' -> 'ANCASH', para unir fuentes que escriben distinto los nombres."""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(texto.upper().split())


def guardar(df, nombre):
    df.to_csv(PROCESADOS / f"{nombre}.csv", index=False)
    registros = json.loads(df.to_json(orient="records", force_ascii=False, double_precision=4))
    (WEB / f"{nombre}.json").write_text(json.dumps(registros, ensure_ascii=False, separators=(",", ":")))
    print(f"{nombre}: {len(df)} filas")


# 1. Mundo: What a Waste 3.0 ------------------------------------------------------------------------------------

COLUMNAS_WAW = {
    "Country code": "iso3",
    "Country name ": "pais",
    "Region": "region",
    "Income group (2022)": "ingreso",
    "MSW generation - year reported": "anio_dato",
    "MSW generation (t/y)": "generacion_t",
    "MSW generation (kg/capita/day)": "kg_persona_dia",
    "Treatment - open dump (% weight MSW generated)": "botadero",
    "Treatment - controlled landfill (% weight MSW generated)": "relleno_controlado",
    "Treatment - sanitary landfill (% weight MSW generated)": "relleno_sanitario",
    "Treatment - unspecified landfill (% weight MSW generated)": "relleno_sin_especificar",
    "Treatment - composting (% weight MSW generated)": "compostaje",
    "Treatment - recycling (% weight MSW generated)": "reciclaje",
    "Treatment - incineration (% weight MSW generated)": "incineracion",
    "Treatment - uncollected (% weight MSW generated)": "no_recolectado",
    "Treatment - unaccounted for (% weight MSW generated)": "no_contabilizado",
    "Composition - food  (% weight MSW)": "comp_organico",
    "Composition - plastic (% weight MSW)": "comp_plastico",
    "Composition - paper & cardboard (% weight MSW)": "comp_papel_carton",
    "Composition - metal (% weight MSW)": "comp_metal",
    "Composition - glass  (% weight MSW)": "comp_vidrio",
    "Informal waste workers ": "recicladores_informales",
    "Formal waste workers": "trabajadores_formales",
}
REGIONES = {
    "E. Asia & Pacific": "Asia oriental y Pacífico",
    "Eur. & Cent. Asia": "Europa y Asia central",
    "L. Amer. & the Caribbean": "América Latina y el Caribe",
    "Mid. East & N. Africa": "Medio Oriente y Norte de África",
    "N. Amer.": "América del Norte",
    "S. Asia": "Asia del Sur",
    "Sub-Saharan Africa": "África subsahariana",
}
INGRESOS = {"HIC": "Alto", "UMIC": "Medio alto", "LMIC": "Medio bajo", "LIC": "Bajo"}

waw = pd.read_excel(ORIGINALES / "waw3_paises.xlsx", sheet_name="Country dataset")
waw = waw[list(COLUMNAS_WAW)].rename(columns=COLUMNAS_WAW)
waw = waw[waw.region.isin(REGIONES)]  # descarta la fila de códigos que sigue al encabezado
porcentajes = [c for c in waw.columns if c not in ("iso3", "pais", "region", "ingreso", "anio_dato", "generacion_t",
                                                   "kg_persona_dia", "recicladores_informales", "trabajadores_formales")]
numericas = porcentajes + ["anio_dato", "generacion_t", "kg_persona_dia", "recicladores_informales",
                           "trabajadores_formales"]
waw[numericas] = waw[numericas].apply(pd.to_numeric, errors="coerce")
waw[porcentajes] = waw[porcentajes] * 100  # la fuente usa fracciones: 0.0093 -> 0.93 %
waw["relleno"] = waw[["relleno_controlado", "relleno_sanitario", "relleno_sin_especificar"]].sum(axis=1, min_count=1)
waw["region"] = waw.region.map(REGIONES)
waw["ingreso"] = waw.ingreso.map(INGRESOS)
waw["pais"] = waw.pais.str.strip()
guardar(waw.drop(columns=["relleno_controlado", "relleno_sanitario", "relleno_sin_especificar"]), "mundo_paises")


def ponderado(d, columna):
    """Promedio ponderado por toneladas: lo que pesa cada país en la basura de su región."""
    d = d.dropna(subset=[columna, "generacion_t"])
    return pd.Series({f"{columna}": (d[columna] * d.generacion_t).sum() / d.generacion_t.sum() if len(d) else None,
                      f"n_{columna}": len(d)})


regiones = []
for nombre, d in [("Mundo", waw)] + list(waw.groupby("region")):
    fila = {"region": nombre, "generacion_t": d.generacion_t.sum()}
    for col in ["reciclaje", "botadero", "relleno", "compostaje", "incineracion", "comp_plastico", "comp_papel_carton",
                "comp_metal", "comp_vidrio", "comp_organico"]:
        fila.update(ponderado(d, col).to_dict())
    regiones.append(fila)
guardar(pd.DataFrame(regiones), "mundo_regiones")


# 2. Perú: MINAM por distrito -----------------------------------------------------------------------------------

val = pd.read_csv(ORIGINALES / "minam_valorizacion_inorganicos.csv", sep=";", encoding="latin-1",
                  dtype={"UBIGEO": str})
val["ubigeo"] = val.UBIGEO.str.zfill(6)

# En 2021 la fuente intercambia DEPARTAMENTO y REG_NAT. El departamento se toma del código UBIGEO (2 primeros
# dígitos) con el nombre de un año sin el error, y la región natural se corrige según el contenido.
correcto = val[val.PERIODO != 2021]
nombres_dep = correcto.groupby(correcto.ubigeo.str[:2]).DEPARTAMENTO.first().map(sin_tildes)
regiones_nat = {"COSTA", "SIERRA", "SELVA", "LIMA Y CALLAO"}
invertido = val.DEPARTAMENTO.map(sin_tildes).isin(regiones_nat)
val["reg_nat"] = val.REG_NAT.where(~invertido, val.DEPARTAMENTO).map(sin_tildes).replace("LIMA Y CALLAO", "COSTA")

distritos = pd.DataFrame({
    "ubigeo": val.ubigeo,
    "anio": val.PERIODO,
    "departamento": val.ubigeo.str[:2].map(nombres_dep),
    "provincia": val.PROVINCIA.map(sin_tildes),
    "distrito": val.DISTRITO.map(sin_tildes),
    "reg_nat": val.reg_nat,
    "poblacion": val.POB_TOTAL,
    "generado_t": val.QRESIDUOS_MUN,
    "valorizado_t": val["QRESIDUOS _VAL_INORGAN"],  # el nombre original trae un espacio
})

disp = pd.read_csv(ORIGINALES / "minam_disposicion_final.csv", sep=";", encoding="latin-1", dtype={"UBIGEO": str})
disp = pd.DataFrame({"ubigeo": disp.UBIGEO.str.zfill(6), "anio": disp.ANIO,
                     "dispuesto_adecuado_t": disp.RESIDUOS_MUNICIPALES_DISPUESTOS})
# En 2019 y 2021 la fuente reporta cero en todo el país: no hay dato, no es que nada se dispusiera bien
anios_vacios = disp.groupby("anio").dispuesto_adecuado_t.sum().loc[lambda s: s == 0].index
disp.loc[disp.anio.isin(anios_vacios), "dispuesto_adecuado_t"] = None
distritos = distritos.merge(disp, on=["ubigeo", "anio"], how="left").sort_values(["anio", "ubigeo"])
distritos["reporta_valorizacion"] = distritos.valorizado_t > 0
guardar(distritos, "peru_distritos")

botaderos = pd.read_csv(ORIGINALES / "oefa_botaderos.csv", encoding="utf-8-sig")
botaderos["departamento"] = botaderos.DEPARTAMENTO.map(sin_tildes)
por_dep_botaderos = botaderos.groupby("departamento").agg(
    botaderos=("DENOMINACION", "size"), botaderos_con_quema=("QUEMA_RRSS", lambda s: (s == "Si").sum()))


def resumir(d):
    adecuado = d.dispuesto_adecuado_t
    return pd.Series({
        "generado_t": d.generado_t.sum(),
        "valorizado_t": d.valorizado_t.sum(),
        "dispuesto_adecuado_t": adecuado.sum() if adecuado.notna().any() else None,
        "distritos": len(d),
        "distritos_que_valorizan": int(d.reporta_valorizacion.sum()),
        "poblacion": d.poblacion.sum(),
    })


def indicadores(t):
    t["pct_valorizado"] = 100 * t.valorizado_t / t.generado_t
    t["pct_dispuesto_adecuado"] = 100 * t.dispuesto_adecuado_t / t.generado_t
    t["pct_distritos_que_valorizan"] = 100 * t.distritos_que_valorizan / t.distritos
    t["kg_valorizado_por_persona"] = 1000 * t.valorizado_t / t.poblacion
    return t


departamentos = indicadores(distritos.groupby(["departamento", "anio"]).apply(resumir, include_groups=False)
                            .reset_index())
departamentos = departamentos.merge(por_dep_botaderos, on="departamento", how="left")
departamentos[["botaderos", "botaderos_con_quema"]] = departamentos[["botaderos", "botaderos_con_quema"]].fillna(0)
guardar(departamentos, "peru_departamentos")

nacional = indicadores(distritos.groupby("anio").apply(resumir, include_groups=False).reset_index())
guardar(nacional, "peru_nacional")

botaderos_lista = pd.DataFrame({
    "departamento": botaderos.departamento,
    "provincia": botaderos.PROVINCIA.map(sin_tildes),
    "distrito": botaderos.DISTRITO.map(sin_tildes),
    "nombre": botaderos.DENOMINACION.str.strip(),
    "quema": botaderos.QUEMA_RRSS == "Si",
    "categoria": botaderos.CATEGORIA,
    "anio_incorporacion": botaderos.ANIO_INCORPORACION,
})
guardar(botaderos_lista, "peru_botaderos")

trujillo = indicadores(distritos[distritos.provincia == "TRUJILLO"]
                       .groupby(["distrito", "anio"]).apply(resumir, include_groups=False).reset_index())
guardar(trujillo, "trujillo_distritos")


# 3. Mercado de material reciclable: Comtrade --------------------------------------------------------------------

MATERIALES = {"7204": "Hierro y acero", "7404": "Cobre", "7602": "Aluminio", "4707": "Papel y cartón",
              "3915": "Plástico", "7001": "Vidrio"}
comtrade = pd.DataFrame(json.loads((ORIGINALES / "comtrade_peru_reciclables.json").read_text()))
comercio = pd.DataFrame({
    "anio": comtrade.period.astype(int),
    "flujo": comtrade.flowCode.map({"X": "Exportación", "M": "Importación"}),
    "partida_hs": comtrade.cmdCode.astype(str),
    "valor_usd": comtrade.primaryValue,
    "toneladas": comtrade.netWgt / 1000,
})
comercio["material"] = comercio.partida_hs.map(MATERIALES)
comercio["usd_por_kg"] = (comercio.valor_usd / (comercio.toneladas * 1000)).where(comercio.toneladas > 0)
guardar(comercio.sort_values(["material", "flujo", "anio"]), "peru_comercio_reciclables")


# 4. Precios: lo que recibe quien recolecta frente al precio de exportación ---------------------------------------

wdi = json.loads((ORIGINALES / "wdi_tipo_de_cambio_peru.json").read_text())[1]
tipo_cambio = next(r["value"] for r in wdi if r["date"] == str(ANIO_PRECIOS))

precios = pd.read_csv(ORIGINALES / "precios_tesis.csv", dtype={"partida_hs": str})
exportacion = comercio[(comercio.flujo == "Exportación") & (comercio.anio == ANIO_PRECIOS)]
precios = precios.merge(exportacion[["partida_hs", "usd_por_kg"]], on="partida_hs", how="left")
precios["tipo_cambio"] = tipo_cambio
precios["exportacion_soles_kg"] = precios.usd_por_kg * tipo_cambio
precios["pct_min_del_precio_exportacion"] = 100 * precios.precio_min_soles_kg / precios.exportacion_soles_kg
precios["pct_max_del_precio_exportacion"] = 100 * precios.precio_max_soles_kg / precios.exportacion_soles_kg
guardar(precios, "precios_comparados")
