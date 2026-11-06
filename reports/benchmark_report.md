# Informe del banco MMM sobre pymc-generator

> Generado automáticamente por `python -m mmm_benchmark.cli report` a partir de los artefactos de `runs/`.
> Ningún resultado procede de River. Todas las cifras: unidad de repetición = mundo.

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



## 2. Diseño, hipótesis (pre-registradas) y versión del generador

Ejecuciones incluidas:

| run | phase | worlds | config_sha256 | code_sha256 | generator_commit |
|---|---|---|---|---|---|
| smoke | F0 | 5 | 9e8b176a5307 | 2074ab5e0f6e | fb9549d78f05 |
| bayes_probe | F1-probe | 1 | 0b775f5685fa | d7c119ca1a13 | fb9549d78f05 |
| pilot | F1 | 45 | 2f8d8310dcd2 | d41b37d0d8e5 | fb9549d78f05 |
| core | F2 | 150 | 3bf32f6d6e0c | d41b37d0d8e5 | fb9549d78f05 |
| extended | F3 | 600 | a64a2fd8512d | d41b37d0d8e5 | fb9549d78f05 |


Hipótesis (fijadas en [docs/methods.md](../docs/methods.md) antes de ejecutar):
 (copiadas del programa, §2)

| Código | Hipótesis | Prueba en este banco |
|---|---|---|
| H1 | Buen ajuste/pronóstico de `Y` no garantiza recuperar contribuciones | Correlación de Spearman entre ranking de RMSE de test y de error de contribución, por mundo |
| H2 | Más semanas mejoran la recuperación media sin garantizar identificación | Error de contribución por `T` y escenario |
| H3 | La confusión latente deteriora a modelos que no la representan | S1 vs S0; M2p vs M2p_D (privilegiado con `D`) |
| H4 | Controles ayudan pero mal ajustados sesgan | S2: M2 con controles vs M2 sin controles (`M2_noZ`) |
| H5 | Correlación entre canales reduce estabilidad | Error vs correlación media entre canales observada (E14 parcial) |
| H6 | Corregir forma funcional ayuda pero no arregla confusión | M0/M1 vs M2 vs M2p en S0 y S1 |
| H7 | `C→C` hace divergir atribución observada y efecto `do` del canal origen | S3: atribución observada del canal origen (0 si `g_cy=0`) vs `do` total |
| H8 | Árboles predicen igual o mejor sin validez causal | RMSE test M5/M6 vs regresiones; árboles sin contribución causal |
| H9 | Intervalos de modelos mal especificados infra-cubren; oracle también puede fallar | Cobertura 50/80/95 de M3 y M4 |
| H10 | Mejor predictor ≠ mejor decisión | Regret de políticas por modelo (E09) |
| H11 | Cambios de prior degradan distinto según método | E10 — no ejecutado en v1 |


Estimandos: [docs/estimands.md](../docs/estimands.md). Auditoría: [docs/generator_audit.md](../docs/generator_audit.md).

## 3. Estado por experimento

| experiment | name | status | evidence |
|---|---|---|---|
| E00 | Sanidad del generador | completed | tests + F0 bundles + worlds.csv |
| E01 | Recuperación fácil (S0) | completed | matriz S0 × T × modelo |
| E02 | Adstock y saturación | partial | M0/M1 vs M2 vs M2p (forma funcional); sin barrido controlado de familias |
| E03 | Confusión latente (S1) | completed | S1 vs S0; M2p vs M2p_D |
| E04 | Control observado y mediación (S2) | completed | M2 vs M2_noZ |
| E05 | Halo y nulos (S3/S4) | completed | falsas atribuciones y feeders |
| E06 | Predicción vs atribución | completed | rankings por mundo |
| E07 | Incertidumbre | completed | cobertura M3/M4 |
| E08 | Intervención real | completed | motor do validado |
| E09 | Valor de decisiones | completed | regret con motor do |
| E10 | Cambio de distribución | not_run_v1 | — |
| E11 | DML / Causal Forest | not_run_v1 | — |
| E12 | MMM neuronal estructurado | not_run_v1 | — |
| E13 | Generador fuera de alcance | not_applicable_v1 | — |
| E14 | Multicolinealidad sin confusión | partial_observational_strata | estratos de correlación observada en S0 (diseño controlado no implementado) |


## 4. Ajustes, coste y fallos

| model_id | N | ok | failed | runtime_s_median | runtime_s_max | peak_rss_mb_max | converged_strict | converged_pilot | rhat_max | ess_bulk_min |
|---|---|---|---|---|---|---|---|---|---|---|
| M0_ols | 600 | 600 | 0 | 0.00 | 0.01 | 921.78 |  |  |  |  |
| M1_ridge | 600 | 600 | 0 | 0.00 | 0.01 | 921.78 |  |  |  |  |
| M2_adstock_sat | 600 | 600 | 0 | 0.06 | 1.21 | 921.79 |  |  |  |  |
| M2_adstock_sat_noZ | 600 | 600 | 0 | 0.06 | 0.79 | 921.79 |  |  |  |  |
| M2p_true_transforms | 600 | 600 | 0 | 1.34 | 5.42 | 932.02 |  |  |  |  |
| M2p_true_transforms_plus_D | 600 | 600 | 0 | 0.00 | 0.00 | 932.65 |  |  |  |  |
| M3_pymc_marketing | 45 | 45 | 0 | 20.22 | 47.77 | 939.86 | 0.24 | 0.29 | 1.05 | 82.90 |
| M4_oracle_plugin | 5 | 5 | 0 | 575.02 | 914.36 | 1166.11 | 0.00 | 0.60 | 1.03 | 109.37 |
| M5_xgboost | 600 | 600 | 0 | 0.78 | 1.77 | 933.81 |  |  |  |  |
| M6_lightgbm | 600 | 600 | 0 | 0.18 | 0.52 | 933.92 |  |  |  |  |
| N0_naive_last | 600 | 600 | 0 | 0.00 | 0.00 | 921.78 |  |  |  |  |
| N1_naive_mean | 600 | 600 | 0 | 0.00 | 0.00 | 921.78 |  |  |  |  |

