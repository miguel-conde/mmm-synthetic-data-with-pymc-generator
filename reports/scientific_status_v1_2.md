# Estado científico v1.2 (P0)

Ningún informe anterior se reescribe: v1 (`reports/v1/`) y v1.1 (`reports/v1_1/`) quedan congeladas con manifiestos SHA-256. Este informe resume lo que sostienen los datos **con la redacción prudente pedida en §1 de la respuesta del diseñador**.

## 1. Hipótesis H1–H11

Estados: `supported`, `not_supported`, `inconclusive`, `not_run`. Intervalos IC95 por bootstrap de **mundos**.

| H | status | estimand | methods | worlds | result | limits |
|---|---|---|---|---|---|---|
| H1 | supported (débil) | historical_observed_path_response vs prediction_y | M0, M1, M2, M2_noZ (4, ciegos) | 150 (F2; ajuste semanas ≥ 8) | coincidencia del mejor 0.307 [0.233, 0.387] vs azar 0,25; Spearman 0.173 [0.073, 0.273]; por escenario {'S0': 0.26, 'S1': 0.02, 'S2': 0.37, 'S3': 0.05, 'S4': 0.17}; empates: 0 | 4 métodos; ranking predictivo ≠ independencia: correlación positiva débil |
| H2 | inconclusive | historical_observed_path_response | M0, M1, M2, M2p | 50 vs 50 (T=52 vs 208; no pareados) | error(208) − error(52): M0_ols: -0.0050 [-0.0145, +0.0044]; M1_ridge: -0.0029 [-0.0126, +0.0070]; M2_adstock_sat: -0.0211 [-0.0512, +0.0056]; M2p_true_transforms: +0.0103 [+0.0036, +0.0178] | mundos distintos por T; sin pares longitudinales |
| H3 | inconclusive | observed-path y do_zero implicado | M0, M1, M2, M2p, M2p_D | E10A: 10 pares × 3 niveles (D) y (rho), T=104 | sin diferencias detectables en M0/M1/M2p; M2 +0,02 con rho (IC toca 0) | potencia baja; ajuste desde semana 0 (artefacto de *burn-in* común a todos los niveles); no identifica el efecto do bajo confusión |
| H4 | partially supported | historical_observed_path_response | M2 vs M2_noZ | 150 (F2) | omitir Z aumenta el error +0.0462 [0.027, 0.065] | mediador/descendiente de C no representable en el generador (blocked_design_not_supported) |
| H5 | not_run | — | — | — | solo estratos observacionales en v1 (sin diseño controlado) | E14 controlado propuesto en P1c |
| H6 | supported | historical_observed_path_response | M0 vs M2p (privilegiado); M2p vs M2p_D en S1 | 150; S1 30 | error(M0) − error(M2p) = +0.0453 [0.041, 0.050]; en S1 error(M2p) − error(M2p_D) = +0.0124 [0.007, 0.019] (positivo = la referencia privilegiada es mejor) | M2p y M2p_D son privilegiados (fuera de ranking); efecto de D pequeño |
| H7 | supported (nivel verdad) | do_zero vs observed-path | motor do (verdad) | S3/S4, 21 canal-mundo feeder | feeders: atribución observed-path 0; efecto total do_zero −1,0 % de Σ|y| | propiedad del SCM, no de un estimador |
| H8 | supported | prediction_y; decision_value | M5, M6 vs M1 | 150 (F2); E09 45 | RMSE LightGBM − Ridge -0.0040 [-0.011, 0.002]; política plug-in de árboles ≈ reparto uniforme | árboles sin estimando causal; SHAP no evaluado como causal |
| H9 | inconclusive | intervalos de contribución (paramétricos) | M3 V3; M4 | 45 (31 válidos); M4 5 (0 válidos) | M3 directos, ajustes válidos: cobertura 95 % ≈ 0,40 con sesgo −0,034 igual al de M2p ajustado desde la semana 0; nulos: 0 por construcción (posterior continua positiva) | la infra-cobertura de M3 en directos es compatible con el artefacto de burn-in (§2); requiere reajuste con verosimilitud enmascarada; el oracle no converge |
| H10 | inconclusive | decision_value (regret, all_channels_clamped_policy) | M0, M1, M2, M2p, M3, M5, M6 | 45 | Spearman RMSE–regret dentro de mundo 0,095 [−0,049; 0,231] | compatible con relación nula o positiva débil/moderada; políticas de modelos ajustados desde semana 0 |
| H11 | not_run | — | — | — | E10B no ejecutado | P2 |

## 2. Error de protocolo encontrado en P0: ventana de ajuste con *burn-in*

**Hallazgo.** El generador simula 8 semanas de historia previa (`carryover_burn_in = 8`) que no se guardan. Todos los modelos de v1/v1.1 se **ajustaron** desde la semana 0, donde su adstock arranca con historia cero, aunque la **evaluación** ya excluía esas semanas. En la semana 0 el modelo ve tratamiento sin efecto acumulado y la verdad sí lo tiene. El ajuste compensa con coeficientes de medios más bajos y produce un sesgo **negativo y sistemático** de las contribuciones en el resto de semanas.

