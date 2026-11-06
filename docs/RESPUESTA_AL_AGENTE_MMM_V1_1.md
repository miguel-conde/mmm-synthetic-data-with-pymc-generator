# Respuesta del diseñador al informe de ejecución v1

**Proyecto:** Banco de pruebas de MMM con `pymc-generator`, sin River  
**Fecha:** 2026-11-05  
**Estado:** v1 ejecutada según el informe del agente; revisión metodológica y plan v1.1  
**Alcance de esta revisión:** basada en `reporte_al_disenador.md` y en la documentación pública del generador; aún no he auditado el código, los resultados desglosados ni las trazas.

## 1. Dictamen

El trabajo de implementación es un avance importante. Conserva todos los mundos, ajustes, resultados y versiones de v1, sin sobrescribirlos. Distingue «sin errores de ejecución» de «estimaciones estadísticamente válidas»: los ajustes con divergencias o mala convergencia no constituyen resultados inferenciales válidos por el mero hecho de terminar.

Las tres conclusiones principales (baja relación entre predicción y atribución; baja cobertura del MMM bayesiano; débil relación entre RMSE predictivo y valor de política) son **hallazgos provisionales** y deben apoyarse en auditorías de comparabilidad, diagnóstico de inferencia y estimandos.

## 2. Decisiones expresas del diseñador

### D1. Canales feeder: informar ambos estimandos

**Decisión: ambos por separado, sin mezclar métricas.**

- `historical_observed_path_response`: por definición, el canal sin arista `C→Y` tiene contribución directa observada igual a cero. Un crédito asignado por un MMM que pretende estimar contribuciones directas es falso **respecto a ese estimando**.
- `interventional_total_effect`: un canal sin arista directa puede tener efecto total distinto de cero por la ruta `C_i→C_j→Y`. Evaluarlo como cero causal sería incorrecto.
- Separar tres clases: (a) directo a `Y`, (b) feeder sin `C→Y` pero con ruta a `Y`, (c) aislado sin ninguna ruta a `Y`.
- Mantener `false_direct_attribution_rate` para (b) y (c), e incorporar `false_total_effect_rate` solo para (c). No llamar genéricamente «canal nulo» a un feeder.
- No interpretar las contribuciones históricas del receptor como asignación de crédito al origen.

### D2. Modo A: mantener train como medida principal

**Decisión: mantener las semanas de ajuste como principal análisis de atribución histórica** (`historical_in_sample_fit`), y conservar el test futuro separado (`future_conditional_on_known_CZ`). No reajustar obligatoriamente todos los modelos sobre T completas.

Para comprobar sensibilidad, se puede hacer un segundo análisis `historical_full_refit` solo con métodos rápidos en un subconjunto de mundos preseleccionado. Nunca mezclar resultados de los dos modos en una misma tabla sin etiqueta. Cuidar que los cálculos de adstock en test utilicen historia de tratamiento previa y no arranquen de cero.

### D3. Motor `do`: aceptado para investigación, con controles adicionales

**Decisión: se acepta la implementación que usa funciones privadas, únicamente con el commit y el entorno fijados. No hay que esperar a una API oficial.**

Antes de declarar resultados E08/E09 como validados:

1. Incorporar pruebas con las distintas familias de arrastre y saturación y con distintas topologías, en especial `C→C` con feeders.
2. Contrastar al menos dos rutas de cálculo independientes en casos pequeños: fórmula analítica o simulación controlada frente a motor `do`, sin duplicar literalmente toda la implementación.
3. Comprobar intervenciones múltiples, pulsos, memoria y límites de la ventana, choques fijados si están disponibles y ausencia de cambios en las innovaciones exógenas compartidas.
4. Guardar los hashes de código y generador; ejecutar pruebas de regresión tras toda actualización de versión.
5. Etiquetar las cifras `counterfactual_engine=research_validated_private_api` y describir sus límites.

### D4. Inferencia MCMC: criterios y cobertura

**Decisión: el criterio estricto es vinculante para inferencias finales**: todas las variables relevantes con R-hat ≤ 1,01, ESS bulk ≥ 400 y cero divergencias. Los resultados que no cumplan se conservan, marcados `nonconverged`; no se presentan como inferencia validada. El criterio piloto solo sirve para exploración.

- La muestra inicial de cuatro cadenas × (1.000 ajuste + 1.000 posteriores) es un punto de partida, no una garantía de éxito.
- Antes de aumentar muestras masivamente, diagnosticar 5–10 casos fallidos de M3: divergencias, pares de parámetros, geometría posterior, priors, identifiabilidad, parámetros de adstock y saturación, divergencias por mecanismo y `target_accept`.
- Probar, con el mismo subconjunto, `target_accept` 0,95 / 0,99 y mejoras de parametrización/prior justificadas. No seleccionar el ajuste favorable usando la verdad causal del mundo.
- Informar por separado: (i) porcentaje de ajustes válidos sobre todos los intentados; (ii) cobertura condicional entre los válidos; (iii) sensibilidad descriptiva de cobertura entre los no válidos, **con aviso de que no es cobertura inferencial fiable**.
- No ocultar los no convergidos ni calcular una «cobertura global» que equivalga a tratarlos como si fueran válidos. Señalar el sesgo de selección de evaluar solo los convergidos.
- No presentar todavía a M3 como ganador definitivo, ni el 38 % como una propiedad universal del método. Examinar calibración, desajuste de priors y coherencia del estimando en el mismo subconjunto.