**Fallos registrados:**

_(sin filas)_


## 5–6. Predicción y atribución histórica (matriz principal)

`pred_rmse_scaled_test` = RMSE en test / media|y_train| (modo B, `conditional_future_inputs_known`).
`contrib_mae_norm_hist` = MAE por canal-semana frente a `historical_observed_path_response` / media|y| (modo A, semanas ≥ 8 de train).
`contrib_mae_norm_future` = mismo estimando en test, respuesta del modelo a `C` futuro sin ver `Y` futuro.
Modelos `M2p*` y `M4` son **privilegiados** y no forman parte de ningún ranking ciego.

Medianas por escenario (todas las `T`); `N` mundos por modelo: M0_ols=600, M1_ridge=600, M2_adstock_sat=600, M2_adstock_sat_noZ=600, M2p_true_transforms=600, M2p_true_transforms_plus_D=600, M3_pymc_marketing=45, M4_oracle_plugin=5, M5_xgboost=600, M6_lightgbm=600, N0_naive_last=600, N1_naive_mean=600.

| scenario_id | model_id | channel_total_abs_err_hist | contrib_mae_norm_future | contrib_mae_norm_hist | pred_rmse_scaled_test |
|---|---|---|---|---|---|
| S0 | M0_ols | 0.075 | 0.076 | 0.075 | 0.062 |
| S0 | M1_ridge | 0.082 | 0.082 | 0.082 | 0.052 |
| S0 | M2_adstock_sat | 0.090 | 0.089 | 0.090 | 0.057 |
| S0 | M2_adstock_sat_noZ | 0.115 | 0.117 | 0.116 | 0.076 |
| S0 | M2p_true_transforms | 0.047 | 0.047 | 0.047 | 0.053 |
| S0 | M2p_true_transforms_plus_D | 0.043 | 0.043 | 0.043 | 0.043 |
| S0 | M3_pymc_marketing | 0.070 | 0.063 | 0.070 | 0.036 |
| S0 | M4_oracle_plugin | 0.022 | 0.025 | 0.022 | 0.006 |
| S0 | M5_xgboost |  |  |  | 0.049 |
| S0 | M6_lightgbm |  |  |  | 0.049 |
| S0 | N0_naive_last |  |  |  | 0.068 |
| S0 | N1_naive_mean |  |  |  | 0.090 |
| S1 | M0_ols | 0.077 | 0.075 | 0.077 | 0.068 |
| S1 | M1_ridge | 0.082 | 0.078 | 0.082 | 0.066 |
| S1 | M2_adstock_sat | 0.099 | 0.099 | 0.099 | 0.064 |
| S1 | M2_adstock_sat_noZ | 0.109 | 0.108 | 0.110 | 0.089 |
| S1 | M2p_true_transforms | 0.047 | 0.042 | 0.047 | 0.062 |
| S1 | M2p_true_transforms_plus_D | 0.038 | 0.038 | 0.038 | 0.044 |
| S1 | M3_pymc_marketing | 0.046 | 0.039 | 0.046 | 0.056 |
| S1 | M4_oracle_plugin | 0.009 | 0.006 | 0.010 | 0.111 |
| S1 | M5_xgboost |  |  |  | 0.059 |
| S1 | M6_lightgbm |  |  |  | 0.060 |
| S1 | N0_naive_last |  |  |  | 0.075 |
| S1 | N1_naive_mean |  |  |  | 0.113 |
| S2 | M0_ols | 0.071 | 0.069 | 0.071 | 0.050 |
| S2 | M1_ridge | 0.070 | 0.070 | 0.070 | 0.046 |
| S2 | M2_adstock_sat | 0.085 | 0.085 | 0.086 | 0.049 |
| S2 | M2_adstock_sat_noZ | 0.120 | 0.120 | 0.121 | 0.102 |
| S2 | M2p_true_transforms | 0.041 | 0.041 | 0.041 | 0.050 |
| S2 | M2p_true_transforms_plus_D | 0.038 | 0.035 | 0.038 | 0.038 |
| S2 | M3_pymc_marketing | 0.038 | 0.035 | 0.038 | 0.056 |
| S2 | M4_oracle_plugin | 0.012 | 0.012 | 0.012 | 0.023 |
| S2 | M5_xgboost |  |  |  | 0.061 |
| S2 | M6_lightgbm |  |  |  | 0.058 |
| S2 | N0_naive_last |  |  |  | 0.079 |
| S2 | N1_naive_mean |  |  |  | 0.120 |
| S3 | M0_ols | 0.052 | 0.054 | 0.052 | 0.055 |
| S3 | M1_ridge | 0.056 | 0.058 | 0.056 | 0.046 |
| S3 | M2_adstock_sat | 0.070 | 0.070 | 0.071 | 0.055 |
| S3 | M2_adstock_sat_noZ | 0.093 | 0.095 | 0.093 | 0.068 |
| S3 | M2p_true_transforms | 0.038 | 0.038 | 0.038 | 0.049 |
| S3 | M2p_true_transforms_plus_D | 0.032 | 0.031 | 0.032 | 0.033 |
| S3 | M3_pymc_marketing | 0.034 | 0.033 | 0.034 | 0.036 |
| S3 | M4_oracle_plugin | 0.003 | 0.003 | 0.003 | 0.020 |
| S3 | M5_xgboost |  |  |  | 0.044 |
| S3 | M6_lightgbm |  |  |  | 0.046 |
| S3 | N0_naive_last |  |  |  | 0.060 |
| S3 | N1_naive_mean |  |  |  | 0.079 |
| S4 | M0_ols | 0.053 | 0.051 | 0.053 | 0.052 |
| S4 | M1_ridge | 0.054 | 0.052 | 0.054 | 0.048 |
| S4 | M2_adstock_sat | 0.075 | 0.071 | 0.075 | 0.044 |
| S4 | M2_adstock_sat_noZ | 0.095 | 0.094 | 0.095 | 0.077 |
| S4 | M2p_true_transforms | 0.036 | 0.034 | 0.036 | 0.040 |
| S4 | M2p_true_transforms_plus_D | 0.031 | 0.030 | 0.031 | 0.038 |
| S4 | M3_pymc_marketing | 0.033 | 0.029 | 0.033 | 0.032 |
| S4 | M4_oracle_plugin | 0.004 | 0.004 | 0.004 | 0.016 |
| S4 | M5_xgboost |  |  |  | 0.047 |
| S4 | M6_lightgbm |  |  |  | 0.046 |
| S4 | N0_naive_last |  |  |  | 0.066 |
| S4 | N1_naive_mean |  |  |  | 0.076 |

