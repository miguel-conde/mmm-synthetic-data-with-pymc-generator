# P1a — Re-línea base de M3: V3 histórica (semana 0) frente a V3 enmascarada (semana 8)

Protocolo: `docs/protocolo_P1_registrado.md` §3. Mundos: los 10 del piloto, registrados antes de ajustar. Estos mundos se consultaron en auditorías de P0, así que el piloto **no** es una prueba independiente.

- **V3_hist_w0:** columna histórica. V3 ajustada desde la semana 0, con escala de `Y` sobre `[0, n_train)`, como en v1.1. Re-ejecutada con la misma semilla para guardar la posterior (`runs/v1_2_p1a_hist`). Resultado contaminado por las semanas 0–7.
- **V3_masked_w8:** V3 con verosimilitud enmascarada (`runs/v1_2_p1a_pilot`).

Mismos priors, misma semilla y mismo muestreo (1000 + 1000, 4 cadenas, `target_accept 0.99`). Validez estricta: R-hat ≤ 1,01, ESS bulk ≥ 400, 0 divergencias. Métricas normalizadas por media|Y| de la ventana. Ventana `historical_in_sample_fit` = `[8, n_train)`.

## 1. Respuesta (regla fijada en el protocolo §3.5)

**¿La corrección de la ventana explica una parte importante del sesgo negativo y la baja cobertura en directos? → NO CONCLUYENTE.** solo 4 mundos con ambos ajustes válidos (< 8).

## 2. Convergencia y coste

| variant | n_ajustes | n_válidos | tiempo_mediano_s | tiempo_max_s | rss_pico_max_mb |
|---|---|---|---|---|---|
| V3_hist_w0 | 10 | 6 | 97.640 | 183.286 | 903.102 |
| V3_masked_w8 | 10 | 7 | 174.333 | 401.198 | 1017.828 |

| world_id | valid_strict·V3_hist_w0 | valid_strict·V3_masked_w8 | rhat_max·V3_hist_w0 | rhat_max·V3_masked_w8 | ess_bulk_min·V3_hist_w0 | ess_bulk_min·V3_masked_w8 | divergences·V3_hist_w0 | divergences·V3_masked_w8 |
|---|---|---|---|---|---|---|---|---|
| S0_direct_only_T104_r00 | True | True | 1.009 | 1.004 | 612.655 | 722.109 | 0 | 0 |
| S0_direct_only_T104_r01 | True | True | 1.005 | 1.007 | 727.836 | 760.871 | 0 | 0 |
| S1_confounded_treatment_T104_r02 | False | True | 1.009 | 1.005 | 373.704 | 639.944 | 0 | 0 |
| S1_confounded_treatment_T208_r00 | False | True | 1.013 | 1.006 | 546.549 | 561.878 | 0 | 0 |
| S2_promo_drives_treatment_T104_r00 | False | True | 1.012 | 1.004 | 680.684 | 631.276 | 0 | 0 |
| S2_promo_drives_treatment_T208_r00 | False | False | 1.023 | 1.025 | 432.856 | 300.610 | 0 | 0 |
| S3_treatment_halo_T104_r01 | True | False | 1.007 | 1.011 | 765.506 | 612.271 | 0 | 0 |
| S3_treatment_halo_T208_r00 | True | True | 1.004 | 1.005 | 751.619 | 731.934 | 0 | 0 |
| S4_kitchen_sink_T104_r02 | True | True | 1.007 | 1.006 | 590.965 | 437.413 | 0 | 0 |
| S4_kitchen_sink_T208_r00 | True | False | 1.004 | 1.014 | 616.834 | 441.226 | 0 | 0 |

## 3. Directos, ventana `[8, n_train)`: diferencias pareadas por mundo (bootstrap de mundos)

