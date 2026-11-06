# P1 — Líneas base corregidas de modelos rápidos (ventana de ajuste `[8, n_train)`)

Protocolo: `docs/protocolo_P1_registrado.md` §5. Mismas configuraciones, semillas, mundos y modelos que los runs históricos; solo cambia `fit_scope: train_after_warmup`. Las semanas 0–7 aportan únicamente historia de tratamiento. **Sin generación nueva.**

- «histórico_w0»: resultado antiguo, ajustado desde la semana 0 y contaminado por el defecto de inicialización. Se conserva como referencia.
- «corregido_w8»: resultado nuevo.

Las políticas y efectos de M3 **no** se incluyen: esperan al nuevo ajuste M3 (Entrega B).

Unidades:
- Errores de contribución y sesgos: normalizados por media|Y| de la ventana.
- Valor E09: en unidades de `Y` normalizado por Σ|Y|. **No es ROAS.**
- Intervalos: bootstrap de mundos.

## 1. Coste (separado de los experimentos nuevos)

| run | n_mundos | n_ajustes | fallos | tiempo_total_min | rss_pico_max_mb |
|---|---|---|---|---|---|
| v1_2_corr_f3 | 600 | 6000 | 0 | 49.3 | 488.0 |
| v1_2_corr_e10a_D | 30 | 240 | 0 | 1.2 | 495.2 |
| v1_2_corr_e10a_rho | 30 | 240 | 0 | 1.5 | 493.0 |
| v1_2_corr_e0809 | 45 | 270 | 0 | 3.0 | 526.5 |

## 2. Atribución y predicción: histórico frente a corregido

Directos para el sesgo; todos los canales para el MAE de contribución; predicción en la ventana futura.

