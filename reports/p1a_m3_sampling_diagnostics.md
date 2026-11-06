# P1a.1 — Diagnóstico y variantes de muestreo de M3 (brazo C, V3)

Protocolo: `docs/protocolo_P1B_registrado.md` §2.

**Mundos de desarrollo:** los 10 del piloto de la Entrega A.
- Ninguno está entre los 10 usados para elegir V3.
- Todos pertenecen a los 45 de `v1_1_m3`, consultados en P0 y en la Entrega A: **no son independientes**.

**Variantes**, sin tocar priors ni parametrización (misma posterior objetivo):
- S0r: referencia re-ejecutada;
- S1: 2000 + 2000;
- S2: matriz de masa de rango bajo de nutpie.

**Selección:** por número de ajustes `converged_strict` y, en caso de empate, por menor tiempo mediano. **No se ha calculado ninguna métrica frente a la verdad** para estas variantes.

## 1. Resumen y selección

| variante | n | converged_strict | secundario R-hat≤1,015 | escenarios con 0/2 | divergencias_tot | bfmi_min | frac_maxdepth_media | tiempo_mediano_s | tiempo_total_min | rss_max_mb |
|---|---|---|---|---|---|---|---|---|---|---|
| S0r | 10 | 7 | 9 | — | 0 | 0.746 | 0.035 | 228.308 | 38.985 | 919.961 |
| S1 | 10 | 9 | 10 | — | 0 | 0.765 | 0.043 | 287.250 | 55.668 | 1204.855 |
| S2 | 10 | 5 | 6 | S0,S3 | 1 | 0.648 | 0.000 | 110.498 | 18.545 | 925.250 |

**Variante elegida: S1** (9/10 `converged_strict`). Puerta registrada (≥ 8/10 y ningún escenario con 0/2): **PASA**.

La sensibilidad con R-hat ≤ 1,015 es secundaria y no cambia la regla.

## 2. Ruido del muestreador: la misma configuración dos veces

S0 del piloto de la Entrega A frente a su re-ejecución S0r (misma semilla):

| world_id | S0 piloto | S0r |
|---|---|---|
| S0_direct_only_T104_r00 | True | True |
| S0_direct_only_T104_r01 | True | True |
| S1_confounded_treatment_T104_r02 | True | True |
| S1_confounded_treatment_T208_r00 | True | True |
| S2_promo_drives_treatment_T104_r00 | True | True |
| S2_promo_drives_treatment_T208_r00 | False | False |
| S3_treatment_halo_T104_r01 | False | False |
| S3_treatment_halo_T208_r00 | True | True |
| S4_kitchen_sink_T104_r02 | True | True |
| S4_kitchen_sink_T208_r00 | False | False |

## 3. Diagnósticos por mundo y variante