**Submuestra común pre-registrada donde se ajustó M3** (45 mundos; medianas, todas las métricas sobre los mismos mundos):

| model_id | N | channel_total_abs_err_hist | contrib_mae_norm_future | contrib_mae_norm_hist | pred_rmse_scaled_test |
|---|---|---|---|---|---|
| M0_ols | 45 | 0.056 | 0.054 | 0.056 | 0.050 |
| M1_ridge | 45 | 0.058 | 0.056 | 0.058 | 0.049 |
| M2_adstock_sat | 45 | 0.091 | 0.089 | 0.094 | 0.051 |
| M2_adstock_sat_noZ | 45 | 0.109 | 0.107 | 0.110 | 0.083 |
| M2p_true_transforms | 45 | 0.038 | 0.038 | 0.038 | 0.048 |
| M2p_true_transforms_plus_D | 45 | 0.031 | 0.026 | 0.031 | 0.042 |
| M3_pymc_marketing | 45 | 0.039 | 0.039 | 0.040 | 0.049 |
| M4_oracle_plugin | 5 | 0.009 | 0.006 | 0.010 | 0.020 |
| M5_xgboost | 45 |  |  |  | 0.054 |
| M6_lightgbm | 45 |  |  |  | 0.050 |
| N0_naive_last | 45 |  |  |  | 0.065 |
| N1_naive_mean | 45 |  |  |  | 0.089 |


### Comparaciones emparejadas (mismos mundos; IC95 bootstrap de mundos)

