# P1a.0 — Control A/B/C: enmascaramiento frente a escala de `Y`

Protocolo: `docs/protocolo_P1B_registrado.md` §1. Todos los brazos usan V3, el muestreo S0, la misma semilla y la misma escala de canales. Son resultados `exploratory` (6 mundos).

| Brazo | Verosimilitud | Escala de `Y` |
|---|---|---|
| A (`legacy_w0`) | `[0, n_train)` | `max Y[0:n_train)` |
| B (control) | `[0, n_train)` | `max Y[8:n_train)` |
| C (`corrected_w8`) | `[8, n_train)` | `max Y[8:n_train)` |

## 1. Identificación del contraste (sin MCMC)

1. **Tests deterministas** (`tests/test_p1a_masking.py`):
   - `test_abc_scales`: B y C tienen la misma escala y difieren de A.
   - `test_abc_mask_is_the_only_difference_between_b_and_c`: `logp(B) − logp(C)` = suma de los términos de log-verosimilitud de `y` de B en las semanas 0–7, en puntos aleatorios. Es decir, C − B cambia solo la verosimilitud.
   - `test_b_equals_a_when_max_is_after_warmup`: si el máximo de `Y` cae después de la semana 8, B ≡ A exactamente.
2. **Consecuencia para la Entrega A:** en los 10 mundos piloto, `max Y[0:n) = max Y[8:n)`, de modo que la escala de A y C era idéntica y **la comparación A frente a C de la Entrega A ya aislaba el enmascaramiento**. La escala solo difiere en 6 de los 45 mundos de `v1_1_m3` y en 26 de los 150 de F2.

## 2. Priors en unidades originales

Las priors de `intercept`, `saturation_beta`, `gamma_control`, `gamma_fourier` y `y_sigma` están en unidades escaladas: en unidades de `Y` se multiplican por la escala. Usar `max Y[8:n)` en lugar de `max Y[0:n)` las **estrecha** en el factor `s_B/s_A`.

`adstock_alpha` y `saturation_lam` no dependen de la escala de `Y`. `lam` sí depende de la escala de canales, que es la misma en los tres brazos.

| world_id | s_A | s_B = s_C | s_B/s_A | válido A | válido B | válido C |
|---|---|---|---|---|---|---|
| S0_direct_only_T208_r01 | 11.653 | 11.203 | 0.961 | True | True | True |
| S0_direct_only_T52_r01 | 12.243 | 11.325 | 0.925 | True | True | False |
| S1_confounded_treatment_T208_r02 | 12.152 | 11.529 | 0.949 | True | True | True |
| S2_promo_drives_treatment_T104_r02 | 13.559 | 12.122 | 0.894 | False | True | False |
| S2_promo_drives_treatment_T208_r02 | 15.354 | 15.025 | 0.979 | False | True | True |
| S3_treatment_halo_T52_r02 | 8.397 | 7.699 | 0.917 | False | False | True |

## 3. Ajustes y diagnósticos