| conjunto | métrica | modelo | n_mundos | histórico_w0 | corregido_w8 | dif | IC95 |
|---|---|---|---|---|---|---|---|
| F3 (600 mundos) | contrib_mae_norm | M0_ols | 600 | 0.0675 | 0.0680 | 0.0006 | [0.0003, 0.0008] |
| F3 (600 mundos) | contrib_mae_norm | M1_ridge | 600 | 0.0703 | 0.0706 | 0.0003 | [-0.0000, 0.0007] |
| F3 (600 mundos) | contrib_mae_norm | M2_adstock_sat | 600 | 0.0985 | 0.1077 | 0.0092 | [0.0022, 0.0163] |
| F3 (600 mundos) | contrib_mae_norm | M2_adstock_sat_noZ | 600 | 0.1324 | 0.1519 | 0.0195 | [0.0100, 0.0292] |
| F3 (600 mundos) | contrib_mae_norm | M2p_true_transforms | 600 | 0.0467 | 0.0232 | -0.0235 | [-0.0258, -0.0211] |
| F3 (600 mundos) | contrib_mae_norm | M2p_true_transforms_plus_D | 600 | 0.0415 | 0.0133 | -0.0282 | [-0.0305, -0.0256] |
| F3 (600 mundos) | channel_total_bias_norm·direct | M0_ols | 600 | -0.0771 | -0.0778 | -0.0007 | [-0.0010, -0.0004] |
| F3 (600 mundos) | channel_total_bias_norm·direct | M1_ridge | 600 | -0.0812 | -0.0816 | -0.0004 | [-0.0008, 0.0000] |
| F3 (600 mundos) | channel_total_bias_norm·direct | M2_adstock_sat | 600 | -0.0361 | 0.0295 | 0.0656 | [0.0562, 0.0754] |
| F3 (600 mundos) | channel_total_bias_norm·direct | M2_adstock_sat_noZ | 600 | -0.0282 | 0.0403 | 0.0685 | [0.0578, 0.0799] |
| F3 (600 mundos) | channel_total_bias_norm·direct | M2p_true_transforms | 600 | -0.0389 | -0.0006 | 0.0383 | [0.0351, 0.0414] |
| F3 (600 mundos) | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | 600 | -0.0373 | -0.0010 | 0.0363 | [0.0332, 0.0392] |
| F3 (600 mundos) | rmse_scaled | M0_ols | 600 | 0.0723 | 0.0945 | 0.0222 | [0.0152, 0.0295] |
| F3 (600 mundos) | rmse_scaled | M1_ridge | 600 | 0.0616 | 0.0646 | 0.0029 | [-0.0001, 0.0063] |
| F3 (600 mundos) | rmse_scaled | M2_adstock_sat | 600 | 0.0805 | 0.0835 | 0.0030 | [-0.0042, 0.0104] |
| F3 (600 mundos) | rmse_scaled | M2_adstock_sat_noZ | 600 | 0.1200 | 0.1305 | 0.0105 | [0.0018, 0.0200] |
| F3 (600 mundos) | rmse_scaled | M2p_true_transforms | 600 | 0.0709 | 0.0444 | -0.0265 | [-0.0317, -0.0218] |
| F3 (600 mundos) | rmse_scaled | M2p_true_transforms_plus_D | 600 | 0.0626 | 0.0288 | -0.0338 | [-0.0390, -0.0289] |
| E10A_D (30) | contrib_mae_norm | M0_ols | 30 | 0.0726 | 0.0735 | 0.0009 | [-0.0001, 0.0021] |
| E10A_D (30) | contrib_mae_norm | M1_ridge | 30 | 0.0737 | 0.0749 | 0.0012 | [0.0001, 0.0024] |
| E10A_D (30) | contrib_mae_norm | M2_adstock_sat | 30 | 0.1002 | 0.1361 | 0.0358 | [0.0104, 0.0613] |
| E10A_D (30) | contrib_mae_norm | M2_adstock_sat_noZ | 30 | 0.1229 | 0.1437 | 0.0209 | [-0.0090, 0.0481] |
| E10A_D (30) | contrib_mae_norm | M2p_true_transforms | 30 | 0.0515 | 0.0194 | -0.0321 | [-0.0375, -0.0273] |
| E10A_D (30) | contrib_mae_norm | M2p_true_transforms_plus_D | 30 | 0.0526 | 0.0099 | -0.0428 | [-0.0494, -0.0365] |
| E10A_D (30) | channel_total_bias_norm·direct | M0_ols | 30 | -0.0714 | -0.0731 | -0.0016 | [-0.0035, -0.0000] |
| E10A_D (30) | channel_total_bias_norm·direct | M1_ridge | 30 | -0.0726 | -0.0744 | -0.0019 | [-0.0038, -0.0002] |
| E10A_D (30) | channel_total_bias_norm·direct | M2_adstock_sat | 30 | -0.0115 | 0.0718 | 0.0833 | [0.0449, 0.1240] |
| E10A_D (30) | channel_total_bias_norm·direct | M2_adstock_sat_noZ | 30 | -0.0145 | 0.0471 | 0.0616 | [0.0305, 0.0954] |
| E10A_D (30) | channel_total_bias_norm·direct | M2p_true_transforms | 30 | -0.0463 | -0.0028 | 0.0434 | [0.0339, 0.0529] |
| E10A_D (30) | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | 30 | -0.0477 | -0.0016 | 0.0461 | [0.0376, 0.0559] |
| E10A_D (30) | rmse_scaled | M0_ols | 30 | 0.0731 | 0.0706 | -0.0025 | [-0.0054, 0.0001] |
| E10A_D (30) | rmse_scaled | M1_ridge | 30 | 0.0793 | 0.0772 | -0.0021 | [-0.0057, 0.0013] |
| E10A_D (30) | rmse_scaled | M2_adstock_sat | 30 | 0.0598 | 0.0601 | 0.0003 | [-0.0049, 0.0058] |
| E10A_D (30) | rmse_scaled | M2_adstock_sat_noZ | 30 | 0.0814 | 0.0764 | -0.0050 | [-0.0101, 0.0004] |
| E10A_D (30) | rmse_scaled | M2p_true_transforms | 30 | 0.0617 | 0.0517 | -0.0100 | [-0.0172, -0.0031] |
| E10A_D (30) | rmse_scaled | M2p_true_transforms_plus_D | 30 | 0.0392 | 0.0191 | -0.0201 | [-0.0338, -0.0082] |
| E10A_rho (30) | contrib_mae_norm | M0_ols | 30 | 0.0908 | 0.0904 | -0.0004 | [-0.0019, 0.0012] |
| E10A_rho (30) | contrib_mae_norm | M1_ridge | 30 | 0.0900 | 0.0908 | 0.0008 | [-0.0011, 0.0028] |
| E10A_rho (30) | contrib_mae_norm | M2_adstock_sat | 30 | 0.1313 | 0.1128 | -0.0185 | [-0.0442, 0.0046] |
| E10A_rho (30) | contrib_mae_norm | M2_adstock_sat_noZ | 30 | 0.1346 | 0.1119 | -0.0227 | [-0.0437, -0.0042] |
| E10A_rho (30) | contrib_mae_norm | M2p_true_transforms | 30 | 0.0812 | 0.0256 | -0.0556 | [-0.0695, -0.0430] |
| E10A_rho (30) | contrib_mae_norm | M2p_true_transforms_plus_D | 30 | 0.0677 | 0.0134 | -0.0543 | [-0.0673, -0.0425] |
| E10A_rho (30) | channel_total_bias_norm·direct | M0_ols | 30 | -0.0883 | -0.0895 | -0.0012 | [-0.0034, 0.0008] |
| E10A_rho (30) | channel_total_bias_norm·direct | M1_ridge | 30 | -0.0879 | -0.0903 | -0.0024 | [-0.0048, -0.0002] |
| E10A_rho (30) | channel_total_bias_norm·direct | M2_adstock_sat | 30 | -0.0544 | 0.0138 | 0.0682 | [0.0291, 0.1075] |
| E10A_rho (30) | channel_total_bias_norm·direct | M2_adstock_sat_noZ | 30 | -0.0805 | 0.0020 | 0.0825 | [0.0467, 0.1220] |
| E10A_rho (30) | channel_total_bias_norm·direct | M2p_true_transforms | 30 | -0.0694 | -0.0017 | 0.0677 | [0.0534, 0.0831] |
| E10A_rho (30) | channel_total_bias_norm·direct | M2p_true_transforms_plus_D | 30 | -0.0635 | 0.0016 | 0.0651 | [0.0533, 0.0772] |
| E10A_rho (30) | rmse_scaled | M0_ols | 30 | 0.0917 | 0.0868 | -0.0049 | [-0.0081, -0.0021] |
| E10A_rho (30) | rmse_scaled | M1_ridge | 30 | 0.0840 | 0.0821 | -0.0019 | [-0.0050, 0.0009] |
| E10A_rho (30) | rmse_scaled | M2_adstock_sat | 30 | 0.0673 | 0.0556 | -0.0118 | [-0.0230, -0.0016] |
| E10A_rho (30) | rmse_scaled | M2_adstock_sat_noZ | 30 | 0.0765 | 0.0684 | -0.0081 | [-0.0215, 0.0031] |
| E10A_rho (30) | rmse_scaled | M2p_true_transforms | 30 | 0.0579 | 0.0429 | -0.0149 | [-0.0245, -0.0068] |
| E10A_rho (30) | rmse_scaled | M2p_true_transforms_plus_D | 30 | 0.0341 | 0.0145 | -0.0196 | [-0.0301, -0.0107] |
| E08/E09 (45) | contrib_mae_norm | M0_ols | 45 | 0.0612 | 0.0614 | 0.0002 | [-0.0004, 0.0007] |
| E08/E09 (45) | contrib_mae_norm | M1_ridge | 45 | 0.0634 | 0.0636 | 0.0002 | [-0.0015, 0.0022] |
| E08/E09 (45) | contrib_mae_norm | M2_adstock_sat | 45 | 0.0991 | 0.0983 | -0.0009 | [-0.0193, 0.0187] |
| E08/E09 (45) | contrib_mae_norm | M2p_true_transforms | 45 | 0.0434 | 0.0189 | -0.0245 | [-0.0324, -0.0172] |
| E08/E09 (45) | channel_total_bias_norm·direct | M0_ols | 45 | -0.0696 | -0.0700 | -0.0004 | [-0.0010, 0.0001] |
| E08/E09 (45) | channel_total_bias_norm·direct | M1_ridge | 45 | -0.0728 | -0.0730 | -0.0002 | [-0.0023, 0.0019] |
| E08/E09 (45) | channel_total_bias_norm·direct | M2_adstock_sat | 45 | -0.0225 | 0.0250 | 0.0474 | [0.0175, 0.0752] |
| E08/E09 (45) | channel_total_bias_norm·direct | M2p_true_transforms | 45 | -0.0356 | 0.0036 | 0.0392 | [0.0288, 0.0503] |
| E08/E09 (45) | rmse_scaled | M0_ols | 45 | 0.0614 | 0.0693 | 0.0079 | [-0.0081, 0.0256] |
| E08/E09 (45) | rmse_scaled | M1_ridge | 45 | 0.0569 | 0.0536 | -0.0032 | [-0.0111, 0.0033] |
| E08/E09 (45) | rmse_scaled | M2_adstock_sat | 45 | 0.0769 | 0.0773 | 0.0004 | [-0.0269, 0.0286] |
| E08/E09 (45) | rmse_scaled | M2p_true_transforms | 45 | 0.0624 | 0.0373 | -0.0251 | [-0.0389, -0.0123] |