| metric | A | B | scenario | N_worlds | mean_A_minus_B | ci95_lo | ci95_hi | median_A_minus_B |
|---|---|---|---|---|---|---|---|---|
| contrib_mae_norm_hist | M0_ols | M1_ridge | all | 600 | -0.003 | -0.003 | -0.002 | -0.000 |
| contrib_mae_norm_hist | M0_ols | M1_ridge | S0 | 120 | -0.005 | -0.007 | -0.003 | -0.001 |
| contrib_mae_norm_hist | M0_ols | M1_ridge | S1 | 120 | -0.004 | -0.006 | -0.002 | -0.000 |
| contrib_mae_norm_hist | M0_ols | M1_ridge | S2 | 120 | -0.001 | -0.003 | -0.001 | -0.000 |
| contrib_mae_norm_hist | M0_ols | M1_ridge | S3 | 120 | -0.002 | -0.003 | -0.000 | -0.000 |
| contrib_mae_norm_hist | M0_ols | M1_ridge | S4 | 120 | -0.002 | -0.002 | -0.001 | -0.000 |
| contrib_mae_norm_hist | M0_ols | M2_adstock_sat | all | 600 | -0.031 | -0.036 | -0.026 | -0.015 |
| contrib_mae_norm_hist | M0_ols | M2_adstock_sat | S0 | 120 | -0.035 | -0.048 | -0.024 | -0.014 |
| contrib_mae_norm_hist | M0_ols | M2_adstock_sat | S1 | 120 | -0.033 | -0.047 | -0.022 | -0.018 |
| contrib_mae_norm_hist | M0_ols | M2_adstock_sat | S2 | 120 | -0.018 | -0.026 | -0.011 | -0.009 |
| contrib_mae_norm_hist | M0_ols | M2_adstock_sat | S3 | 120 | -0.031 | -0.041 | -0.021 | -0.019 |
| contrib_mae_norm_hist | M0_ols | M2_adstock_sat | S4 | 120 | -0.037 | -0.048 | -0.028 | -0.016 |
| contrib_mae_norm_hist | M1_ridge | M2_adstock_sat | all | 600 | -0.028 | -0.033 | -0.024 | -0.014 |
| contrib_mae_norm_hist | M1_ridge | M2_adstock_sat | S0 | 120 | -0.030 | -0.043 | -0.019 | -0.010 |
| contrib_mae_norm_hist | M1_ridge | M2_adstock_sat | S1 | 120 | -0.029 | -0.042 | -0.018 | -0.015 |
| contrib_mae_norm_hist | M1_ridge | M2_adstock_sat | S2 | 120 | -0.017 | -0.025 | -0.009 | -0.009 |
| contrib_mae_norm_hist | M1_ridge | M2_adstock_sat | S3 | 120 | -0.029 | -0.040 | -0.020 | -0.016 |
| contrib_mae_norm_hist | M1_ridge | M2_adstock_sat | S4 | 120 | -0.036 | -0.046 | -0.027 | -0.016 |
| contrib_mae_norm_hist | M2_adstock_sat | M2_adstock_sat_noZ | all | 600 | -0.034 | -0.041 | -0.027 | -0.014 |
| contrib_mae_norm_hist | M2_adstock_sat | M2_adstock_sat_noZ | S0 | 120 | -0.037 | -0.054 | -0.023 | -0.014 |
| contrib_mae_norm_hist | M2_adstock_sat | M2_adstock_sat_noZ | S1 | 120 | -0.028 | -0.043 | -0.014 | -0.013 |
| contrib_mae_norm_hist | M2_adstock_sat | M2_adstock_sat_noZ | S2 | 120 | -0.059 | -0.079 | -0.041 | -0.029 |
| contrib_mae_norm_hist | M2_adstock_sat | M2_adstock_sat_noZ | S3 | 120 | -0.021 | -0.036 | -0.008 | -0.011 |
| contrib_mae_norm_hist | M2_adstock_sat | M2_adstock_sat_noZ | S4 | 120 | -0.024 | -0.036 | -0.012 | -0.010 |
| contrib_mae_norm_hist | M2_adstock_sat | M3_pymc_marketing | all | 45 | 0.056 | 0.043 | 0.069 | 0.044 |
| contrib_mae_norm_hist | M2_adstock_sat | M3_pymc_marketing | S0 | 9 | 0.034 | 0.015 | 0.059 | 0.035 |
| contrib_mae_norm_hist | M2_adstock_sat | M3_pymc_marketing | S1 | 9 | 0.085 | 0.061 | 0.111 | 0.090 |
| contrib_mae_norm_hist | M2_adstock_sat | M3_pymc_marketing | S2 | 9 | 0.054 | 0.020 | 0.094 | 0.026 |
| contrib_mae_norm_hist | M2_adstock_sat | M3_pymc_marketing | S3 | 9 | 0.054 | 0.035 | 0.077 | 0.045 |
| contrib_mae_norm_hist | M2_adstock_sat | M3_pymc_marketing | S4 | 9 | 0.053 | 0.027 | 0.083 | 0.037 |
| contrib_mae_norm_hist | M2_adstock_sat | M2p_true_transforms | all | 600 | 0.052 | 0.047 | 0.057 | 0.038 |
| contrib_mae_norm_hist | M2_adstock_sat | M2p_true_transforms | S0 | 120 | 0.058 | 0.046 | 0.072 | 0.039 |
| contrib_mae_norm_hist | M2_adstock_sat | M2p_true_transforms | S1 | 120 | 0.058 | 0.048 | 0.071 | 0.042 |
| contrib_mae_norm_hist | M2_adstock_sat | M2p_true_transforms | S2 | 120 | 0.047 | 0.038 | 0.055 | 0.038 |
| contrib_mae_norm_hist | M2_adstock_sat | M2p_true_transforms | S3 | 120 | 0.044 | 0.035 | 0.055 | 0.034 |
| contrib_mae_norm_hist | M2_adstock_sat | M2p_true_transforms | S4 | 120 | 0.052 | 0.043 | 0.063 | 0.036 |
| contrib_mae_norm_hist | M3_pymc_marketing | M4_oracle_plugin | all | 5 | 0.037 | 0.030 | 0.043 | 0.038 |
| contrib_mae_norm_hist | M3_pymc_marketing | M4_oracle_plugin | S0 | 1 | 0.045 | 0.045 | 0.045 | 0.045 |
| contrib_mae_norm_hist | M3_pymc_marketing | M4_oracle_plugin | S1 | 1 | 0.036 | 0.036 | 0.036 | 0.036 |
| contrib_mae_norm_hist | M3_pymc_marketing | M4_oracle_plugin | S2 | 1 | 0.038 | 0.038 | 0.038 | 0.038 |
| contrib_mae_norm_hist | M3_pymc_marketing | M4_oracle_plugin | S3 | 1 | 0.023 | 0.023 | 0.023 | 0.023 |
| contrib_mae_norm_hist | M3_pymc_marketing | M4_oracle_plugin | S4 | 1 | 0.042 | 0.042 | 0.042 | 0.042 |
| contrib_mae_norm_hist | M2p_true_transforms | M2p_true_transforms_plus_D | all | 600 | 0.005 | 0.004 | 0.006 | 0.002 |
| contrib_mae_norm_hist | M2p_true_transforms | M2p_true_transforms_plus_D | S0 | 120 | 0.003 | 0.001 | 0.006 | 0.001 |
| contrib_mae_norm_hist | M2p_true_transforms | M2p_true_transforms_plus_D | S1 | 120 | 0.009 | 0.006 | 0.013 | 0.005 |
| contrib_mae_norm_hist | M2p_true_transforms | M2p_true_transforms_plus_D | S2 | 120 | 0.002 | 0.001 | 0.004 | 0.000 |
| contrib_mae_norm_hist | M2p_true_transforms | M2p_true_transforms_plus_D | S3 | 120 | 0.007 | 0.004 | 0.009 | 0.003 |
| contrib_mae_norm_hist | M2p_true_transforms | M2p_true_transforms_plus_D | S4 | 120 | 0.004 | 0.003 | 0.006 | 0.002 |
| pred_rmse_scaled_test | M0_ols | M2_adstock_sat | all | 600 | -0.008 | -0.014 | -0.003 | 0.000 |
| pred_rmse_scaled_test | M0_ols | M2_adstock_sat | S0 | 120 | -0.011 | -0.024 | 0.002 | -0.002 |
| pred_rmse_scaled_test | M0_ols | M2_adstock_sat | S1 | 120 | -0.007 | -0.019 | 0.005 | -0.000 |
| pred_rmse_scaled_test | M0_ols | M2_adstock_sat | S2 | 120 | -0.014 | -0.028 | -0.001 | -0.000 |
| pred_rmse_scaled_test | M0_ols | M2_adstock_sat | S3 | 120 | -0.007 | -0.016 | 0.001 | -0.002 |
| pred_rmse_scaled_test | M0_ols | M2_adstock_sat | S4 | 120 | -0.003 | -0.016 | 0.008 | 0.004 |
| pred_rmse_scaled_test | M1_ridge | M2_adstock_sat | all | 600 | -0.019 | -0.025 | -0.013 | -0.002 |
| pred_rmse_scaled_test | M1_ridge | M2_adstock_sat | S0 | 120 | -0.025 | -0.039 | -0.011 | -0.008 |
| pred_rmse_scaled_test | M1_ridge | M2_adstock_sat | S1 | 120 | -0.015 | -0.029 | -0.004 | -0.004 |
| pred_rmse_scaled_test | M1_ridge | M2_adstock_sat | S2 | 120 | -0.022 | -0.039 | -0.008 | -0.001 |
| pred_rmse_scaled_test | M1_ridge | M2_adstock_sat | S3 | 120 | -0.018 | -0.029 | -0.007 | -0.002 |
| pred_rmse_scaled_test | M1_ridge | M2_adstock_sat | S4 | 120 | -0.015 | -0.029 | -0.003 | 0.002 |
| pred_rmse_scaled_test | M5_xgboost | M2_adstock_sat | all | 600 | -0.021 | -0.027 | -0.015 | -0.003 |
| pred_rmse_scaled_test | M5_xgboost | M2_adstock_sat | S0 | 120 | -0.029 | -0.044 | -0.016 | -0.007 |
| pred_rmse_scaled_test | M5_xgboost | M2_adstock_sat | S1 | 120 | -0.021 | -0.035 | -0.009 | -0.008 |
| pred_rmse_scaled_test | M5_xgboost | M2_adstock_sat | S2 | 120 | -0.014 | -0.032 | 0.001 | 0.006 |
| pred_rmse_scaled_test | M5_xgboost | M2_adstock_sat | S3 | 120 | -0.023 | -0.034 | -0.013 | -0.007 |
| pred_rmse_scaled_test | M5_xgboost | M2_adstock_sat | S4 | 120 | -0.017 | -0.031 | -0.006 | -0.003 |
| pred_rmse_scaled_test | M6_lightgbm | M2_adstock_sat | all | 600 | -0.022 | -0.028 | -0.015 | -0.005 |
| pred_rmse_scaled_test | M6_lightgbm | M2_adstock_sat | S0 | 120 | -0.029 | -0.044 | -0.017 | -0.008 |
| pred_rmse_scaled_test | M6_lightgbm | M2_adstock_sat | S1 | 120 | -0.022 | -0.036 | -0.010 | -0.009 |
| pred_rmse_scaled_test | M6_lightgbm | M2_adstock_sat | S2 | 120 | -0.016 | -0.034 | -0.000 | 0.005 |
| pred_rmse_scaled_test | M6_lightgbm | M2_adstock_sat | S3 | 120 | -0.023 | -0.034 | -0.012 | -0.010 |
| pred_rmse_scaled_test | M6_lightgbm | M2_adstock_sat | S4 | 120 | -0.018 | -0.031 | -0.006 | -0.003 |

