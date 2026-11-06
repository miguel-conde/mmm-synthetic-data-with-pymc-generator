## 1. Resumen ejecutivo

Ciclo v1 ejecutado el 2026-11-05 en WSL2 con CPU, sobre `pymc-generator 0.0.2` (`fb9549d`). Se generaron **600 mundos** (5 escenarios × T ∈ {52, 104, 208} × 40 réplicas). Los modelos rápidos se ajustaron en los 600 mundos. PyMC-Marketing (M3) se ajustó en una submuestra común de **45 mundos** fijada a priori (réplicas 0–2) y el oracle (M4) en **5 mundos** (T=104, r0). E08/E09 se ejecutaron en 45 mundos con un motor contrafactual **validado en 45/45**. Hubo **0 ajustes fallidos** de 8 057 registrados. Salvo indicación, los errores se expresan como fracción de `media|y|` de la ventana (contribución) o de `media|y_train|` (predicción). Las comparaciones están emparejadas por mundo, con IC95 por bootstrap de mundos.

Resultados verificables (estimando, mundos y ventana indicados en cada tabla):

1. **Predecir bien no implica atribuir bien (H1, E06).** En los 600 mundos, la correlación de Spearman entre el ranking de RMSE de test y el ranking de error de contribución histórica de los modelos ciegos es **0.19** [0.14, 0.23]. El mejor predictor es también el mejor en atribución en solo el 21–34 % de los mundos, según el escenario.
2. **La regresión con adstock/saturación elegida por validación (M2) atribuye peor que OLS con canales crudos.** M2 tiene **+0.031** [0.026, 0.036] más error de contribución que M0 (600 mundos). Además asigna crédito por encima del 2 % de Σ|y| al **65 %** de los canales *feeder* (sin `C→Y`), frente al 8 % de OLS. Con las transformaciones **verdaderas** (M2p, privilegiado) el error baja a 0.047 de mediana, frente a 0.075 de OLS. El problema es la especificación seleccionada por predicción, no la idea de transformar (H6).
3. **El MMM bayesiano (M3) atribuye claramente mejor que las regresiones ciegas** en la submuestra común de 45 mundos: −0.018 [−0.023, −0.014] frente a OLS y −0.056 [−0.069, −0.043] frente a M2. No se distingue de la referencia privilegiada M2p (diferencia −0.0005 [−0.007, 0.006]). Su RMSE predictivo es similar al de los demás (mediana 0.049 frente a 0.050 de OLS y LightGBM).
4. **Las bandas de M3 están muy mal calibradas (H9).** La cobertura empírica de contribuciones es del **38 %** para una nominal del 95 % (15 % al 50 %) y la predictiva del 67 % al 95 %. No se debe a la falta de convergencia: el subconjunto que cumple el criterio piloto cubre el 30 %. Solo el 24 % de los ajustes cumple el criterio estricto (R-hat ≤ 1.01, ESS ≥ 400, 0 divergencias), y el 62 % tiene alguna divergencia. El oracle (5 mundos) cubre 97 % / 90 % / 73 % al 95 / 80 / 50 % y tiene error de contribución 0.010.
5. **XGBoost y LightGBM predicen mejor que M2** (−0.021 [−0.027, −0.015] en RMSE escalado) y de forma comparable a Ridge, pero no ofrecen un estimando causal. Usados como «plug-in» para reasignar presupuesto (política no causal etiquetada como tal), su *regret* (4.0 %) iguala al del reparto igualitario (4.1 %) (H8).
6. **Decisión (H10, E09).** Partiendo del plan actual, el óptimo verdadero mejora el valor un **6.3 %** de Σ|y|. El *regret* medio es: M2p 1.4 %, M3 2.1 %, Ridge 3.2 %, M2 3.5 %, OLS 3.6 %, árboles 4.0 %. La correlación entre RMSE predictivo y *regret* es **0.08** (315 pares mundo × modelo): el error de predicción apenas informa sobre la calidad de la decisión.
7. **Confusión latente (H3, E03).** No se detecta un deterioro de la atribución *observed-path* en S1 frente a S0 para ningún modelo ni horizonte: todos los IC95 de S1 − S0 contienen 0, excepto M2_noZ a T=52 (mejor en S1) y M3 a T=52 con N=3. Ver la interpretación en §11.
8. **Controles (H4, E04).** Quitar `Z` de M2 empeora el error en todos los escenarios. El efecto es el doble en S2 (`Z→C`, `Z→Y`): **+0.059** [0.041, 0.079], frente a +0.021…+0.037 en el resto.
9. **Intervención (E08) y halo (H7).** Para `do_zero` sobre la ventana histórica, el error de los efectos implicados por los modelos, que suponen exogeneidad, va de 0.040 (M3) a 0.092 (M2) de Σ|y|. En S3/S4, apagar un canal *feeder* reduce las ventas un 0.9–1.0 % de Σ|y| aunque su atribución *observed-path* verdadera sea 0. Ese efecto aparece atribuido al canal receptor, como predice H7.

