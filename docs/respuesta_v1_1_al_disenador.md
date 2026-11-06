# Respuesta al diseñador — revisión v1.1

**Fecha:** 2026-11-05 · **Responde a:** [RESPUESTA_AL_AGENTE_MMM_V1_1.md](RESPUESTA_AL_AGENTE_MMM_V1_1.md)

**Entregables:**
- [revision_v1_1.md](revision_v1_1.md): registro previo, escrito antes de ejecutar.
- [../reports/quality_gate_v1_1.md](../reports/quality_gate_v1_1.md)
- [../reports/benchmark_report_v1_1.md](../reports/benchmark_report_v1_1.md): incluye el estado de cada conclusión.
- [../reports/mcmc_diagnostics.md](../reports/mcmc_diagnostics.md)
- Configuraciones `configs/v1_1_*.yaml` y runs `runs/v1_1_*`.

**v1 congelada:** `reports/v1/`, con el SHA-256 de 18 233 artefactos en `FREEZE_MANIFEST.json`. No se ha modificado.

## 1. Decisiones aplicadas

| Decisión | Aplicación | Estado |
|---|---|---|
| D1 feeders | Clases `direct` / `feeder` / `isolated`. Métricas `false_direct_attribution_rate` (feeder + aislado) y `false_total_effect_rate` (solo aislado, vía `do_zero`). Efecto total verdadero frente al implicado para feeders. | aplicada |
| D2 Modo A | Etiquetas `historical_in_sample_fit` / `prediction_future_conditional_on_known_CZ` / `attribution_future_conditional_on_known_CZ`. Sensibilidad `historical_full_refit` (45 mundos, modelos rápidos), en tabla separada. El adstock de test usa la historia previa (verificado en código). | aplicada |
| D3 motor `do` | Etiqueta `research_validated_private_api` en E08/E09. Pruebas nuevas: ruta analítica independiente para `C→C` (error ≤ 1e-12), intervenciones múltiples, pulsos en los bordes, mundo con choques, innovaciones sin cambios. Validado en todos los mundos causales de v1 y v1.1, incluidos los de E02 lineal y E10A. | aplicada; límite: API privada |
| D4 MCMC | Criterio estricto vinculante. Diagnóstico de 10 casos fallidos: arista `log lam`–`log beta` con correlación de 0,75 a 0,99. Variantes `target_accept` 0,95 / 0,99 y una prior registrada antes de ejecutarla (V3). Selección sin usar la verdad. Cobertura en tres bloques. | aplicada |
| D5 E09 | Renombrada `all_channels_clamped_policy`. Añadidas `random_feasible` y `selected_channels_do_policy`, esta con presupuesto sobre todos los tratamientos realizados y una comparación con presupuesto igualado (ver §3). | aplicada |
| D6 confusión | E10A con dos factores separados y mundos **pareados** (misma semilla ⇒ mismo DAG, mismos parámetros salvo el manipulado, mismas innovaciones; verificado por test). E10B aplazada a v2. | piloto ejecutado |
| D7 oracle | Diagnóstico de 3 casos con 2 variantes. No converge ninguno; no se amplía. | aplicada |
| Corr. 1 | `response_warmup_weeks` por mundo (regla del generador; un test comprueba que es la exclusión mínima válida). Re-puntuación de los 8 057 resultados v1 sin reajustar: cambios < 1e-3. | aplicada |
| Corr. 2 | `nonlinearity="linear"` en `fb9549d` da arrastre `none` **y** saturación identidad. Control E02 de 30 mundos. | aplicada |
| Corr. 3–4 | `n_worlds` en todas las tablas. M3 solo en sus 45 mundos. Bootstrap por mundo y por célula DAG. S0 tiene **una sola** célula, así que el remuestreo por célula no se aplica dentro de S0. | aplicada |
| Corr. 5–6 | Diagnóstico de la búsqueda de M2. Clases de `Z` según el DAG. | aplicada |
| Corr. 7 | Tests de contaminación y revisión de código (quality gate §3). | aplicada |
| Corr. 8 | Tasa de acierto frente a 1/N. | aplicada; cambia la lectura (§2) |
| Corr. 9 | Tabla de tipos de intervalo (§4). | aplicada |
| Corr. 10 | Registro previo antes de cada experimento, incluida V3. | aplicada |

## 2. Cambios de cifras respecto de v1

| Cifra | v1 | v1.1 | Motivo |
|---|---|---|---|
| Canales aislados en falsas atribuciones | ausentes | 194 canal-mundo; OLS 14 %, M2 67 %, M3 20 % | **Error de v1**: `pd.read_csv` leía el rol `"null"` como NaN |
| «Mejor predictor = mejor atribuidor» | 21–34 % | 26,7 % [23 %; 30 %] **frente a 25 % de azar** | Comparación con el azar (corr. 8) |
| RMSE frente a *regret* | 0,076 (315 pares) | 0,095 [−0,05; 0,23] dentro de cada mundo | Dependencia (corr. 4) |
| Convergencia estricta de M3 | 24 % | 69 % (V3) | D4 |
| Cobertura 95 % de M3 | 38 % global | 33 % en válidos (V3); 0 % en feeders/aislados; 50 % descriptiva en no válidos | D4; la causa es de especificación |
| Error de contribución de M3 | 0,040 | 0,039 (diferencia −0,0001 [−0,0011; 0,0010]) | V3 no cambia la estimación puntual |
| Exclusión inicial | 8 semanas | 7 en 587 de 600 mundos; métricas sin cambio | Corr. 1 |