Tabla completa: `tables/paired_comparisons.csv`.

### H2 — horizonte `T` (error de contribución histórica)

| model_id | T | N | median | mean |
|---|---|---|---|---|
| M0_ols | 52 | 200 | 0.067 | 0.070 |
| M0_ols | 104 | 200 | 0.065 | 0.069 |
| M0_ols | 208 | 200 | 0.062 | 0.064 |
| M1_ridge | 52 | 200 | 0.069 | 0.072 |
| M1_ridge | 104 | 200 | 0.069 | 0.072 |
| M1_ridge | 208 | 200 | 0.064 | 0.067 |
| M2_adstock_sat | 52 | 200 | 0.087 | 0.107 |
| M2_adstock_sat | 104 | 200 | 0.088 | 0.103 |
| M2_adstock_sat | 208 | 200 | 0.075 | 0.085 |
| M2_adstock_sat_noZ | 52 | 200 | 0.116 | 0.147 |
| M2_adstock_sat_noZ | 104 | 200 | 0.116 | 0.136 |
| M2_adstock_sat_noZ | 208 | 200 | 0.089 | 0.114 |
| M2p_true_transforms | 52 | 200 | 0.040 | 0.043 |
| M2p_true_transforms | 104 | 200 | 0.048 | 0.054 |
| M2p_true_transforms | 208 | 200 | 0.036 | 0.043 |
| M2p_true_transforms_plus_D | 52 | 200 | 0.034 | 0.041 |
| M2p_true_transforms_plus_D | 104 | 200 | 0.041 | 0.046 |
| M2p_true_transforms_plus_D | 208 | 200 | 0.032 | 0.037 |
| M3_pymc_marketing | 52 | 15 | 0.038 | 0.045 |
| M3_pymc_marketing | 104 | 15 | 0.046 | 0.044 |
| M3_pymc_marketing | 208 | 15 | 0.036 | 0.040 |
| M4_oracle_plugin | 104 | 5 | 0.010 | 0.010 |


