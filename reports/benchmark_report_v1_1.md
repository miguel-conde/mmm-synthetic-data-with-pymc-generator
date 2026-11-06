# Informe del banco MMM — revisión v1.1

> Generado por `python -m mmm_benchmark.cli revise`. v1 congelada en `reports/v1/` (no modificada).
> Decisiones aplicadas: [docs/revision_v1_1.md](../docs/revision_v1_1.md). Calidad: [quality_gate_v1_1.md](quality_gate_v1_1.md). MCMC: [mcmc_diagnostics.md](mcmc_diagnostics.md).
> Ningún resultado procede de River. Unidad de repetición: mundo. Etiquetas de tarea v1.1: `historical_in_sample_fit`, `prediction_future_conditional_on_known_CZ`, `attribution_future_conditional_on_known_CZ`, `historical_full_refit`.

## 0. Estado de las conclusiones (condición de cierre del diseñador)

Cada fila indica el estimando, los mundos, la validez del ajuste y el límite del contrafactual. Estados: **sostenida** (resiste las correcciones v1.1), **matizada** (se mantiene con cambios de alcance o cifra), **revisada** (cambia de sentido o deja de sostenerse), **abierta** (sin evidencia suficiente).

| # | Conclusión v1 | Estado v1.1 | Evidencia v1.1 (estimando · mundos · validez) |
|---|---|---|---|
| 1 | «Predecir bien no implica atribuir bien» | **sostenida, reformulada** | `historical_in_sample_fit` frente a `prediction_future_conditional_on_known_CZ`, 600 mundos, 4 modelos ciegos rápidos: el mejor predictor es el mejor atribuidor en el **26,7 % [23 %, 30 %]** de los mundos, frente al **25 %** esperable por azar; Spearman medio 0,18 [0,13; 0,23]. El ranking predictivo **no informa** sobre el de atribución más allá del azar. |
| 2 | M2 (adstock/saturación por validación) atribuye peor que OLS | **sostenida y reforzada** | Mismo resultado en el control lineal E02 (30 mundos, OLS bien especificado): M2 +0,095 [0,065; 0,127]. En los 45 mundos F2, reajustar M2 con todas las T semanas lo mejora (−0,019 [−0,037; 0,000]) sin cerrar la brecha. Ningún paso de M2 usa la verdad; elige saturación «lineal» casi igual de a menudo si la verdad es lineal (53 %) que si no (28–43 %): la selección por RMSE predictivo apenas reconoce la forma verdadera. |
| 3 | M3 es el mejor modelo ciego en atribución | **matizada** | Solo en la submuestra común de 45 mundos (3 por celda): −0,018 [−0,023; −0,014] frente a OLS (IC por células DAG: [−0,023; −0,013]). Con la variante V3 la convergencia estricta pasa de 24 % a 69 % y el error no cambia (−0,0001 [−0,0011; 0,0010]). No es un «ganador» general: un tercio de los ajustes sigue sin validez estricta y sus intervalos están mal calibrados (fila 4). En el control lineal E02 (9 mundos), M3 V3 es **peor** que OLS bien especificado (+0,008 [0,007; 0,009]): su ventaja depende de que la verdad sea no lineal. |
| 4 | Intervalos de M3 infra-cubren (38 % al 95 %) | **revisada en su causa** | Cobertura 95 % entre ajustes **válidos**: 0,33 (V3, 31 mundos). Por canal: directos 0,40; feeders y aislados **0,00** por construcción (prior positiva). El error de los directos es casi todo sesgo constante (\|sesgo\| / MAE = 0,99). Es un problema de **especificación**, no de convergencia (ver [mcmc_diagnostics.md](mcmc_diagnostics.md) §7). |
| 5 | Mejor predicción ≠ mejor decisión (H10) | **sostenida, cifra corregida** | Correlación RMSE–*regret* **dentro de cada mundo**: 0,095 [−0,049; 0,231] (45 mundos); v1 trataba 315 pares como independientes. `all_channels_clamped_policy`: *regret* M2p 1,4 %, M3 2,1 %, Ridge 3,2 %, árboles 4,0 %, aleatoria 6,9 %. `selected_channels_do_policy` (18 mundos con `C→C`, presupuesto realizado igualado): M2p 0,9 %, M3 1,3 %, M2 2,5 %, Ridge 3,8 %, OLS 4,1 %. Contrafactual: `research_validated_private_api`. |
| 6 | La confusión latente no deteriora la atribución observed-path (H3) | **sostenida en el rango probado** | E10A pareado (10 pares por nivel, T=104): ni la fuerza `D→C` (0 / 0,25 / 0,5) ni `rho` (≈0 / 0,3 / 0,6) cambian de forma detectable el error de OLS, Ridge o M2p, ni su error en `do_zero`. M2 empeora con `rho` (+0,021, IC con 0 en el límite). Con 10 pares por nivel, el diseño solo detecta efectos ≳ 0,005–0,02. No demuestra inocuidad fuera de los rangos del generador. |
| 7 | Quitar controles empeora M2, sobre todo en S2 | **matizada** | S2 (todos los mundos con causa común `Z→C`, `Z→Y`): +0,059 [0,041; 0,079]. En S4, omitir `Z` empeora igual con o sin causa común (+0,027 frente a +0,023): el efecto no se debe solo a la confusión por `Z`. El contraste mediador/descendiente de `C` **no es representable** (el generador no tiene `C→Z`). |
| 8 | Árboles predicen como Ridge sin validez causal | **sostenida** | Predicción en 600 mundos; política *plug-in* no causal con *regret* igual al reparto uniforme. |
| 9 | Falsas atribuciones a canales sin `C→Y` | **corregida** (v1 omitía los aislados) | `false_direct_attribution_rate` en aislados: OLS 14 %, Ridge 10 %, M2 67 %, M3 20 %. `false_total_effect_rate` (aislados, `do_zero` implicado, 15 canal-mundo): OLS 20 %, M2 53 %, M3 20 %. Feeders: efecto total verdadero −1,0 % de Σ\|y\|; M3 lo estima bien en media (−1,0 %), OLS lo ignora (−0,1 %) y M2 tiene el signo opuesto (+9,5 %). |
| 10 | Oracle como referencia | **abierta** | 0 de 8 ajustes con convergencia estricta (5 de v1 + 3 diagnósticos con dos variantes). No se amplía (D7). Sus cifras son descriptivas. |

