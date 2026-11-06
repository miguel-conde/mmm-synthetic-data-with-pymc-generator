# P1b — E10A: confusión (piloto pareado)

Diseño registrado antes de generar: `docs/protocolo_P1_registrado.md`, Anexo A. T = 104, 40 réplicas por nivel. Niveles pareados con la misma semilla de mundo: idénticos DAG e innovaciones exógenas; solo cambia el parámetro del mecanismo (test `test_e10a_mechanisms_are_paired`).

- Ventana de ajuste `[8, n_train)`.
- Verdad: el contrafactual `do` de **cada mundo** (`research_validated_private_api`).
- Sin M3.
- M2p y M2p_D son **privilegiados** (transformaciones verdaderas; M2p_D además observa D). Se presentan separados de los modelos ciegos.

## 1. Coste y validez del motor

| run | mundos | ajustes | fallos | motor_validado | tiempo_ajustes_min |
|---|---|---|---|---|---|
| v1_2_p1b_e10a_dc | 120 | 960 | 0 | 120 | 7.9 |
| v1_2_p1b_e10a_dy | 120 | 960 | 0 | 120 | 8.0 |
| v1_2_p1b_e10a_rho | 120 | 960 | 0 | 120 | 7.3 |

## 2. ¿Qué cambia realmente con cada nivel? (descriptivo)

Correlación lograda entre canales y entre cada canal y la base o la contribución latente de D. Es información privilegiada, solo descriptiva. Correlación observada ≠ confusión causal ≠ falta de identificación.

| mecanismo | level | corr_C_baseline_media_abs | corr_C_latentD_media_abs |
|---|---|---|---|
| dc | p1bdc000 | 0.230 | 0.268 |
| dc | p1bdc025 | 0.233 | 0.278 |
| dc | p1bdc050 | 0.258 | 0.327 |
| dy | p1bdy000 | 0.211 |  |
| dy | p1bdy025 | 0.233 | 0.286 |
| dy | p1bdy050 | 0.251 | 0.286 |
| rho | p1brho000 | 0.238 | 0.274 |
| rho | p1brho030 | 0.244 | 0.276 |
| rho | p1brho060 | 0.251 | 0.285 |

| mecanismo | level | mean_abs_channel_corr | condition_number | media_share_of_y | noise_to_y_sd | confounding_strength |
|---|---|---|---|---|---|---|
| dc | p1bdc000 | 0.158 | 1.640 | 0.408 | 0.068 | 0.000 |
| dc | p1bdc025 | 0.163 | 1.652 | 0.408 | 0.064 | 0.000 |
| dc | p1bdc050 | 0.190 | 1.734 | 0.408 | 0.061 | 0.000 |
| dy | p1bdy000 | 0.168 | 1.663 | 0.408 | 0.075 | 0.000 |
| dy | p1bdy025 | 0.168 | 1.663 | 0.408 | 0.066 | 0.000 |
| dy | p1bdy050 | 0.168 | 1.663 | 0.408 | 0.053 | 0.000 |
| rho | p1brho000 | 0.149 | 1.629 | 0.404 | 0.075 | 0.000 |
| rho | p1brho030 | 0.154 | 1.649 | 0.404 | 0.072 | 0.300 |
| rho | p1brho060 | 0.171 | 1.699 | 0.404 | 0.068 | 0.600 |

## 3. Métrica primaria: sesgo del efecto `do_zero` en canales directos

`err_norm = (Δ_est − Δ_true)/Σ|Y|`, promedio por mundo sobre directos. Contraste pareado = nivel alto − nivel 0 del mismo par. IC95 por bootstrap de pares.

**Potencia:** solo se declara para los privilegiados M2p y M2p_D. Para los ciegos (M0, M1, M2, M2_noZ, M5/M6 si tienen efecto implicado), los intervalos se informan sin pretensión de potencia.