## 3. Anomalías abiertas

1. **Cobertura de M3.** La infra-cobertura persiste con convergencia estricta. Combina dos cosas: (a) la prior `HalfNormal` sobre `beta` no admite efecto nulo, así que la cobertura es 0 en canales sin `C→Y`; (b) el error de los canales directos es casi todo sesgo constante por canal. Propuesta para v2: priors que admitan efecto nulo y familias más flexibles.
2. **S2 en M3.** Solo el 22 % de los ajustes converge con V3; es el peor escenario.
3. **Oracle.** 0 de 8 ajustes con convergencia estricta, con R-hat de hasta 1,11 en `sampled`. Hace falta revisar con PyMC Labs su parametrización o sus priors antes de usarlo como referencia estadística.
4. **Presupuesto en `selected_channels_do_policy`.** Las políticas de los modelos (que suponen exogeneidad) se desvían del presupuesto realizado un 1,3–1,6 % en valor absoluto medio (sesgo medio +0,1 % a +0,3 %), porque los descendientes reaccionan. Sin igualar, 17 de las 90 políticas de modelo superan al óptimo verdadero gastando más (*regret* negativo). Reescaladas al presupuesto realizado (con el motor verdadero, etiquetado), ninguna lo supera y el orden de los modelos se mantiene. **Las cifras comparables son las igualadas.**
5. **Potencia de E10A.** Con 10 pares por nivel solo se detectan efectos ≳ 0,005–0,02. El efecto de `rho` sobre M2 queda en el límite.
6. **Motor `do` frágil a versiones.** Depende de API privada. Cualquier actualización del generador obliga a re-ejecutar `pytest -q`.

## 4. Tipos de intervalo (corr. 9)

| Intervalo | Modelo | Fuentes de incertidumbre incluidas | Excluidas |
|---|---|---|---|
| Contribución por canal-semana (posterior) | M3, M4 | parámetros, dentro de la forma funcional del modelo | forma funcional, estructura DAG, ruido de observación |
| Predictivo de ventas en test | M3 | parámetros + ruido de observación | forma funcional, estructura, futuro de `C`/`Z` (se condiciona) |
| Efecto de intervención | ninguno | — | no se calculan intervalos de `do` en v1/v1.1 |
| IC95 de comparaciones | todos | variación entre mundos (o células DAG) | es frecuentista; no es un intervalo creíble |

## 5. Tiempos de cómputo

Ejecutado el 2026-11-05 entre las 20:55 y las 22:55 en WSL2, 14 CPU, hasta 3 cadenas en paralelo, sin fallos.

| Ejecución | Ajustes | Coste por ajuste |
|---|---|---|
| Diagnóstico M3 (10 mundos × 4 variantes) | 40 | 17–29 s sin competencia (V0–V2); 74–116 s V3 con competencia |
| M3 V3 en los 45 mundos | 45 | mediana 70 s |
| Oracle | 6 | `marginal` 14–27 min; `sampled` 1,5–2 min |
| E02, `full_refit`, E10A | 300 + 180 + 480 | modelos rápidos, < 1 h en total |
| E09 v1.1 (45 mundos, M3 incluido) | — | ≈ 45 min |
| Re-puntuación de v1 | 8 057 resultados | ≈ 1 min |

## 6. Propuesta v2

1. **M3 bien especificado para nulos:** prior *spike-and-slab* o *horseshoe* sobre `beta`; familias de arrastre Weibull y saturación Hill. Medir la cobertura en válidos frente a V3 en los mismos 45 mundos y la tasa de falsos positivos en feeders/aislados.
2. **E10A con más potencia:** 40 pares por nivel y T ∈ {52, 104, 208}. Añadir `dy_coeff_range` para separar `D→Y` de `D→C`, y un nivel `D` observable (M2p_D) como control.
3. **E10B:** cambio de distribución pre-definido. Elegir hiperparámetros en un prior (p. ej. `nonlinearity="diverse"`, T=104) y evaluar en otro (familias desplazadas, `rho` > 0, más canales), con desarrollo y evaluación separados por célula DAG.
4. **E14 controlado:** correlación entre canales inducida por un `Z` observado (`zc_coeff_range`) con `zy = 0` y sin `D→C`. Verificar el DAG mundo a mundo.
5. **Oracle:** solo si una revisión de parametrización con PyMC Labs logra convergencia en 3–5 casos.
6. **E11 (DML/Causal Forest):** solo para contrastes `do_zero` de canales en S0/S2, identificables con `Z` observado, con validación en bloques temporales.
7. **Robustez del motor `do`:** pedir a PyMC Labs una API `do` pública. Mientras tanto, mantener las pruebas de regresión.