| variante | world_id | converged_strict | rhat_max | ess_bulk_min | divergencias | bfmi_min | escala_Y | ventana_verosimilitud | tiempo_s |
|---|---|---|---|---|---|---|---|---|---|
| A | S0_direct_only_T208_r01 | True | 1.009 | 489.217 | 0 | 0.850 | 11.653 | [0, 166] | 93.571 |
| A | S0_direct_only_T52_r01 | True | 1.004 | 677.963 | 0 | 0.790 | 12.243 | [0, 42] | 105.096 |
| A | S1_confounded_treatment_T208_r02 | True | 1.006 | 415.399 | 0 | 0.828 | 12.152 | [0, 166] | 99.019 |
| A | S2_promo_drives_treatment_T104_r02 | False | 1.011 | 715.673 | 0 | 0.803 | 13.559 | [0, 83] | 131.601 |
| A | S2_promo_drives_treatment_T208_r02 | False | 1.014 | 426.872 | 0 | 0.892 | 15.354 | [0, 166] | 137.280 |
| A | S3_treatment_halo_T52_r02 | False | 1.016 | 342.811 | 0 | 0.821 | 8.397 | [0, 42] | 85.368 |
| B | S0_direct_only_T208_r01 | True | 1.007 | 631.428 | 0 | 0.810 | 11.203 | [0, 166] | 80.295 |
| B | S0_direct_only_T52_r01 | True | 1.003 | 756.894 | 0 | 0.808 | 11.325 | [0, 42] | 126.587 |
| B | S1_confounded_treatment_T208_r02 | True | 1.008 | 504.475 | 0 | 0.825 | 11.529 | [0, 166] | 146.524 |
| B | S2_promo_drives_treatment_T104_r02 | True | 1.005 | 721.506 | 0 | 0.788 | 12.122 | [0, 83] | 132.390 |
| B | S2_promo_drives_treatment_T208_r02 | True | 1.008 | 506.542 | 0 | 0.826 | 15.025 | [0, 166] | 132.533 |
| B | S3_treatment_halo_T52_r02 | False | 1.009 | 305.595 | 0 | 0.845 | 7.699 | [0, 42] | 93.123 |
| C | S0_direct_only_T208_r01 | True | 1.007 | 652.343 | 0 | 0.783 | 11.203 | [8, 166] | 270.396 |
| C | S0_direct_only_T52_r01 | False | 1.010 | 688.531 | 0 | 0.815 | 11.325 | [8, 42] | 268.120 |
| C | S1_confounded_treatment_T208_r02 | True | 1.008 | 420.511 | 0 | 0.855 | 11.529 | [8, 166] | 345.661 |
| C | S2_promo_drives_treatment_T104_r02 | False | 1.011 | 512.448 | 0 | 0.814 | 12.122 | [8, 83] | 232.711 |
| C | S2_promo_drives_treatment_T208_r02 | True | 1.008 | 473.177 | 0 | 0.839 | 15.025 | [8, 166] | 279.206 |
| C | S3_treatment_halo_T52_r02 | True | 1.009 | 611.749 | 0 | 0.847 | 7.699 | [8, 42] | 225.520 |

## 4. Contrastes (directos, ventana `[8, n_train)`, media por mundo, bootstrap de mundos; n = 6, `exploratory`)

| contraste | subconjunto | métrica | n_mundos | media | IC95 (exploratory) |
|---|---|---|---|---|---|
| B − A (escala) | todos | bias_norm | 6 | 0.0000 | [-0.0003, 0.0003] |
| B − A (escala) | todos | cov95 | 6 | -0.0026 | [-0.0095, 0.0017] |
| B − A (escala) | todos | width95_norm | 6 | -0.0001 | [-0.0013, 0.0015] |
| B − A (escala) | todos | mae_norm | 6 | 0.0000 | [-0.0002, 0.0003] |
| B − A (escala) | ambos válidos | bias_norm | 3 | 0.0000 | [-0.0007, 0.0007] |
| B − A (escala) | ambos válidos | cov95 | 3 | -0.0063 | [-0.0190, 0.0000] |
| B − A (escala) | ambos válidos | width95_norm | 3 | -0.0001 | [-0.0026, 0.0035] |
| B − A (escala) | ambos válidos | mae_norm | 3 | 0.0001 | [-0.0003, 0.0007] |
| C − B (máscara) | todos | bias_norm | 6 | 0.0345 | [0.0131, 0.0553] |
| C − B (máscara) | todos | cov95 | 6 | 0.0917 | [-0.1897, 0.4196] |
| C − B (máscara) | todos | width95_norm | 6 | 0.0476 | [0.0208, 0.0785] |
| C − B (máscara) | todos | mae_norm | 6 | -0.0068 | [-0.0314, 0.0104] |
| C − B (máscara) | ambos válidos | bias_norm | 3 | 0.0597 | [0.0508, 0.0725] |
| C − B (máscara) | ambos válidos | cov95 | 3 | 0.1060 | [-0.4589, 0.8370] |
| C − B (máscara) | ambos válidos | width95_norm | 3 | 0.0385 | [0.0237, 0.0628] |
| C − B (máscara) | ambos válidos | mae_norm | 3 | -0.0139 | [-0.0652, 0.0207] |
| C − A (total) | todos | bias_norm | 6 | 0.0345 | [0.0133, 0.0550] |
| C − A (total) | todos | cov95 | 6 | 0.0891 | [-0.1886, 0.4107] |
| C − A (total) | todos | width95_norm | 6 | 0.0475 | [0.0202, 0.0780] |
| C − A (total) | todos | mae_norm | 6 | -0.0067 | [-0.0312, 0.0104] |
| C − A (total) | ambos válidos | bias_norm | 2 | 0.0639 | [0.0553, 0.0726] |
| C − A (total) | ambos válidos | cov95 | 2 | 0.3790 | [-0.0601, 0.8180] |
| C − A (total) | ambos válidos | width95_norm | 2 | 0.0441 | [0.0279, 0.0602] |
| C − A (total) | ambos válidos | mae_norm | 2 | -0.0309 | [-0.0653, 0.0035] |

