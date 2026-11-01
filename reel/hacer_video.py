"""Del audio narrado al reel: mapas y gráficos animados del tablero, subtítulos y música.

Uso (después de voz.py y musica.py):
    python3 hacer_video.py

Lee guion.json, salidas/escenas.json, salidas/reel.wav, recursos/musica.wav y los datos del tablero
(../artifact/datos). Escribe en salidas/:
    reel.mp4     1080×1920, 30 fps, H.264 + AAC, voz a −14 LUFS y música por debajo
    reel.srt     subtítulos aparte
    portada.png  primer cuadro útil, para la miniatura
"""
import argparse
import difflib
import json
import math
import os
import subprocess

import mlx_whisper
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from voz import MODELO_ASR, normalizar

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "..", "artifact", "datos")
FUENTES = os.path.join(AQUI, "recursos", "fuentes")

ANCHO, ALTO, FPS = 1080, 1920, 30
MARGEN = 60
CIERRE = 5.5  # segundos de la tarjeta final después de la narración (el reel debe durar al menos 45 s)
DURACION_MAX = 74.5  # el reel debe durar entre 45 y 75 s
URL_TABLERO = "claude.ai/artifact/6bTVbbocVNX5enTreJr638"

# Colores del tablero (tema claro)
PAGINA = (246, 244, 234)
PANEL = (255, 253, 246)
LINEA = (227, 224, 207)
TINTA = (23, 35, 27)
TINTA_2 = (75, 90, 79)
TENUE = (111, 122, 113)
VERDE = (47, 125, 74)
VERDE_OSCURO = (31, 61, 43)
AMARILLO = (210, 154, 0)
MOSTAZA = (242, 194, 48)
CREMA = (246, 241, 220)
BARRA = (207, 203, 182)
SIN_DATO = (235, 232, 216)
RAMPA = [(228, 241, 217), (29, 90, 48)]

# Zonas de la pantalla
CAJA = (MARGEN, 240, ANCHO - MARGEN, 1000)  # gráfico o mapa
Y_FUENTE = 1018
Y_CIFRA = 1085
Y_SUB = 1420


def fuente(nombre, tam):
    archivos = {"num": "barlow-condensed-latin-600-normal.woff", "texto": "source-sans-3-latin-400-normal.woff",
                "semi": "source-sans-3-latin-600-normal.woff", "negrita": "source-sans-3-latin-700-normal.woff",
                "mono": "ibm-plex-mono-latin-400-normal.woff"}
    return ImageFont.truetype(os.path.join(FUENTES, archivos[nombre]), tam)


def leer(nombre):
    return json.load(open(os.path.join(DATOS, f"{nombre}.json"), encoding="utf-8"))