## Cómputo de v1.1

Ejecutado el 2026-11-05 entre las 20:55 y las 22:55 en WSL2 (14 CPU), con hasta tres cadenas en paralelo. Todos los ajustes v1.1 terminaron sin error.
- Oracle: 14–27 min/ajuste en `marginal`, 1,5–2 min en `sampled`.
- M3 V3: mediana de 70 s/ajuste con otras ejecuciones compitiendo por la CPU.
- RSS máximo por proceso: 1,4 GB.


## A. Cambios de cifras y etiquetas respecto de v1

| cifra | v1 | v1.1 |
|---|---|---|
| Canales aislados en tabla de falsas atribuciones | omitidos (rol 'null' leído como NaN) | 194 canal-mundo por modelo rápido |
| «Mejor predictor = mejor atribuidor» (600 mundos) | 21–34 % (sin referencia de azar) | ver tabla H1 frente a 1/N = 25 % |
| RMSE predictivo vs regret | Spearman 0,076 sobre 315 pares (no independientes) | correlación dentro de mundo (sección E09) |
| Cobertura M3 95 % | 38 % global (válidos + no válidos) | separada: válidos / no válidos (sección D4) |
| Exclusión inicial | 8 semanas fijas | sensibilidad con `response_warmup_weeks` por mundo |


## B. Matriz principal (corr. 3)

Modelos rápidos, 600 mundos, 15 celdas escenario × T de 40 mundos cada una. Mediana de las medianas por celda; tabla por celda en `tables_v1_1/main_matrix_fast_600.csv`.

| model_id | n_worlds | pred | contrib |
|---|---|---|---|
| M0_ols | 600 | 0.060 | 0.071 |
| M1_ridge | 600 | 0.050 | 0.072 |
| M2_adstock_sat | 600 | 0.053 | 0.080 |
| M2_adstock_sat_noZ | 600 | 0.083 | 0.107 |
| M2p_true_transforms | 600 | 0.047 | 0.042 |
| M2p_true_transforms_plus_D | 600 | 0.037 | 0.035 |
| M5_xgboost | 600 | 0.053 |  |
| M6_lightgbm | 600 | 0.049 |  |
| N0_naive_last | 600 | 0.070 |  |
| N1_naive_mean | 600 | 0.094 |  |


Submuestra común pre-registrada (45 mundos: 5 escenarios × 3 T × réplicas 0–2; 3 mundos por celda). M3 solo se compara aquí.

| model_id | n_worlds | pred_rmse_scaled_test_median | contrib_mae_norm_hist_median |
|---|---|---|---|
| M0_ols | 45 | 0.050 | 0.056 |
| M1_ridge | 45 | 0.049 | 0.058 |
| M2_adstock_sat | 45 | 0.051 | 0.094 |
| M2_adstock_sat_noZ | 45 | 0.083 | 0.110 |
| M3_pymc_marketing | 45 | 0.049 | 0.040 |
| M5_xgboost | 45 | 0.054 |  |
| M6_lightgbm | 45 | 0.050 |  |
| M2p_true_transforms | 45 | 0.048 | 0.038 |
| M2p_true_transforms_plus_D | 45 | 0.042 | 0.031 |