| mecanismo | modelo | nivel | contraste | n_pares | sesgo_do_zero | IC95_lo | IC95_hi |
|---|---|---|---|---|---|---|---|
| dc | M0_ols | p1bdc025 − p1bdc000 | pareado | 40 | -0.0011 | -0.0020 | -0.0003 |
| dc | M0_ols | p1bdc050 − p1bdc000 | pareado | 40 | -0.0025 | -0.0042 | -0.0008 |
| dc | M1_ridge | p1bdc025 − p1bdc000 | pareado | 40 | -0.0014 | -0.0023 | -0.0006 |
| dc | M1_ridge | p1bdc050 − p1bdc000 | pareado | 40 | -0.0021 | -0.0044 | 0.0005 |
| dc | M2_adstock_sat | p1bdc025 − p1bdc000 | pareado | 40 | -0.0076 | -0.0286 | 0.0134 |
| dc | M2_adstock_sat | p1bdc050 − p1bdc000 | pareado | 40 | -0.0018 | -0.0338 | 0.0297 |
| dc | M2_adstock_sat_noZ | p1bdc025 − p1bdc000 | pareado | 40 | -0.0162 | -0.0493 | 0.0122 |
| dc | M2_adstock_sat_noZ | p1bdc050 − p1bdc000 | pareado | 40 | -0.0201 | -0.0578 | 0.0140 |
| dc | M2p_true_transforms | p1bdc025 − p1bdc000 | pareado | 40 | -0.0077 | -0.0171 | -0.0029 |
| dc | M2p_true_transforms | p1bdc050 − p1bdc000 | pareado | 40 | -0.0084 | -0.0133 | -0.0046 |
| dc | M2p_true_transforms_plus_D | p1bdc025 − p1bdc000 | pareado | 40 | 0.0000 | -0.0009 | 0.0011 |
| dc | M2p_true_transforms_plus_D | p1bdc050 − p1bdc000 | pareado | 40 | 0.0003 | -0.0016 | 0.0031 |
| dy | M0_ols | p1bdy025 − p1bdy000 | pareado | 40 | -0.0015 | -0.0025 | -0.0004 |
| dy | M0_ols | p1bdy050 − p1bdy000 | pareado | 40 | -0.0029 | -0.0050 | -0.0008 |
| dy | M1_ridge | p1bdy025 − p1bdy000 | pareado | 40 | -0.0027 | -0.0050 | -0.0009 |
| dy | M1_ridge | p1bdy050 − p1bdy000 | pareado | 40 | -0.0035 | -0.0072 | -0.0001 |
| dy | M2_adstock_sat | p1bdy025 − p1bdy000 | pareado | 40 | -0.0159 | -0.0390 | 0.0091 |
| dy | M2_adstock_sat | p1bdy050 − p1bdy000 | pareado | 40 | -0.0617 | -0.0931 | -0.0298 |
| dy | M2_adstock_sat_noZ | p1bdy025 − p1bdy000 | pareado | 40 | -0.0216 | -0.0467 | 0.0076 |
| dy | M2_adstock_sat_noZ | p1bdy050 − p1bdy000 | pareado | 40 | -0.0292 | -0.0614 | 0.0037 |
| dy | M2p_true_transforms | p1bdy025 − p1bdy000 | pareado | 40 | -0.0056 | -0.0127 | 0.0022 |
| dy | M2p_true_transforms | p1bdy050 − p1bdy000 | pareado | 40 | -0.0112 | -0.0255 | 0.0043 |
| dy | M2p_true_transforms_plus_D | p1bdy025 − p1bdy000 | pareado | 40 | 0.0000 | 0.0000 | 0.0001 |
| dy | M2p_true_transforms_plus_D | p1bdy050 − p1bdy000 | pareado | 40 | 0.0000 | 0.0000 | 0.0001 |
| rho | M0_ols | p1brho030 − p1brho000 | pareado | 40 | -0.0021 | -0.0039 | -0.0005 |
| rho | M0_ols | p1brho060 − p1brho000 | pareado | 40 | -0.0048 | -0.0079 | -0.0018 |
| rho | M1_ridge | p1brho030 − p1brho000 | pareado | 40 | -0.0021 | -0.0041 | -0.0003 |
| rho | M1_ridge | p1brho060 − p1brho000 | pareado | 40 | -0.0056 | -0.0092 | -0.0022 |
| rho | M2_adstock_sat | p1brho030 − p1brho000 | pareado | 40 | -0.0247 | -0.0447 | -0.0078 |
| rho | M2_adstock_sat | p1brho060 − p1brho000 | pareado | 40 | -0.0163 | -0.0392 | 0.0040 |
| rho | M2_adstock_sat_noZ | p1brho030 − p1brho000 | pareado | 40 | 0.0074 | -0.0165 | 0.0328 |
| rho | M2_adstock_sat_noZ | p1brho060 − p1brho000 | pareado | 40 | -0.0005 | -0.0301 | 0.0298 |
| rho | M2p_true_transforms | p1brho030 − p1brho000 | pareado | 40 | -0.0026 | -0.0060 | 0.0002 |
| rho | M2p_true_transforms | p1brho060 − p1brho000 | pareado | 40 | -0.0049 | -0.0105 | -0.0001 |
| rho | M2p_true_transforms_plus_D | p1brho030 − p1brho000 | pareado | 40 | -0.0020 | -0.0038 | -0.0007 |
| rho | M2p_true_transforms_plus_D | p1brho060 − p1brho000 | pareado | 40 | -0.0034 | -0.0056 | -0.0015 |

Por nivel:

