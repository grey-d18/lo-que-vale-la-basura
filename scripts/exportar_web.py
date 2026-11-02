"""Genera web/index.html: el tablero como página independiente, para publicarlo en GitHub Pages.

El Artifact de Claude solo muestra sus datos a quien inició sesión en Claude. Esta versión
lleva los datos de artifact/datos/ dentro de la página y reemplaza las pocas funciones del
Artifact que usa el tablero (dash.data, dash.draw, dash.calc, filtros), así que se abre sin cuenta.

Uso: uv run scripts/exportar_web.py   (después de preparar_artifact.py)
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARTIFACT = RAIZ / "artifact"
WEB = RAIZ / "web"

D3 = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"

# Valores de diseño que el Artifact pone por su cuenta (sistema de diseño del tipo Dashboard)
TOKENS = """
:root {
  --cds-pad-xs: .375rem; --cds-pad-sm: .5rem; --cds-pad-md: .75rem; --cds-pad-lg: 1rem; --cds-pad-xl: 1.5rem;
  --cds-gap-sm: .75rem; --cds-gap-md: 1rem; --cds-gap-lg: 1.75rem; --cds-gap-xl: 2.5rem;
  --cds-radius: .375rem; --cds-dur-slow: .45s; --cds-font-weight-medium: 500;
  --cds-font-size-body: .875rem; --cds-font-size-caption: .75rem; --cds-font-size-heading: .9375rem;
  --cds-border: rgb(0 0 0 / 0.08); --cds-text-secondary: rgb(0 0 0 / 0.6);
  --cds-surface-popover: #ffffff; --cds-shadow-popover: 0 8px 24px #0000001f, 0 2px 6px #00000014;
}
@media (prefers-color-scheme: dark) {
  :root {
    --cds-border: rgb(255 255 255 / 0.08); --cds-text-secondary: rgb(255 255 255 / 0.57);
    --cds-surface-popover: #303030; --cds-shadow-popover: 0 8px 24px #00000052, 0 2px 6px #0003;
  }
}
body { margin: 0; }
"""

# Lo mínimo del Artifact que usa el tablero
DASH = """
const dash = (() => {
  const datos = {};
  for (const [id, filas] of Object.entries(DATOS)) datos[id] = { status: 'ok', data: filas };
  const calcs = [], dibujos = {}, avisos = [];
  let params = {};
  try { params = Object.fromEntries(new URLSearchParams(location.search)); if (params.anio) params.anio = Number(params.anio); } catch (e) {}
  let pendiente = false;
  function dibujar() {
    pendiente = false;
    for (const c of calcs) datos[c.id] = { status: 'ok', data: c.fn(...c.inputs.map((i) => datos[i].data)) };
    for (const [nombre, fn] of Object.entries(dibujos)) {
      document.querySelectorAll(`[data-draw="${nombre}"]`).forEach((el) => {
        el.classList.remove('dash-skeleton');
        try { fn(el); } catch (e) { console.error(nombre, e); }
      });
    }
    avisos.forEach((fn) => fn());
  }
  function programar() { if (!pendiente) { pendiente = true; requestAnimationFrame(dibujar); } }
  return {
    data: (id) => datos[id] ?? { status: 'loading', data: [] },
    calc: (id, def) => { calcs.push({ id, ...def }); programar(); },
    draw: (nombre, fn) => { dibujos[nombre] = fn; programar(); },
    onData: (fn) => { avisos.push(fn); programar(); },
    params: () => ({ ...params }),
    setParams: (cambios) => {
      params = { ...params, ...cambios };
      try { history.replaceState(null, '', '?' + new URLSearchParams(params) + location.hash); } catch (e) {}
      programar();
    },
    setLink: (id) => { try { history.replaceState(null, '', '#' + id); } catch (e) {} },
  };
})();
"""


def main():
    pagina = (ARTIFACT / "index.html").read_text(encoding="utf-8")
    pagina = pagina.replace('<meta name="dash-one-writer">\n', "")
    datos = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ARTIFACT / "datos").glob("*.json"))}
    datos_js = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    cabecera = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lo que vale la basura</title>
<meta name="description" content="Generación de residuos, reciclaje y circuitos informales de reciclaje: del mundo al Perú y a Trujillo.">
<style>{TOKENS}</style>
<script src="{D3}"></script>
<script>
const DATOS = {datos_js};
{DASH}
</script>
</head>
<body>
"""
    WEB.mkdir(exist_ok=True)
    (WEB / "index.html").write_text(cabecera + pagina + "\n</body>\n</html>\n", encoding="utf-8")
    (WEB / ".nojekyll").write_text("")
    print(f"web/index.html · {(WEB / 'index.html').stat().st_size / 1e6:.2f} MB · {len(datos)} tablas")


if __name__ == "__main__":
    main()
