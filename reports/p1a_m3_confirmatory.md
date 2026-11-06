# P1a.2 — Evaluación confirmatoria de M3: `legacy_w0` frente a `corrected_w8`

Protocolo: `docs/protocolo_P1B_registrado.md` §3. Variante de muestreo congelada: **S1**.

**Mundos reservados:** F2 réplicas 3–5, 45 mundos, nunca usados en decisiones sobre M3.
- Unidad de inferencia: el mundo.
- IC95 por bootstrap de mundos y, como sensibilidad, de células DAG.

## 1. Pares válidos

`converged_strict` en ambos brazos: **37** mundos. Umbral confirmatorio: ≥ 20. Conclusión: **confirmatoria**.

Validez por brazo: `legacy_w0` 44/45; `corrected_w8` 37/45.

## 2. Comparación pareada por rol (ventana `[8, n_train)`, `historical_observed_path`)

| subconjunto | rol | métrica | n_mundos | legacy_w0 | corrected_w8 | dif | IC95 mundos | IC95 células |
|---|---|---|---|---|---|---|---|---|
| pares converged_strict (principal) | direct | bias_norm | 37 | -0.0445 | -0.0212 | 0.0233 | [0.0167, 0.0300] | [0.0148, 0.0297] |
| pares converged_strict (principal) | direct | mae_norm | 37 | 0.0575 | 0.0512 | -0.0063 | [-0.0121, -0.0003] | [-0.0138, -0.0007] |
| pares converged_strict (principal) | direct | cov50 | 37 | 0.1270 | 0.1568 | 0.0298 | [-0.0304, 0.0946] | [-0.0223, 0.1028] |
| pares converged_strict (principal) | direct | cov80 | 37 | 0.2519 | 0.3740 | 0.1221 | [0.0500, 0.1999] | [0.0530, 0.2078] |
| pares converged_strict (principal) | direct | cov95 | 37 | 0.4153 | 0.5617 | 0.1465 | [0.0745, 0.2225] | [0.0598, 0.2566] |
| pares converged_strict (principal) | direct | width95_norm | 37 | 0.0683 | 0.1059 | 0.0377 | [0.0253, 0.0511] | [0.0234, 0.0505] |
| pares converged_strict (principal) | feeder | bias_norm | 13 | 0.0181 | 0.0225 | 0.0044 | [-0.0028, 0.0131] | [-0.0024, 0.0134] |
| pares converged_strict (principal) | feeder | mae_norm | 13 | 0.0181 | 0.0225 | 0.0044 | [-0.0028, 0.0131] | [-0.0024, 0.0134] |
| pares converged_strict (principal) | feeder | cov50 | 13 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| pares converged_strict (principal) | feeder | cov80 | 13 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| pares converged_strict (principal) | feeder | cov95 | 13 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| pares converged_strict (principal) | feeder | width95_norm | 13 | 0.0493 | 0.0801 | 0.0308 | [-0.0024, 0.0769] | [-0.0019, 0.0776] |
| pares converged_strict (principal) | isolated | bias_norm | 12 | 0.0219 | 0.0464 | 0.0246 | [0.0084, 0.0428] | [0.0089, 0.0421] |
| pares converged_strict (principal) | isolated | mae_norm | 12 | 0.0219 | 0.0464 | 0.0246 | [0.0084, 0.0428] | [0.0089, 0.0421] |
| pares converged_strict (principal) | isolated | cov50 | 12 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| pares converged_strict (principal) | isolated | cov80 | 12 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| pares converged_strict (principal) | isolated | cov95 | 12 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| pares converged_strict (principal) | isolated | width95_norm | 12 | 0.0508 | 0.1050 | 0.0543 | [0.0213, 0.0930] | [0.0219, 0.0948] |
| todos los ajustes (descriptivo) | direct | bias_norm | 45 | -0.0427 | -0.0168 | 0.0259 | [0.0196, 0.0326] | [0.0175, 0.0325] |
| todos los ajustes (descriptivo) | direct | mae_norm | 45 | 0.0555 | 0.0524 | -0.0030 | [-0.0095, 0.0040] | [-0.0114, 0.0038] |
| todos los ajustes (descriptivo) | direct | cov50 | 45 | 0.1470 | 0.1753 | 0.0282 | [-0.0283, 0.0859] | [-0.0217, 0.0966] |
| todos los ajustes (descriptivo) | direct | cov80 | 45 | 0.2907 | 0.3914 | 0.1007 | [0.0307, 0.1750] | [0.0328, 0.1740] |
| todos los ajustes (descriptivo) | direct | cov95 | 45 | 0.4517 | 0.5832 | 0.1315 | [0.0611, 0.2000] | [0.0588, 0.2210] |
| todos los ajustes (descriptivo) | direct | width95_norm | 45 | 0.0717 | 0.1182 | 0.0465 | [0.0326, 0.0631] | [0.0302, 0.0607] |
| todos los ajustes (descriptivo) | feeder | bias_norm | 18 | 0.0226 | 0.0348 | 0.0122 | [-0.0005, 0.0304] | [-0.0002, 0.0321] |
| todos los ajustes (descriptivo) | feeder | mae_norm | 18 | 0.0226 | 0.0348 | 0.0122 | [-0.0005, 0.0304] | [-0.0002, 0.0321] |
| todos los ajustes (descriptivo) | feeder | cov50 | 18 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| todos los ajustes (descriptivo) | feeder | cov80 | 18 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| todos los ajustes (descriptivo) | feeder | cov95 | 18 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| todos los ajustes (descriptivo) | feeder | width95_norm | 18 | 0.0777 | 0.1223 | 0.0445 | [0.0083, 0.0856] | [0.0097, 0.0897] |
| todos los ajustes (descriptivo) | isolated | bias_norm | 16 | 0.0213 | 0.0519 | 0.0306 | [0.0139, 0.0479] | [0.0139, 0.0476] |
| todos los ajustes (descriptivo) | isolated | mae_norm | 16 | 0.0213 | 0.0519 | 0.0306 | [0.0139, 0.0479] | [0.0139, 0.0476] |
| todos los ajustes (descriptivo) | isolated | cov50 | 16 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| todos los ajustes (descriptivo) | isolated | cov80 | 16 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| todos los ajustes (descriptivo) | isolated | cov95 | 16 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | [0.0000, 0.0000] |
| todos los ajustes (descriptivo) | isolated | width95_norm | 16 | 0.0547 | 0.1750 | 0.1203 | [0.0358, 0.2365] | [0.0366, 0.2307] |

