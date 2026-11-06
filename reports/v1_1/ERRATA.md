# Fe de erratas v1.1 (añadida en v1.2 P1; no modifica artefactos congelados)

**Defecto de inicialización del arrastre.** v1.1 heredó el defecto de v1: los modelos se ajustaron desde la semana 0 aunque el generador tiene 8 semanas de historia previa no observada. Ver `reports/v1/ERRATA.md` y `reports/scientific_status_v1_2.md` §2.

**Alcance específico de v1.1:**
- D4 (selección de V3) y la cobertura de M3 V3 en directos (0,40) se obtuvieron con la ventana contaminada. No deben presentarse como conclusiones definitivas sobre sesgo o cobertura.
- H9 pasó a `inconclusive` en P0.
- E02 lineal, E10A y `historical_full_refit` usan ajustes desde la semana 0.

**Corrección:** v1.2 P0 (modelos rápidos) y v1.2 P1a (M3 enmascarado). Los resultados corregidos se presentan en informes nuevos, junto a una columna histórica separada con los antiguos.

Los ficheros de v1.1 siguen intactos (`reports/v1_1/FREEZE_MANIFEST.json`).