| mecanismo | modelo | nivel | contraste | n_pares | sesgo_do_zero | IC95_lo | IC95_hi |
|---|---|---|---|---|---|---|---|
| dc | M0_ols | p1bdc000 | nivel | 40 | 0.0743 | 0.0680 | 0.0813 |
| dc | M0_ols | p1bdc025 | nivel | 40 | 0.0731 | 0.0667 | 0.0804 |
| dc | M0_ols | p1bdc050 | nivel | 40 | 0.0718 | 0.0650 | 0.0792 |
| dc | M1_ridge | p1bdc000 | nivel | 40 | 0.0789 | 0.0721 | 0.0866 |
| dc | M1_ridge | p1bdc025 | nivel | 40 | 0.0775 | 0.0706 | 0.0850 |
| dc | M1_ridge | p1bdc050 | nivel | 40 | 0.0768 | 0.0699 | 0.0847 |
| dc | M2_adstock_sat | p1bdc000 | nivel | 40 | -0.0639 | -0.0927 | -0.0348 |
| dc | M2_adstock_sat | p1bdc025 | nivel | 40 | -0.0715 | -0.0975 | -0.0455 |
| dc | M2_adstock_sat | p1bdc050 | nivel | 40 | -0.0657 | -0.0926 | -0.0401 |
| dc | M2_adstock_sat_noZ | p1bdc000 | nivel | 40 | -0.0746 | -0.1076 | -0.0392 |
| dc | M2_adstock_sat_noZ | p1bdc025 | nivel | 40 | -0.0909 | -0.1350 | -0.0486 |
| dc | M2_adstock_sat_noZ | p1bdc050 | nivel | 40 | -0.0947 | -0.1391 | -0.0554 |
| dc | M2p_true_transforms | p1bdc000 | nivel | 40 | -0.0014 | -0.0103 | 0.0093 |
| dc | M2p_true_transforms | p1bdc025 | nivel | 40 | -0.0091 | -0.0244 | 0.0038 |
| dc | M2p_true_transforms | p1bdc050 | nivel | 40 | -0.0098 | -0.0207 | 0.0017 |
| dc | M2p_true_transforms_plus_D | p1bdc000 | nivel | 40 | -0.0006 | -0.0069 | 0.0046 |
| dc | M2p_true_transforms_plus_D | p1bdc025 | nivel | 40 | -0.0006 | -0.0060 | 0.0042 |
| dc | M2p_true_transforms_plus_D | p1bdc050 | nivel | 40 | -0.0003 | -0.0046 | 0.0041 |
| dy | M0_ols | p1bdy000 | nivel | 40 | 0.0746 | 0.0682 | 0.0819 |
| dy | M0_ols | p1bdy025 | nivel | 40 | 0.0732 | 0.0667 | 0.0805 |
| dy | M0_ols | p1bdy050 | nivel | 40 | 0.0717 | 0.0652 | 0.0792 |
| dy | M1_ridge | p1bdy000 | nivel | 40 | 0.0804 | 0.0734 | 0.0880 |
| dy | M1_ridge | p1bdy025 | nivel | 40 | 0.0776 | 0.0709 | 0.0853 |
| dy | M1_ridge | p1bdy050 | nivel | 40 | 0.0768 | 0.0697 | 0.0851 |
| dy | M2_adstock_sat | p1bdy000 | nivel | 40 | -0.0361 | -0.0603 | -0.0128 |
| dy | M2_adstock_sat | p1bdy025 | nivel | 40 | -0.0520 | -0.0745 | -0.0285 |
| dy | M2_adstock_sat | p1bdy050 | nivel | 40 | -0.0978 | -0.1328 | -0.0620 |
| dy | M2_adstock_sat_noZ | p1bdy000 | nivel | 40 | -0.0653 | -0.1058 | -0.0275 |
| dy | M2_adstock_sat_noZ | p1bdy025 | nivel | 40 | -0.0868 | -0.1310 | -0.0448 |
| dy | M2_adstock_sat_noZ | p1bdy050 | nivel | 40 | -0.0945 | -0.1405 | -0.0520 |
| dy | M2p_true_transforms | p1bdy000 | nivel | 40 | -0.0028 | -0.0107 | 0.0032 |
| dy | M2p_true_transforms | p1bdy025 | nivel | 40 | -0.0084 | -0.0218 | 0.0030 |
| dy | M2p_true_transforms | p1bdy050 | nivel | 40 | -0.0140 | -0.0335 | 0.0049 |
| dy | M2p_true_transforms_plus_D | p1bdy000 | nivel | 40 | -0.0005 | -0.0057 | 0.0041 |
| dy | M2p_true_transforms_plus_D | p1bdy025 | nivel | 40 | -0.0005 | -0.0057 | 0.0041 |
| dy | M2p_true_transforms_plus_D | p1bdy050 | nivel | 40 | -0.0005 | -0.0056 | 0.0042 |
| rho | M0_ols | p1brho000 | nivel | 40 | 0.0742 | 0.0685 | 0.0803 |
| rho | M0_ols | p1brho030 | nivel | 40 | 0.0721 | 0.0661 | 0.0785 |
| rho | M0_ols | p1brho060 | nivel | 40 | 0.0694 | 0.0633 | 0.0763 |
| rho | M1_ridge | p1brho000 | nivel | 40 | 0.0769 | 0.0710 | 0.0830 |
| rho | M1_ridge | p1brho030 | nivel | 40 | 0.0748 | 0.0687 | 0.0812 |
| rho | M1_ridge | p1brho060 | nivel | 40 | 0.0714 | 0.0651 | 0.0780 |
| rho | M2_adstock_sat | p1brho000 | nivel | 40 | -0.0262 | -0.0512 | -0.0018 |
| rho | M2_adstock_sat | p1brho030 | nivel | 40 | -0.0509 | -0.0854 | -0.0192 |
| rho | M2_adstock_sat | p1brho060 | nivel | 40 | -0.0425 | -0.0700 | -0.0164 |
| rho | M2_adstock_sat_noZ | p1brho000 | nivel | 40 | -0.0416 | -0.0806 | -0.0064 |
| rho | M2_adstock_sat_noZ | p1brho030 | nivel | 40 | -0.0342 | -0.0606 | -0.0088 |
| rho | M2_adstock_sat_noZ | p1brho060 | nivel | 40 | -0.0421 | -0.0696 | -0.0148 |
| rho | M2p_true_transforms | p1brho000 | nivel | 40 | 0.0020 | -0.0039 | 0.0078 |
| rho | M2p_true_transforms | p1brho030 | nivel | 40 | -0.0006 | -0.0065 | 0.0055 |
| rho | M2p_true_transforms | p1brho060 | nivel | 40 | -0.0029 | -0.0091 | 0.0037 |
| rho | M2p_true_transforms_plus_D | p1brho000 | nivel | 40 | -0.0009 | -0.0024 | 0.0006 |
| rho | M2p_true_transforms_plus_D | p1brho030 | nivel | 40 | -0.0029 | -0.0052 | -0.0009 |
| rho | M2p_true_transforms_plus_D | p1brho060 | nivel | 40 | -0.0043 | -0.0068 | -0.0019 |

