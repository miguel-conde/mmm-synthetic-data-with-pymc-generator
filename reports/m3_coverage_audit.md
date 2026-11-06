# Auditoría de cobertura de M3 (v1.2 P0, correcciones C1–C2)

Fuentes, **sin reajustar nada**: V0 = `runs/core` (configuración v1, 4×(1000+1000), `target_accept` 0,90); V3 = `runs/v1_1_m3` (`target_accept` 0,99, `saturation_lam ~ Gamma(6,2)`). Los mismos 45 mundos (F2, réplicas 0–2). Tabla por mundo-canal: `reports/v1_2/m3_world_channel.csv`.

**Misma magnitud en verdad y posterior.** Estimando `historical_observed_path_response` = `world.data["contributions_observed"]`, frente a la posterior de `channel_contribution × target_scale` de PyMC-Marketing, ambos en unidades de `y` y semana a semana. Ventana `historical_in_sample_fit` = semanas `[8, n_train)`. PyMC-Marketing arranca el adstock con historia cero en la semana 0 (`l_max = 8`) y el generador con 8 semanas de *burn-in*, así que la exclusión de las semanas 0–7 deja ambas magnitudes definidas sobre la misma historia observada. Los intervalos son de cola igual e incluyen **solo incertidumbre paramétrica dentro de la forma funcional de M3**.

**Unidad estadística.** Primero se calcula la fracción de semanas cubiertas por **canal**; después se promedia **por mundo**; los IC95 remuestrean **mundos** (2000 réplicas). Las semanas de un canal no se tratan como réplicas.

**Selección por convergencia.** `valid_strict` = R-hat ≤ 1,01, ESS bulk ≥ 400 y 0 divergencias en todas las variables libres. Las filas con `valid_strict = False` son **descriptivas**: no son cobertura inferencial fiable.

## 1. Validez de ajuste por escenario

| variant | scenario_id | n_fits | n_valid_strict | valid_rate |
|---|---|---|---|---|
| V0 | S0 | 9 | 4 | 0.444 |
| V0 | S1 | 9 | 1 | 0.111 |
| V0 | S2 | 9 | 1 | 0.111 |
| V0 | S3 | 9 | 1 | 0.111 |
| V0 | S4 | 9 | 4 | 0.444 |
| V3 | S0 | 9 | 5 | 0.556 |
| V3 | S1 | 9 | 9 | 1.000 |
| V3 | S2 | 9 | 2 | 0.222 |
| V3 | S3 | 9 | 7 | 0.778 |
| V3 | S4 | 9 | 8 | 0.889 |

S2 tiene la tasa válida más baja: sus cifras de cobertura en ajustes válidos se apoyan en muy pocos mundos y no son representativas del escenario.

## 2. Cobertura, anchura y sesgo por rol de canal

Normalizado por media\|y\| de la ventana. `bias_norm` = media(estimación − verdad).

| variant | valid_strict | role | n_worlds | n_channels | n_valid_fits | cov50 | cov80 | cov95 | cov95_ci95 | width95_norm | bias_norm | bias_norm_ci95 | mae_norm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 | False | direct | 34 | 128 | 0 | 0.201 | 0.338 | 0.467 | [0.397, 0.537] | 0.079 | -0.034 | [-0.043, -0.024] | 0.047 |
| V0 | False | feeder | 13 | 18 | 0 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.029 | 0.009 | [0.006, 0.012] | 0.009 |
| V0 | False | isolated | 8 | 8 | 0 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.030 | 0.008 | [0.005, 0.011] | 0.008 |
| V0 | True | direct | 11 | 43 | 11 | 0.131 | 0.248 | 0.393 | [0.266, 0.529] | 0.063 | -0.032 | [-0.048, -0.014] | 0.052 |
| V0 | True | feeder | 3 | 3 | 3 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.034 | 0.010 | [0.003, 0.020] | 0.010 |
| V0 | True | isolated | 5 | 7 | 5 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.034 | 0.015 | [0.010, 0.022] | 0.015 |
| V3 | False | direct | 14 | 54 | 0 | 0.198 | 0.367 | 0.553 | [0.463, 0.637] | 0.070 | -0.025 | [-0.036, -0.013] | 0.041 |
| V3 | False | feeder | 2 | 3 | 0 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.039 | 0.012 | [0.011, 0.013] | 0.012 |
| V3 | False | isolated | 2 | 3 | 0 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.026 | 0.010 | [0.005, 0.015] | 0.010 |
| V3 | True | direct | 31 | 117 | 31 | 0.148 | 0.255 | 0.398 | [0.325, 0.470] | 0.065 | -0.038 | [-0.048, -0.028] | 0.051 |
| V3 | True | feeder | 14 | 18 | 14 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.026 | 0.008 | [0.005, 0.012] | 0.008 |
| V3 | True | isolated | 11 | 12 | 11 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.029 | 0.011 | [0.007, 0.015] | 0.011 |