## C. Sensibilidad a la exclusión inicial (corr. 1)

Distribución de `response_warmup_weeks` por mundo: 0 semanas: 1 mundos, 6 semanas: 12 mundos, 7 semanas: 587 mundos.

| model_id | n_worlds | median_excl8 | median_min_warmup | mean_diff | ci95_lo | ci95_hi |
|---|---|---|---|---|---|---|
| M0_ols | 600 | 0.064 | 0.064 | 0.000 | -0.000 | 0.000 |
| M1_ridge | 600 | 0.067 | 0.067 | -0.000 | -0.000 | 0.000 |
| M2_adstock_sat | 600 | 0.082 | 0.082 | -0.000 | -0.000 | 0.000 |
| M2_adstock_sat_noZ | 600 | 0.105 | 0.105 | -0.000 | -0.000 | 0.000 |
| M2p_true_transforms | 600 | 0.042 | 0.041 | 0.000 | -0.000 | 0.000 |
| M2p_true_transforms_plus_D | 600 | 0.035 | 0.035 | 0.000 | -0.000 | 0.000 |
| M3_pymc_marketing | 45 | 0.040 | 0.040 | 0.000 | -0.000 | 0.000 |
| M4_oracle_plugin | 5 | 0.010 | 0.010 | 0.000 | -0.000 | 0.000 |


## D. Canales feeder y aislados (D1)

**`false_direct_attribution_rate`** (estimando *observed-path*, ventana `historical_in_sample_fit`, 600 mundos para modelos rápidos, 45 para M3, 5 para M4):

| model_id | role | n_channel_worlds | false_direct_attribution_rate |
|---|---|---|---|
| M0_ols | feeder | 286 | 0.084 |
| M0_ols | isolated | 194 | 0.139 |
| M1_ridge | feeder | 286 | 0.056 |
| M1_ridge | isolated | 194 | 0.098 |
| M2_adstock_sat | feeder | 286 | 0.647 |
| M2_adstock_sat | isolated | 194 | 0.670 |
| M2_adstock_sat_noZ | feeder | 286 | 0.713 |
| M2_adstock_sat_noZ | isolated | 194 | 0.696 |
| M2p_true_transforms | feeder | 286 | 0.490 |
| M2p_true_transforms | isolated | 194 | 0.505 |
| M2p_true_transforms_plus_D | feeder | 286 | 0.416 |
| M2p_true_transforms_plus_D | isolated | 194 | 0.407 |
| M3_pymc_marketing | feeder | 21 | 0.143 |
| M3_pymc_marketing | isolated | 15 | 0.200 |
| M4_oracle_plugin | feeder | 3 | 0.000 |
| M4_oracle_plugin | isolated | 1 | 0.000 |

**Efecto total (`do_zero` sobre la ventana histórica), 45 mundos causales.** `false_total_effect_rate` solo para canales aislados; para *feeders* se muestra el efecto total verdadero frente al implicado por el modelo:

| model_id | role | n_channel_worlds | mean_true_total_effect_norm | mean_est_total_effect_norm | mae_total_effect_norm | false_total_effect_rate |
|---|---|---|---|---|---|---|
| M0_ols | feeder | 21 | -0.010 | -0.001 | 0.012 |  |
| M0_ols | isolated | 15 | 0.000 | -0.002 |  | 0.200 |
| M1_ridge | feeder | 21 | -0.010 | -0.001 | 0.011 |  |
| M1_ridge | isolated | 15 | 0.000 | -0.000 |  | 0.200 |
| M2_adstock_sat | feeder | 21 | -0.010 | 0.095 | 0.112 |  |
| M2_adstock_sat | isolated | 15 | 0.000 | 0.037 |  | 0.533 |
| M2p_true_transforms | feeder | 21 | -0.010 | 0.028 | 0.037 |  |
| M2p_true_transforms | isolated | 15 | 0.000 | 0.018 |  | 0.200 |
| M3_pymc_marketing | feeder | 21 | -0.010 | -0.010 | 0.009 |  |
| M3_pymc_marketing | isolated | 15 | 0.000 | -0.012 |  | 0.200 |
| truth_do_engine | feeder | 21 | -0.010 | -0.010 | 0.000 |  |
| truth_do_engine | isolated | 15 | 0.000 | 0.000 |  | 0.000 |


## E. Predicción frente a atribución, ajustado por azar (H1, corr. 8)