### H1 / E06 — concordancia de rankings predicción vs atribución por mundo

Modelos ciegos con contribución: M0_ols, M1_ridge, M2_adstock_sat, M2_adstock_sat_noZ, M3_pymc_marketing. Spearman medio (todas) = 0.188 [IC95 0.139, 0.234], N = 600 mundos.

| scenario_id | N | mean_spearman | same_best |
|---|---|---|---|
| S0 | 120 | 0.222 | 0.283 |
| S1 | 120 | 0.216 | 0.292 |
| S2 | 120 | 0.275 | 0.342 |
| S3 | 120 | 0.113 | 0.233 |
| S4 | 120 | 0.113 | 0.208 |


### H3 / E03 — confusión latente (S1 − S0, no emparejado; IC95 bootstrap)

| model_id | T | N_S0 | N_S1 | mean_S0 | mean_S1 | diff_S1_minus_S0 | ci95_lo | ci95_hi |
|---|---|---|---|---|---|---|---|---|
| M0_ols | 52 | 40 | 40 | 0.079 | 0.079 | -0.000 | -0.011 | 0.010 |
| M0_ols | 104 | 40 | 40 | 0.078 | 0.075 | -0.002 | -0.013 | 0.009 |
| M0_ols | 208 | 40 | 40 | 0.072 | 0.077 | 0.006 | -0.004 | 0.015 |
| M1_ridge | 52 | 40 | 40 | 0.083 | 0.082 | -0.002 | -0.012 | 0.009 |
| M1_ridge | 104 | 40 | 40 | 0.081 | 0.081 | -0.001 | -0.012 | 0.012 |
| M1_ridge | 208 | 40 | 40 | 0.079 | 0.082 | 0.003 | -0.008 | 0.013 |
| M2_adstock_sat | 52 | 40 | 40 | 0.136 | 0.117 | -0.019 | -0.056 | 0.018 |
| M2_adstock_sat | 104 | 40 | 40 | 0.102 | 0.122 | 0.020 | -0.006 | 0.050 |
| M2_adstock_sat | 208 | 40 | 40 | 0.097 | 0.093 | -0.005 | -0.029 | 0.017 |
| M2_adstock_sat_noZ | 52 | 40 | 40 | 0.200 | 0.142 | -0.059 | -0.109 | -0.005 |
| M2_adstock_sat_noZ | 104 | 40 | 40 | 0.132 | 0.148 | 0.016 | -0.026 | 0.059 |
| M2_adstock_sat_noZ | 208 | 40 | 40 | 0.114 | 0.126 | 0.011 | -0.025 | 0.048 |
| M3_pymc_marketing | 52 | 3 | 3 | 0.082 | 0.035 | -0.047 | -0.068 | -0.027 |
| M3_pymc_marketing | 104 | 3 | 3 | 0.057 | 0.054 | -0.003 | -0.027 | 0.027 |
| M3_pymc_marketing | 208 | 3 | 3 | 0.055 | 0.054 | -0.001 | -0.029 | 0.032 |
| M2p_true_transforms | 52 | 40 | 40 | 0.054 | 0.045 | -0.010 | -0.026 | 0.005 |
| M2p_true_transforms | 104 | 40 | 40 | 0.059 | 0.058 | -0.001 | -0.016 | 0.013 |
| M2p_true_transforms | 208 | 40 | 40 | 0.047 | 0.055 | 0.007 | -0.006 | 0.021 |
| M2p_true_transforms_plus_D | 52 | 40 | 40 | 0.053 | 0.040 | -0.013 | -0.031 | 0.002 |
| M2p_true_transforms_plus_D | 104 | 40 | 40 | 0.056 | 0.045 | -0.011 | -0.025 | 0.003 |
| M2p_true_transforms_plus_D | 208 | 40 | 40 | 0.041 | 0.044 | 0.003 | -0.007 | 0.013 |
| M4_oracle_plugin | 104 | 1 | 1 | 0.022 | 0.010 | -0.012 | -0.012 | -0.012 |