**Lectura (C1).** En *feeders* y aislados la verdad *observed-path* es exactamente 0. Con `saturation_beta ~ HalfNormal` y saturación logística, las extracciones posteriores de la contribución son > 0 casi con seguridad, así que un intervalo de cola igual casi nunca contiene el 0 puntual. Es una propiedad de una posterior continua frente a un estimando exactamente nulo, no una prueba de mala calibración en canales activos. Una prior *horseshoe* continua tendría la misma propiedad. Para ausencia exacta de efecto hace falta masa en cero o una regla ROPE (propuesta P1a).

## 3. Canales directos: por escenario y por T

| variant | scenario_id | valid_strict | n_worlds | n_channels | n_valid_fits | cov50 | cov80 | cov95 | cov95_ci95 | width95_norm | bias_norm | bias_norm_ci95 | mae_norm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 | S0 | False | 5 | 20 | 0 | 0.041 | 0.207 | 0.375 | [0.266, 0.473] | 0.072 | -0.060 | [-0.081, -0.034] | 0.068 |
| V0 | S0 | True | 4 | 16 | 4 | 0.064 | 0.123 | 0.270 | [0.108, 0.428] | 0.075 | -0.022 | [-0.044, 0.014] | 0.060 |
| V0 | S1 | False | 8 | 32 | 0 | 0.171 | 0.354 | 0.527 | [0.421, 0.631] | 0.093 | -0.033 | [-0.050, -0.013] | 0.048 |
| V0 | S1 | True | 1 | 4 | 1 | 0.127 | 0.226 | 0.252 | [0.252, 0.252] | 0.042 | -0.015 | [-0.015, -0.015] | 0.041 |
| V0 | S2 | False | 8 | 32 | 0 | 0.229 | 0.390 | 0.538 | [0.411, 0.663] | 0.066 | -0.022 | [-0.033, -0.011] | 0.035 |
| V0 | S2 | True | 1 | 4 | 1 | 0.000 | 0.153 | 0.250 | [0.250, 0.250] | 0.046 | -0.050 | [-0.050, -0.050] | 0.050 |
| V0 | S3 | False | 8 | 24 | 0 | 0.298 | 0.367 | 0.427 | [0.261, 0.608] | 0.092 | -0.024 | [-0.041, -0.004] | 0.042 |
| V0 | S3 | True | 1 | 3 | 1 | 0.333 | 0.333 | 0.333 | [0.333, 0.333] | 0.075 | -0.065 | [-0.065, -0.065] | 0.072 |
| V0 | S4 | False | 5 | 20 | 0 | 0.207 | 0.315 | 0.413 | [0.255, 0.562] | 0.061 | -0.045 | [-0.066, -0.023] | 0.050 |
| V0 | S4 | True | 4 | 16 | 4 | 0.182 | 0.382 | 0.602 | [0.375, 0.763] | 0.056 | -0.033 | [-0.064, -0.013] | 0.041 |
| V3 | S0 | False | 4 | 16 | 0 | 0.096 | 0.239 | 0.395 | [0.301, 0.489] | 0.073 | -0.023 | [-0.056, 0.011] | 0.056 |
| V3 | S0 | True | 5 | 20 | 5 | 0.010 | 0.074 | 0.265 | [0.196, 0.378] | 0.059 | -0.062 | [-0.079, -0.045] | 0.071 |
| V3 | S1 | True | 9 | 36 | 9 | 0.172 | 0.325 | 0.470 | [0.370, 0.578] | 0.079 | -0.029 | [-0.045, -0.009] | 0.049 |
| V3 | S2 | False | 7 | 28 | 0 | 0.231 | 0.360 | 0.580 | [0.449, 0.705] | 0.063 | -0.022 | [-0.034, -0.010] | 0.034 |
| V3 | S2 | True | 2 | 8 | 2 | 0.140 | 0.250 | 0.313 | [0.250, 0.377] | 0.043 | -0.040 | [-0.042, -0.038] | 0.040 |
| V3 | S3 | False | 2 | 6 | 0 | 0.201 | 0.466 | 0.667 | [0.667, 0.667] | 0.096 | -0.044 | [-0.049, -0.040] | 0.050 |
| V3 | S3 | True | 7 | 21 | 7 | 0.243 | 0.312 | 0.413 | [0.236, 0.623] | 0.072 | -0.028 | [-0.048, -0.004] | 0.044 |
| V3 | S4 | False | 1 | 4 | 0 | 0.369 | 0.728 | 0.771 | [0.771, 0.771] | 0.050 | -0.011 | [-0.011, -0.011] | 0.014 |
| V3 | S4 | True | 8 | 32 | 8 | 0.124 | 0.240 | 0.409 | [0.279, 0.534] | 0.053 | -0.043 | [-0.061, -0.027] | 0.050 |