| set | scenario | n_worlds | chance_1_over_N | hit_rate | hit_ci95 | mean_spearman | spearman_ci95 |
|---|---|---|---|---|---|---|---|
| 4 modelos rápidos ciegos (600 mundos) | all | 600 | 0.250 | 0.267 | [0.23, 0.30] | 0.180 | [0.13, 0.23] |
| 4 modelos rápidos ciegos (600 mundos) | S0 | 120 | 0.250 | 0.275 | [0.19, 0.36] | 0.213 | [0.10, 0.32] |
| 4 modelos rápidos ciegos (600 mundos) | S1 | 120 | 0.250 | 0.283 | [0.21, 0.37] | 0.205 | [0.10, 0.30] |
| 4 modelos rápidos ciegos (600 mundos) | S2 | 120 | 0.250 | 0.350 | [0.27, 0.43] | 0.267 | [0.15, 0.38] |
| 4 modelos rápidos ciegos (600 mundos) | S3 | 120 | 0.250 | 0.225 | [0.15, 0.31] | 0.107 | [-0.01, 0.22] |
| 4 modelos rápidos ciegos (600 mundos) | S4 | 120 | 0.250 | 0.200 | [0.12, 0.28] | 0.110 | [-0.01, 0.22] |
| 4 rápidos + M3 (45 mundos) | all | 45 | 0.200 | 0.267 | [0.13, 0.40] | 0.173 | [0.01, 0.34] |
| 4 rápidos + M3 (45 mundos) | S0 | 9 | 0.200 | 0.222 | [0.00, 0.56] | 0.022 | [-0.33, 0.36] |
| 4 rápidos + M3 (45 mundos) | S1 | 9 | 0.200 | 0.444 | [0.11, 0.78] | 0.189 | [-0.19, 0.57] |
| 4 rápidos + M3 (45 mundos) | S2 | 9 | 0.200 | 0.111 | [0.00, 0.33] | 0.311 | [-0.06, 0.64] |
| 4 rápidos + M3 (45 mundos) | S3 | 9 | 0.200 | 0.222 | [0.00, 0.56] | -0.000 | [-0.28, 0.28] |
| 4 rápidos + M3 (45 mundos) | S4 | 9 | 0.200 | 0.333 | [0.11, 0.67] | 0.344 | [-0.01, 0.66] |


## F. Dependencia estadística (corr. 4)

Células DAG distintas por escenario (600 mundos): S0=1, S1=47, S2=112, S3=113, S4=120. En S0 todas las réplicas comparten célula, así que el remuestreo por célula no es aplicable dentro de S0; en el resto casi cada mundo es su propia célula.

| A | B | n_worlds | n_dag_cells | mean_A_minus_B | ci95_worlds | ci95_dag_cells |
|---|---|---|---|---|---|---|
| M0_ols | M2_adstock_sat | 600 | 393 | -0.031 | [-0.0359, -0.0263] | [-0.0354, -0.0258] |
| M1_ridge | M0_ols | 600 | 393 | 0.003 | [0.0022, 0.0034] | [0.0018, 0.0036] |
| M2_adstock_sat | M2_adstock_sat_noZ | 600 | 393 | -0.034 | [-0.0411, -0.0272] | [-0.0402, -0.0273] |
| M3_pymc_marketing | M0_ols | 45 | 37 | -0.018 | [-0.0228, -0.0136] | [-0.0226, -0.0133] |
| M3_pymc_marketing | M2p_true_transforms | 45 | 37 | -0.000 | [-0.0070, 0.0055] | [-0.0070, 0.0052] |


## G. M2 frente a OLS (corr. 5)

Búsqueda de M2 (por mundo): por canal, rejilla α ∈ {0; 0,3; 0,5; 0,7; 0,85} × κ ∈ {0,25; 0,5; 1; 2; 4; lineal} (30 combinaciones), 2 pasadas de descenso por coordenadas (≈ 60·K ajustes OLS), criterio = RMSE en el último 20 % de train (validación temporal), escalas κ con estadísticas del sub-train. **Ningún paso usa la verdad.** M0/M1 no tienen hiperparámetros de forma (M1 solo α de Ridge, misma validación). Diagnóstico (no usado para seleccionar) frente a las familias verdaderas:

| true_carryover | count | frac_alpha0 |
|---|---|---|
| geometric | 1219 | 0.181 |
| none | 392 | 0.401 |
| weibull | 1149 | 0.185 |

| true_saturation | count | frac_linear |
|---|---|---|
| hill | 512 | 0.363 |
| linear | 446 | 0.534 |
| logistic | 475 | 0.339 |
| michaelis_menten | 453 | 0.351 |
| root | 440 | 0.427 |
| tanh | 434 | 0.276 |

Brecha M2 − M2p (privilegiado, fuera de ranking) por escenario:

| scenario_id | median_gap_M2_minus_M2p |
|---|---|
| S0 | 0.039 |
| S1 | 0.042 |
| S2 | 0.038 |
| S3 | 0.034 |
| S4 | 0.036 |


