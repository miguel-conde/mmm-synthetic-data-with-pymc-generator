"""v1.2 P1B — scientific status table (new file; the P0 table in reports/scientific_status_v1_2.md stays frozen)."""

from __future__ import annotations

import pandas as pd

from .provenance import ROOT
from .reporting import md_table

STATES = ("confirmado (banco sintético)", "provisional", "no concluyente", "no ejecutado")


def rows(m3: dict) -> list[dict]:
    return [
        {"H": "H1", "afirmación": "Buen pronóstico de Y no garantiza recuperar contribuciones", "estado": "provisional",
         "base": "P0: coincidencia del mejor 0,31 vs 0,25 por azar; Spearman 0,17 (F2, `corrected_w8`, 4 modelos ciegos)",
         "nota": "sin cambios en P1B"},
        {"H": "H2", "afirmación": "Más semanas mejoran la recuperación sin garantizar identificación", "estado": "no concluyente",
         "base": "P0", "nota": "sin cambios"},
        {"H": "H3", "afirmación": "La confusión latente deteriora a modelos que no la representan",
         "estado": "confirmado (banco sintético)",
         "base": "E10A, 40 pares por nivel, `do_zero` y ±10 %: sesgo de M2p (privileged) solo en canales con ruta C←D→Y (−0,012 [−0,019, −0,007]); M2p_D ≈ 0; `rho` sesga también a M2p_D",
         "nota": "confirmado para los modelos privilegiados y M0; M2 ciego sin potencia con `dc`"},
        {"H": "H4", "afirmación": "Controles ayudan, pero mal ajustados sesgan", "estado": "provisional", "base": "P0", "nota": "sin cambios"},
        {"H": "H5", "afirmación": "La correlación entre canales reduce la estabilidad", "estado": "no ejecutado",
         "base": "E14: la puerta de diseño no pasa (los márgenes cambian: sd ×1,35–2,06)",
         "nota": "solo cabría como «correlación inducida por Z con cambios de distribución»; pendiente de decisión"},
        {"H": "H6", "afirmación": "Corregir la forma funcional ayuda, pero no arregla la confusión", "estado": "confirmado (banco sintético)",
         "base": "líneas base corregidas (600 mundos): M2p sesgo −0,001; E10A: M2p sigue sesgado con D→C/D→Y",
         "nota": "con transformaciones verdaderas (privileged)"},
        {"H": "H7", "afirmación": "C→C separa la atribución observada del efecto `do`", "estado": "confirmado (banco sintético)",
         "base": "P0, nivel de verdad", "nota": "sin cambios"},
        {"H": "H8", "afirmación": "Los árboles predicen igual o mejor sin validez causal", "estado": "provisional", "base": "P0", "nota": "sin cambios"},
        {"H": "H9", "afirmación": "Intervalos de modelos mal especificados infra-cubren", "estado": m3["estado"], "base": m3["base"],
         "nota": "Las conclusiones de M3 de v1/v1.1 son anteriores a la corrección del ajuste y no son válidas como evidencia"},
        {"H": "H10", "afirmación": "Mejor predictor ≠ mejor decisión", "estado": "no concluyente",
         "base": "P0; E09 corregido sin M3", "nota": "políticas de M3 no recalculadas"},
        {"H": "H11", "afirmación": "Cambios de prior degradan distinto según el método", "estado": "no ejecutado", "base": "—", "nota": "E10B no autorizado"},
        {"H": "M2", "afirmación": "La selección de formas de M2 identifica el mecanismo", "estado": "confirmado (banco sintético) que NO",
         "base": "auditoría F3: α elegido vs verdadero, Spearman 0,16; el 62 % de las formas cambia al quitar 8 filas",
         "nota": "M2 se mantiene como caso de contraste; M2v2 solo como diseño"},
        {"H": "M3-ventana", "afirmación": "El sesgo negativo de M3 en v1/v1.1 procedía de la ventana de ajuste", "estado": m3["ventana_estado"],
         "base": m3["ventana_base"], "nota": "el control A/B/C muestra que la escala no contribuye"},
    ]


def write(m3: dict) -> str:
    df = pd.DataFrame(rows(m3))
    df.to_csv(ROOT / "reports" / "v1_2" / "scientific_status_P1B.csv", index=False)
    text = f"""# Estado científico tras P1B (v1.2)

Sustituye como estado vigente a `reports/scientific_status_v1_2.md` (P0), que se conserva congelado.

Estados: {", ".join(f"«{s}»" for s in STATES)}. «Confirmado» se refiere solo a este banco sintético, con sus presets, niveles y T.

**Etiqueta histórica:** todas las cifras de M3 de v1 y v1.1 (sesgo, cobertura, V3 elegida) son **anteriores a la corrección de la ventana de ajuste** (`legacy_w0`). No deben citarse como evidencia sobre M3.

{md_table(df)}
"""
    path = ROOT / "reports" / "scientific_status_P1B.md"
    path.write_text(text)
    return str(path)