Por mundo:

| world_id | bias_norm·A | bias_norm·B | bias_norm·C | mae_norm·A | mae_norm·B | mae_norm·C | cov95·A | cov95·B | cov95·C | cov80·A | cov80·B | cov80·C | cov50·A | cov50·B | cov50·C | width95_norm·A | width95_norm·B | width95_norm·C |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0_direct_only_T208_r01 | -0.0765 | -0.0764 | -0.0039 | 0.0765 | 0.0764 | 0.0112 | 0.1772 | 0.1582 | 0.9953 | 0.0633 | 0.0633 | 0.9715 | 0.0158 | 0.0142 | 0.7816 | 0.0637 | 0.0612 | 0.1240 |
| S0_direct_only_T52_r01 | -0.0940 | -0.0933 | -0.0936 | 0.1027 | 0.1024 | 0.0936 | 0.5000 | 0.5000 | 0.5000 | 0.2500 | 0.2500 | 0.5000 | 0.0515 | 0.0368 | 0.0662 | 0.0699 | 0.0733 | 0.1242 |
| S1_confounded_treatment_T208_r02 | -0.0686 | -0.0693 | -0.0133 | 0.0734 | 0.0741 | 0.0770 | 0.2563 | 0.2563 | 0.1962 | 0.2342 | 0.2263 | 0.0759 | 0.1535 | 0.1503 | 0.0174 | 0.0677 | 0.0667 | 0.0957 |
| S2_promo_drives_treatment_T104_r02 | -0.0302 | -0.0301 | -0.0252 | 0.0302 | 0.0302 | 0.0321 | 0.4900 | 0.4933 | 0.5000 | 0.3267 | 0.3300 | 0.4833 | 0.2700 | 0.2700 | 0.0133 | 0.0264 | 0.0268 | 0.0299 |
| S2_promo_drives_treatment_T208_r02 | -0.0206 | -0.0209 | 0.0299 | 0.0274 | 0.0273 | 0.0480 | 0.7358 | 0.7358 | 0.2769 | 0.7089 | 0.7104 | 0.2500 | 0.5934 | 0.5918 | 0.2500 | 0.0497 | 0.0488 | 0.0725 |
| S3_treatment_halo_T52_r02 | -0.0495 | -0.0494 | -0.0264 | 0.0497 | 0.0496 | 0.0576 | 0.6667 | 0.6667 | 0.8922 | 0.4216 | 0.4216 | 0.3333 | 0.0784 | 0.0686 | 0.3235 | 0.0737 | 0.0741 | 0.1900 |

