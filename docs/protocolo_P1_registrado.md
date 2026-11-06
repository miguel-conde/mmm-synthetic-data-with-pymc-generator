# Protocolo P1 registrado (v1.2) — tras la autorización del diseñador

**Registrado:** antes de cualquier ajuste MCMC de P1. Sustituye como protocolo vigente al borrador `docs/protocolo_v1_2_P1.md`, que se conserva sin cambios (congelado en `reports/v1_2/FREEZE_MANIFEST_P0.json`).
**Autorización:** `docs/RESPUESTA_AL_AGENTE_MMM_TRAS_P0_V1_2.md` (aprobación provisional de P0 basada en el resumen del agente; el diseñador no ha auditado aún los artefactos).

## 0. Estado congelado de partida

| Fase | Manifiesto | Notas |
|---|---|---|
| v1 | `reports/v1/FREEZE_MANIFEST.json` | sin cambios; fe de erratas nueva en `reports/v1/ERRATA.md` |
| v1.1 | `reports/v1_1/FREEZE_MANIFEST.json` | sin cambios; fe de erratas nueva en `reports/v1_1/ERRATA.md` |
| v1.2 P0 | `reports/v1_2/FREEZE_MANIFEST_P0.json` | informes P0, `reports/v1_2/`, `runs/v1_2_warmfit/`, configuración, borrador de protocolo y snapshot de código `reports/v1_2/code_snapshot_P0/` |

El snapshot P0 se reconstruyó revirtiendo solo los cambios de P1a en `models/bayes.py` y en un test; pasa los 87 tests de P0 (mismo número que el registrado).

## 1. D1 — Ventana de ajuste (aprobada)

- `warmup = 8` semanas, fija para todos los experimentos actuales (`carryover_burn_in` del generador). Sensibilidad 7/8, si se hace, en tabla aparte; nunca en el ranking principal.
- Entradas desde la semana 0 para el arrastre; verosimilitud y cualquier ajuste de parámetros solo con `Y` en `[8, n_train)`.
- **Uso permitido de canales en semanas 0–7:** forman el estado de arrastre de las semanas posteriores y entran en la escala de canales de M3 (`max` de cada canal sobre `[0, n_train)`, igual que antes). `Y` de esas semanas no se usa en nada.
- **Modelos rápidos:** `fit_scope: train_after_warmup` (ya implementado en P0).
- **M3:** verosimilitud enmascarada (§2). Clase estándar `pymc_marketing.mmm.MMM` 1.3.0 con una modificación controlada:
  1. `Y[0:8]` se sustituye por un marcador (media de `Y[8:n_train)`) antes de entrar al modelo;
  2. escala de `Y` = `FixedScaling(max Y[8:n_train))` con la API oficial;
  3. un `pm.Potential` resta exactamente los términos de log-verosimilitud de las semanas 0–7, construidos con `model.logp(vars=[y], sum=False)` del propio grafo.
  
  No es un modelo PyMC propio.
- Rankings: misma ventana útil y mismos mundos. Los resultados antiguos (ajuste desde la semana 0) quedan en una columna «histórica» separada.

## 2. Validación previa a MCMC (P1a, regla de interrupción)

Tests en `tests/test_p1a_masking.py`. Si alguno de 1–3 falla, no se ejecuta M3.

| Propiedad del diseñador | Test |
|---|---|
| 1. Arrastre sobre la secuencia completa | `test_adstock_uses_full_input_sequence` |
| 2. logp = suma manual solo en `[8, n_train)`; una sola verosimilitud | `test_logp_is_manual_sum_over_permitted_weeks_only`, `test_target_scale_uses_permitted_weeks_only` |
| 3. `Y[0:8]` no cambia logp ni gradiente; los canales de 0–7 sí | `test_history_y_does_not_change_logp_or_gradient`, `test_history_channels_do_change_logp` |
| 4. Referencia independiente | igualdad determinista de transformaciones (test 1) y de la densidad conjunta frente a un modelo PyMC escrito a mano (`mmm_benchmark/p1a.py::reference_model`): `test_masked_m3_equals_independent_reference`; después, MCMC de ambos en E02 lineal y en un mundo con Weibull/no lineal (ensayo) |
| 5. Contribuciones, escalas, predicción, extracción y diagnósticos | `test_masked_fit_end_to_end` (slow) |
| 6. Arquitectura | campo `architecture` en los diagnósticos de cada ajuste |