**Demostración (privilegiada, sin MCMC).** OLS con las transformaciones verdaderas y la base verdadera sin ruido como *offset* tiene un sesgo medio de −0,038 de media\|y\| si se ajusta desde la semana 0 y de −0,0005 si se ajusta desde la semana 8 (45 mundos). Test de regresión: `test_fitting_burn_in_weeks_biases_media_coefficients`. El oracle (M4) ya excluía esas filas de su verosimilitud (`warmup = 7`), lo que explica en parte su error bajo.

**Corrección aplicada a los modelos rápidos** (`configs/v1_2_warmfit.yaml`, 150 mundos F2, sin MCMC): se ajustan en `[8, n_train)` y las semanas 0–7 solo aportan historia de tratamiento.

| model_id | n_worlds | contrib_err_fit_from_week0 | contrib_err_fit_from_week8 | mean_diff | ci95 | mean_bias_week0 | mean_bias_week8 | pred_rmse_test_week0 | pred_rmse_test_week8 |
|---|---|---|---|---|---|---|---|---|---|
| M0_ols | 150 | 0.0626 | 0.0623 | 0.0004 | [-0.0000, 0.0008] | -0.0759 | -0.0764 | 0.0569 | 0.0595 |
| M1_ridge | 150 | 0.0683 | 0.0667 | -0.0000 | [-0.0009, 0.0008] | -0.0803 | -0.0803 | 0.0497 | 0.0504 |
| M2_adstock_sat | 150 | 0.0789 | 0.0869 | 0.0141 | [0.0023, 0.0270] | -0.0396 | 0.0262 | 0.0556 | 0.0531 |
| M2_adstock_sat_noZ | 150 | 0.1047 | 0.1160 | 0.0198 | [0.0025, 0.0376] | -0.0334 | 0.0228 | 0.0847 | 0.0856 |
| M2p_true_transforms | 150 | 0.0417 | 0.0162 | -0.0257 | [-0.0305, -0.0213] | -0.0388 | 0.0010 | 0.0546 | 0.0342 |
| M2p_true_transforms_plus_D | 150 | 0.0365 | 0.0092 | -0.0291 | [-0.0334, -0.0252] | -0.0352 | 0.0009 | 0.0418 | 0.0197 |

| A | B | fit_window | n_worlds | mean_A_minus_B | ci95 |
|---|---|---|---|---|---|
| M0_ols | M2_adstock_sat | week0 (v1) | 150 | -0.0234 | [-0.0306, -0.0164] |
| M0_ols | M2_adstock_sat | week8 (v1.2) | 150 | -0.0371 | [-0.0490, -0.0267] |
| M1_ridge | M0_ols | week0 (v1) | 150 | 0.0031 | [0.0020, 0.0044] |
| M1_ridge | M0_ols | week8 (v1.2) | 150 | 0.0027 | [0.0016, 0.0039] |
| M2_adstock_sat | M2_adstock_sat_noZ | week0 (v1) | 150 | -0.0404 | [-0.0542, -0.0278] |
| M2_adstock_sat | M2_adstock_sat_noZ | week8 (v1.2) | 150 | -0.0462 | [-0.0654, -0.0272] |
| M2_adstock_sat | M2p_true_transforms | week0 (v1) | 150 | 0.0427 | [0.0364, 0.0493] |
| M2_adstock_sat | M2p_true_transforms | week8 (v1.2) | 150 | 0.0824 | [0.0711, 0.0949] |
| M2p_true_transforms | M2p_true_transforms_plus_D | week0 (v1) | 150 | 0.0065 | [0.0041, 0.0089] |
| M2p_true_transforms | M2p_true_transforms_plus_D | week8 (v1.2) | 150 | 0.0099 | [0.0075, 0.0127] |

**Consecuencias:**
- Las cifras de atribución de v1/v1.1 están afectadas por este artefacto, en distinta medida según el modelo. Los rankings y conclusiones que dependan de errores de contribución deben releerse con la tabla anterior.
- M3 (PyMC-Marketing) **no** puede corregirse solo cambiando filas: `MMM.fit` reinicia el adstock en la primera fila recibida. Hace falta una verosimilitud enmascarada (propuesta P1a, prerrequisito). El código ahora **rechaza** ese ajuste en lugar de producir un resultado erróneo (test `test_pymc_marketing_refuses_fit_window_without_history`).
- Parte del sesgo negativo constante de M3 en canales directos (auditoría de cobertura, §7) puede deberse a este artefacto y no solo a la forma funcional. Las conclusiones sobre su origen quedan **inconclusive** hasta repetir M3 con la verosimilitud enmascarada.
- E08/E09 (efectos implicados y políticas de los modelos) usan modelos ajustados desde la semana 0; no se han recalculado en P0.
