"""Música de fondo del reel, generada por código: no usa grabaciones ni obras de terceros.

Uso:
    python3 musica.py --segundos 75

Un colchón suave de acordes (la menor, fa, do, sol) con un pulso leve, en estéreo.
Escribe recursos/musica.wav. Al ser generada aquí, se puede usar sin restricciones de licencia.
"""
import argparse
import os

import numpy as np
import soundfile as sf

SR = 48000
TEMPO = 84  # pulsos por minuto
ACORDES = [  # notas MIDI de cada acorde, un acorde cada 4 pulsos
    [57, 60, 64, 69],  # la menor
    [53, 57, 60, 65],  # fa
    [48, 55, 60, 64],  # do
    [55, 59, 62, 67],  # sol
]


def hz(nota):
    return 440 * 2 ** ((nota - 69) / 12)


def pad(nota, dur, sr=SR):
    """Tono suave: fundamental y armónicos débiles, levemente desafinados para que respire."""
    t = np.arange(int(dur * sr)) / sr
    f = hz(nota)
    onda = sum(a * np.sin(2 * np.pi * f * k * t + k) for k, a in [(1, 1.0), (2, 0.25), (3, 0.08)])
    onda += 0.6 * np.sin(2 * np.pi * f * 1.003 * t)
    ataque = np.minimum(1, t / 0.8)
    caida = np.minimum(1, (dur - t) / 0.8)
    return onda * ataque * caida


def pulso(nota, dur, sr=SR):
    """Nota corta y apagada en cada pulso, como un piano lejano."""
    t = np.arange(int(dur * sr)) / sr
    f = hz(nota)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 5)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--segundos", type=float, default=75)
    ap.add_argument("--salida", default="recursos/musica.wav")
    args = ap.parse_args()

    pulso_s = 60 / TEMPO
    compas = 4 * pulso_s
    n = int(args.segundos * SR)
    izq, der = np.zeros(n), np.zeros(n)
    i = 0
    while i * compas < args.segundos:
        acorde = ACORDES[i % len(ACORDES)]
        ini = int(i * compas * SR)
        for k, nota in enumerate(acorde):
            s = pad(nota, compas + 0.8)
            fin = min(n, ini + len(s))
            lado = 0.35 + 0.1 * k  # cada nota en un lugar distinto del estéreo
            izq[ini:fin] += s[:fin - ini] * (1 - lado)
            der[ini:fin] += s[:fin - ini] * lado
        for b in range(4):
            ini_b = ini + int(b * pulso_s * SR)
            s = 0.5 * pulso(acorde[(b * 2) % 4] + 12, pulso_s)
            fin = min(n, ini_b + len(s))
            izq[ini_b:fin] += s[:fin - ini_b] * 0.5
            der[ini_b:fin] += s[:fin - ini_b] * 0.5
        i += 1

    audio = np.stack([izq, der], axis=1)
    t = np.arange(n) / SR
    audio *= np.minimum(1, t / 2)[:, None] * np.minimum(1, (args.segundos - t) / 3)[:, None]  # entrada y salida
    audio *= 0.5 / np.abs(audio).max()
    os.makedirs(os.path.dirname(args.salida), exist_ok=True)
    sf.write(args.salida, audio.astype(np.float32), SR)
    print(f"{args.salida}: {args.segundos:.0f} s")


if __name__ == "__main__":
    main()