| subconjunto | n_mundos | métrica | V3_hist_w0 | V3_masked_w8 | dif (enm. − hist.) | IC95_lo | IC95_hi |
|---|---|---|---|---|---|---|---|
| ambos válidos (pareado) | 4 | bias_norm | -0.0199 | -0.0023 | 0.0177 | 0.0089 | 0.0312 |
| ambos válidos (pareado) | 4 | mae_norm | 0.0357 | 0.0281 | -0.0076 | -0.0243 | 0.0112 |
| ambos válidos (pareado) | 4 | cov95 | 0.4610 | 0.6050 | 0.1440 | 0.0496 | 0.2383 |
| ambos válidos (pareado) | 4 | cov80 | 0.3236 | 0.5608 | 0.2372 | 0.1428 | 0.3689 |
| ambos válidos (pareado) | 4 | width95_norm | 0.0527 | 0.0589 | 0.0062 | -0.0034 | 0.0145 |
| todos los ajustes (descriptivo) | 10 | bias_norm | -0.0224 | 0.0008 | 0.0232 | 0.0121 | 0.0369 |
| todos los ajustes (descriptivo) | 10 | mae_norm | 0.0449 | 0.0391 | -0.0059 | -0.0159 | 0.0042 |
| todos los ajustes (descriptivo) | 10 | cov95 | 0.4302 | 0.4332 | 0.0030 | -0.1276 | 0.1283 |
| todos los ajustes (descriptivo) | 10 | cov80 | 0.2413 | 0.3340 | 0.0926 | -0.0432 | 0.2400 |
| todos los ajustes (descriptivo) | 10 | width95_norm | 0.0593 | 0.0687 | 0.0094 | -0.0147 | 0.0339 |

Por mundo (media sobre canales directos):

| world_id | bias_norm·V3_hist_w0 | bias_norm·V3_masked_w8 | cov95·V3_hist_w0 | cov95·V3_masked_w8 |
|---|---|---|---|---|
| S0_direct_only_T104_r00 | -0.0340 | -0.0221 | 0.5000 | 0.5000 |
| S0_direct_only_T104_r01 | -0.0470 | -0.0331 | 0.2300 | 0.5033 |
| S1_confounded_treatment_T104_r02 | 0.0356 | 0.0365 | 0.3567 | 0.3300 |
| S1_confounded_treatment_T208_r00 | -0.0379 | -0.0144 | 0.3972 | 0.0870 |
| S2_promo_drives_treatment_T104_r00 | -0.0495 | -0.0115 | 0.2500 | 0.5000 |
| S2_promo_drives_treatment_T208_r00 | -0.0014 | 0.0043 | 0.6234 | 0.5744 |
| S3_treatment_halo_T104_r01 | -0.0659 | 0.0070 | 0.3333 | 0.3333 |
| S3_treatment_halo_T208_r00 | 0.0044 | 0.0421 | 0.5675 | 0.6667 |
| S4_kitchen_sink_T104_r02 | -0.0032 | 0.0040 | 0.5467 | 0.7500 |
| S4_kitchen_sink_T208_r00 | -0.0251 | -0.0052 | 0.4968 | 0.0870 |

## 4. Todos los roles (todos los ajustes, descriptivo)

| variant | role | n_canales | sesgo | mae | cov95 | ancho95 |
|---|---|---|---|---|---|---|
| V3_hist_w0 | direct | 38 | -0.0220 | 0.0448 | 0.4291 | 0.0589 |
| V3_hist_w0 | feeder | 3 | 0.0091 | 0.0091 | 0.0000 | 0.0277 |
| V3_hist_w0 | isolated | 5 | 0.0169 | 0.0169 | 0.0000 | 0.0346 |
| V3_masked_w8 | direct | 38 | -0.0005 | 0.0380 | 0.4297 | 0.0663 |
| V3_masked_w8 | feeder | 3 | 0.0091 | 0.0091 | 0.0000 | 0.0358 |
| V3_masked_w8 | isolated | 5 | 0.0136 | 0.0136 | 0.0000 | 0.0383 |

Directos, ventana futura (`attribution_future_conditional_on_known_CZ`):

| variant | bias_norm | mae_norm | cov95 |
|---|---|---|---|
| V3_hist_w0 | -0.0226 | 0.0440 | 0.4173 |
| V3_masked_w8 | -0.0013 | 0.0396 | 0.4806 |

## 5. Indicadores sobre nulos (ROPE)