## 4. Métricas secundarias

Sesgo de contribución directa, MAE de contribución y RMSE de predicción futura.

| mecanismo | métrica | modelo | nivel | n | media | IC95 |
|---|---|---|---|---|---|---|
| dc | channel_total_bias_norm·direct | M0_ols | p1bdc000 | 40 | -0.0770 | [-0.0845, -0.0705] |
| dc | channel_total_bias_norm·direct | M0_ols | p1bdc025 | 40 | -0.0759 | [-0.0835, -0.0691] |
| dc | channel_total_bias_norm·direct | M0_ols | p1bdc050 | 40 | -0.0745 | [-0.0823, -0.0675] |
| dc | channel_total_bias_norm·direct | M1_ridge | p1bdc000 | 40 | -0.0816 | [-0.0897, -0.0746] |
| dc | channel_total_bias_norm·direct | M1_ridge | p1bdc025 | 40 | -0.0802 | [-0.0880, -0.0731] |
| dc | channel_total_bias_norm·direct | M1_ridge | p1bdc050 | 40 | -0.0795 | [-0.0877, -0.0722] |
| dc | channel_total_bias_norm·direct | M2_adstock_sat | p1bdc000 | 40 | 0.0678 | [0.0370, 0.0983] |
| dc | channel_total_bias_norm·direct | M2_adstock_sat | p1bdc025 | 40 | 0.0763 | [0.0487, 0.1036] |
| dc | channel_total_bias_norm·direct | M2_adstock_sat | p1bdc050 | 40 | 0.0701 | [0.0430, 0.0984] |
| dc | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1bdc000 | 40 | 0.0793 | [0.0418, 0.1142] |
| dc | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1bdc025 | 40 | 0.0963 | [0.0514, 0.1430] |
| dc | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1bdc050 | 40 | 0.0999 | [0.0590, 0.1467] |
| dc | channel_total_bias_norm·direct | M2p_true_transforms | p1bdc000 | 40 | 0.0015 | [-0.0097, 0.0108] |
| dc | channel_total_bias_norm·direct | M2p_true_transforms | p1bdc025 | 40 | 0.0095 | [-0.0041, 0.0254] |
| dc | channel_total_bias_norm·direct | M2p_true_transforms | p1bdc050 | 40 | 0.0101 | [-0.0020, 0.0215] |
| dc | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1bdc000 | 40 | 0.0007 | [-0.0048, 0.0073] |
| dc | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1bdc025 | 40 | 0.0006 | [-0.0043, 0.0063] |
| dc | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1bdc050 | 40 | 0.0003 | [-0.0042, 0.0048] |
| dc | contrib_mae_norm | M0_ols | p1bdc000 | 40 | 0.0772 | [0.0708, 0.0847] |
| dc | contrib_mae_norm | M0_ols | p1bdc025 | 40 | 0.0762 | [0.0696, 0.0837] |
| dc | contrib_mae_norm | M0_ols | p1bdc050 | 40 | 0.0754 | [0.0687, 0.0831] |
| dc | contrib_mae_norm | M1_ridge | p1bdc000 | 40 | 0.0817 | [0.0747, 0.0897] |
| dc | contrib_mae_norm | M1_ridge | p1bdc025 | 40 | 0.0803 | [0.0733, 0.0881] |
| dc | contrib_mae_norm | M1_ridge | p1bdc050 | 40 | 0.0798 | [0.0726, 0.0880] |
| dc | contrib_mae_norm | M2_adstock_sat | p1bdc000 | 40 | 0.1358 | [0.1137, 0.1604] |
| dc | contrib_mae_norm | M2_adstock_sat | p1bdc025 | 40 | 0.1386 | [0.1166, 0.1614] |
| dc | contrib_mae_norm | M2_adstock_sat | p1bdc050 | 40 | 0.1275 | [0.1048, 0.1519] |
| dc | contrib_mae_norm | M2_adstock_sat_noZ | p1bdc000 | 40 | 0.1554 | [0.1262, 0.1876] |
| dc | contrib_mae_norm | M2_adstock_sat_noZ | p1bdc025 | 40 | 0.1653 | [0.1301, 0.2024] |
| dc | contrib_mae_norm | M2_adstock_sat_noZ | p1bdc050 | 40 | 0.1618 | [0.1309, 0.1991] |
| dc | contrib_mae_norm | M2p_true_transforms | p1bdc000 | 40 | 0.0279 | [0.0204, 0.0374] |
| dc | contrib_mae_norm | M2p_true_transforms | p1bdc025 | 40 | 0.0311 | [0.0210, 0.0454] |
| dc | contrib_mae_norm | M2p_true_transforms | p1bdc050 | 40 | 0.0291 | [0.0205, 0.0401] |
| dc | contrib_mae_norm | M2p_true_transforms_plus_D | p1bdc000 | 40 | 0.0116 | [0.0073, 0.0173] |
| dc | contrib_mae_norm | M2p_true_transforms_plus_D | p1bdc025 | 40 | 0.0110 | [0.0071, 0.0162] |
| dc | contrib_mae_norm | M2p_true_transforms_plus_D | p1bdc050 | 40 | 0.0103 | [0.0069, 0.0147] |
| dc | rmse_scaled | M0_ols | p1bdc000 | 40 | 0.0628 | [0.0523, 0.0755] |
| dc | rmse_scaled | M0_ols | p1bdc025 | 40 | 0.0705 | [0.0582, 0.0852] |
| dc | rmse_scaled | M0_ols | p1bdc050 | 40 | 0.0789 | [0.0644, 0.0957] |
| dc | rmse_scaled | M1_ridge | p1bdc000 | 40 | 0.0620 | [0.0516, 0.0741] |
| dc | rmse_scaled | M1_ridge | p1bdc025 | 40 | 0.0695 | [0.0568, 0.0844] |
| dc | rmse_scaled | M1_ridge | p1bdc050 | 40 | 0.0849 | [0.0668, 0.1059] |
| dc | rmse_scaled | M2_adstock_sat | p1bdc000 | 40 | 0.0612 | [0.0512, 0.0721] |
| dc | rmse_scaled | M2_adstock_sat | p1bdc025 | 40 | 0.0615 | [0.0505, 0.0732] |
| dc | rmse_scaled | M2_adstock_sat | p1bdc050 | 40 | 0.0599 | [0.0501, 0.0710] |
| dc | rmse_scaled | M2_adstock_sat_noZ | p1bdc000 | 40 | 0.0896 | [0.0731, 0.1097] |
| dc | rmse_scaled | M2_adstock_sat_noZ | p1bdc025 | 40 | 0.0878 | [0.0715, 0.1089] |
| dc | rmse_scaled | M2_adstock_sat_noZ | p1bdc050 | 40 | 0.0844 | [0.0690, 0.1031] |
| dc | rmse_scaled | M2p_true_transforms | p1bdc000 | 40 | 0.0513 | [0.0426, 0.0610] |
| dc | rmse_scaled | M2p_true_transforms | p1bdc025 | 40 | 0.0507 | [0.0423, 0.0603] |
| dc | rmse_scaled | M2p_true_transforms | p1bdc050 | 40 | 0.0486 | [0.0402, 0.0581] |
| dc | rmse_scaled | M2p_true_transforms_plus_D | p1bdc000 | 40 | 0.0252 | [0.0191, 0.0326] |
| dc | rmse_scaled | M2p_true_transforms_plus_D | p1bdc025 | 40 | 0.0251 | [0.0191, 0.0322] |
| dc | rmse_scaled | M2p_true_transforms_plus_D | p1bdc050 | 40 | 0.0249 | [0.0191, 0.0319] |
| dy | channel_total_bias_norm·direct | M0_ols | p1bdy000 | 40 | -0.0774 | [-0.0851, -0.0706] |
| dy | channel_total_bias_norm·direct | M0_ols | p1bdy025 | 40 | -0.0759 | [-0.0835, -0.0691] |
| dy | channel_total_bias_norm·direct | M0_ols | p1bdy050 | 40 | -0.0745 | [-0.0823, -0.0676] |
| dy | channel_total_bias_norm·direct | M1_ridge | p1bdy000 | 40 | -0.0831 | [-0.0910, -0.0759] |
| dy | channel_total_bias_norm·direct | M1_ridge | p1bdy025 | 40 | -0.0804 | [-0.0882, -0.0733] |
| dy | channel_total_bias_norm·direct | M1_ridge | p1bdy050 | 40 | -0.0796 | [-0.0882, -0.0722] |
| dy | channel_total_bias_norm·direct | M2_adstock_sat | p1bdy000 | 40 | 0.0384 | [0.0140, 0.0640] |
| dy | channel_total_bias_norm·direct | M2_adstock_sat | p1bdy025 | 40 | 0.0553 | [0.0306, 0.0789] |
| dy | channel_total_bias_norm·direct | M2_adstock_sat | p1bdy050 | 40 | 0.1042 | [0.0664, 0.1412] |
| dy | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1bdy000 | 40 | 0.0693 | [0.0297, 0.1120] |
| dy | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1bdy025 | 40 | 0.0920 | [0.0475, 0.1386] |
| dy | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1bdy050 | 40 | 0.1000 | [0.0552, 0.1486] |
| dy | channel_total_bias_norm·direct | M2p_true_transforms | p1bdy000 | 40 | 0.0029 | [-0.0034, 0.0111] |
| dy | channel_total_bias_norm·direct | M2p_true_transforms | p1bdy025 | 40 | 0.0087 | [-0.0033, 0.0227] |
| dy | channel_total_bias_norm·direct | M2p_true_transforms | p1bdy050 | 40 | 0.0145 | [-0.0052, 0.0349] |
| dy | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1bdy000 | 40 | 0.0006 | [-0.0042, 0.0060] |
| dy | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1bdy025 | 40 | 0.0006 | [-0.0043, 0.0060] |
| dy | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1bdy050 | 40 | 0.0005 | [-0.0043, 0.0060] |
| dy | contrib_mae_norm | M0_ols | p1bdy000 | 40 | 0.0777 | [0.0710, 0.0852] |
| dy | contrib_mae_norm | M0_ols | p1bdy025 | 40 | 0.0762 | [0.0696, 0.0837] |
| dy | contrib_mae_norm | M0_ols | p1bdy050 | 40 | 0.0756 | [0.0690, 0.0832] |
| dy | contrib_mae_norm | M1_ridge | p1bdy000 | 40 | 0.0832 | [0.0761, 0.0911] |
| dy | contrib_mae_norm | M1_ridge | p1bdy025 | 40 | 0.0805 | [0.0734, 0.0883] |
| dy | contrib_mae_norm | M1_ridge | p1bdy050 | 40 | 0.0802 | [0.0728, 0.0886] |
| dy | contrib_mae_norm | M2_adstock_sat | p1bdy000 | 40 | 0.0979 | [0.0771, 0.1203] |
| dy | contrib_mae_norm | M2_adstock_sat | p1bdy025 | 40 | 0.1178 | [0.1003, 0.1364] |
| dy | contrib_mae_norm | M2_adstock_sat | p1bdy050 | 40 | 0.1691 | [0.1420, 0.1985] |
| dy | contrib_mae_norm | M2_adstock_sat_noZ | p1bdy000 | 40 | 0.1430 | [0.1123, 0.1803] |
| dy | contrib_mae_norm | M2_adstock_sat_noZ | p1bdy025 | 40 | 0.1572 | [0.1239, 0.1940] |
| dy | contrib_mae_norm | M2_adstock_sat_noZ | p1bdy050 | 40 | 0.1753 | [0.1395, 0.2154] |
| dy | contrib_mae_norm | M2p_true_transforms | p1bdy000 | 40 | 0.0126 | [0.0075, 0.0201] |
| dy | contrib_mae_norm | M2p_true_transforms | p1bdy025 | 40 | 0.0267 | [0.0177, 0.0392] |
| dy | contrib_mae_norm | M2p_true_transforms | p1bdy050 | 40 | 0.0482 | [0.0342, 0.0667] |
| dy | contrib_mae_norm | M2p_true_transforms_plus_D | p1bdy000 | 40 | 0.0108 | [0.0070, 0.0157] |
| dy | contrib_mae_norm | M2p_true_transforms_plus_D | p1bdy025 | 40 | 0.0108 | [0.0071, 0.0157] |
| dy | contrib_mae_norm | M2p_true_transforms_plus_D | p1bdy050 | 40 | 0.0108 | [0.0070, 0.0157] |
| dy | rmse_scaled | M0_ols | p1bdy000 | 40 | 0.0541 | [0.0451, 0.0649] |
| dy | rmse_scaled | M0_ols | p1bdy025 | 40 | 0.0672 | [0.0552, 0.0812] |
| dy | rmse_scaled | M0_ols | p1bdy050 | 40 | 0.0956 | [0.0781, 0.1151] |
| dy | rmse_scaled | M1_ridge | p1bdy000 | 40 | 0.0519 | [0.0416, 0.0638] |
| dy | rmse_scaled | M1_ridge | p1bdy025 | 40 | 0.0654 | [0.0534, 0.0797] |
| dy | rmse_scaled | M1_ridge | p1bdy050 | 40 | 0.1006 | [0.0808, 0.1224] |
| dy | rmse_scaled | M2_adstock_sat | p1bdy000 | 40 | 0.0370 | [0.0310, 0.0438] |
| dy | rmse_scaled | M2_adstock_sat | p1bdy025 | 40 | 0.0549 | [0.0453, 0.0658] |
| dy | rmse_scaled | M2_adstock_sat | p1bdy050 | 40 | 0.0846 | [0.0693, 0.1028] |
| dy | rmse_scaled | M2_adstock_sat_noZ | p1bdy000 | 40 | 0.0726 | [0.0580, 0.0904] |
| dy | rmse_scaled | M2_adstock_sat_noZ | p1bdy025 | 40 | 0.0819 | [0.0665, 0.1010] |
| dy | rmse_scaled | M2_adstock_sat_noZ | p1bdy050 | 40 | 0.1098 | [0.0901, 0.1338] |
| dy | rmse_scaled | M2p_true_transforms | p1bdy000 | 40 | 0.0196 | [0.0140, 0.0259] |
| dy | rmse_scaled | M2p_true_transforms | p1bdy025 | 40 | 0.0437 | [0.0363, 0.0522] |
| dy | rmse_scaled | M2p_true_transforms | p1bdy050 | 40 | 0.0775 | [0.0639, 0.0925] |
| dy | rmse_scaled | M2p_true_transforms_plus_D | p1bdy000 | 40 | 0.0250 | [0.0191, 0.0320] |
| dy | rmse_scaled | M2p_true_transforms_plus_D | p1bdy025 | 40 | 0.0250 | [0.0192, 0.0322] |
| dy | rmse_scaled | M2p_true_transforms_plus_D | p1bdy050 | 40 | 0.0251 | [0.0192, 0.0323] |
| rho | channel_total_bias_norm·direct | M0_ols | p1brho000 | 40 | -0.0769 | [-0.0834, -0.0709] |
| rho | channel_total_bias_norm·direct | M0_ols | p1brho030 | 40 | -0.0748 | [-0.0816, -0.0686] |
| rho | channel_total_bias_norm·direct | M0_ols | p1brho060 | 40 | -0.0722 | [-0.0793, -0.0659] |
| rho | channel_total_bias_norm·direct | M1_ridge | p1brho000 | 40 | -0.0796 | [-0.0861, -0.0734] |
| rho | channel_total_bias_norm·direct | M1_ridge | p1brho030 | 40 | -0.0775 | [-0.0844, -0.0712] |
| rho | channel_total_bias_norm·direct | M1_ridge | p1brho060 | 40 | -0.0742 | [-0.0811, -0.0675] |
| rho | channel_total_bias_norm·direct | M2_adstock_sat | p1brho000 | 40 | 0.0278 | [0.0022, 0.0542] |
| rho | channel_total_bias_norm·direct | M2_adstock_sat | p1brho030 | 40 | 0.0538 | [0.0203, 0.0897] |
| rho | channel_total_bias_norm·direct | M2_adstock_sat | p1brho060 | 40 | 0.0446 | [0.0172, 0.0731] |
| rho | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1brho000 | 40 | 0.0441 | [0.0072, 0.0851] |
| rho | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1brho030 | 40 | 0.0361 | [0.0095, 0.0642] |
| rho | channel_total_bias_norm·direct | M2_adstock_sat_noZ | p1brho060 | 40 | 0.0441 | [0.0153, 0.0732] |
| rho | channel_total_bias_norm·direct | M2p_true_transforms | p1brho000 | 40 | -0.0022 | [-0.0082, 0.0039] |
| rho | channel_total_bias_norm·direct | M2p_true_transforms | p1brho030 | 40 | 0.0005 | [-0.0058, 0.0066] |
| rho | channel_total_bias_norm·direct | M2p_true_transforms | p1brho060 | 40 | 0.0028 | [-0.0039, 0.0094] |
| rho | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1brho000 | 40 | 0.0010 | [-0.0006, 0.0025] |
| rho | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1brho030 | 40 | 0.0030 | [0.0009, 0.0054] |
| rho | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | p1brho060 | 40 | 0.0044 | [0.0019, 0.0070] |
| rho | contrib_mae_norm | M0_ols | p1brho000 | 40 | 0.0776 | [0.0716, 0.0837] |
| rho | contrib_mae_norm | M0_ols | p1brho030 | 40 | 0.0760 | [0.0701, 0.0823] |
| rho | contrib_mae_norm | M0_ols | p1brho060 | 40 | 0.0742 | [0.0681, 0.0808] |
| rho | contrib_mae_norm | M1_ridge | p1brho000 | 40 | 0.0798 | [0.0737, 0.0862] |
| rho | contrib_mae_norm | M1_ridge | p1brho030 | 40 | 0.0778 | [0.0716, 0.0846] |
| rho | contrib_mae_norm | M1_ridge | p1brho060 | 40 | 0.0750 | [0.0685, 0.0818] |
| rho | contrib_mae_norm | M2_adstock_sat | p1brho000 | 40 | 0.1019 | [0.0820, 0.1246] |
| rho | contrib_mae_norm | M2_adstock_sat | p1brho030 | 40 | 0.1232 | [0.0952, 0.1536] |
| rho | contrib_mae_norm | M2_adstock_sat | p1brho060 | 40 | 0.1170 | [0.0932, 0.1438] |
| rho | contrib_mae_norm | M2_adstock_sat_noZ | p1brho000 | 40 | 0.1416 | [0.1114, 0.1749] |
| rho | contrib_mae_norm | M2_adstock_sat_noZ | p1brho030 | 40 | 0.1213 | [0.1021, 0.1427] |
| rho | contrib_mae_norm | M2_adstock_sat_noZ | p1brho060 | 40 | 0.1254 | [0.1064, 0.1466] |
| rho | contrib_mae_norm | M2p_true_transforms | p1brho000 | 40 | 0.0219 | [0.0172, 0.0270] |
| rho | contrib_mae_norm | M2p_true_transforms | p1brho030 | 40 | 0.0217 | [0.0171, 0.0267] |
| rho | contrib_mae_norm | M2p_true_transforms | p1brho060 | 40 | 0.0223 | [0.0170, 0.0281] |
| rho | contrib_mae_norm | M2p_true_transforms_plus_D | p1brho000 | 40 | 0.0095 | [0.0074, 0.0118] |
| rho | contrib_mae_norm | M2p_true_transforms_plus_D | p1brho030 | 40 | 0.0104 | [0.0080, 0.0131] |
| rho | contrib_mae_norm | M2p_true_transforms_plus_D | p1brho060 | 40 | 0.0102 | [0.0080, 0.0126] |
| rho | rmse_scaled | M0_ols | p1brho000 | 40 | 0.0813 | [0.0647, 0.1009] |
| rho | rmse_scaled | M0_ols | p1brho030 | 40 | 0.0864 | [0.0698, 0.1050] |
| rho | rmse_scaled | M0_ols | p1brho060 | 40 | 0.0924 | [0.0760, 0.1108] |
| rho | rmse_scaled | M1_ridge | p1brho000 | 40 | 0.0788 | [0.0632, 0.0965] |
| rho | rmse_scaled | M1_ridge | p1brho030 | 40 | 0.0766 | [0.0628, 0.0918] |
| rho | rmse_scaled | M1_ridge | p1brho060 | 40 | 0.0800 | [0.0663, 0.0953] |
| rho | rmse_scaled | M2_adstock_sat | p1brho000 | 40 | 0.0561 | [0.0438, 0.0712] |
| rho | rmse_scaled | M2_adstock_sat | p1brho030 | 40 | 0.0565 | [0.0465, 0.0679] |
| rho | rmse_scaled | M2_adstock_sat | p1brho060 | 40 | 0.0588 | [0.0493, 0.0698] |
| rho | rmse_scaled | M2_adstock_sat_noZ | p1brho000 | 40 | 0.0764 | [0.0606, 0.0979] |
| rho | rmse_scaled | M2_adstock_sat_noZ | p1brho030 | 40 | 0.0744 | [0.0591, 0.0942] |
| rho | rmse_scaled | M2_adstock_sat_noZ | p1brho060 | 40 | 0.0708 | [0.0574, 0.0879] |
| rho | rmse_scaled | M2p_true_transforms | p1brho000 | 40 | 0.0374 | [0.0302, 0.0456] |
| rho | rmse_scaled | M2p_true_transforms | p1brho030 | 40 | 0.0364 | [0.0295, 0.0443] |
| rho | rmse_scaled | M2p_true_transforms | p1brho060 | 40 | 0.0357 | [0.0293, 0.0429] |
| rho | rmse_scaled | M2p_true_transforms_plus_D | p1brho000 | 40 | 0.0156 | [0.0123, 0.0195] |
| rho | rmse_scaled | M2p_true_transforms_plus_D | p1brho030 | 40 | 0.0163 | [0.0125, 0.0207] |
| rho | rmse_scaled | M2p_true_transforms_plus_D | p1brho060 | 40 | 0.0149 | [0.0118, 0.0182] |

