# Lo que vale la basura

Generación de residuos, reciclaje y circuitos informales de reciclaje: del mundo al Perú y a Trujillo.
Tarea 3 del curso Python Intermedio.

- **Dashboard:** https://claude.ai/artifact/6bTVbbocVNX5enTreJr638
- **Publicación en LinkedIn (reel):** _pendiente_

## 1. Tema y pregunta de investigación

**Tema:** la basura como problema y como recurso. Cuánta se genera, cuánta se recicla oficialmente y quiénes sostienen el reciclaje que no aparece en las cifras.

**Pregunta:** ¿Cuánto de lo que se recicla en el Perú registran las cifras oficiales, y quiénes sostienen el reciclaje que no se ve?

## 2. Descripción

Cada año se generan enormes cantidades de basura en el mundo, y gestionarlas es un desafío para los gobiernos. Pero los residuos también tienen valor: muchos materiales se recuperan, se venden y vuelven a la industria, y de ese trabajo viven muchas familias.

El dashboard recorre tres escalas:

1. **El mundo:** cuánta basura se genera, cuánta se recoge para reciclar y cuánta termina en botaderos, por país y por región (Banco Mundial, What a Waste 3.0).
2. **El Perú:** generación, valorización y disposición final por departamento entre 2019 y 2024 (MINAM–SIGERSOL), áreas degradadas por basura (OEFA) y recicladores formales e informales.
3. **Los circuitos informales:** cuánto vale cada material en el mercado internacional, cómo fluctúan sus precios y cuánto recibe quien recolecta en El Porvenir (Trujillo), frente al precio de exportación.

El tablero complementa con un análisis cuantitativo mi investigación etnográfica de tesis de licenciatura en Antropología (PUCP) sobre los circuitos informales de reciclaje en Trujillo.

Tiene 5 indicadores clave, más de 10 visualizaciones (mapas del mundo y del Perú, ranking, series, barras y comparación de precios) y 5 filtros: indicador mundial, año, departamento, indicador del Perú y material.

## 3. Fuentes y metodología