## 3. Directos por escenario y T (pares válidos)

| scenario_id | T | bias_norm corrected_w8 | bias_norm legacy_w0 | cov95 corrected_w8 | cov95 legacy_w0 |
|---|---|---|---|---|---|
| S0 | 52 | -0.0506 | -0.0675 | 0.5123 | 0.5000 |
| S0 | 104 | -0.0526 | -0.0658 | 0.2533 | 0.3667 |
| S0 | 208 | 0.0415 | -0.0265 | 0.4984 | 0.5422 |
| S1 | 52 | -0.0395 | -0.0450 | 0.6801 | 0.5184 |
| S1 | 104 | -0.0075 | -0.0332 | 0.5622 | 0.4833 |
| S1 | 208 | -0.0215 | -0.0379 | 0.5549 | 0.3344 |
| S2 | 52 | -0.0120 | -0.0319 | 0.6936 | 0.4902 |
| S2 | 104 | -0.0280 | -0.0759 | 0.6683 | 0.1800 |
| S2 | 208 | -0.0221 | -0.0357 | 0.3850 | 0.4320 |
| S3 | 52 | -0.0247 | -0.0364 | 0.6520 | 0.5539 |
| S3 | 104 | -0.0130 | -0.0367 | 0.7111 | 0.4178 |
| S3 | 208 | -0.0461 | -0.0555 | 0.3924 | 0.3312 |
| S4 | 52 | 0.0093 | 0.0188 | 0.9632 | 0.5074 |
| S4 | 104 | -0.0336 | -0.0527 | 0.6656 | 0.3211 |
| S4 | 208 | -0.0230 | -0.0590 | 0.4968 | 0.2706 |

## 4. ROPE (regla revisada)

- **Estimando:** contribución directa media semanal en `[8, n_train)`, en unidades de `Y`.
- **Umbral:** `δ = 0,005·media|Y[8:n_train)|`, igual en ambos brazos.
- **Decisión:** «relevante» si `P(c > δ) ≥ 0,95`; «no relevante» si `P(c ≤ δ) ≥ 0,95`; en otro caso, «indeterminado».
- Razones agregadas con IC por bootstrap de mundos; `den` = número de canales en el denominador.
- La verdad «relevante» es `c_true > δ`. En feeders, la contribución directa verdadera es 0.