| variante | world_id | converged_strict | rhat_max | ess_bulk_min | ess_tail_min | divergencias | bfmi_min | frac_maxdepth | prof_media | paso_medio | max|corr(log λ, log β)| | params_rhat>1.01 | params_ess<400 | tiempo_s | rss_mb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0r | S0_direct_only_T104_r00 | True | 1.004 | 722.109 | 752.903 | 0 | 0.764 | 0.018 | 8.552 | 0.030 | 0.990 |  |  | 292.616 | 594.965 |
| S0r | S0_direct_only_T104_r01 | True | 1.007 | 760.871 | 805.894 | 0 | 0.746 | 0.001 | 8.040 | 0.037 | 0.740 |  |  | 189.889 | 672.145 |
| S0r | S1_confounded_treatment_T104_r02 | True | 1.005 | 639.944 | 707.829 | 0 | 0.765 | 0.011 | 8.384 | 0.032 | 0.962 |  |  | 259.754 | 698.863 |
| S0r | S1_confounded_treatment_T208_r00 | True | 1.006 | 561.878 | 563.221 | 0 | 0.890 | 0.000 | 7.331 | 0.044 | 0.828 |  |  | 196.759 | 823.074 |
| S0r | S2_promo_drives_treatment_T104_r00 | True | 1.004 | 631.276 | 669.409 | 0 | 0.755 | 0.001 | 8.174 | 0.034 | 0.948 |  |  | 204.687 | 810.301 |
| S0r | S2_promo_drives_treatment_T208_r00 | False | 1.025 | 300.610 | 296.094 | 0 | 0.829 | 0.004 | 7.848 | 0.036 | 0.992 | {'saturation_lam': 1.0246, 'saturation_beta': 1.0248} | {'saturation_lam': 301, 'saturation_beta': 305} | 275.847 | 678.930 |
| S0r | S3_treatment_halo_T104_r01 | False | 1.011 | 612.271 | 817.840 | 0 | 0.815 | 0.004 | 8.386 | 0.033 | 0.568 | {'saturation_beta': 1.0109} |  | 208.207 | 740.117 |
| S0r | S3_treatment_halo_T208_r00 | True | 1.005 | 731.934 | 763.700 | 0 | 0.826 | 0.000 | 7.718 | 0.043 | 0.633 |  |  | 172.373 | 809.887 |
| S0r | S4_kitchen_sink_T104_r02 | True | 1.006 | 437.413 | 387.828 | 0 | 0.753 | 0.304 | 9.131 | 0.021 | 0.999 |  |  | 290.531 | 817.164 |
| S0r | S4_kitchen_sink_T208_r00 | False | 1.014 | 441.226 | 622.128 | 0 | 0.873 | 0.005 | 8.046 | 0.034 | 0.993 | {'saturation_lam': 1.0122, 'saturation_beta': 1.0141} |  | 248.409 | 919.961 |
| S1 | S0_direct_only_T104_r00 | True | 1.002 | 1467.039 | 1512.585 | 0 | 0.802 | 0.021 | 8.669 | 0.028 | 0.990 |  |  | 571.983 | 681.641 |
| S1 | S0_direct_only_T104_r01 | True | 1.004 | 1505.250 | 1371.594 | 0 | 0.777 | 0.002 | 8.118 | 0.033 | 0.752 |  |  | 388.759 | 810.730 |
| S1 | S1_confounded_treatment_T104_r02 | True | 1.002 | 1577.148 | 1699.552 | 0 | 0.779 | 0.025 | 8.467 | 0.031 | 0.959 |  |  | 455.167 | 841.949 |
| S1 | S1_confounded_treatment_T208_r00 | False | 1.015 | 578.227 | 624.458 | 0 | 0.913 | 0.000 | 7.380 | 0.044 | 0.850 | {'saturation_lam': 1.015, 'saturation_beta': 1.0137} |  | 277.177 | 1045.688 |
| S1 | S2_promo_drives_treatment_T104_r00 | True | 1.008 | 1010.619 | 1094.111 | 0 | 0.765 | 0.002 | 8.185 | 0.033 | 0.949 |  |  | 246.769 | 994.520 |
| S1 | S2_promo_drives_treatment_T208_r00 | True | 1.005 | 1038.394 | 1014.348 | 0 | 0.897 | 0.003 | 7.961 | 0.032 | 0.991 |  |  | 386.514 | 847.879 |
| S1 | S3_treatment_halo_T104_r01 | True | 1.003 | 1268.193 | 1609.062 | 0 | 0.872 | 0.015 | 8.606 | 0.028 | 0.562 |  |  | 244.248 | 950.992 |
| S1 | S3_treatment_halo_T208_r00 | True | 1.003 | 1163.768 | 986.755 | 0 | 0.802 | 0.000 | 7.686 | 0.040 | 0.603 |  |  | 203.374 | 1048.457 |
| S1 | S4_kitchen_sink_T104_r02 | True | 1.004 | 807.859 | 984.382 | 0 | 0.808 | 0.355 | 9.204 | 0.021 | 0.999 |  |  | 297.323 | 1051.109 |
| S1 | S4_kitchen_sink_T208_r00 | True | 1.004 | 1082.839 | 1324.398 | 0 | 0.828 | 0.005 | 8.069 | 0.034 | 0.993 |  |  | 268.755 | 1204.855 |
| S2 | S0_direct_only_T104_r00 | False | 1.018 | 413.002 | 396.551 | 0 | 0.791 | 0.000 | 5.963 | 0.070 | 0.990 | {'saturation_beta': 1.0182} |  | 98.876 | 597.953 |
| S2 | S0_direct_only_T104_r01 | False | 1.015 | 231.794 | 303.704 | 0 | 0.789 | 0.000 | 6.233 | 0.063 | 0.750 | {'saturation_beta': 1.0147, 'gamma_control': 1.0106} | {'saturation_beta': 232, 'gamma_control': 287} | 123.847 | 677.000 |
| S2 | S1_confounded_treatment_T104_r02 | True | 1.005 | 648.478 | 763.512 | 0 | 0.734 | 0.000 | 5.830 | 0.082 | 0.959 |  |  | 87.773 | 698.598 |
| S2 | S1_confounded_treatment_T208_r00 | True | 1.005 | 677.230 | 567.334 | 0 | 0.847 | 0.000 | 5.764 | 0.086 | 0.840 |  |  | 105.820 | 825.742 |
| S2 | S2_promo_drives_treatment_T104_r00 | True | 1.006 | 406.010 | 272.039 | 0 | 0.648 | 0.000 | 6.038 | 0.073 | 0.949 |  |  | 91.147 | 812.980 |
| S2 | S2_promo_drives_treatment_T208_r00 | True | 1.006 | 632.482 | 606.497 | 0 | 0.923 | 0.000 | 5.142 | 0.109 | 0.992 |  |  | 115.176 | 679.734 |
| S2 | S3_treatment_halo_T104_r01 | False | 1.010 | 595.964 | 617.118 | 0 | 0.824 | 0.000 | 6.843 | 0.050 | 0.592 | {'saturation_lam': 1.0101} |  | 156.682 | 744.254 |
| S2 | S3_treatment_halo_T208_r00 | False | 1.024 | 199.189 | 168.137 | 0 | 0.870 | 0.000 | 5.949 | 0.066 | 0.585 | {'saturation_beta': 1.0238} | {'saturation_beta': 199} | 115.658 | 812.930 |
| S2 | S4_kitchen_sink_T104_r02 | False | 1.008 | 612.391 | 695.264 | 1 | 0.776 | 0.000 | 5.686 | 0.086 | 0.999 |  |  | 84.667 | 822.227 |
| S2 | S4_kitchen_sink_T208_r00 | True | 1.003 | 756.003 | 823.568 | 0 | 0.824 | 0.000 | 5.775 | 0.087 | 0.994 |  |  | 133.070 | 925.250 |