### H5 / E14 (parcial) — correlación observada entre canales vs error de contribución

| model_id | scenario_id | N | spearman_corr_vs_error | median_mean_abs_corr |
|---|---|---|---|---|
| M0_ols | S0 | 120 | 0.023 | 0.133 |
| M0_ols | S3 | 120 | 0.203 | 0.169 |
| M1_ridge | S0 | 120 | -0.038 | 0.133 |
| M1_ridge | S3 | 120 | 0.175 | 0.169 |
| M2_adstock_sat | S0 | 120 | 0.000 | 0.133 |
| M2_adstock_sat | S3 | 120 | 0.056 | 0.169 |
| M2_adstock_sat_noZ | S0 | 120 | -0.013 | 0.133 |
| M2_adstock_sat_noZ | S3 | 120 | 0.114 | 0.169 |
| M3_pymc_marketing | S0 | 9 | -0.183 | 0.121 |
| M3_pymc_marketing | S3 | 9 | -0.167 | 0.188 |
| M2p_true_transforms | S0 | 120 | -0.001 | 0.133 |
| M2p_true_transforms | S3 | 120 | 0.174 | 0.169 |
| M2p_true_transforms_plus_D | S0 | 120 | 0.070 | 0.133 |
| M2p_true_transforms_plus_D | S3 | 120 | 0.215 | 0.169 |


### E05 — falsas atribuciones a canales sin `C→Y` (umbral pre-registrado 2 % de Σ|y|)

| model_id | role | N_channel_worlds | false_attribution_rate |
|---|---|---|---|
| M0_ols | feeder | 286 | 0.084 |
| M1_ridge | feeder | 286 | 0.056 |
| M2_adstock_sat | feeder | 286 | 0.647 |
| M2_adstock_sat_noZ | feeder | 286 | 0.713 |
| M2p_true_transforms | feeder | 286 | 0.490 |
| M2p_true_transforms_plus_D | feeder | 286 | 0.416 |
| M3_pymc_marketing | feeder | 21 | 0.143 |
| M4_oracle_plugin | feeder | 3 | 0.000 |


## 7. Incertidumbre y diagnósticos

| model_id | task | metric | count | mean |
|---|---|---|---|---|
| M3_pymc_marketing | attribution_future_response | coverage_50 | 45 | 0.125 |
| M3_pymc_marketing | attribution_future_response | coverage_80 | 45 | 0.243 |
| M3_pymc_marketing | attribution_future_response | coverage_95 | 45 | 0.381 |
| M3_pymc_marketing | attribution_future_response | width_norm_50 | 45 | 0.019 |
| M3_pymc_marketing | attribution_future_response | width_norm_80 | 45 | 0.040 |
| M3_pymc_marketing | attribution_future_response | width_norm_95 | 45 | 0.066 |
| M3_pymc_marketing | attribution_historical | coverage_50 | 45 | 0.147 |
| M3_pymc_marketing | attribution_historical | coverage_80 | 45 | 0.264 |
| M3_pymc_marketing | attribution_historical | coverage_95 | 45 | 0.382 |
| M3_pymc_marketing | attribution_historical | width_norm_50 | 45 | 0.020 |
| M3_pymc_marketing | attribution_historical | width_norm_80 | 45 | 0.041 |
| M3_pymc_marketing | attribution_historical | width_norm_95 | 45 | 0.068 |
| M3_pymc_marketing | prediction_conditional_future_inputs_known | coverage_50 | 45 | 0.239 |
| M3_pymc_marketing | prediction_conditional_future_inputs_known | coverage_80 | 45 | 0.482 |
| M3_pymc_marketing | prediction_conditional_future_inputs_known | coverage_95 | 45 | 0.671 |
| M4_oracle_plugin | attribution_future_response | coverage_50 | 5 | 0.731 |
| M4_oracle_plugin | attribution_future_response | coverage_80 | 5 | 0.900 |
| M4_oracle_plugin | attribution_future_response | coverage_95 | 5 | 0.955 |
| M4_oracle_plugin | attribution_future_response | width_norm_50 | 5 | 0.021 |
| M4_oracle_plugin | attribution_future_response | width_norm_80 | 5 | 0.038 |
| M4_oracle_plugin | attribution_future_response | width_norm_95 | 5 | 0.054 |
| M4_oracle_plugin | attribution_historical | coverage_50 | 5 | 0.734 |
| M4_oracle_plugin | attribution_historical | coverage_80 | 5 | 0.900 |
| M4_oracle_plugin | attribution_historical | coverage_95 | 5 | 0.969 |
| M4_oracle_plugin | attribution_historical | width_norm_50 | 5 | 0.022 |
| M4_oracle_plugin | attribution_historical | width_norm_80 | 5 | 0.039 |
| M4_oracle_plugin | attribution_historical | width_norm_95 | 5 | 0.056 |


## 8. Efectos de intervención (E08)