Tabla completa (incluye N0/N1, XGBoost y LightGBM): `reports/v1_2/p1_corr/metrics_hist_vs_corr.csv`.

## 3. E08 — efecto total de intervención (`do`) implicado por cada modelo

`err_norm` = (efecto estimado − efecto verdadero) / Σ|Y|, sobre `[8, n_train)`. La verdad de cada mundo es su propio contrafactual con el motor `do` (`research_validated_private_api`). Verdad idéntica entre runs: {'E10A_D (30)': True, 'E10A_rho (30)': True, 'E08/E09 (45)': True}. Antes de esta comparación se corrigió un defecto: con la ventana tardía, la ventana E08/E09 se habría acortado 8 semanas (`causal.horizon`).

| conjunto | modelo | intervención | n_mundos | |err|_hist | |err|_corr | sesgo_hist | sesgo_corr | dif |err| | IC95 |
|---|---|---|---|---|---|---|---|---|---|
| E10A_D (30) | M0_ols | do_increase_10 | 30 | 0.0041 | 0.0041 | -0.0038 | -0.0040 | 0.0001 | [-0.0000, 0.0002] |
| E10A_D (30) | M0_ols | do_reduce_10 | 30 | 0.0045 | 0.0046 | 0.0043 | 0.0044 | 0.0001 | [-0.0000, 0.0002] |
| E10A_D (30) | M0_ols | do_zero | 30 | 0.0693 | 0.0703 | 0.0682 | 0.0698 | 0.0010 | [-0.0001, 0.0022] |
| E10A_D (30) | M1_ridge | do_increase_10 | 30 | 0.0042 | 0.0042 | -0.0039 | -0.0041 | 0.0001 | [-0.0000, 0.0002] |
| E10A_D (30) | M1_ridge | do_reduce_10 | 30 | 0.0046 | 0.0047 | 0.0044 | 0.0046 | 0.0001 | [-0.0000, 0.0002] |
| E10A_D (30) | M1_ridge | do_zero | 30 | 0.0705 | 0.0717 | 0.0693 | 0.0712 | 0.0012 | [0.0001, 0.0024] |
| E10A_D (30) | M2_adstock_sat | do_increase_10 | 30 | 0.0048 | 0.0036 | -0.0028 | -0.0011 | -0.0012 | [-0.0017, -0.0007] |
| E10A_D (30) | M2_adstock_sat | do_reduce_10 | 30 | 0.0050 | 0.0040 | 0.0031 | 0.0010 | -0.0011 | [-0.0015, -0.0006] |
| E10A_D (30) | M2_adstock_sat | do_zero | 30 | 0.0958 | 0.1283 | 0.0099 | -0.0673 | 0.0325 | [0.0088, 0.0564] |
| E10A_D (30) | M2p_true_transforms | do_increase_10 | 30 | 0.0031 | 0.0011 | -0.0028 | -0.0003 | -0.0020 | [-0.0023, -0.0016] |
| E10A_D (30) | M2p_true_transforms | do_reduce_10 | 30 | 0.0034 | 0.0012 | 0.0030 | 0.0003 | -0.0022 | [-0.0025, -0.0018] |
| E10A_D (30) | M2p_true_transforms | do_zero | 30 | 0.0491 | 0.0185 | 0.0440 | 0.0027 | -0.0307 | [-0.0358, -0.0262] |
| E10A_D (30) | M2p_true_transforms_plus_D | do_increase_10 | 30 | 0.0031 | 0.0005 | -0.0027 | 0.0000 | -0.0026 | [-0.0031, -0.0022] |
| E10A_D (30) | M2p_true_transforms_plus_D | do_reduce_10 | 30 | 0.0034 | 0.0005 | 0.0030 | -0.0000 | -0.0028 | [-0.0033, -0.0024] |
| E10A_D (30) | M2p_true_transforms_plus_D | do_zero | 30 | 0.0501 | 0.0094 | 0.0453 | 0.0015 | -0.0407 | [-0.0470, -0.0347] |
| E10A_rho (30) | M0_ols | do_increase_10 | 30 | 0.0045 | 0.0044 | -0.0039 | -0.0040 | -0.0001 | [-0.0003, -0.0000] |
| E10A_rho (30) | M0_ols | do_reduce_10 | 30 | 0.0049 | 0.0048 | 0.0044 | 0.0045 | -0.0001 | [-0.0003, -0.0000] |
| E10A_rho (30) | M0_ols | do_zero | 30 | 0.0877 | 0.0873 | 0.0853 | 0.0865 | -0.0004 | [-0.0019, 0.0014] |
| E10A_rho (30) | M1_ridge | do_increase_10 | 30 | 0.0044 | 0.0043 | -0.0039 | -0.0041 | -0.0001 | [-0.0003, 0.0001] |
| E10A_rho (30) | M1_ridge | do_reduce_10 | 30 | 0.0048 | 0.0047 | 0.0044 | 0.0046 | -0.0001 | [-0.0003, 0.0001] |
| E10A_rho (30) | M1_ridge | do_zero | 30 | 0.0868 | 0.0877 | 0.0849 | 0.0873 | 0.0009 | [-0.0010, 0.0030] |
| E10A_rho (30) | M2_adstock_sat | do_increase_10 | 30 | 0.0041 | 0.0033 | -0.0026 | -0.0004 | -0.0007 | [-0.0013, -0.0002] |
| E10A_rho (30) | M2_adstock_sat | do_reduce_10 | 30 | 0.0045 | 0.0036 | 0.0029 | 0.0005 | -0.0009 | [-0.0015, -0.0004] |
| E10A_rho (30) | M2_adstock_sat | do_zero | 30 | 0.1264 | 0.1079 | 0.0509 | -0.0128 | -0.0185 | [-0.0430, 0.0032] |
| E10A_rho (30) | M2p_true_transforms | do_increase_10 | 30 | 0.0034 | 0.0011 | -0.0027 | -0.0002 | -0.0023 | [-0.0030, -0.0015] |
| E10A_rho (30) | M2p_true_transforms | do_reduce_10 | 30 | 0.0039 | 0.0013 | 0.0031 | 0.0002 | -0.0026 | [-0.0034, -0.0018] |
| E10A_rho (30) | M2p_true_transforms | do_zero | 30 | 0.0783 | 0.0247 | 0.0667 | 0.0017 | -0.0536 | [-0.0670, -0.0414] |
| E10A_rho (30) | M2p_true_transforms_plus_D | do_increase_10 | 30 | 0.0029 | 0.0005 | -0.0026 | -0.0000 | -0.0024 | [-0.0032, -0.0015] |
| E10A_rho (30) | M2p_true_transforms_plus_D | do_reduce_10 | 30 | 0.0033 | 0.0006 | 0.0030 | 0.0000 | -0.0027 | [-0.0036, -0.0018] |
| E10A_rho (30) | M2p_true_transforms_plus_D | do_zero | 30 | 0.0652 | 0.0129 | 0.0611 | -0.0014 | -0.0523 | [-0.0648, -0.0409] |
| E08/E09 (45) | M0_ols | do_increase_10 | 45 | 0.0033 | 0.0034 | -0.0030 | -0.0031 | 0.0000 | [-0.0000, 0.0001] |
| E08/E09 (45) | M0_ols | do_reduce_10 | 45 | 0.0036 | 0.0036 | 0.0034 | 0.0034 | 0.0000 | [-0.0000, 0.0001] |
| E08/E09 (45) | M0_ols | do_zero | 45 | 0.0593 | 0.0595 | 0.0578 | 0.0582 | 0.0002 | [-0.0004, 0.0008] |
| E08/E09 (45) | M1_ridge | do_increase_10 | 45 | 0.0035 | 0.0035 | -0.0033 | -0.0033 | 0.0000 | [-0.0001, 0.0002] |
| E08/E09 (45) | M1_ridge | do_reduce_10 | 45 | 0.0038 | 0.0038 | 0.0036 | 0.0037 | 0.0000 | [-0.0001, 0.0002] |
| E08/E09 (45) | M1_ridge | do_zero | 45 | 0.0615 | 0.0617 | 0.0606 | 0.0608 | 0.0002 | [-0.0014, 0.0022] |
| E08/E09 (45) | M2_adstock_sat | do_increase_10 | 45 | 0.0037 | 0.0030 | -0.0021 | -0.0006 | -0.0007 | [-0.0011, -0.0003] |
| E08/E09 (45) | M2_adstock_sat | do_reduce_10 | 45 | 0.0040 | 0.0032 | 0.0024 | 0.0007 | -0.0007 | [-0.0011, -0.0004] |
| E08/E09 (45) | M2_adstock_sat | do_zero | 45 | 0.0935 | 0.0924 | 0.0310 | -0.0167 | -0.0011 | [-0.0185, 0.0177] |
| E08/E09 (45) | M2p_true_transforms | do_increase_10 | 45 | 0.0023 | 0.0011 | -0.0018 | 0.0000 | -0.0013 | [-0.0017, -0.0009] |
| E08/E09 (45) | M2p_true_transforms | do_reduce_10 | 45 | 0.0025 | 0.0011 | 0.0020 | -0.0000 | -0.0014 | [-0.0019, -0.0010] |
| E08/E09 (45) | M2p_true_transforms | do_zero | 45 | 0.0419 | 0.0184 | 0.0352 | -0.0007 | -0.0236 | [-0.0305, -0.0169] |

