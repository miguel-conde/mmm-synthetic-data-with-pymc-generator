# P1c — E14: puerta de calidad del diseño (sin ajustes)

Protocolo: `docs/protocolo_P1B_registrado.md` §6. Configuración: `configs/v1_2_p1c_e14.yaml`.
- 30 pares × 3 niveles de `zc_coeff_range` ∈ {0, 1,5, 3,0}, T = 104.
- `direct_only` con `edge_budget`: Z→C = 6, Z→Y = 0, D→C = 0, C→C = 0; D→Y = 1 por conectividad.
- Métricas sobre `[8, n_train)`.
- Efecto verdadero `do_zero` por canal medido con el motor de intervenciones validado.

## 1. Comprobación del DAG en cada mundo

| level | n | zy | dc | cc | dz | zc | dy | rho_max |
|---|---|---|---|---|---|---|---|---|
| p1czc000 | 30 | 0 | 0 | 0 | 0 | 6.000 | 1.000 | 0.000 |
| p1czc150 | 30 | 0 | 0 | 0 | 0 | 6.000 | 1.000 | 0.000 |
| p1czc300 | 30 | 0 | 0 | 0 | 0 | 6.000 | 1.000 | 0.000 |

**Resultado:** pasa. En los 90 mundos: Z→Y = 0, D→C = 0, C→C = 0, D→Z = 0 y `rho` = 0. La única ruta de D es D→Y, así que D no confunde C→Y. Z solo llega a Y a través de C (sin Z→Y ni Z→Z→Y), de modo que Z no es confusor de C→Y.

## 2. Separación de la correlación lograda (pareada)

| contraste | mediana Δ media|corr| | media | IC95 | frac pares Δ>0,05 |
|---|---|---|---|---|
| p1czc150 − p1czc000 | 0.248 | 0.262 | [0.182, 0.341] | 0.767 |
| p1czc300 − p1czc150 | 0.112 | 0.087 | [0.015, 0.146] | 0.667 |

**Criterio registrado** (mediana Δ ≥ 0,1 entre niveles consecutivos y ≥ 70 % de pares con Δ > 0,05): NO pasa.

## 3. Márgenes: ¿cambia algo más que la dependencia?

Cocientes pareados nivel / nivel 0. Puerta registrada: la mediana de `C_sd`, `media_share` y `abs_do_zero_norm` debe quedar dentro de ±20 %.

| magnitud | contraste | mediana_cociente | q10 | q90 | dentro_±20% |
|---|---|---|---|---|---|
| C_sd | p1czc150 / p1czc000 | 1.350 | 1.009 | 2.483 | False |
| C_sd | p1czc300 / p1czc000 | 2.056 | 1.065 | 3.619 | False |
| C_mean | p1czc150 / p1czc000 | 0.897 | 0.662 | 1.404 | True |
| C_mean | p1czc300 / p1czc000 | 1.185 | 0.624 | 2.367 | True |
| media_share | p1czc150 / p1czc000 | 1.011 | 0.964 | 1.102 | True |
| media_share | p1czc300 / p1czc000 | 1.005 | 0.902 | 1.417 | True |
| abs_do_zero_norm | p1czc150 / p1czc000 | 1.008 | 0.941 | 1.101 | True |
| abs_do_zero_norm | p1czc300 / p1czc000 | 1.036 | 0.897 | 1.478 | True |
| noise_to_y_sd | p1czc150 / p1czc000 | 0.594 | 0.206 | 0.814 | False |
| noise_to_y_sd | p1czc300 / p1czc000 | 0.502 | 0.123 | 1.039 | False |
| y_abs_sum | p1czc150 / p1czc000 | 1.009 | 0.967 | 1.069 | True |
| y_abs_sum | p1czc300 / p1czc000 | 1.003 | 0.805 | 1.152 | True |

**Puerta de márgenes:** NO pasa.

Medianas por nivel:

| level | mean_abs_corr | max_abs_corr | cond_raw | cond_transformed | rank_raw | C_mean | C_sd | C_q10 | C_q90 | media_share | noise_to_y_sd | abs_do_zero_norm | engine_vs_contrib |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p1czc000 | 0.119 | 0.264 | 1.436 | 1.895 | 4.000 | 2.813 | 1.375 | 1.141 | 5.268 | 0.394 | 0.093 | 0.094 | 0.046 |
| p1czc150 | 0.377 | 0.750 | 3.125 | 3.449 | 4.000 | 2.748 | 2.052 | 0.279 | 6.015 | 0.382 | 0.034 | 0.094 | 0.048 |
| p1czc300 | 0.468 | 0.844 | 5.189 | 3.923 | 4.000 | 3.742 | 2.710 | 0.160 | 8.253 | 0.390 | 0.045 | 0.096 | 0.031 |

- `cond_transformed`: número de condición con las transformaciones verdaderas de arrastre y saturación (canales estandarizados).
- `engine_vs_contrib`: discrepancia relativa máxima entre el efecto `do_zero` del motor (intervención en `[8, n_train)`) y la contribución observada del canal en esa ventana. Sin C→C, la diferencia corresponde al arrastre de exposiciones anteriores a la semana 8, que `do` en la ventana no elimina (3–5 %). No indica un error del motor.

## 4. Decisión

E14, con estos niveles, se denomina **«correlación inducida por Z con cambios de distribución»**.

Siguiendo la regla del diseñador, **no se ejecutan los 90 mundos como prueba confirmatoria** de multicolinealidad pura. Hay dos opciones registrables:

- (a) Ejecutar E14 tal como está, etiquetado como «correlación inducida por Z con cambios de distribución», informando junto a los errores los cambios de márgenes de esta tabla y usando métricas normalizadas por la magnitud del efecto verdadero de cada mundo.
- (b) **Control con márgenes fijados**: en cada nivel, reescalar la parte de cada canal explicada por Z para que la varianza total del canal coincida con la del nivel 0. Es decir, C_k = μ_k + s_k·(base_k + λ·v_k·Z) con s_k elegido para fijar sd(C_k). Esto exige intervenir los tensores del generador (API privada, como el motor `do`) y validarlo antes, porque cambia el SCM respecto al preset. Se propone solo como diseño; no se implementa sin aprobación.