Validación del motor contrafactual por mundo:

| status | N_worlds |
|---|---|
| validated | 45 |

**do_zero, todos los escenarios:**

| model_id | N | mae_norm | bias_norm |
|---|---|---|---|
| M0_ols | 45 | 0.058 | 0.056 |
| M1_ridge | 45 | 0.060 | 0.059 |
| M2_adstock_sat | 45 | 0.092 | 0.031 |
| M2p_true_transforms | 45 | 0.041 | 0.034 |
| M3_pymc_marketing | 45 | 0.040 | 0.025 |

**H7 — atribución observada verdadera vs efecto total do_zero verdadero (normalizado por Σ|y|):**

| scenario_id | role | N | mean_do_zero_effect_norm | mean_attr_minus_do_norm | max_abs_attr_minus_do_norm |
|---|---|---|---|---|---|
| S0 | direct | 36 | -0.098 | -0.005 | 0.027 |
| S1 | direct | 36 | -0.099 | -0.003 | 0.018 |
| S2 | direct | 36 | -0.088 | -0.002 | 0.011 |
| S3 | direct | 27 | -0.090 | 0.000 | 0.024 |
| S3 | feeder | 13 | -0.010 | 0.010 | 0.027 |
| S4 | direct | 36 | -0.101 | -0.002 | 0.012 |
| S4 | feeder | 8 | -0.009 | 0.009 | 0.020 |


## 9. Calidad de decisiones (E09)

Presupuesto adimensional en unidades de tratamiento (no euros), multiplicadores por canal en [0.5, 1.5] sobre la ventana histórica; valor evaluado con `do` sobre todos los canales.

| policy | label | N | regret_norm_mean | regret_norm_median | improvement_norm_mean | frac_at_bounds |
|---|---|---|---|---|---|---|
| oracle_interventional | oracle_interventional_policy | 45 | 0.0000 | 0.0000 | 0.0630 | 0.5419 |
| M2p_true_transforms | model_implied_under_exogeneity_assumption | 45 | 0.0136 | 0.0060 | 0.0494 | 0.6778 |
| M3_pymc_marketing | model_implied_under_exogeneity_assumption | 45 | 0.0209 | 0.0104 | 0.0421 | 0.6493 |
| M1_ridge | model_implied_under_exogeneity_assumption | 45 | 0.0322 | 0.0144 | 0.0308 | 0.7767 |
| M2_adstock_sat | model_implied_under_exogeneity_assumption | 45 | 0.0350 | 0.0139 | 0.0280 | 0.7063 |
| M0_ols | model_implied_under_exogeneity_assumption | 45 | 0.0362 | 0.0153 | 0.0268 | 0.7767 |
| M5_xgboost | naive_predictive_plugin_policy | 45 | 0.0397 | 0.0355 | 0.0233 | 0.0881 |
| M6_lightgbm | naive_predictive_plugin_policy | 45 | 0.0398 | 0.0355 | 0.0232 | 0.0881 |
| equal_allocation | reference_equal_allocation_bounded | 45 | 0.0410 | 0.0355 | 0.0220 | 0.1574 |
| current | reference_current_plan | 45 | 0.0630 | 0.0520 | 0.0000 | 0.0000 |

Spearman(RMSE predictivo test, regret) sobre 315 pares mundo×modelo = 0.076.


## Figuras

![F0_S0_direct_only_T104_r00_dag.png](figures/F0_S0_direct_only_T104_r00_dag.png)
![F0_S0_direct_only_T104_r00_decomposition.png](figures/F0_S0_direct_only_T104_r00_decomposition.png)
![F0_S1_confounded_treatment_T104_r00_dag.png](figures/F0_S1_confounded_treatment_T104_r00_dag.png)
![F0_S1_confounded_treatment_T104_r00_decomposition.png](figures/F0_S1_confounded_treatment_T104_r00_decomposition.png)
![F0_S2_promo_drives_treatment_T104_r00_dag.png](figures/F0_S2_promo_drives_treatment_T104_r00_dag.png)
![F0_S2_promo_drives_treatment_T104_r00_decomposition.png](figures/F0_S2_promo_drives_treatment_T104_r00_decomposition.png)
![F0_S3_treatment_halo_T104_r00_dag.png](figures/F0_S3_treatment_halo_T104_r00_dag.png)
![F0_S3_treatment_halo_T104_r00_decomposition.png](figures/F0_S3_treatment_halo_T104_r00_decomposition.png)
![F0_S4_kitchen_sink_T104_r00_dag.png](figures/F0_S4_kitchen_sink_T104_r00_dag.png)
![F0_S4_kitchen_sink_T104_r00_decomposition.png](figures/F0_S4_kitchen_sink_T104_r00_decomposition.png)
![example_S1_confounded_treatment_T104_r00.png](figures/example_S1_confounded_treatment_T104_r00.png)
![contrib_error_by_scenario_T.png](figures/contrib_error_by_scenario_T.png)
![prediction_vs_contribution.png](figures/prediction_vs_contribution.png)
![coverage_calibration.png](figures/coverage_calibration.png)
![null_false_attribution.png](figures/null_false_attribution.png)
![e08_intervention_error.png](figures/e08_intervention_error.png)
![e09_regret.png](figures/e09_regret.png)
![cost_and_failures.png](figures/cost_and_failures.png)




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