Tabla completa: `reports/v1_2/p1_corr/e08_hist_vs_corr.csv`.

## 4. E09 — valor de decisión (45 mundos)

- `all_channels_clamped_policy` es una **intervención sintética definida por el protocolo**.
- `selected_channels_do_policy` sigue siendo exploratoria.
- La referencia `oracle_interventional` es la **estabilidad del mejor valor encontrado**, no un óptimo global certificado.

| familia | política | n_mundos | regret_hist | regret_corr | dif | IC95 | viol_presup_max_corr |
|---|---|---|---|---|---|---|---|
| all_channels_clamped_policy | M0_ols | 45 | 0.0362 | 0.0385 | 0.0022 | [-0.0018, 0.0064] | 0.0000 |
| all_channels_clamped_policy | M1_ridge | 45 | 0.0322 | 0.0344 | 0.0021 | [-0.0049, 0.0108] | 0.0000 |
| all_channels_clamped_policy | M2_adstock_sat | 45 | 0.0350 | 0.0227 | -0.0122 | [-0.0254, -0.0013] | 0.0000 |
| all_channels_clamped_policy | M2p_true_transforms | 45 | 0.0136 | 0.0036 | -0.0100 | [-0.0153, -0.0054] | 0.0000 |
| all_channels_clamped_policy | M5_xgboost | 45 | 0.0397 | 0.0397 | -0.0001 | [-0.0002, 0.0000] | 0.0000 |
| all_channels_clamped_policy | M6_lightgbm | 45 | 0.0398 | 0.0394 | -0.0004 | [-0.0011, 0.0000] | 0.0000 |
| all_channels_clamped_policy | current | 45 | 0.0630 | 0.0630 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| all_channels_clamped_policy | equal_allocation | 45 | 0.0410 | 0.0410 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| all_channels_clamped_policy | oracle_interventional | 45 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| all_channels_clamped_policy | random_feasible | 45 | 0.0691 | 0.0691 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| selected_channels_do_policy | M0_ols | 18 | 0.0405 | 0.0418 | 0.0013 | [-0.0053, 0.0083] |  |
| selected_channels_do_policy | M1_ridge | 18 | 0.0376 | 0.0348 | -0.0028 | [-0.0076, 0.0000] |  |
| selected_channels_do_policy | M2_adstock_sat | 18 | 0.0244 | 0.0193 | -0.0051 | [-0.0166, 0.0036] |  |
| selected_channels_do_policy | M2p_true_transforms | 18 | 0.0075 | 0.0029 | -0.0046 | [-0.0109, 0.0004] |  |
| selected_channels_do_policy | current | 18 | 0.0559 | 0.0559 | 0.0000 | [0.0000, 0.0000] |  |
| selected_channels_do_policy | equal_allocation | 18 | 0.0456 | 0.0456 | 0.0000 | [0.0000, 0.0000] |  |
| selected_channels_do_policy | oracle_interventional | 18 | 0.0000 | 0.0000 | 0.0000 | [0.0000, 0.0000] |  |
| selected_channels_do_policy | random_feasible | 18 | 0.0576 | 0.0576 | 0.0000 | [0.0000, 0.0000] |  |

## 5. Lectura

- Atribución histórica, efecto total de intervención y valor de decisión son magnitudes distintas. Una mejora en una no implica mejora en las otras.
- La corrección afecta sobre todo a los modelos con arrastre o transformaciones (M2, M2p). M0/M1 sin arrastre cambian poco porque sus filas 0–7 no tienen un estado de arrastre que reconstruir.
- Estas cifras sustituyen a las de v1/v1.1 para M0–M2p, M5 y M6 cuando se citen junto a M3 enmascarado. Las antiguas permanecen congeladas.