| Fuente | Qué se usa |
|---|---|
| [Banco Mundial, What a Waste 3.0](https://datacatalog.worldbank.org/search/dataset/0039597) (CC BY 4.0) | Generación, tratamiento, composición y recicladores por país; proyecciones a 2050 |
| [MINAM–SIGERSOL](https://www.datosabiertos.gob.pe/) | Generación, valorización de inorgánicos y disposición final por distrito, 2019–2024 |
| [OEFA](https://www.datosabiertos.gob.pe/) | Inventario nacional de áreas degradadas por residuos |
| [UN Comtrade](https://comtradeplus.un.org/) | Exportaciones del Perú por partida (anual, 2015–2025) y exportaciones mensuales del Japón de plástico y papel (2024–2026) |
| [Banco Mundial, Pink Sheet](https://www.worldbank.org/en/research/commodity-markets) | Precios mensuales del cobre, el aluminio y el mineral de hierro (2024–2026) |
| Banco Mundial, WDI | Tipo de cambio oficial (soles por dólar) |
| Tesis de la autora (trabajo de campo, 2026) | Precios pagados por los acopiadores en El Porvenir; solo cifras agregadas y seudónimos |

**Indicadores principales:**

- **Porcentaje valorizado:** residuos inorgánicos valorizados entre todos los residuos municipales generados. MINAM mide los orgánicos en otro dataset que no se usa aquí, así que el porcentaje es un piso.
- **Basura por persona:** residuos municipales entre la población urbana, por día.
- **Disposición final adecuada:** toneladas llevadas a rellenos sanitarios u otra infraestructura segura, entre las generadas. Los datos de 2021 repiten los de 2022, así que 2021 se trató como faltante.
- **Promedios regionales:** ponderados por las toneladas que genera cada país.
- **Precio de exportación:** valor FOB entre peso neto de lo que exportó el Perú en 2025, por partida (cobre 7404, aluminio 7602, hierro y acero 7204, papel 4707, plástico 3915, vidrio 7001).
- **Lo que recibe quien recolecta:** precio de campo en soles frente al de exportación, convertido con el tipo de cambio de 2025.

La metodología completa está al final del dashboard.

## 4. Hallazgos principales

1. **Oficialmente, el Perú casi no recicla.** En el mundo se recoge para reciclar el 18% de la basura municipal, y en América Latina el 4.8%, el promedio regional más bajo. En el Perú, en 2024 se valorizó el 1.3% de los residuos municipales (inorgánicos), y solo 283 de 1891 distritos reportaron alguna valorización.
2. **La gestión pública no llega a todas partes.** En 2024, solo el 63% de los residuos municipales llegó a un relleno sanitario u otra infraestructura segura. OEFA tiene inventariadas 2119 áreas degradadas por basura, 619 de ellas con quema. En La Libertad hay 101, 58 con quema, y no se reportó ninguna tonelada con disposición adecuada.
3. **Las cifras oficiales son bajas, pero el reciclaje no lo es.** En el Perú hay 53,000 recicladores informales frente a 13,788 trabajadores formales. Su trabajo abastece a la industria, pero el valor no se reparte por igual: por el fierro, en El Porvenir se paga entre el 15% y el 18% del precio de exportación (cifra referencial), y el reciclador de a pie, sin dónde almacenar, vende al precio del día.

## 5. Limitaciones

- Las cifras oficiales solo cuentan lo que reportan las municipalidades; el reciclaje informal no aparece.
- What a Waste compara países con datos de años distintos: es una foto, no una serie. Su «reciclaje» es lo que se recoge para reciclar, no lo que se termina reciclando.
- Las áreas degradadas de OEFA se cuentan por número de lugares, no por tamaño, y el inventario no dice cuáles siguen recibiendo basura hoy.
- Comtrade mide comercio formal, y sus precios son valor entre peso del año, no cotizaciones.
- Los precios de campo son de 2026 y de dos locales de El Porvenir. Se comparan con las exportaciones de 2025 porque Comtrade aún no publica las del Perú de 2026. El precio de exportación es de material clasificado y embalado, así que la comparación indica distancia, no margen.
- Los precios mensuales (Pink Sheet y Japón) muestran cómo se mueve el mercado internacional, no el precio de la chatarra en el Perú.

## 6. Enlaces

- Dashboard: https://claude.ai/artifact/6bTVbbocVNX5enTreJr638
- Reel en LinkedIn: _pendiente_

## 7. Cómo reproducir

Requiere Python 3.12 o superior y [uv](https://docs.astral.sh/uv/) (o pip con `requirements.txt`).

```bash
uv sync                                  # o: pip install -r requirements.txt
uv run scripts/obtener_datos.py          # descarga las fuentes en datos/originales/
uv run scripts/procesar_datos.py         # limpia y genera datos/procesados/ y web/data/
uv run scripts/preparar_artifact.py      # genera artifact/datos/ para el dashboard
```

El dashboard es `artifact/index.html`, publicado como Artifact de Claude y alimentado con los archivos de `artifact/datos/`.

**Reel** (`reel/`, en Mac con Apple Silicon, con `mlx-audio` y `mlx-whisper` instalados):

```bash
cd reel
python3 musica.py --segundos 75                        # música generada por código
python3 voz.py --voz mi_voz.m4a --voz-texto mi_voz.txt # narra guion.json con la voz clonada
python3 hacer_video.py                                 # arma salidas/reel.mp4 y reel.srt
```

La grabación de voz de la autora y los audios y videos generados con ella no se suben al repositorio. Para reproducir el reel hace falta una grabación de referencia propia. El reel se publica en LinkedIn.

```
├── scripts/            descarga, procesamiento y preparación de datos
├── datos/originales/   fuentes tal como se descargan
├── datos/procesados/   tablas limpias (CSV)
├── web/data/           los mismos datos en JSON
├── artifact/           dashboard (index.html) y sus datos
└── reel/               guion, voz, video y subtítulos
```

## 8. Uso de inteligencia artificial

- **Claude Code (Anthropic):** ayudó a escribir los scripts de descarga y procesamiento, el código del dashboard y el del reel, y a verificar las cifras con las fuentes. La pregunta, la estructura en tres escalas, los textos de introducción, hallazgos y reflexión, y el guion del reel son de la autora, que revisó cada cifra.
- **Qwen3-TTS:** narración del reel con la voz clonada de la autora, a partir de una grabación suya. El reel lo indica en pantalla.
- **Whisper:** transcripción de la narración para revisar que la voz dijera el guion completo y para sincronizar los subtítulos.
- La música del reel se generó por código (`reel/musica.py`), sin grabaciones de terceros.

## Licencia

Código bajo MIT. Contenido derivado de la tesis bajo CC BY-NC-ND 4.0. Datos de terceros según su fuente. Ver [LICENCIAS.md](LICENCIAS.md).