<!-- END-SUMMARY -->

## 10. Robustez y casos extremos

- **Horizonte (H2).** Las regresiones mejoran poco con `T`: OLS pasa de 0.067 a 0.062 de mediana entre 52 y 208 semanas. M2 mejora más (0.087 → 0.075), pero su cola es pesada (media 0.107 → 0.085). M2p no mejora de forma monótona (0.040 / 0.048 / 0.036), lo que indica que el límite no es solo el tamaño muestral.
- **Correlación entre canales (H5 / E14 parcial).** En S0 la correlación media observada entre canales es baja (mediana |ρ| = 0.13) y no se asocia con el error (Spearman ≈ 0). En S3 la asociación es positiva y débil (0.06–0.22). Los presets no permiten fijar grados de correlación sin abrir rutas de confusión, así que **no hay diseño controlado de E14**.
- **Casos extremos.** Están en `reports/tables/` y en los JSON por mundo de `runs/*/results/`. Los hiperparámetros elegidos por M2 en cada mundo están en `diagnostics` del JSON correspondiente. No se ha analizado aún qué los caracteriza.

## 11. Conclusiones por estimando y supuestos

- **Atribución histórica observed-path con entradas observadas.** Mejor ciego: M3. Le siguen OLS y Ridge (prácticamente iguales; OLS es 0.003 mejor). M2 elegido por validación predictiva es el peor de los ciegos con contribución. Conocer las formas funcionales verdaderas (M2p) lleva a un error similar al de M3. Conocer además `D` (M2p_D) lo reduce algo más, sobre todo en S1 (−0.009 [−0.013, −0.006]).
- **Por qué S1 no empeora.** El estimando pertinente es la respuesta sobre el canal *tal como se observó*, que incluye el movimiento del canal inducido por `D`. Lo que la confusión puede sesgar es el **coeficiente**, si `D→Y` está correlacionado con `C` y no se modela. Con la fuerza de confusión de estos presets (`confounding_strength = 0`: la confusión actúa solo por aristas `D→C` y `D→Y`), ese sesgo es pequeño frente a otros errores (forma funcional, base). **Esto no prueba que la confusión sea inocua**; E10 debería aumentarla.
- **Predicción.** Árboles, Ridge y M3 son comparables; las referencias ingenuas son peores. La predicción no sirve para ordenar métodos por calidad de atribución ni de decisión en este banco.
- **Incertidumbre.** Los intervalos de M3 no son utilizables como medida de error de atribución sin recalibración. El oracle está cerca de la calibración nominal en 5 mundos, sin convergencia estricta.
- **Decisiones.** Ningún modelo ciego alcanza el óptimo. M3 se queda con dos tercios de la mejora posible (4.2 de 6.3 puntos). Las políticas de los modelos tocan los límites de soporte con frecuencia (65–78 % de canales en 0.5 o 1.5), así que dependen del soporte permitido.

## 12. Límites

Validez interna:
- **M4 en solo 5 mundos.** El oracle cuesta 8–15 minutos por mundo en CPU; su cola F2 de 45 mundos está en `configs/core_oracle.yaml`.
- **M3 en 45 de 600 mundos.** Los rankings que incluyen M3 usan solo esa intersección.
- **Presupuesto MCMC limitado** (4 cadenas × 1000 + 1000). Una parte de los ajustes de M3 no convergió.

Validez externa:
- **Mundos del prior por defecto de `pymc-generator`.** Los resultados describen ese prior, no datos reales.
- **No se crean datos geo-jerárquicos ni interacciones multiplicativas.** El generador es aditivo.
- **El presupuesto de E09 está en unidades de tratamiento, no en euros.**

Ver [docs/assumptions_and_limits.md](../docs/assumptions_and_limits.md).

## 13. Trabajo pendiente

- Ejecutar `configs/core_oracle.yaml` (M4 en 45 mundos).
- Recalibrar o revisar priors de M3 y repetir la cobertura.
- E10: desplazar priors (fuerza de confusión con `confounding_strength_range`, ruido, número de canales).
- Implementar un diseño controlado de E14, M7/M8 (DML/Causal Forest solo para contrastes identificables), M9 (MMM neuronal estructurado) y la variante lineal de S0 para E02.
- Cuando haya acceso a River, compararlo **en los mismos mundos y con los mismos estimandos**, usando esta tabla de rendimiento como referencia sin River.