### D5. E09: conservar el plan completo, añadir política de propagación

**Decisión: se conserva la política v1 de multiplicadores constantes [0,5; 1,5] y presupuesto fijo en unidades de tratamiento como ejercicio principal y reproducible.** Se debe llamar `all_channels_clamped_policy` y no simular que representa un presupuesto monetario real.

Una intervención que fija todos los canales corta las aristas `C→C` entre canales intervenidos. Por tanto, su efecto no es el mismo que el `do` de un canal que deja reaccionar a sus descendientes. Añadir, como análisis de sensibilidad, `selected_channels_do_policy`: el agente modifica solo los canales accionables y deja que los demás reaccionen siguiendo el SCM. En esta variante recalcular el coste **sobre todos los tratamientos realizados**, ya que los descendientes pueden consumir recursos y cambiar el presupuesto efectivo.

Todas las políticas competidoras (observada, uniforme, aleatoria, sugerida por modelos y óptima verdadera) deben respetar idéntico espacio factible y horizonte. Reportar la pérdida respecto al óptimo y las restricciones. No llamar ROAS al resultado: las unidades de tratamiento no son euros.

### D6. Confusión: sí, máxima prioridad, con un cambio sustancial de diseño

**Decisión: priorizar una extensión experimental sobre confusión, pero no interpretar `confounding_strength=0` como ausencia de confusión en S1.**

La documentación de `pymc-generator` indica que `confounding_strength_range` regula una correlación `rho` entre innovaciones de tratamientos y de la base. Por otro lado, S1 ya incorpora un confusor estructural no observado `D→C` y `D→Y`, aunque `rho=0`.

Crear dos factores diferenciados:

- **Confusión estructural `D`**: estudiar ausencia/presencia y fuerza de `D→C` y `D→Y` mediante configuraciones que mantengan comparables los demás mecanismos. Medir efectos verdaderos mediante `do`, sesgo y cambios al añadir la variante privilegiada que observa `D`.
- **Innovaciones compartidas con la base (`rho`)**: niveles de prueba 0, 0,3, 0,6 (comprobar en API instalada). Variar `rho` manteniendo fija, cuando sea viable, la estructura del DAG; no asignar su efecto a `D`.

Cuando sea posible, usar mundos pareados con la misma estructura, parámetros no manipulados e innovaciones. Si la API no lo facilita, crear grupos de mundos estratificados y describir las diferencias no controladas. La comparación S1 frente a S0 **no** constituye por sí sola un experimento que aísle la intensidad de confusión.

Dividir E10 en `E10A_confusores_y_choques_compartidos` y `E10B_distribution_shift`. La segunda requiere comparar distribuciones de desarrollo y evaluación distintas; cambiar un parámetro generador sin ese diseño no basta para demostrar generalización fuera de distribución.

### D7. Oracle: no lanzar ahora los 45 ajustes

**Decisión: posponer la cola costosa de M4.** Cinco casos no bastan como referencia estadística global, pero ejecutar 45 ajustes con convergencia estricta del 0 % tampoco es útil.

Diagnosticar primero 3–5 casos de M4 representativos, revisar geometría y parametrizaciones y probar la representación latente alternativa si procede. Solo ampliar a una muestra estratificada de 10–15 mundos si las pruebas de inferencia muestran una mejora clara y caben en el presupuesto del equipo. Mantener M4 como referencia con estructura conocida, **no** como límite universal de error ni como verdad causal.

## 3. Correcciones adicionales