| variant | T | valid_strict | n_worlds | n_channels | n_valid_fits | cov50 | cov80 | cov95 | cov95_ci95 | width95_norm | bias_norm | bias_norm_ci95 | mae_norm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 | 52 | False | 14 | 53 | 0 | 0.240 | 0.395 | 0.525 | [0.430, 0.633] | 0.101 | -0.039 | [-0.052, -0.026] | 0.050 |
| V0 | 52 | True | 1 | 4 | 1 | 0.103 | 0.206 | 0.632 | [0.632, 0.632] | 0.063 | -0.021 | [-0.021, -0.021] | 0.041 |
| V0 | 104 | False | 10 | 38 | 0 | 0.186 | 0.314 | 0.441 | [0.343, 0.549] | 0.064 | -0.033 | [-0.049, -0.016] | 0.045 |
| V0 | 104 | True | 5 | 19 | 5 | 0.095 | 0.153 | 0.270 | [0.141, 0.409] | 0.060 | -0.047 | [-0.057, -0.038] | 0.059 |
| V0 | 208 | False | 10 | 37 | 0 | 0.160 | 0.283 | 0.410 | [0.276, 0.546] | 0.062 | -0.028 | [-0.048, -0.007] | 0.044 |
| V0 | 208 | True | 5 | 20 | 5 | 0.173 | 0.353 | 0.468 | [0.262, 0.673] | 0.065 | -0.019 | [-0.053, 0.009] | 0.047 |
| V3 | 52 | False | 5 | 18 | 0 | 0.208 | 0.413 | 0.605 | [0.510, 0.700] | 0.099 | -0.035 | [-0.057, -0.014] | 0.053 |
| V3 | 52 | True | 10 | 39 | 10 | 0.181 | 0.330 | 0.511 | [0.380, 0.649] | 0.076 | -0.042 | [-0.055, -0.031] | 0.049 |
| V3 | 104 | False | 3 | 12 | 0 | 0.147 | 0.210 | 0.413 | [0.250, 0.500] | 0.045 | -0.038 | [-0.050, -0.030] | 0.048 |
| V3 | 104 | True | 12 | 45 | 12 | 0.146 | 0.229 | 0.373 | [0.281, 0.479] | 0.062 | -0.037 | [-0.051, -0.021] | 0.050 |
| V3 | 208 | False | 6 | 24 | 0 | 0.215 | 0.407 | 0.580 | [0.420, 0.731] | 0.057 | -0.010 | [-0.024, 0.006] | 0.029 |
| V3 | 208 | True | 9 | 33 | 9 | 0.112 | 0.206 | 0.306 | [0.206, 0.402] | 0.058 | -0.036 | [-0.058, -0.014] | 0.054 |

## 4. Ventana futura (`attribution_future_conditional_on_known_CZ`), canales directos