## H. Controles Z según el DAG (corr. 6)

El generador no tiene aristas `C→Z`: **ningún `Z` puede ser mediador ni descendiente de un canal** (`blocked_design_not_supported` para ese contraste). Clases observadas en S2/S4 (600 mundos):

| scenario_id | class | n | frac_descendant_of_D |
|---|---|---|---|
| S2 | common_cause_C_Y | 262 | 0.668 |
| S2 | outcome_only | 98 | 0.663 |
| S4 | common_cause_C_Y | 88 | 0.466 |
| S4 | outcome_only | 152 | 0.553 |
| S4 | treatment_only | 139 | 0.417 |
| S4 | via_Z_or_inert | 101 | 0.366 |

Efecto de omitir `Z` en M2, estratificado por presencia de una causa común `Z→C`, `Z→Y` en el mundo:

| scenario | world_has_common_cause_Z | n_worlds | mean_err_increase_without_Z | ci95_lo | ci95_hi |
|---|---|---|---|---|---|
| S2 | True | 120 | 0.059 | 0.041 | 0.079 |
| S4 | False | 47 | 0.027 | 0.009 | 0.046 |
| S4 | True | 73 | 0.023 | 0.008 | 0.040 |


## I. Incertidumbre por validez del ajuste (D4, corr. 9)

| model_id | run | n_attempted | n_valid_strict | valid_rate | cov50_valid | cov50_INVALID_descriptive | cov80_valid | cov80_INVALID_descriptive | cov95_valid | cov95_INVALID_descriptive |
|---|---|---|---|---|---|---|---|---|---|---|
| M3_pymc_marketing | v1 | 45 | 11 | 0.244 | 0.097 | 0.162 | 0.190 | 0.288 | 0.308 | 0.406 |
| M3_pymc_marketing@v3 | v1_1_m3 | 45 | 31 | 0.689 | 0.115 | 0.178 | 0.206 | 0.323 | 0.326 | 0.497 |
| M4_oracle_plugin | v1 | 5 | 0 | 0.000 |  | 0.734 |  | 0.900 |  | 0.969 |
| M4_oracle_plugin@marginal_ta095 | v1_1_m4_diag | 3 | 0 | 0.000 |  | 0.723 |  | 0.917 |  | 1.000 |
| M4_oracle_plugin@sampled_ta090 | v1_1_m4_diag | 3 | 0 | 0.000 |  | 0.684 |  | 0.917 |  | 1.000 |

> Las columnas `*_INVALID_descriptive` resumen ajustes `nonconverged`: **no son cobertura inferencial fiable**. La cobertura condicional en válidos tiene sesgo de selección: los mundos que convergen pueden ser sistemáticamente más fáciles.


Variante elegida `M3_pymc_marketing@v3` en los 45 mundos M3: convergencia estricta 69% (v1: 24 %), divergencias > 0 en 2%, mediana 70 s/ajuste. Error de contribución histórica: mediana 0.039 (v1 0.040); diferencia emparejada -0.0001 [-0.0011, +0.0010], 45 mundos.


## J. Control lineal E02 (corr. 2)

`direct_only` con `nonlinearity="linear"` (arrastre `none`, saturación identidad; `response_warmup_weeks = 0`). OLS con canales crudos está **bien especificado** para la parte de medios.

| model_id | n_worlds | pred_rmse_scaled_test_median | contrib_mae_norm_hist_median |
|---|---|---|---|
| M0_ols | 30 | 0.019 | 0.002 |
| M1_ridge | 30 | 0.019 | 0.003 |
| M2_adstock_sat | 30 | 0.057 | 0.069 |
| M2_adstock_sat_noZ | 30 | 0.069 | 0.121 |
| M2p_true_transforms | 30 | 0.019 | 0.002 |
| M2p_true_transforms_plus_D | 30 | 0.008 | 0.002 |
| M3_pymc_marketing@v3 | 9 | 0.017 | 0.012 |
| M5_xgboost | 30 | 0.069 |  |
| M6_lightgbm | 30 | 0.077 |  |
| N0_naive_last | 30 | 0.136 |  |
| N1_naive_mean | 30 | 0.158 |  |

Comparaciones emparejadas (error de contribución histórica):

| A | B | n_worlds | mean_A_minus_B | ci95_lo | ci95_hi |
|---|---|---|---|---|---|
| M2_adstock_sat | M0_ols | 30 | 0.095 | 0.065 | 0.127 |
| M1_ridge | M0_ols | 30 | 0.003 | 0.001 | 0.005 |
| M3_pymc_marketing@v3 | M0_ols | 9 | 0.008 | 0.007 | 0.009 |
| M2p_true_transforms | M0_ols | 30 | 0.000 | -0.000 | 0.000 |