def suave(x):
    """Curva de entrada y salida para las animaciones (0 → 1)."""
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def mezclar(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def envolver(draw, texto, f, ancho):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if draw.textlength(prueba, font=f) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return lineas + [actual] if actual else lineas


def espaciado(draw, xy, texto, f, color, sep=0.08, anchor="l"):
    """Texto en mayúsculas con letras separadas, como las etiquetas del tablero."""
    ancho = sum(draw.textlength(c, font=f) + f.size * sep for c in texto) - f.size * sep
    x, y = xy
    if anchor == "m":
        x -= ancho / 2
    elif anchor == "r":
        x -= ancho
    for c in texto:
        draw.text((x, y), c, font=f, fill=color)
        x += draw.textlength(c, font=f) + f.size * sep
    return ancho


def nombre_dep(dep):
    """Los departamentos vienen en mayúsculas y sin tildes."""
    tildes = {"Apurimac": "Apurímac", "Huanuco": "Huánuco", "Junin": "Junín", "San Martin": "San Martín"}
    nombre = dep.title()
    return tildes.get(nombre, nombre)


# ---------- Mapas ----------

def equal_earth(lon, lat):
    a1, a2, a3, a4 = 1.340264, -0.081106, 0.000893, 0.003796
    m = math.sqrt(3) / 2
    lam, phi = math.radians(lon), math.radians(lat)
    th = math.asin(m * math.sin(phi))
    x = 2 * math.sqrt(3) * lam * math.cos(th) / (3 * (a1 + 3 * a2 * th ** 2 + th ** 6 * (7 * a3 + 9 * a4 * th ** 2)))
    y = th * (a1 + a2 * th ** 2 + th ** 6 * (a3 + a4 * th ** 2))
    return x, -y


def mercator(lon, lat):
    return math.radians(lon), -math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def anillos(geometria):
    polis = geometria["coordinates"] if geometria["type"] == "MultiPolygon" else [geometria["coordinates"]]
    return [anillo for poli in polis for anillo in poli]


def dibujar_mapa(formas, proyeccion, ancho, alto, escala=2, margen=16):
    """formas = [(geometria, color_relleno, color_borde_o_None, grosor)]. Devuelve dos capas del mismo tamaño:
    el mapa sin datos (gris) y el mapa con datos, dibujadas al doble y reducidas para que los bordes no se vean
    serruchados."""
    proyectados = [([[proyeccion(*p) for p in anillo] for anillo in anillos(g)], c, b, w) for g, c, b, w in formas]
    xs = [x for a, *_ in proyectados for anillo in a for x, _ in anillo]
    ys = [y for a, *_ in proyectados for anillo in a for _, y in anillo]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = min((ancho - 2 * margen) / (x1 - x0), (alto - 2 * margen) / (y1 - y0)) * escala
    dx = (ancho * escala - (x1 - x0) * k) / 2
    dy = (alto * escala - (y1 - y0) * k) / 2

    def pt(p):
        return (dx + (p[0] - x0) * k, dy + (p[1] - y0) * k)

    capas = []
    for con_datos in (False, True):
        img = Image.new("RGBA", (ancho * escala, alto * escala), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for a, color, _, _ in proyectados:
            for anillo in a:
                if len(anillo) > 2:
                    d.polygon([pt(p) for p in anillo], fill=color if con_datos else SIN_DATO, outline=PANEL,
                              width=escala)
        if con_datos:  # bordes resaltados encima de todo
            for a, _, borde, grosor in proyectados:
                if borde:
                    for anillo in a:
                        d.line([pt(p) for p in anillo] + [pt(anillo[0])], fill=borde, width=grosor * escala,
                               joint="curve")
        capas.append(img.resize((ancho, alto), Image.LANCZOS))
    return capas


def color_rampa(v, vmax):
    return SIN_DATO if v is None else mezclar(RAMPA[0], RAMPA[1], min(1, (v / vmax) ** 0.6))


def barrido(base, datos, avance, vertical=False):
    """Revela la capa con datos sobre la gris con un borde difuso que avanza."""
    w, h = base.size
    largo = h if vertical else w
    pos = avance * (largo + 120) - 60
    rampa = np.clip((pos - np.arange(largo)) / 60 + 0.5, 0, 1)
    mascara = np.tile(rampa[:, None], (1, w)) if vertical else np.tile(rampa[None, :], (h, 1))
    m = Image.fromarray((mascara * 255).astype(np.uint8))
    m = Image.composite(datos.getchannel("A"), Image.new("L", (w, h), 0), m)
    out = base.copy()
    capa = datos.copy()
    capa.putalpha(m)
    out.alpha_composite(capa)
    return out


def leyenda(d, x, y, texto_min, texto_max, ancho=260):
    for i in range(ancho):
        d.line([(x + i, y), (x + i, y + 14)], fill=mezclar(RAMPA[0], RAMPA[1], (i / ancho) ** 0.6))
    f = fuente("mono", 22)
    d.text((x, y + 22), texto_min, font=f, fill=TENUE)
    d.text((x + ancho, y + 22), texto_max, font=f, fill=TENUE, anchor="ra")


# ---------- Visuales de cada escena ----------
# Cada visual recibe (t, dur): segundos desde que empezó la escena y su duración; devuelve una imagen RGBA del
# tamaño de la caja.

class Visuales:
    def __init__(self):
        self.w = CAJA[2] - CAJA[0]
        self.h = CAJA[3] - CAJA[1]
        paises = {r["iso3"]: r for r in leer("mundo_paises")}
        deps = [r for r in leer("peru_departamentos") if int(r["anio"]) == 2024]
        self.deps = {r["departamento"]: r for r in deps}
        mundo = [f for f in leer("mundo_mapa") if f["iso3"] != "ATA"]
        peru = leer("peru_mapa")

        def num(v):
            return None if v is None else float(v)

        # Mapa mundial: % recogido para reciclar
        vmax = 40
        self.mundo = dibujar_mapa(
            [(f["geometria"], color_rampa(num(paises.get(f["iso3"], {}).get("reciclaje")), vmax), None, 0)
             for f in mundo if f["iso3"] != "PER"]
            + [(f["geometria"], color_rampa(num(paises["PER"]["reciclaje"]), vmax), AMARILLO, 3)
               for f in mundo if f["iso3"] == "PER"], equal_earth, self.w - 40, 520)
        # Mapas del Perú
        val = {k: num(r["pct_valorizado"]) for k, r in self.deps.items()}
        self.peru_val = dibujar_mapa([(f["geometria"], color_rampa(val.get(f["departamento"]), max(v for v in val.values() if v)),
                                       None, 0) for f in peru], mercator, 560, self.h - 150)
        bot = {k: num(r["botaderos"]) for k, r in self.deps.items()}
        self.peru_bot = dibujar_mapa([(f["geometria"], color_rampa(bot.get(f["departamento"]), max(bot.values())), None, 0)
                                      for f in peru], mercator, 560, self.h - 150)
        self.val_max = max(v for v in val.values() if v)
        self.bot_max = max(bot.values())
        self.top_val = sorted(val.items(), key=lambda kv: -(kv[1] or 0))[:3]
        self.top_bot = sorted(bot.items(), key=lambda kv: -kv[1])[:3]
        self.bot_total = int(sum(bot.values()))
        self.peru_pais = paises["PER"]
        self.mundo_reg = {r["region"]: r for r in leer("mundo_regiones")}
        hierro = [r for r in leer("precios_mensuales") if r["material"] == "Hierro y acero"]
        self.hierro = sorted(((r["mes"], float(r["usd_por_kg"]) * 1000) for r in hierro))

    def lienzo(self):
        img = Image.new("RGBA", (self.w, self.h), PANEL + (255,))
        d = ImageDraw.Draw(img)
        return img, d

    def titulo(self, d, texto, nota=None):
        d.text((32, 26), texto, font=fuente("negrita", 40), fill=TINTA)
        if nota:
            d.text((32, 76), nota, font=fuente("texto", 28), fill=TENUE)

    def portada_tablero(self, t, dur):
        img = Image.new("RGBA", (self.w, self.h), VERDE_OSCURO + (255,))
        d = ImageDraw.Draw(img)
        a = suave(t / 0.8)
        espaciado(d, (48, 56), "RECICLAJE · BOTADEROS · CIRCUITOS INFORMALES", fuente("mono", 22),
                  mezclar(VERDE_OSCURO, MOSTAZA, a))
        f = fuente("negrita", 100)
        y = 100 + int(30 * (1 - a))
        d.text((48, y), "Lo que vale", font=f, fill=mezclar(VERDE_OSCURO, CREMA, a))
        d.text((48, y + 100), "la basura", font=f, fill=mezclar(VERDE_OSCURO, MOSTAZA, a))
        d.text((48, y + 236), "Datos del Banco Mundial, MINAM, OEFA y UN Comtrade,", font=fuente("texto", 30),
               fill=mezclar(VERDE_OSCURO, CREMA, a))
        d.text((48, y + 274), "y trabajo de campo de mi tesis en Trujillo.", font=fuente("texto", 30),
               fill=mezclar(VERDE_OSCURO, CREMA, a))
        # Tarjetas de indicadores del tablero, una tras otra
        kpis = [("1.3%", "se valorizó en el Perú, 2024"), ("15%", "de distritos valoriza"),
                ("2119", "áreas degradadas"), ("53,000", "recicladores informales")]
        cw, ch, gap = (self.w - 96 - 24) // 2, 132, 20
        for i, (v, txt) in enumerate(kpis):
            b = suave((t - 0.9 - 0.35 * i) / 0.5)
            if b <= 0:
                continue
            x = 48 + (i % 2) * (cw + gap)
            yk = 450 + (i // 2) * (ch + gap) + int(20 * (1 - b))
            fondo = mezclar(VERDE_OSCURO, PANEL, b)
            d.rounded_rectangle((x, yk, x + cw, yk + ch), radius=14, fill=fondo)
            d.rounded_rectangle((x, yk, x + cw, yk + 14), radius=14, fill=mezclar(fondo, MOSTAZA if i % 2 else VERDE, b))
            d.rectangle((x, yk + 7, x + cw, yk + 14), fill=fondo)
            d.text((x + 24, yk + 18), v, font=fuente("num", 60), fill=mezclar(fondo, TINTA, b))
            d.text((x + 24, yk + 88), txt, font=fuente("texto", 26), fill=mezclar(fondo, TINTA_2, b))
        return img

    def mapa_mundo_reciclaje(self, t, dur):
        img, d = self.lienzo()
        self.titulo(d, "% de la basura que se recoge para reciclar", "Cada país con su último dato disponible")
        mapa = barrido(*self.mundo, suave(t / 2.2))
        z = 1 + 0.06 * suave((t - 2) / max(1, dur - 2))  # acercamiento lento
        if z > 1:
            w, h = mapa.size
            mapa = mapa.resize((int(w * z), int(h * z)), Image.LANCZOS).crop(
                (int(w * (z - 1) * 0.35), int(h * (z - 1) * 0.6), int(w * (z - 1) * 0.35) + w, int(h * (z - 1) * 0.6) + h))
        img.alpha_composite(mapa, (20, 140))
        a = suave((t - 2.2) / 0.5)
        if a > 0:
            d.text((32, 690), f"Perú: {float(self.peru_pais['reciclaje']):.2f}%",
                   font=fuente("negrita", 34), fill=mezclar(PANEL, AMARILLO, a))
        leyenda(d, self.w - 32 - 260, 690, "0%", "40% o más")
        return img

    def _mapa_peru(self, t, dur, capas, titulo, nota, top, fmt, maximo, leyenda_max):
        img, d = self.lienzo()
        self.titulo(d, titulo, nota)
        mapa = barrido(*capas, suave(t / 2.0), vertical=True)
        img.alpha_composite(mapa, (10, 130))
        # Los tres departamentos con más, a la derecha
        x = 580
        d.text((x, 200), "Los tres primeros", font=fuente("mono", 24), fill=TENUE)
        for i, (dep, v) in enumerate(top):
            a = suave((t - 1.6 - 0.4 * i) / 0.4)
            if a <= 0:
                continue
            y = 250 + i * 120
            d.text((x, y), nombre_dep(dep), font=fuente("semi", 32), fill=mezclar(PANEL, TINTA, a))
            largo = int(300 * (v / maximo) * a)
            d.rounded_rectangle((x, y + 46, x + max(8, largo), y + 76), radius=6, fill=mezclar(PANEL, VERDE, a))
            d.text((x + max(8, largo) + 10, y + 44), fmt(v), font=fuente("num", 34), fill=mezclar(PANEL, TINTA, a))
        leyenda(d, x, self.h - 80, "menos", leyenda_max)
        return img

    def mapa_peru_valorizado(self, t, dur):
        return self._mapa_peru(t, dur, self.peru_val, "% de la basura que se valoriza", "Por departamento, 2024",
                               self.top_val, lambda v: f"{v:.1f}%", self.val_max, f"{self.val_max:.1f}%")

    def mapa_peru_botaderos(self, t, dur):
        img = self._mapa_peru(t, dur, self.peru_bot, "Áreas degradadas por basura", "Número de lugares, por departamento",
                              self.top_bot, lambda v: f"{v:.0f}", self.bot_max, f"{self.bot_max:.0f}")
        return img

    def barras_generacion(self, t, dur):
        """Basura generada por región en 2022 (sin proyecciones), con América Latina resaltada."""
        img, d = self.lienzo()
        total = float(self.mundo_reg["Mundo"]["generacion_2022_t"]) / 1e6
        self.titulo(d, "Basura generada por región, 2022", f"Millones de toneladas · total mundial: {total:,.0f}")
        filas = sorted(((r, float(v["generacion_2022_t"]) / 1e6) for r, v in self.mundo_reg.items() if r != "Mundo"),
                       key=lambda x: -x[1])
        maximo = filas[0][1]
        f = fuente("semi", 28)
        for i, (region, v) in enumerate(filas):
            a = suave((t - 0.2 - 0.15 * i) / 0.9)
            y = 160 + i * 82
            latam = region == "América Latina y el Caribe"
            d.text((32, y), region, font=f, fill=TINTA if latam else TINTA_2)
            largo = max(8, int((self.w - 64 - 110) * v / maximo * a))
            d.rounded_rectangle((32, y + 38, 32 + largo, y + 70), radius=6, fill=AMARILLO if latam else BARRA)
            d.text((32 + largo + 12, y + 34), f"{v * a:,.0f}", font=fuente("num", 36), fill=TINTA)
        return img

    def barras_recicladores(self, t, dur):
        img, d = self.lienzo()
        self.titulo(d, "¿Quién recicla en el Perú?", "Personas que trabajan en el reciclaje")
        filas = [("Recicladores informales", float(self.peru_pais["recicladores_informales"]), VERDE),
                 ("Trabajadores formales", float(self.peru_pais["trabajadores_formales"]), BARRA)]
        maximo = filas[0][1]
        for i, (txt, v, color) in enumerate(filas):
            a = suave((t - 0.3 - 0.5 * i) / 1.4)
            y = 220 + i * 230
            d.text((32, y), txt, font=fuente("semi", 36), fill=TINTA)
            largo = int((self.w - 64) * 0.78 * v / maximo * a)
            d.rounded_rectangle((32, y + 60, 32 + max(10, largo), y + 150), radius=10, fill=color)
            d.text((32 + max(10, largo) + 16, y + 70), f"{v * a:,.0f}", font=fuente("num", 64),
                   fill=TINTA)
        b = suave((t - 2.0) / 0.6)
        if b > 0:
            razon = filas[0][1] / filas[1][1]
            d.text((32, 640), f"Por cada trabajador formal, hay {razon:.1f} recicladores informales.",
                   font=fuente("semi", 32), fill=mezclar(PANEL, TINTA_2, b))
        return img

    def linea_hierro(self, t, dur):
        img, d = self.lienzo()
        self.titulo(d, "Precio internacional del mineral de hierro", "US$ por tonelada, cada mes")
        datos = self.hierro
        vals = [v for _, v in datos]
        y0, y1 = math.floor(min(vals) / 10) * 10, math.ceil(max(vals) / 10) * 10
        izq, der, arr, aba = 110, self.w - 40, 170, self.h - 90

        def px(i):
            return izq + (der - izq) * i / (len(datos) - 1)

        def py(v):
            return aba - (aba - arr) * (v - y0) / (y1 - y0)

        f = fuente("mono", 24)
        for v in range(y0, y1 + 1, 10):
            d.line([(izq, py(v)), (der, py(v))], fill=LINEA, width=2)
            d.text((izq - 12, py(v)), f"{v}", font=f, fill=TENUE, anchor="rm")
        meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        for i, (mes, _) in enumerate(datos):
            if mes.endswith("-01") or mes.endswith("-07"):
                d.text((px(i), aba + 22), f"{meses[int(mes[5:]) - 1]} {mes[2:4]}", font=f, fill=TENUE, anchor="mt")
        avance = suave(t / max(2.0, dur * 0.75)) * (len(datos) - 1)
        n = int(avance)
        puntos = [(px(i), py(v)) for i, (_, v) in enumerate(datos[:n + 1])]
        if n < len(datos) - 1:
            frac = avance - n
            puntos.append((px(n + frac), py(datos[n][1] + (datos[n + 1][1] - datos[n][1]) * frac)))
        if len(puntos) > 1:
            d.line(puntos, fill=VERDE, width=6, joint="curve")
        for p in puntos[:n + 1]:
            d.ellipse((p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6), fill=VERDE, outline=PANEL, width=2)
        # Marca el mes más caro y el más barato cuando la línea ya pasó por ellos
        imax = vals.index(max(vals))
        imin = vals.index(min(vals))
        for i, txt in [(imax, "más caro"), (imin, "más barato")]:
            if i <= avance:
                x, y = px(i), py(vals[i])
                d.ellipse((x - 11, y - 11, x + 11, y + 11), outline=AMARILLO, width=4)
                d.text((x + 22, y), f"{txt}: US$ {vals[i]:.0f}", font=fuente("semi", 28), fill=TINTA, anchor="lm")
        return img

    def cierre(self, t, dur):
        img = Image.new("RGBA", (self.w, self.h), VERDE_OSCURO + (255,))
        d = ImageDraw.Draw(img)
        a = suave(t / 0.8)
        d.text((48, 90), "Explora el tablero", font=fuente("mono", 30), fill=mezclar(VERDE_OSCURO, MOSTAZA, a))
        d.text((48, 150), "Lo que vale", font=fuente("negrita", 112), fill=mezclar(VERDE_OSCURO, CREMA, a))
        d.text((48, 262), "la basura", font=fuente("negrita", 112), fill=mezclar(VERDE_OSCURO, MOSTAZA, a))
        b = suave((t - 0.8) / 0.6)
        d.rounded_rectangle((48, 430, self.w - 48, 520), radius=45, fill=mezclar(VERDE_OSCURO, PANEL, b))
        d.text((self.w / 2, 475), URL_TABLERO, font=fuente("mono", 30), fill=mezclar(VERDE_OSCURO, VERDE_OSCURO, b),
               anchor="mm")
        d.text((48, 580), "Mapas, indicadores y precios, con la metodología", font=fuente("texto", 32),
               fill=mezclar(VERDE_OSCURO, CREMA, b))
        d.text((48, 622), "y las fuentes de cada cifra.", font=fuente("texto", 32), fill=mezclar(VERDE_OSCURO, CREMA, b))
        return img


# ---------- Subtítulos (como en la tarea de la Sesión 15) ----------

def tiempos_de_palabras(guion, escenas, reel_wav):
    """Toma las palabras del guion (bien escritas) y les pone los tiempos que oyó Whisper."""
    palabras = [(p, i) for i, e in enumerate(guion["escenas"]) for p in e["frase"].split()]
    r = mlx_whisper.transcribe(reel_wav, path_or_hf_repo=MODELO_ASR, language="es", word_timestamps=True)
    oidas = []
    for s in r["segments"]:
        for w in s["words"]:
            tokens = normalizar(w["word"]).split()
            paso = (w["end"] - w["start"]) / max(len(tokens), 1)
            oidas += [(tok, w["start"] + k * paso, w["start"] + (k + 1) * paso) for k, tok in enumerate(tokens)]

    guion_norm = [normalizar(p) for p, _ in palabras]
    inicio, fin = [None] * len(palabras), [None] * len(palabras)
    sm = difflib.SequenceMatcher(None, guion_norm, [t for t, _, _ in oidas], autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            inicio[a + k], fin[a + k] = oidas[b + k][1], oidas[b + k][2]

    for i, (_, esc) in enumerate(palabras):
        if inicio[i] is None:
            prev = next((fin[j] for j in range(i - 1, -1, -1) if fin[j] is not None and palabras[j][1] == esc),
                        escenas[esc]["inicio"])
            nxt = next((inicio[j] for j in range(i + 1, len(palabras)) if inicio[j] is not None
                        and palabras[j][1] == esc), escenas[esc]["fin"])
            huecos = [j for j in range(i, len(palabras)) if inicio[j] is None and palabras[j][1] == esc]
            huecos = huecos[:next((k for k, j in enumerate(huecos) if j != i + k), len(huecos))]
            paso = (nxt - prev) / len(huecos)
            for k, j in enumerate(huecos):
                inicio[j], fin[j] = prev + k * paso, prev + (k + 1) * paso
    for i, (_, esc) in enumerate(palabras):
        inicio[i] = max(inicio[i], escenas[esc]["inicio"])
        fin[i] = max(min(fin[i], escenas[esc]["fin"]), inicio[i])
    return [{"palabra": p, "escena": e, "inicio": a, "fin": b} for (p, e), a, b in zip(palabras, inicio, fin)]


def agrupar(palabras, maximo):
    grupos, actual = [], []
    for w in palabras:
        if actual and (len(actual) == maximo or w["escena"] != actual[-1]["escena"]
                       or w["inicio"] - actual[-1]["fin"] > 0.35):
            grupos.append(actual)
            actual = []
        actual.append(w)
        if w["palabra"][-1] in ".,;:?!":
            grupos.append(actual)
            actual = []
    return grupos + [actual] if actual else grupos


def escribir_srt(grupos, ruta):
    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(ruta, "w", encoding="utf-8") as f:
        for n, g in enumerate(grupos, 1):
            fin = g[-1]["fin"] + 0.1
            if n < len(grupos):
                fin = min(fin, grupos[n][0]["inicio"])
            f.write(f"{n}\n{ts(g[0]['inicio'])} --> {ts(fin)}\n{' '.join(w['palabra'] for w in g)}\n\n")


def dibujar_subtitulo(d, grupo, t):
    f = fuente("negrita", 64)
    lineas = envolver(d, " ".join(w["palabra"] for w in grupo), f, ANCHO - 2 * MARGEN - 40)
    alto = len(lineas) * int(f.size * 1.2) + 36
    d.rounded_rectangle((MARGEN, Y_SUB - 18, ANCHO - MARGEN, Y_SUB - 18 + alto), radius=22, fill=PANEL,
                        outline=LINEA, width=2)
    y, k = Y_SUB, 0
    for linea in lineas:
        n = len(linea.split())
        x = (ANCHO - d.textlength(linea, font=f)) / 2
        for w in grupo[k:k + n]:
            suena = w["inicio"] <= t < w["fin"] + 0.05
            d.text((x, y), w["palabra"], font=f, fill=VERDE if suena else TINTA)
            x += d.textlength(w["palabra"] + " ", font=f)
        y += int(f.size * 1.2)
        k += n


# ---------- Composición ----------

def capa_fija():
    """Lo que está en todas las escenas: título del reel y aviso de voz con IA."""
    img = Image.new("RGB", (ANCHO, ALTO), PAGINA)
    d = ImageDraw.Draw(img)
    espaciado(d, (MARGEN, 128), "LO QUE VALE LA BASURA", fuente("mono", 30), VERDE)
    f = fuente("semi", 28)
    texto = "Voz generada con IA"
    w = d.textlength(texto, font=f)
    x1 = ANCHO - MARGEN
    d.rounded_rectangle((x1 - w - 44, 118, x1, 170), radius=26, outline=VERDE, width=2)
    d.text((x1 - w / 2 - 22, 144), texto, font=f, fill=VERDE, anchor="mm")
    return img


def capa_textos(escena, alfa):
    img = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    a = int(255 * alfa)
    if escena["fuente"]:
        d.text((MARGEN, Y_FUENTE), f"Fuente: {escena['fuente']}", font=fuente("mono", 24), fill=TENUE + (a,))
    if escena["cifra"]:
        tam = 150  # la cifra se achica si no cabe en el ancho
        while tam > 70 and d.textlength(escena["cifra"], font=fuente("num", tam)) > ANCHO - 2 * MARGEN:
            tam -= 6
        d.text((MARGEN, Y_CIFRA + (150 - tam)), escena["cifra"], font=fuente("num", tam), fill=TINTA + (a,))
        y = Y_CIFRA + 165
        for linea in envolver(d, escena["etiqueta"], fuente("semi", 40), ANCHO - 2 * MARGEN)[:2]:
            d.text((MARGEN, y), linea, font=fuente("semi", 40), fill=TINTA_2 + (a,))
            y += 50
    elif escena["etiqueta"]:
        y = Y_CIFRA + 40
        for linea in envolver(d, escena["etiqueta"], fuente("negrita", 56), ANCHO - 2 * MARGEN)[:2]:
            d.text((MARGEN, y), linea, font=fuente("negrita", 56), fill=TINTA + (a,))
            y += 68
    return img


def creditos(d):
    lineas = [
        "Datos: Banco Mundial (What a Waste 3.0, Pink Sheet), MINAM–SIGERSOL,",
        "OEFA, UN Comtrade y trabajo de campo de tesis (Antropología, PUCP).",
        "Mapas: Natural Earth y juaneladio/peru-geojson.",
        "Voz generada con IA (Qwen3-TTS) a partir de la voz de la autora.",
        "Música generada por código para este reel.",
    ]
    y = Y_CIFRA - 40
    for linea in lineas:
        d.text((MARGEN, y), linea, font=fuente("mono", 22), fill=TINTA_2)
        y += 36


def medir_volumen(wav):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    salida = r.stderr
    return json.loads(salida[salida.rindex("{"):salida.rindex("}") + 1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default="salidas")
    ap.add_argument("--muestra", type=float, nargs="*", help="solo guarda cuadros en estos segundos (para revisar)")
    args = ap.parse_args()
    s = args.salida

    guion = json.load(open("guion.json", encoding="utf-8"))
    escenas = json.load(open(f"{s}/escenas.json", encoding="utf-8"))
    # Los textos en pantalla se toman del guion actual: se pueden corregir sin volver a generar la voz
    for e, g in zip(escenas, guion["escenas"]):
        e.update({k: g[k] for k in ("cifra", "etiqueta", "visual", "fuente")})
    reel_wav = f"{s}/reel.wav"
    dur_audio = sf.info(reel_wav).duration
    # La tarjeta final se acorta si hace falta para no pasar de DURACION_MAX (mínimo 2.5 s)
    total = dur_audio + max(2.5, min(CIERRE, DURACION_MAX - dur_audio))

    palabras = tiempos_de_palabras(guion, escenas, reel_wav)
    escribir_srt(agrupar(palabras, 7), f"{s}/reel.srt")
    grupos = agrupar(palabras, 5)

    vis = Visuales()
    base = capa_fija()
    textos = [capa_textos(e, 1.0) for e in escenas]
    # Cada escena dura desde su inicio hasta el inicio de la siguiente; la última, hasta el final del video
    limites = [e["inicio"] for e in escenas[1:]] + [total]

    def cuadro(t):
        esc = next((i for i, fin in enumerate(limites) if t < fin), len(escenas) - 1)
        ini = 0 if esc == 0 else escenas[esc]["inicio"]
        dur = limites[esc] - ini
        img = base.copy()
        visual = getattr(vis, escenas[esc]["visual"])(t - ini, dur)
        # Transición: la caja entra deslizándose y aparece
        a = suave((t - ini) / 0.35)
        caja = Image.new("RGBA", visual.size, (0, 0, 0, 0))
        caja.alpha_composite(visual)
        mascara = Image.new("L", visual.size, 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, *visual.size), radius=24, fill=int(255 * a))
        sombra = Image.new("RGBA", (visual.size[0] + 40, visual.size[1] + 40), (0, 0, 0, 0))
        ImageDraw.Draw(sombra).rounded_rectangle((20, 24, visual.size[0] + 20, visual.size[1] + 24), radius=24,
                                                 fill=(23, 35, 27, int(28 * a)))
        sombra = sombra.filter(ImageFilter.GaussianBlur(10))
        img.paste(sombra, (CAJA[0] - 20, CAJA[1] - 20 + int(24 * (1 - a))), sombra)
        img.paste(caja, (CAJA[0], CAJA[1] + int(24 * (1 - a))), mascara)
        d = ImageDraw.Draw(img)
        if escenas[esc]["visual"] == "cierre":
            creditos(d)
        else:
            capa = textos[esc]
            b = suave((t - ini - 0.3) / 0.4)
            if b < 1:
                capa = capa.copy()
                capa.putalpha(capa.getchannel("A").point(lambda v: int(v * b)))
            img.paste(capa, (0, 0), capa)
        grupo = next((g for g in grupos if g[0]["inicio"] - 0.05 <= t <= g[-1]["fin"] + 0.25), None)
        if grupo:
            dibujar_subtitulo(d, grupo, t)
        d.rectangle((MARGEN, 196, MARGEN + (ANCHO - 2 * MARGEN) * min(1, t / total), 200), fill=VERDE)
        return img

    if args.muestra:
        for t in args.muestra:
            cuadro(t).save(f"{s}/muestra_{t:05.1f}.png")
        print("muestras guardadas")
        return

    cuadro(escenas[0]["fin"] - 0.5).save(f"{s}/portada.png")

    # Música por debajo de la voz: −14 LUFS la voz; la música baja más mientras se habla (sidechain)
    m = medir_volumen(reel_wav)
    voz = (f"[1:a]apad,loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
           f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
           "linear=true,aresample=48000,asplit=2[voz][guia]")
    musica = "[2:a]volume=0.22,aresample=48000[mus]"
    mezcla = ("[mus][guia]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[musb];"
              "[voz][musb]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]")
    ffmpeg = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-",
        "-i", reel_wav, "-i", "recursos/musica.wav",
        "-filter_complex", f"{voz};{musica};{mezcla}", "-map", "0:v", "-map", "[a]", "-t", f"{total:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", f"{s}/reel.mp4"], stdin=subprocess.PIPE)

    for n in range(int(total * FPS)):
        t = n / FPS
        ffmpeg.stdin.write(cuadro(t).convert("RGB").tobytes())
        if n % (FPS * 5) == 0:
            print(f"  {t:4.0f} s / {total:.0f} s", flush=True)
    ffmpeg.stdin.close()
    ffmpeg.wait()
    print(f"{s}/reel.mp4 · {s}/reel.srt · {s}/portada.png ({total:.1f} s)")


if __name__ == "__main__":
    main()