ROPE de referencia del protocolo (§4).
- **Estimando:** contribución directa media semanal en `[8, n_train)`, en unidades de `Y`.
- **Umbral:** `delta = 0,005·media|Y[8:n_train)|`; «relevante» si `P(c ≥ delta) ≥ 0,95`.
- Es un umbral de decisión exploratorio: no es cobertura ni una prueba de `beta = 0`.
- En feeders la verdad directa es 0 aunque el efecto total `do` sea positivo.

| variante | válido | rol | n_canales | n_mundos | verdad_relevante | sensibilidad | falsos_positivos | precisión | nulo_correcto | nulo_en_relevante | indeterminado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V3_hist_w0 | False | direct | 16 | 4 | 16 | 0.688 |  | 1.000 |  | 0.000 | 0.312 |
| V3_hist_w0 | True | direct | 22 | 6 | 22 | 0.818 |  | 1.000 |  | 0.000 | 0.182 |
| V3_hist_w0 | True | feeder | 3 | 3 | 0 |  | 0.000 |  | 0.000 |  | 1.000 |
| V3_hist_w0 | True | isolated | 5 | 4 | 0 |  | 0.400 | 0.000 | 0.200 |  | 0.400 |
| V3_masked_w8 | False | direct | 11 | 3 | 11 | 0.909 |  | 1.000 |  | 0.000 | 0.091 |
| V3_masked_w8 | False | feeder | 1 | 1 | 0 |  | 0.000 |  | 0.000 |  | 1.000 |
| V3_masked_w8 | False | isolated | 3 | 2 | 0 |  | 0.333 | 0.000 | 0.000 |  | 0.667 |
| V3_masked_w8 | True | direct | 27 | 7 | 27 | 0.963 |  | 1.000 |  | 0.000 | 0.037 |
| V3_masked_w8 | True | feeder | 2 | 2 | 0 |  | 0.000 |  | 0.000 |  | 1.000 |
| V3_masked_w8 | True | isolated | 2 | 2 | 0 |  | 0.000 |  | 0.500 |  | 0.500 |

Columnas:
- `sensibilidad`: P(decisión relevante | verdad relevante).
- `falsos_positivos`: P(decisión relevante | verdad no relevante).
- `nulo_correcto`: P(decisión prácticamente nulo | verdad no relevante).
- `nulo_en_relevante`: P(decisión prácticamente nulo | verdad relevante).

Con 10 mundos son cifras descriptivas.

## 6. Comprobación frente a los ajustes originales de v1.1

Re-ejecución de V3 desde la semana 0 (misma semilla y entorno) comparada con `runs/v1_1_m3`:

| world_id | max_abs_diff_contrib | max_abs_contrib | rhat_rerun | rhat_v1_1 | valid_rerun | valid_v1_1 |
|---|---|---|---|---|---|---|
| S0_direct_only_T104_r00 | 0.0105 | 3.0054 | 1.0092 | 1.0121 | True | False |
| S0_direct_only_T104_r01 | 0.0329 | 1.1095 | 1.0051 | 1.0072 | True | True |
| S1_confounded_treatment_T104_r02 | 0.0789 | 3.7933 | 1.0086 | 1.0077 | False | True |
| S1_confounded_treatment_T208_r00 | 0.0036 | 1.3090 | 1.0130 | 1.0040 | False | True |
| S2_promo_drives_treatment_T104_r00 | 0.0000 | 2.0805 | 1.0120 | 1.0120 | False | False |
| S2_promo_drives_treatment_T208_r00 | 0.0000 | 2.4288 | 1.0227 | 1.0227 | False | False |
| S3_treatment_halo_T104_r01 | 0.0060 | 0.9689 | 1.0069 | 1.0050 | True | True |
| S3_treatment_halo_T208_r00 | 0.0151 | 2.3536 | 1.0036 | 1.0050 | True | True |
| S4_kitchen_sink_T104_r02 | 0.0000 | 3.8288 | 1.0072 | 1.0072 | True | True |
| S4_kitchen_sink_T208_r00 | 0.0000 | 2.4276 | 1.0036 | 1.0036 | True | True |

Las diferencias son ruido Monte Carlo: el muestreo no es bit a bit reproducible.

Datos: `reports/v1_2/p1a/pilot_world_channel.csv`, `pilot_paired_direct.csv`, `pilot_rope_by_role.csv`.