## 3. Secuencia M3 y criterios

1. **Ensayo mínimo** (`configs/v1_2_p1a_trial.yaml`, 4 mundos): `S0_direct_only_T104_r00__linear`, `S0_direct_only_T104_r01__linear` (E02), `S0_direct_only_T104_r00`, `S4_kitchen_sink_T104_r00` (Weibull). Comprobación técnica; no es evidencia.
2. **Piloto pareado** (`configs/v1_2_p1a_pilot.yaml`, 10 mundos). Selección mecánica fijada aquí: los dos primeros mundos de `runs/v1_1_m3` por escenario, en orden alfabético, que no están entre los 10 de desarrollo de V3.
   - Mundos: `S0_direct_only_T104_r00`, `S0_direct_only_T104_r01`, `S1_confounded_treatment_T104_r02`, `S1_confounded_treatment_T208_r00`, `S2_promo_drives_treatment_T104_r00`, `S2_promo_drives_treatment_T208_r00`, `S3_treatment_halo_T104_r01`, `S3_treatment_halo_T208_r00`, `S4_kitchen_sink_T104_r02`, `S4_kitchen_sink_T208_r00`.
   - Misma semilla de ajuste y mismos ajustes de muestreo que V3 (1000 + 1000, 4 cadenas, `target_accept 0.99`, `lam ~ Gamma(6, 2)`).
   - Estos mundos ya se consultaron en las auditorías de P0: el piloto **no** es una prueba independiente.
3. **Validez de un ajuste:** `R-hat ≤ 1,01`, ESS bulk ≥ 400, 0 divergencias.
4. **Ampliación** solo si el piloto cumple los diagnósticos y la propuesta se registra antes.
5. **Pregunta de la Entrega A:** «¿La corrección de la ventana explica una parte importante del sesgo negativo y la baja cobertura en directos?».
   - Métricas pareadas por mundo-canal directo: sesgo medio normalizado por media|Y| y cobertura IC95, entre V3 histórica y V3 enmascarada.
   - Se usan solo pares con **ambos** ajustes válidos. Las tablas con todos los ajustes se dan aparte.
   - **Regla fijada antes de ver resultados:**
     - **«sí»**: hay ≥ 8 mundos con ambos ajustes válidos, el sesgo medio en directos se reduce al menos a la mitad en valor absoluto y la cobertura IC95 sube al menos 0,15;
     - **«no»**: hay ≥ 8 mundos pareados válidos y ninguna de las dos condiciones se cumple;
     - **«parcial»**: en cualquier otro caso con ≥ 8 mundos pareados válidos;
     - **«no concluyente»**: hay menos de 8 mundos pareados válidos.

## 4. D2 — Efectos nulos (Entrega B, tras superar A)

- **Estimando:** contribución directa media semanal del canal en unidades de `Y`, sobre las semanas `[8, n_train)` y con las exposiciones observadas. Verdad: `contributions_observed` del generador en esas semanas.
- **Umbral:** `delta = 0,005 × media(|Y|)` sobre `[8, n_train)`.
- **Decisión** (umbral de decisión exploratorio, no cobertura ni prueba de `beta = 0`):
  - «prácticamente nulo» si `P(0 ≤ c < delta) ≥ 0,95`;
  - «efecto relevante» si `P(c ≥ delta) ≥ 0,95`;
  - «indeterminado» en otro caso.
- **Evaluación por rol** (`direct`, `feeder`, `isolated`): sensibilidad, falsos positivos, precisión, proporción de indeterminados, error de contribución; cobertura IC95 en directos; tasa de validez MCMC.
  - La verdad de «relevante» es `c_true ≥ delta`.
  - En feeders, la verdad directa es 0 aunque el efecto total `do` sea positivo.
- **Variantes**, con los mismos mundos, la misma ventana corregida y una sola modificación a la vez:
  - (a) V3 enmascarada (referencia);
  - (b) V3 con contracción continua modificada de `saturation_beta`, sin cambiar las familias;
  - (c) V3 con familias de respuesta más flexibles, sin cambiar la prior de efecto.
  
  Las combinaciones solo se prueban si (b) o (c) muestran utilidad y el coste es razonable. `spike-and-slab` queda reservada.