| variant | valid_strict | n_worlds | n_channels | n_valid_fits | cov50 | cov80 | cov95 | cov95_ci95 | width95_norm | bias_norm | bias_norm_ci95 | mae_norm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 | False | 34 | 128 | 0 | 0.170 | 0.302 | 0.473 | [0.397, 0.541] | 0.076 | -0.033 | [-0.043, -0.023] | 0.046 |
| V0 | True | 11 | 43 | 11 | 0.131 | 0.256 | 0.386 | [0.266, 0.519] | 0.062 | -0.031 | [-0.048, -0.013] | 0.051 |
| V3 | False | 14 | 54 | 0 | 0.178 | 0.329 | 0.531 | [0.438, 0.614] | 0.070 | -0.028 | [-0.040, -0.015] | 0.043 |
| V3 | True | 31 | 117 | 31 | 0.132 | 0.243 | 0.380 | [0.303, 0.458] | 0.063 | -0.036 | [-0.046, -0.026] | 0.049 |

## 5. V0 frente a V3

Diferencias por mundo (canales directos promediados dentro de mundo), IC95 remuestreando mundos. El subconjunto «válido en ambas» es el único **inferencial**, y está seleccionado por convergencia.

| subset | n_worlds | metric | V0_mean | V3_mean | V3_minus_V0 | ci95_lo | ci95_hi |
|---|---|---|---|---|---|---|---|
| valid in V0 and V3 (paired, inferential) | 7 | cov95 | 0.356 | 0.306 | -0.051 | -0.171 | 0.062 |
| valid in V0 and V3 (paired, inferential) | 7 | width95_norm | 0.054 | 0.052 | -0.002 | -0.006 | 0.001 |
| valid in V0 and V3 (paired, inferential) | 7 | bias_norm | -0.042 | -0.041 | 0.000 | -0.001 | 0.001 |
| valid in V0 and V3 (paired, inferential) | 7 | mae_norm | 0.052 | 0.052 | -0.000 | -0.001 | 0.001 |
| all 45 (descriptive) | 45 | cov95 | 0.449 | 0.446 | -0.002 | -0.033 | 0.028 |
| all 45 (descriptive) | 45 | width95_norm | 0.075 | 0.067 | -0.008 | -0.012 | -0.004 |
| all 45 (descriptive) | 45 | bias_norm | -0.033 | -0.034 | -0.001 | -0.002 | 0.000 |
| all 45 (descriptive) | 45 | mae_norm | 0.048 | 0.048 | -0.000 | -0.001 | 0.001 |

## 6. Separación desarrollo / evaluación

Los 10 mundos usados para elegir V3 (solo con diagnósticos del muestreador) **están incluidos** en los 45. La tabla separa los 35 mundos no usados. **No hay validación independiente de la elección de prior más allá de esos 35 mundos**, que comparten receta y escenarios con los de desarrollo.

| worlds | n_worlds | valid_rate | direct_cov95_all_fits | ci95 | direct_cov95_valid_fits | direct_mae_norm |
|---|---|---|---|---|---|---|
| evaluation only (not used) | 35 | 0.657 | 0.467 | [0.395, 0.537] | 0.407 | 0.049 |
| development (used to choose V3) | 10 | 0.800 | 0.375 | [0.272, 0.499] | 0.368 | 0.046 |

## 7. Origen del sesgo en canales directos (V3)

Referencias en los mismos canales y ventana: `M2p` = OLS con las transformaciones **verdaderas** (privilegiado), ajustado desde la semana 0 (como M3 en v1/v1.1) o desde la semana 8 (ventana corregida en v1.2); `M0_raw` = OLS con canales crudos. Sesgo medio con signo, normalizado por media\|y\|.

| modelo | n_worlds | mean_bias_direct | ci95 |
|---|---|---|---|
| M3 V3 (ajuste desde semana 0) | 45 | -0.0341 | [-0.0421, -0.0259] |
| M2p forma verdadera, desde semana 0 | 45 | -0.0356 | [-0.0458, -0.0261] |
| M2p forma verdadera, desde semana 8 | 45 | 0.0036 | [-0.0005, 0.0078] |