1. **Arrastre inicial:** aceptar la exclusión conservadora de las primeras ocho semanas en v1. Registrar además `response_warmup_weeks` del mundo y repetir las métricas principales con la exclusión mínima válida por mundo. La documentación del generador expone ese campo; ocho semanas pueden excluir más datos de los necesarios.
2. **Caso lineal S0/E02:** revisar `make_scm_prior(..., nonlinearity="linear")`, documentado en la guía del corpus. Comprobar por separado que el arrastre sea `none` si se desea un verdadero control sin memoria; no asumir que la opción `linear` elimina el arrastre. Crear una muestra de control mínima.
3. **Resultados con distinto número de mundos:** comparaciones M3 vs otros solo sobre los 45 mundos compartidos y con los mismos tramos temporales, no contra estadísticas globales de los 600. Las conclusiones principales deben mostrar `n_worlds`, `n_models`, escenarios y tamaños de muestra por celda.
4. **Dependencia estadística:** para cada comparación usar diferencias por mundo y remuestreo de mundos, y por célula DAG si distintas réplicas comparten estructura. La correlación entre RMSE y pérdida de decisión debe analizarse también *dentro de cada mundo* (o con un modelo que tenga en cuenta la agrupación); los 315 pares mundo-modelo no son 315 observaciones independientes.
5. **Resultado M2 peor que OLS:** comprobar cómo se eligieron arrastre y saturación, qué presupuesto de ajuste tuvo cada método y si se optimizaron hiperparámetros usando solo validación temporal. Mostrar el gap M2/M2p sin incluir M2p en el ranking justo.
6. **Controles `Z`:** no generalizar que «incluir todos los controles ayuda». Clasificarlos según el DAG y el estimando, y contrastar casos con causa común, mediador y variable descendiente.
7. **Prueba de contaminación de datos:** verificar que los modelos ciegos no reciben parámetros del SCM, `D`, máscaras de verdad ni contribuciones verdaderas, tampoco de forma indirecta en selección de hiperparámetros.
8. **Tasa de acierto del mejor predictor:** comparar el 21–34 % con el azar `1/N_métodos` para el conjunto concreto de métodos evaluados y desglosar por escenario.
9. **Terminología:** no confundir cobertura de intervalos posteriores de contribuciones, intervalos predictivos de ventas e intervalos de efectos de intervención. Indicar por cada uno qué fuentes de incertidumbre incluyen.
10. **Ciclo de resultados:** no sobrescribir v1 ni elegir retrospectivamente mundos favorables para demostrar las conclusiones. Registrar las decisiones de v1.1 antes de ejecutar nuevos experimentos.

## 4. Prioridades de ejecución

### P0. Auditoría y resultados sólidos (antes de ampliar)

- Congelar y versionar v1, incluidos los 600 mundos, los diagnósticos y los 8.057 registros.
- Preparar un paquete de revisión con `reports/benchmark_report.md`, `docs/generator_audit.md`, `docs/estimands.md`, `docs/methods.md`, `docs/assumptions_and_limits.md`, configuraciones, hashes, un extracto de métricas por mundo y diagnósticos M3/M4.
- Verificar motor `do` con pruebas independientes adicionales.
- Rehacer tablas de comparación pareada y figuras con N exacto, estimando y ventana.
- Diagnosticar convergencia de M3 y emitir un informe específico de calidad de inferencia.
- Corregir estimandos de feeders y etiquetas de E09.

### P1. Pruebas específicas nuevas

- Control lineal/identidad E02.
- E10A: confusión estructural y rho por separado, con un piloto estratificado pequeño.
- Sensibilidad E09 con `selected_channels_do_policy` cuando el motor esté validado para esa política.

### P2. Después de P0 y P1

- E10B: cambio de distribución predefinido.
- E11: DML / Causal Forest solo para contrastes identificables según el DAG, con ajuste por bloques temporales.
- E12: red neuronal estructurada si existe una pregunta concreta que no resuelvan los métodos ya incluidos.
- Oracle ampliado solo si los diagnósticos de convergencia justifican el coste.

## 5. Entregables exigidos al agente

1. `docs/revision_v1_1.md`: qué se ha cambiado y por qué, enlazando hallazgos v1 y decisiones D1–D7.
2. `reports/quality_gate_v1_1.md`: auditoría del motor `do`, fuga de información, máscaras temporales, comparabilidad y calidad de MCMC.
3. `reports/benchmark_report_v1_1.md`: resultados v1 revisados con cifras correctas, límites y estatus de cada conclusión.
4. `reports/mcmc_diagnostics.md`: cuadros por modelo y escenario, divergencias, R-hat, ESS, cobertura condicional y tasa de inferencia válida.
5. `configs/` y `runs/`: nuevos experimentos etiquetados como v1.1, sin sobrescribir v1; trazabilidad completa por mundo.
6. Una respuesta al diseñador con: decisiones aplicadas, cambios de cifras respecto de v1, anomalías aún abiertas, tiempos de cómputo y una nueva propuesta de experimentación v2.

**Condición de cierre:** ninguna conclusión debe presentarse como definitiva sin informar el estimando que evalúa, los mundos comparados, la validez del ajuste y las limitaciones del contrafactual.

## Referencias públicas contrastadas

- Generador y límites: https://github.com/pymc-labs/pymc-generator
- Escenarios, incluidos `D→C` y `D→Y`: https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/scenarios.md
- Configuración de `confounding_strength_range` y shocks: https://github.com/pymc-labs/pymc-generator/blob/main/docs/reference/config.md
- Metadatos `response_warmup_weeks` y modo lineal: https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/corpus.md
- Alcance del oracle: https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/oracle.md

**Precaución sobre versiones:** verificar todas las opciones en el commit local `fb9549d`; las páginas públicas pueden haber cambiado después de fijar ese commit.
