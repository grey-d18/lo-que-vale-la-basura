# Licencias

Este repositorio combina cuatro tipos de material, cada uno con su propia licencia.

## 1. Código: MIT

Los scripts de `scripts/` y el código del tablero en `artifact/index.html` se publican bajo la licencia MIT (ver `LICENSE`).

## 2. Contenido derivado de la tesis: CC BY-NC-ND 4.0

Los datos de campo, textos, hallazgos, guion y reel que provienen de la investigación de tesis de Greicy Rodriguez Coronel
(*Gestión informal de residuos sólidos y economías populares entre acopiadores-recicladores de la ciudad de Trujillo*,
Pontificia Universidad Católica del Perú) se publican bajo
[Creative Commons Atribución-NoComercial-SinDerivadas 4.0 Internacional](https://creativecommons.org/licenses/by-nc-nd/4.0/deed.es).

Esto incluye:

- `datos/originales/precios_tesis.csv`
- los textos de hallazgos, metodología y conclusiones del dashboard y del `README.md`
- el contenido de `reel/`

Se puede compartir citando la fuente, sin fines comerciales y sin modificar el contenido. Para otros usos, escribir a la autora.
La tesis no se reproduce en este repositorio: solo se usan cifras agregadas y seudónimos.

## 3. Datos de terceros: licencia de cada fuente

Los archivos descargados en `datos/originales/` y sus versiones procesadas mantienen los términos de su fuente:

| Fuente | Términos |
|---|---|
| Banco Mundial, What a Waste 3.0 y WDI | [Creative Commons Atribución 4.0](https://creativecommons.org/licenses/by/4.0/) |
| MINAM / SIGERSOL y OEFA (Plataforma Nacional de Datos Abiertos) | [Términos de la Plataforma Nacional de Datos Abiertos](https://www.datosabiertos.gob.pe/) |
| Natural Earth, países 1:110m (mapa mundial) | [Dominio público](https://www.naturalearthdata.com/about/terms-of-use/) |
| [juaneladio/peru-geojson](https://github.com/juaneladio/peru-geojson), departamentos del Perú (mapa del Perú) | [Mozilla Public License 2.0](https://www.mozilla.org/en-US/MPL/2.0/) |
| UN Comtrade | [Policy on Comtrade Data Use](https://uncomtrade.org/docs/policy-on-comtrade-data-use/). Se publican solo tablas y gráficos procesados, que la política permite sin licencia ([Re-dissemination of data](https://uncomtrade.org/docs/re-dissemination-of-data/)); el extracto crudo no se sube y se obtiene con `scripts/obtener_datos.py`. Fuente: "UN Comtrade". |

## 4. Tipografías: SIL Open Font License 1.1

El tablero (`artifact/index.html`) lleva incrustadas, en base64, tres tipografías tomadas de los paquetes de
[Fontsource](https://fontsource.org/) (solo el subconjunto latin y los pesos que se usan). Todas se distribuyen bajo la
[SIL Open Font License 1.1](https://openfontlicense.org/), que permite usarlas e incluirlas en otros trabajos citando su
licencia; no se pueden vender por sí solas.

| Tipografía | Pesos incluidos | Copyright |
|---|---|---|
| [Barlow Condensed](https://github.com/jpt/barlow) | 600 | The Barlow Project Authors (2017) |
| [Source Sans 3](https://github.com/adobe-fonts/source-sans) | 400, 600, 700 | Adobe, con nombre reservado "Source" |
| [IBM Plex Mono](https://github.com/IBM/plex) | 400 | IBM Corp. (2017) |
