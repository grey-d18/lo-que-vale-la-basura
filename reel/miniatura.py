"""Miniatura del reel para LinkedIn: sin ella, el video se ve en blanco hasta darle play.

Uso:
    python3 miniatura.py

Escribe salidas/miniatura.png (1080×1920). Lo importante va en la franja central de 1080×1350,
que es lo que LinkedIn muestra cuando recorta un video vertical en el feed.
"""
import os

from PIL import Image, ImageDraw

from hacer_video import ALTO, ANCHO, CREMA, MARGEN, MOSTAZA, VERDE_OSCURO, fuente

AQUI = os.path.dirname(os.path.abspath(__file__))
TENUE_CLARO = (170, 190, 175)


def texto_ancho(d, texto, f):
    return d.textlength(texto, font=f)


def main():
    im = Image.new("RGB", (ANCHO, ALTO), VERDE_OSCURO)
    d = ImageDraw.Draw(im)
    x = MARGEN + 20

    d.text((x, 330), "RECICLAJE · BOTADEROS · CIRCUITOS INFORMALES", font=fuente("mono", 30), fill=MOSTAZA)
    titulo = fuente("negrita", 172)
    d.text((x, 390), "Lo que vale", font=titulo, fill=CREMA)
    d.text((x, 575), "la basura", font=titulo, fill=MOSTAZA)

    d.line((x, 870, x + 120, 870), fill=MOSTAZA, width=6)
    d.text((x - 8, 900), "1.3%", font=fuente("num", 300), fill=CREMA)
    cuerpo = fuente("texto", 46)
    for i, linea in enumerate(["de toda la basura municipal del Perú", "fueron inorgánicos valorizados (2024)."]):
        d.text((x, 1240 + i * 60), linea, font=cuerpo, fill=CREMA)
    d.text((x, 1400), "¿Quién recicla lo que no", font=fuente("negrita", 64), fill=MOSTAZA)
    d.text((x, 1480), "se registra?", font=fuente("negrita", 64), fill=MOSTAZA)

    pie = fuente("semi", 34)
    d.text((x, 1700), "Greicy Rodriguez Coronel · Antropología PUCP", font=pie, fill=TENUE_CLARO)
    etiqueta = "Voz generada con IA"
    fe = fuente("semi", 32)
    w = texto_ancho(d, etiqueta, fe)
    d.rounded_rectangle((x, 1770, x + w + 48, 1830), radius=30, outline=TENUE_CLARO, width=2)
    d.text((x + 24, 1780), etiqueta, font=fe, fill=TENUE_CLARO)

    salida = os.path.join(AQUI, "salidas", "miniatura.png")
    im.save(salida)
    print(salida)


if __name__ == "__main__":
    main()