## 5. Límites

- Es un piloto: 40 pares por nivel y una sola T.
- El efecto de `rho` cambia los tratamientos realizados; los contrastes de `rho` comparan mundos con distinta verdad, cada uno evaluado frente a la suya.
- M2p_D usa D, que un analista no observa: es una cota de referencia, no un método aplicable.
- Atribución histórica (§4) y efecto de intervención (§3) son estimandos distintos.

Datos: `reports/v1_2/p1b/`.

## 6. Lectura (agente; contrastes pareados nivel alto − nivel 0, sesgo `do_zero` en directos, unidades Σ|Y|)

- **D→C (`dc`, con D→Y = 0,3 fijo).**
  - M2p, privilegiado sin D: el sesgo aumenta con `dc` (−0,008, IC95 [−0,013, −0,005] en `dc = 0,5`).
  - M2p_D, que observa D: no cambia (+0,000, [−0,002, 0,003]). La confusión por D es detectable con las formas verdaderas y desaparece al condicionar en D.
  - M0/M1: cambios pequeños (≈ −0,002).
  - M2 y M2_noZ: intervalos demasiado anchos para concluir (±0,03), como se anticipó en el protocolo. No se declara potencia.
- **D→Y (`dy`, con D→C = 0,3 fijo).**
  - M2, ciego: el sesgo crece en `dy = 0,5` (−0,062, [−0,093, −0,030]).
  - M2p: −0,011, [−0,026, 0,004], no concluyente.
  - M2p_D: sin cambio.
  
  Con D→C fijo, reforzar D→Y aumenta la confusión: hacen falta ambas aristas.
- **`rho` (innovaciones compartidas, sin D→C).**
  - Desplazamientos pequeños pero distintos de 0 en M0, M1, M2p y **también M2p_D** (−0,003 a −0,006 en `rho = 0,6`). Observar D no corrige esta confusión, porque no pasa por D.
  - Recordatorio: `rho` cambia los tratamientos realizados (Anexo A), así que cada mundo se compara con su propia verdad.
- **Correlación lograda.** Cambia poco entre niveles: media|corr| entre canales 0,16 → 0,19 (`dc`) y 0,15 → 0,17 (`rho`). La correlación observada canal–base sube de 0,23 a 0,26. Correlaciones similares conviven con sesgos causales distintos: correlación observada ≠ confusión causal.
- **Límites.** Piloto con T = 104, 40 pares y un solo par de niveles fijos por mecanismo. M2p y M2p_D son referencias privilegiadas, no métodos aplicables. M3 no se ha incluido.