- **Selección de hiperparámetros:** solo con criterios disponibles para un analista (diagnósticos MCMC, predicción en validación temporal dentro del entrenamiento, comprobaciones predictivas a priori). Se usan los 10 mundos de desarrollo, nunca el error frente a la verdad. La decisión se registra antes de evaluar.
- **Confirmación fuerte (opcional):** muestra nueva con semillas registradas tras congelar las especificaciones, usada una sola vez.

## 5. Correcciones de modelos rápidos y E08/E09

Las mismas configuraciones y semillas, con `fit_scope: train_after_warmup`, se aplican a los subconjuntos F3 y E10A de v1/v1.1. No hay generación nueva. El coste y los resultados se informan aparte de los experimentos nuevos (`reports/p1_corrected_baselines.md`). Las políticas que incluyen M3 esperan al nuevo ajuste M3.

## 6. D3 — E10A y E14 (pilotos)

Los niveles exactos y el número efectivo de mundos se registran en un anexo a este documento **antes** de generar los mundos.

- **E10A** (40 pares por nivel, T = 104), un mecanismo cada vez:
  1. `dc_coeff_range` variando con `dy` fijo;
  2. `dy_coeff_range` variando con `dc` fijo;
  3. `confounding_strength_range` (rho) en `direct_only`, sin cambiar los coeficientes de `D`.
  
  `D` observable solo como control privilegiado (M2p_D). Antes de ajustar se verifica qué cantidades cambian entre niveles: parámetros, innovaciones y series.
  - **Métrica primaria (fijada aquí):** sesgo del efecto de intervención E08 (`all_channels_clamped` y por canal) frente a la verdad contrafactual de cada mundo, normalizado por media|Y|.
  - **Secundarias:** sesgo de la contribución directa, MAE de predicción, atribución.
  - No se declara potencia para M2.
- **E14** (30 pares × 3 niveles de `zc_coeff_range`, T = 104), tras E10A. Estructura con `Z→C`, sin `Z→Y`, sin `D` y sin `C→C`, verificada en el DAG de cada mundo.
  - Se mide la correlación lograda entre canales, el número de condición y el rango, tanto en entradas crudas como transformadas, y se comparan los ajustes con y sin `Z`.
  - Si los niveles no separan la correlación, el piloto se detiene y se propone una modificación registrada.

## 7. Comunicación

- «Estabilidad del mejor valor encontrado», no óptimo global.
- `all_channels_clamped_policy` es una intervención sintética del protocolo.
- Nunca «ROAS».
- Atribución histórica, efecto total de una intervención y valor de una decisión se tratan por separado.
- No se afirma que el diseñador haya auditado los artefactos.

## Anexo A — E10A registrado (antes de generar los mundos)

**Diseño.** T = 104, réplicas 0–39 (40 pares/tríos por nivel). Los niveles de cada mecanismo comparten semilla de mundo. Los niveles son fijos (rango degenerado `(v, v)`), no muestreados.

| Mecanismo | Estructura | Nivel variable | Fijo |
|---|---|---|---|
| E10A_dc | `confounded_treatment` (D→C 3 aristas, D→Y 2) | `dc_coeff_range` ∈ {0, 0,25, 0,5} | `dy_coeff_range = (0,3, 0,3)` |
| E10A_dy | `confounded_treatment` | `dy_coeff_range` ∈ {0, 0,25, 0,5} | `dc_coeff_range = (0,3, 0,3)` |
| E10A_rho | `direct_only` (sin D→C) | `confounding_strength_range` ∈ {1e-6, 0,3, 0,6} | resto del preset |

Mundos efectivos: 3 × 3 × 40 = 360. En `rho`, el nivel 1e-6 sustituye a 0, que desactiva el flujo compartido de innovaciones y rompería el pareamiento (verificado en v1.1).