| factor | level | n_channels | n_worlds | M3_bias | M2p_true_form_week0_bias | M2p_true_form_week8_bias | M0_raw_bias | M3_abs_bias | M3_cov95 |
|---|---|---|---|---|---|---|---|---|---|
| true_carryover | geometric | 73 | 39 | -0.026 | -0.020 | -0.000 | -0.063 | 0.040 | 0.473 |
| true_carryover | none | 25 | 22 | -0.002 | -0.001 | 0.002 | -0.030 | 0.023 | 0.648 |
| true_carryover | weibull | 73 | 38 | -0.053 | -0.066 | 0.007 | -0.089 | 0.064 | 0.348 |
| true_saturation | hill | 33 | 23 | -0.014 | -0.019 | 0.001 | -0.046 | 0.035 | 0.610 |
| true_saturation | linear | 25 | 18 | -0.025 | -0.032 | -0.000 | -0.074 | 0.044 | 0.502 |
| true_saturation | logistic | 24 | 20 | -0.035 | -0.054 | 0.020 | -0.079 | 0.048 | 0.437 |
| true_saturation | michaelis_menten | 36 | 27 | -0.035 | -0.021 | 0.008 | -0.056 | 0.037 | 0.381 |
| true_saturation | root | 22 | 19 | -0.044 | -0.027 | 0.006 | -0.092 | 0.066 | 0.308 |
| true_saturation | tanh | 31 | 24 | -0.056 | -0.072 | -0.011 | -0.084 | 0.065 | 0.401 |
| scenario_id | S0 | 36 | 9 | -0.044 | -0.054 | 0.008 | -0.082 | 0.064 | 0.323 |
| scenario_id | S1 | 36 | 9 | -0.029 | -0.052 | 0.002 | -0.068 | 0.048 | 0.470 |
| scenario_id | S2 | 36 | 9 | -0.026 | -0.021 | 0.003 | -0.059 | 0.035 | 0.521 |
| scenario_id | S3 | 27 | 9 | -0.031 | -0.014 | 0.006 | -0.070 | 0.045 | 0.470 |
| scenario_id | S4 | 36 | 9 | -0.040 | -0.037 | -0.001 | -0.069 | 0.046 | 0.449 |

Spearman(|corr(log lam, log beta)| posterior, |sesgo| M3) en canales directos V3: -0.295 (171 canales, 45 mundos; descriptivo, canales del mismo mundo no son independientes).

**Interpretación (revisada en P0):**
- El sesgo negativo de M3 (−0,034 [−0,042; −0,026]) es casi igual al de M2p **ajustado desde la semana 0** (−0,036) y desaparece en M2p ajustado desde la semana 8 (+0,004 [−0,0005; 0,008]). Ese sesgo constante por canal es **compatible sobre todo con el artefacto de ajuste en semanas de *burn-in*** ([scientific_status_v1_2.md](scientific_status_v1_2.md) §2), no con la forma funcional de M3. Una primera lectura de esta auditoría lo atribuía a la forma funcional; esa lectura comparaba con M2p contaminado por el mismo artefacto y se retira.
- El patrón por familia verdadera (sesgo mayor con arrastre Weibull, casi nulo sin arrastre) coincide con el artefacto: cuanto más pesa el arrastre en las primeras semanas, más diferencia hay entre historia cero e historia real.
- **No demostrado para M3**: hace falta reajustar M3 con verosimilitud enmascarada (prerrequisito de P1a). Hasta entonces el origen del sesgo de M3 es **inconclusive**, con el artefacto como explicación principal candidata. La cobertura de canales directos (≈ 0,40 en ajustes válidos) puede cambiar al eliminar el sesgo.

## 8. Canales sin `C→Y` (feeders y aislados)

| variant | role | n_worlds | n_channels | n_valid_fits | cov50 | cov80 | cov95 | cov95_ci95 | width95_norm | bias_norm | bias_norm_ci95 | mae_norm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 | feeder | 16 | 21 | 3 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.030 | 0.009 | [0.006, 0.012] | 0.009 |
| V0 | isolated | 13 | 15 | 5 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.032 | 0.011 | [0.008, 0.014] | 0.011 |
| V3 | feeder | 16 | 21 | 14 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.027 | 0.009 | [0.006, 0.012] | 0.009 |
| V3 | isolated | 13 | 15 | 11 | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.028 | 0.011 | [0.007, 0.014] | 0.011 |