E08 `do_zero` (control lineal): |error| / Σ|y| medio por modelo:

| model_id | n_worlds | mae_norm |
|---|---|---|
| M0_ols | 9 | 0.003 |
| M1_ridge | 9 | 0.005 |
| M2_adstock_sat | 9 | 0.091 |
| M2p_true_transforms | 9 | 0.003 |
| M3_pymc_marketing@v3 | 9 | 0.011 |


## K. Sensibilidad `historical_full_refit` (D2)

`historical_full_refit`: mismos 45 mundos (F2 réplicas 0–2), reajuste sobre las T semanas, evaluación en `[8, T)`. La ventana evaluada difiere (más semanas), así que la diferencia mezcla más datos y ventana distinta.

| model_id | n_worlds | median_in_sample_fit | median_full_refit | mean_full_minus_train | ci95_lo | ci95_hi |
|---|---|---|---|---|---|---|
| M0_ols | 45 | 0.056 | 0.056 | -0.001 | -0.003 | 0.001 |
| M1_ridge | 45 | 0.058 | 0.058 | -0.000 | -0.003 | 0.003 |
| M2_adstock_sat | 45 | 0.094 | 0.070 | -0.019 | -0.037 | -0.000 |
| M2_adstock_sat_noZ | 45 | 0.110 | 0.097 | -0.014 | -0.035 | 0.006 |


## L. E10A — confusión estructural `D` (D6)

Descriptores verdaderos por nivel (medianas):

| level | confounding_strength | indirect_share_of_y | mean_abs_channel_corr |
|---|---|---|---|
| dc000 | 0.000 | 0.000 | 0.142 |
| dc025 | 0.000 | 0.007 | 0.145 |
| dc050 | 0.000 | 0.014 | 0.156 |

Error de contribución *observed-path* y error del efecto `do_zero` implicado; diferencias **emparejadas** frente a `dc000`:

| level | model_id | n_pairs | median_contrib_err | diff_vs_base | ci95_lo | ci95_hi | mean_abs_do_zero_err_norm |
|---|---|---|---|---|---|---|---|
| dc000 | M0_ols | 10 | 0.071 | 0.000 | 0.000 | 0.000 | 0.070 |
| dc000 | M1_ridge | 10 | 0.071 | 0.000 | 0.000 | 0.000 | 0.071 |
| dc000 | M2_adstock_sat | 10 | 0.094 | 0.000 | 0.000 | 0.000 | 0.098 |
| dc000 | M2_adstock_sat_noZ | 10 | 0.112 | 0.000 | 0.000 | 0.000 |  |
| dc000 | M2p_true_transforms | 10 | 0.048 | 0.000 | 0.000 | 0.000 | 0.050 |
| dc000 | M2p_true_transforms_plus_D | 10 | 0.052 | 0.000 | 0.000 | 0.000 | 0.049 |
| dc025 | M0_ols | 10 | 0.070 | -0.001 | -0.001 | 0.000 | 0.069 |
| dc025 | M1_ridge | 10 | 0.070 | -0.000 | -0.001 | 0.001 | 0.070 |
| dc025 | M2_adstock_sat | 10 | 0.088 | 0.001 | -0.018 | 0.026 | 0.099 |
| dc025 | M2_adstock_sat_noZ | 10 | 0.106 | 0.012 | -0.020 | 0.062 |  |
| dc025 | M2p_true_transforms | 10 | 0.050 | -0.001 | -0.002 | 0.001 | 0.049 |
| dc025 | M2p_true_transforms_plus_D | 10 | 0.052 | 0.002 | -0.001 | 0.005 | 0.051 |
| dc050 | M0_ols | 10 | 0.069 | -0.001 | -0.004 | 0.001 | 0.069 |
| dc050 | M1_ridge | 10 | 0.071 | -0.001 | -0.003 | 0.001 | 0.070 |
| dc050 | M2_adstock_sat | 10 | 0.098 | -0.009 | -0.023 | 0.007 | 0.090 |
| dc050 | M2_adstock_sat_noZ | 10 | 0.106 | -0.007 | -0.029 | 0.013 |  |
| dc050 | M2p_true_transforms | 10 | 0.052 | -0.002 | -0.006 | 0.001 | 0.048 |
| dc050 | M2p_true_transforms_plus_D | 10 | 0.051 | 0.001 | -0.002 | 0.006 | 0.050 |


## M. E10A — innovaciones compartidas `rho` (D6)

Descriptores verdaderos por nivel (medianas):

| level | confounding_strength | indirect_share_of_y | mean_abs_channel_corr |
|---|---|---|---|
| rho000 | 0.000 | 0.000 | 0.112 |
| rho030 | 0.300 | 0.000 | 0.133 |
| rho060 | 0.600 | 0.000 | 0.140 |