| brazo | subconjunto | rol | n_canales | n_mundos | sensibilidad | IC_sens | falsos_pos | IC_fp | precisión | no_relevante_correcto | IC_nr | abstención |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| legacy_w0 | pares válidos | direct | 142 | 37 | 0.655 | [0.59, 0.72] (den 142) |  | [nan, nan] (den 0) | 1.000 |  | (den 0) | 0.345 |
| legacy_w0 | pares válidos | feeder | 14 | 13 |  | [nan, nan] (den 0) | 0.214 | [0.00, 0.43] (den 14) | 0.000 | 0.000 | (den 14) | 0.786 |
| legacy_w0 | pares válidos | isolated | 12 | 12 |  | [nan, nan] (den 0) | 0.417 | [0.17, 0.67] (den 12) | 0.000 | 0.000 | (den 12) | 0.583 |
| legacy_w0 | todos | direct | 171 | 45 | 0.655 | [0.59, 0.71] (den 171) |  | [nan, nan] (den 0) | 1.000 |  | (den 0) | 0.345 |
| legacy_w0 | todos | feeder | 20 | 18 |  | [nan, nan] (den 0) | 0.200 | [0.05, 0.36] (den 20) | 0.000 | 0.000 | (den 20) | 0.800 |
| legacy_w0 | todos | isolated | 16 | 16 |  | [nan, nan] (den 0) | 0.375 | [0.12, 0.62] (den 16) | 0.000 | 0.062 | (den 16) | 0.562 |
| corrected_w8 | pares válidos | direct | 142 | 37 | 0.768 | [0.69, 0.84] (den 142) |  | [nan, nan] (den 0) | 1.000 |  | (den 0) | 0.232 |
| corrected_w8 | pares válidos | feeder | 14 | 13 |  | [nan, nan] (den 0) | 0.143 | [0.00, 0.31] (den 14) | 0.000 | 0.000 | (den 14) | 0.857 |
| corrected_w8 | pares válidos | isolated | 12 | 12 |  | [nan, nan] (den 0) | 0.500 | [0.25, 0.75] (den 12) | 0.000 | 0.000 | (den 12) | 0.500 |
| corrected_w8 | todos | direct | 171 | 45 | 0.760 | [0.69, 0.83] (den 171) |  | [nan, nan] (den 0) | 1.000 |  | (den 0) | 0.240 |
| corrected_w8 | todos | feeder | 20 | 18 |  | [nan, nan] (den 0) | 0.150 | [0.00, 0.29] (den 20) | 0.000 | 0.000 | (den 20) | 0.850 |
| corrected_w8 | todos | isolated | 16 | 16 |  | [nan, nan] (den 0) | 0.562 | [0.31, 0.81] (den 16) | 0.000 | 0.062 | (den 16) | 0.375 |


## 5. Lectura (agente)

1. **Conclusión confirmatoria en 37 pares válidos** (umbral registrado: ≥ 20). En directos, con la ventana corregida:
   - el sesgo medio pasa de −0,045 a −0,021 (diferencia +0,023, IC95 [0,017, 0,030]; también con bootstrap por células);
   - la cobertura nominal al 95 % sube de 0,42 a 0,56 (+0,15, [0,07, 0,22]);
   - la de 80 % sube de 0,25 a 0,37;
   - el MAE baja ligeramente (−0,006 [−0,012, −0,000]);
   - los intervalos son un 55 % más anchos.
2. **La corrección explica parte, no todo.**
   - Queda un sesgo negativo de −0,021 y la cobertura del 95 % sigue muy por debajo de la nominal (0,56).
   - La mejora es heterogénea por escenario: grande en S2–S4 con T104 y pequeña o negativa en S0 con T104/T208.
   - El resto de la infra-cobertura debe atribuirse a otras causas, como la forma funcional (geométrica/logística frente a Weibull/Hill del generador) o la prior. Esto no se ha contrastado todavía.
3. **Coste en canales sin efecto directo.**
   - En feeders y aislados (verdad directa = 0), la contribución estimada crece: aislados +0,025 [0,008, 0,043].
   - La cobertura es 0 por construcción: `saturation_beta ~ HalfNormal` hace la contribución estrictamente positiva y el intervalo nunca contiene 0.
4. **ROPE (regla revisada).**
   - En directos, todos verdaderamente relevantes (142 canales), la sensibilidad sube de 0,66 a 0,77.
   - En feeders y aislados, la decisión «no relevante» **no se alcanza nunca** (0 de 26 canales en pares válidos).
   - Los falsos positivos son del 14–50 % y las abstenciones del 50–86 %.
   - Con esta prior M3 no puede declarar «no relevante» en estos mundos. No se evalúa la detección de nulos más allá de constatarlo. `spike-and-slab` o contracción quedan como líneas posteriores, una sola cada vez.
5. **Convergencia en los mundos reservados:** `legacy_w0` 44/45 y `corrected_w8` 37/45 con S1. La verosimilitud enmascarada converge peor; los 8 fallos se informan y no se usan en el análisis principal.
6. **Trazabilidad.** Los dos procesos del brazo C (T52/104) coincidieron en 6 mundos de S3, que se ajustaron dos veces. Se conserva el último resultado escrito, como se registró antes de lanzar.