**Pareamiento verificado antes de ejecutar** (réplicas 0 y 1, comparación exacta de todos los parámetros, innovaciones exógenas y series). Entre niveles de un mismo mecanismo solo cambian:
- **dc:** `w_dc`, `baseline_floor` (derivado) y las series `treatments`, `contributions_observed`, `indirect_effects*`, `outcome`;
- **dy:** `delta_dy`, `baseline_floor`, `baseline`, `latent_unobserved_contribution`, `outcome`;
- **rho:** `confounding_strength`, `baseline_floor`, `treatments`, `treatments_base`, `contributions*`, `outcome`.

El DAG (`g`) y las innovaciones exógenas (`eps_*`) son idénticos. **Al variar `rho` cambian los tratamientos realizados**, no solo la correlación con la base, así que también cambian la verdad de atribución y la contrafactual. Por eso cada mundo se evalúa con su propia verdad. Test: `test_e10a_mechanisms_are_paired`.

**Modelos.** Ciegos: M0, M1, M2, M2_noZ, M5, M6. Privilegiados, separados: M2p (transformaciones verdaderas, sin D) y M2p_D (transformaciones verdaderas + D observado como control). Ventana de ajuste `[8, n_train)`. Sin M3.

**Métrica primaria (fijada antes de ver resultados):** sesgo del efecto total de intervención `do_zero` por canal directo, `err_norm = (Δ_est − Δ_true)/Σ|Y|` sobre `[8, n_train)`.
- Primero se promedia por mundo sobre los canales directos.
- Contraste pareado: nivel alto − nivel 0 (o 1e-6) del mismo mecanismo, por modelo, con bootstrap de mundos (IC95).

**Secundarias:**
- sesgo de contribución directa (`channel_total_bias_norm`, directos, `historical_in_sample_fit`);
- MAE de contribución;
- RMSE de predicción futura;
- correlación lograda entre cada canal y la base/latente D (descriptiva, para separar correlación observada de confusión causal).

**Límites:**
- La potencia solo se declara para M2p y M2p_D, cuya variabilidad es baja según v1.1. No se promete detectar 0,005 en M2.
- No se amplía T.
- E08 se usa como estimando de intervención; la atribución no lo sustituye.

## Anexo B — E14: comprobación de diseño y propuesta registrada (sin ejecutar)

**Estructura (verificada en el DAG de cada mundo de la sonda):**
- preset `direct_only` con `edge_budget` modificado: `zc = 6`, `zy = 0`, `dc = 0`, `cc = 0`;
- se conservan `cy = 4` y `dy = 1`.

La única arista de D es D→Y. Con `dy = 0`, el generador no encuentra un DAG conexo en 2000 intentos. D→Y sin D→C es un componente no observado de la base, **no** un confusor de C→Y.

**Sonda de separación** (solo métricas de diseño; ninguna métrica causal calculada). 10 réplicas, T = 104, niveles fijos `zc_coeff_range = (v, v)`:

| v | mediana media\|corr\| entre canales | mediana máx\|corr\| | mediana nº condición (canales estandarizados) | pares con Δ media\|corr\| > 0,1 frente a v = 0 |
|---|---|---|---|---|
| 0 | 0,13 | 0,32 | 1,5 | — |
| 0,8 | 0,26 | 0,50 | 2,2 | 6/10 |
| 1,5 | 0,41 | 0,75 | 3,2 | 8/10 |
| 3,0 | 0,56 | 0,86 | 5,2 | 8/10 |

**Conclusión de la sonda:** con el rango por defecto del generador (`zc_coeff_range = (0,05, 0,3)`), los niveles **no** separarían la correlación. En la sonda, incluso v = 0,4 separa solo en parte (0,12–0,34).

**Propuesta registrada:** niveles `v ∈ {0, 1,5, 3,0}`, 30 réplicas por nivel. Antes de ajustar se exige este criterio de separación sobre los 30 pares reales:
- la mediana de la diferencia pareada de media|corr| debe ser ≥ 0,1 entre niveles consecutivos;
- al menos el 70 % de los pares debe tener Δ > 0,05.

Si no se cumple, E14 se detiene. Se medirán además el número de condición y el rango de la matriz de diseño cruda y transformada, la cuota de medios y el ruido, para controlar que la señal sea comparable. También se compararán ajustes con y sin Z.

**Estado:** no se ejecuta en esta entrega. Requiere que E10A supere sus controles, y los niveles muy por encima del rango por defecto son una modificación que conviene que el diseñador confirme.