Error de contribución *observed-path* y error del efecto `do_zero` implicado; diferencias **emparejadas** frente a `rho000`:

| level | model_id | n_pairs | median_contrib_err | diff_vs_base | ci95_lo | ci95_hi | mean_abs_do_zero_err_norm |
|---|---|---|---|---|---|---|---|
| rho000 | M0_ols | 10 | 0.085 | 0.000 | 0.000 | 0.000 | 0.088 |
| rho000 | M1_ridge | 10 | 0.086 | 0.000 | 0.000 | 0.000 | 0.089 |
| rho000 | M2_adstock_sat | 10 | 0.095 | 0.000 | 0.000 | 0.000 | 0.113 |
| rho000 | M2_adstock_sat_noZ | 10 | 0.106 | 0.000 | 0.000 | 0.000 |  |
| rho000 | M2p_true_transforms | 10 | 0.075 | 0.000 | 0.000 | 0.000 | 0.076 |
| rho000 | M2p_true_transforms_plus_D | 10 | 0.065 | 0.000 | 0.000 | 0.000 | 0.062 |
| rho030 | M0_ols | 10 | 0.082 | 0.000 | -0.004 | 0.004 | 0.088 |
| rho030 | M1_ridge | 10 | 0.086 | -0.001 | -0.004 | 0.003 | 0.088 |
| rho030 | M2_adstock_sat | 10 | 0.100 | 0.021 | -0.000 | 0.045 | 0.133 |
| rho030 | M2_adstock_sat_noZ | 10 | 0.123 | 0.017 | -0.012 | 0.051 |  |
| rho030 | M2p_true_transforms | 10 | 0.078 | 0.001 | -0.005 | 0.007 | 0.077 |
| rho030 | M2p_true_transforms_plus_D | 10 | 0.065 | 0.004 | -0.001 | 0.011 | 0.066 |
| rho060 | M0_ols | 10 | 0.084 | -0.000 | -0.006 | 0.004 | 0.087 |
| rho060 | M1_ridge | 10 | 0.086 | -0.004 | -0.012 | 0.002 | 0.084 |
| rho060 | M2_adstock_sat | 10 | 0.109 | 0.022 | -0.008 | 0.059 | 0.134 |
| rho060 | M2_adstock_sat_noZ | 10 | 0.123 | 0.023 | -0.005 | 0.062 |  |
| rho060 | M2p_true_transforms | 10 | 0.079 | 0.007 | 0.000 | 0.016 | 0.082 |
| rho060 | M2p_true_transforms_plus_D | 10 | 0.061 | 0.005 | -0.005 | 0.018 | 0.067 |


## N. E09 v1.1 — familias de política (D5)

Correlación de Spearman entre RMSE predictivo y *regret* **dentro de cada mundo** (políticas de modelos con predicción, ≥ 4 por mundo): media 0.095 [IC95 -0.049, 0.231], 45 mundos. (v1 reportó 0,076 sobre 315 pares mundo × modelo, tratándolos como independientes).


