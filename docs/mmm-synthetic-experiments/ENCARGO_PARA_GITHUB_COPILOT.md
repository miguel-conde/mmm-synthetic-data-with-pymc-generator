# Encargo a GitHub Copilot: banco experimental MMM con datos sintéticos

Dispones en este workspace de VS Code / WSL2 de `pymc-generator`, ya instalado y probado. Debes **implementar y ejecutar** el programa adjunto en `PROGRAMA_EXPERIMENTACION_MMM_PYMC_GENERATOR.md`.

## Objetivo

Construir un banco Python reproducible para comparar OLS, Ridge, regresiones con adstock/saturación, PyMC-Marketing, oracle de `pymc-generator`, XGBoost/LightGBM y, como extensiones, DML/Causal Forest y MMM neuronal estructurado. Evalúa **por separado** predicción, recuperación de contribuciones históricas, incertidumbre y, solo si validas un motor contrafactual, efectos de intervención y decisiones de presupuesto.

## Plan de trabajo imperativo

1. **Audita primero el entorno y la API instalada.** No reinstales ni rompas la biblioteca que ya funciona. Identifica funciones, datos, artefactos, priors, oracle y soporte de replay/choques. Documenta versiones y discrepancias con la documentación pública.
2. Crea las interfaces y la separación `ObservedDataset` / `TruthRegistry`. Establece los estimandos **antes de entrenar**. Los modelos ordinarios no pueden leer la verdad del SCM.
3. Implementa sanidad y reproducibilidad del generador para los cinco escenarios: `direct_only`, `confounded_treatment`, `promo_drives_treatment`, `treatment_halo`, `kitchen_sink`.
4. Implementa modelos base, métricas, cortes temporales y CLI. Ejecuta un **smoke** con 5 mundos y un **piloto** de 45 mundos (5 escenarios × 52/104/208 semanas × 3 semillas) para los modelos rápidos.
5. Integra un MMM bayesiano y el oracle, prueba primero un ajuste pequeño, registra R-hat, ESS, divergencias, tiempo y memoria. Amplía de forma prudente en CPU.
6. Integra XGBoost y LightGBM como modelos predictivos. No presentes SHAP ni la eliminación de variables como efectos causales demostrados.
7. Ejecuta una muestra común de la fase principal de 150 mundos donde el coste lo permita, y extiende a 600 para los métodos rápidos. **Los rankings entre métodos solo usarán mundos comunes**; informa `N` por comparación.
8. Comprueba si el generador permite un replay causal fiel con los **mismos parámetros e innovaciones exógenas** para ambas ramas. Prueba intervención nula, arrastre y transmisión `C→C`. Si falla, marca las pruebas de intervención y optimización como bloqueadas; nunca compares mundos aleatorios distintos como si fueran contrafactuales.
9. Genera gráficos, tablas, manifiestos, pruebas unitarias, informe técnico y un README con comandos reproducibles. Cada experimento debe quedar `completed`, `blocked`, `not_applicable` o `failed` con causa.

## Reglas técnicas críticas

- No mezcles `contributions` directas/aisladas con `contributions_observed` ni con efectos de `do`.
- El `baseline` del generador contiene ruido de observación. El oracle es *structure-known plug-in*, no la posterior causal completa.
- El generador actual es aditivo, sin interacciones multiplicativas explícitas entre tratamientos; no inventes soporte para ellas.
- No llames ROAS a una respuesta por unidad de tratamiento sin especificar euros y ventas.
- Separa evaluación histórica de pronóstico con `Y` futuro oculto; no filtres datos futuros al ajuste ni a las transformaciones.
- Para datos entre mundos usa separación por células de estructura DAG cuando entrenes modelos generales; para MMM por mundo usa ventanas temporales sin fuga.
- No lances un gran lote MCMC sin medir y registrar tiempo y RAM de un caso. Usa ejecución reanudable y conserva fallos.

Lee el documento completo antes de empezar. **Empieza ya por H0 y H1, ejecuta las pruebas disponibles y continúa por los hitos.** No te limites a describir un plan: deja código, pruebas y resultados. Si una fase no puede completarse, documenta el bloqueo y avanza con las demás. No atribuyas a River resultados producidos sin River.
