# Fe de erratas v1 (añadida en v1.2 P1; no modifica artefactos congelados)

**Defecto de inicialización del arrastre.** El generador simula 8 semanas de historia previa (`carryover_burn_in = 8`) que no se guardan. En v1, todos los modelos se **ajustaron** desde la semana 0, donde su adstock arranca sin historia. La evaluación sí excluía esas semanas. El resultado es un sesgo negativo sistemático de los coeficientes de medios en los modelos con arrastre o transformaciones verdaderas. Demostración: `reports/scientific_status_v1_2.md` §2; tabla `reports/v1_2/fit_window_correction.csv`.

**Alcance:**
- Las cifras de atribución y contribución de M2, M2p y M3 en v1 están afectadas.
- M0/M1 cambian poco al corregir la ventana.
- Las conclusiones sobre sesgo, cobertura y capacidad de decisión de M3 no son definitivas.
- E08/E09 de v1 usan modelos ajustados desde la semana 0.

**Corrección:** v1.2 P0 (modelos rápidos, `runs/v1_2_warmfit`) y v1.2 P1a (M3 con verosimilitud enmascarada). Ver `docs/protocolo_P1_registrado.md`.

Los ficheros de v1 siguen intactos (`reports/v1/FREEZE_MANIFEST.json`).