| policy_family | policy | label | n_worlds | regret_norm_mean | regret_norm_median | improvement_norm_mean | mean_abs_realized_budget_dev |
|---|---|---|---|---|---|---|---|
| all_channels_clamped_policy | oracle_interventional | oracle_interventional_policy | 45 | 0.0000 | 0.0000 | 0.0630 |  |
| all_channels_clamped_policy | M2p_true_transforms | model_implied_under_exogeneity_assumption | 45 | 0.0136 | 0.0060 | 0.0494 |  |
| all_channels_clamped_policy | M3_pymc_marketing | model_implied_under_exogeneity_assumption | 45 | 0.0208 | 0.0104 | 0.0422 |  |
| all_channels_clamped_policy | M1_ridge | model_implied_under_exogeneity_assumption | 45 | 0.0322 | 0.0144 | 0.0308 |  |
| all_channels_clamped_policy | M2_adstock_sat | model_implied_under_exogeneity_assumption | 45 | 0.0350 | 0.0139 | 0.0280 |  |
| all_channels_clamped_policy | M0_ols | model_implied_under_exogeneity_assumption | 45 | 0.0362 | 0.0153 | 0.0268 |  |
| all_channels_clamped_policy | M5_xgboost | naive_predictive_plugin_policy | 45 | 0.0397 | 0.0355 | 0.0233 |  |
| all_channels_clamped_policy | M6_lightgbm | naive_predictive_plugin_policy | 45 | 0.0398 | 0.0355 | 0.0232 |  |
| all_channels_clamped_policy | equal_allocation | reference_equal_allocation_bounded | 45 | 0.0410 | 0.0355 | 0.0220 |  |
| all_channels_clamped_policy | current | reference_current_plan | 45 | 0.0630 | 0.0520 | 0.0000 |  |
| all_channels_clamped_policy | random_feasible | reference_random_feasible | 45 | 0.0691 | 0.0548 | -0.0061 |  |
| selected_channels_do_policy | oracle_interventional | oracle_interventional_policy | 18 | 0.0000 | 0.0000 | 0.0559 | 0.0000 |
| selected_channels_do_policy | M2p_true_transforms | model_implied_under_exogeneity_assumption | 18 | 0.0075 | 0.0015 | 0.0484 | 0.0156 |
| selected_channels_do_policy | M2p_true_transforms|budget_equalized | model_policy_rescaled_to_true_budget_via_engine | 18 | 0.0085 | 0.0010 | 0.0474 | 0.0000 |
| selected_channels_do_policy | M3_pymc_marketing | model_implied_under_exogeneity_assumption | 18 | 0.0123 | 0.0035 | 0.0436 | 0.0136 |
| selected_channels_do_policy | M3_pymc_marketing|budget_equalized | model_policy_rescaled_to_true_budget_via_engine | 18 | 0.0131 | 0.0056 | 0.0428 | 0.0000 |
| selected_channels_do_policy | M2_adstock_sat | model_implied_under_exogeneity_assumption | 18 | 0.0244 | 0.0078 | 0.0315 | 0.0136 |
| selected_channels_do_policy | M2_adstock_sat|budget_equalized | model_policy_rescaled_to_true_budget_via_engine | 18 | 0.0253 | 0.0080 | 0.0306 | 0.0000 |
| selected_channels_do_policy | M1_ridge | model_implied_under_exogeneity_assumption | 18 | 0.0376 | 0.0236 | 0.0183 | 0.0128 |
| selected_channels_do_policy | M1_ridge|budget_equalized | model_policy_rescaled_to_true_budget_via_engine | 18 | 0.0384 | 0.0259 | 0.0175 | 0.0000 |
| selected_channels_do_policy | M0_ols | model_implied_under_exogeneity_assumption | 18 | 0.0405 | 0.0269 | 0.0154 | 0.0143 |
| selected_channels_do_policy | M0_ols|budget_equalized | model_policy_rescaled_to_true_budget_via_engine | 18 | 0.0407 | 0.0278 | 0.0152 | 0.0000 |
| selected_channels_do_policy | equal_allocation | reference_equal_allocation_true_budget | 18 | 0.0456 | 0.0313 | 0.0103 | 0.0000 |
| selected_channels_do_policy | current | reference_current_plan | 18 | 0.0559 | 0.0366 | 0.0000 | 0.0000 |
| selected_channels_do_policy | random_feasible | reference_random_true_budget | 18 | 0.0576 | 0.0362 | -0.0017 | 0.0000 |


## O. Oracle: diagnóstico (D7)

| world_id | model_id | runtime_s | rhat_max | ess_bulk_min | divergences | converged_strict | contrib_mae_norm | coverage_95 |
|---|---|---|---|---|---|---|---|---|
| S2_promo_drives_treatment_T104_r00 | M4 v1 (marginal, ta 0.90) | 650.213 | 1.032 | 119.427 | 9.000 | False |  |  |
| S2_promo_drives_treatment_T104_r00 | M4_oracle_plugin@marginal_ta095 | 1595.266 | 1.033 | 114.954 | 0.000 | False | 0.014 | 1.000 |
| S2_promo_drives_treatment_T104_r00 | M4_oracle_plugin@sampled_ta090 | 89.285 | 1.030 | 59.985 | 0.000 | False | 0.014 | 1.000 |
| S3_treatment_halo_T104_r00 | M4 v1 (marginal, ta 0.90) | 425.846 | 1.008 | 150.814 | 0.000 | False |  |  |
| S3_treatment_halo_T104_r00 | M4_oracle_plugin@marginal_ta095 | 844.138 | 1.016 | 174.341 | 0.000 | False | 0.003 | 1.000 |
| S3_treatment_halo_T104_r00 | M4_oracle_plugin@sampled_ta090 | 120.601 | 1.021 | 124.688 | 7.000 | False | 0.003 | 1.000 |
| S4_kitchen_sink_T104_r00 | M4 v1 (marginal, ta 0.90) | 575.019 | 1.022 | 109.371 | 0.000 | False |  |  |
| S4_kitchen_sink_T104_r00 | M4_oracle_plugin@marginal_ta095 | 1209.929 | 1.028 | 142.755 | 0.000 | False | 0.003 | 1.000 |
| S4_kitchen_sink_T104_r00 | M4_oracle_plugin@sampled_ta090 | 106.024 | 1.114 | 15.774 | 0.000 | False | 0.005 | 1.000 |

