# Auditoría de la selección de formas de M2 (sin modificar M2)

Protocolo: `docs/protocolo_P1B_registrado.md` §5. Datos: F3, 600 mundos, ajustes `legacy_w0` (`runs/extended`) y `corrected_w8` (`runs/v1_2_corr_f3`). No se reajusta nada.

**Selección (información de analista):**
- adstock geométrico (no normalizado) con `α ∈ (0.0, 0.3, 0.5, 0.7, 0.85)`;
- saturación `x/(x+κ)` con `κ = κ_mult × media en entrenamiento del canal con adstock`, `κ_mult ∈ [0.25, 0.5, 1.0, 2.0, 4.0, inf]` (`inf` = lineal);
- búsqueda por coordenadas (2 pasadas) que minimiza el RMSE de validación temporal en el último 20 % de las filas de entrenamiento.

**Adstock entre entrenamiento y test:** se calcula sobre la serie completa de canales, de modo que el test hereda el estado de arrastre del entrenamiento. Los coeficientes se estiman solo con filas de entrenamiento.

La verdad del SCM aparece solo en las columnas de diagnóstico (§3–§5).

## 1. Frecuencia de formas elegidas (M2, todos los canales)

α:

| fit | 0.0 | 0.3 | 0.5 | 0.7 | 0.85 |
|---|---|---|---|---|---|
| corrected_w8 | 0.244 | 0.141 | 0.194 | 0.146 | 0.276 |
| legacy_w0 | 0.214 | 0.147 | 0.204 | 0.131 | 0.304 |

κ_mult:

| fit | 0.25 | 0.5 | 1.0 | 2.0 | 4.0 | inf |
|---|---|---|---|---|---|---|
| corrected_w8 | 0.299 | 0.078 | 0.061 | 0.075 | 0.091 | 0.396 |
| legacy_w0 | 0.283 | 0.078 | 0.086 | 0.068 | 0.104 | 0.381 |

Estabilidad de la elección entre `legacy_w0` y `corrected_w8` (mismo canal): α igual en 38.2% de los canales, κ igual en 39.1%.

## 2. Por rol y extremos de la rejilla

| fit | role | n | sesgo | frac_lineal | frac_alpha_max | frac_kappa_min |
|---|---|---|---|---|---|---|
| corrected_w8 | direct | 2280 | 0.030 | 0.393 | 0.263 | 0.287 |
| corrected_w8 | feeder | 286 | 0.007 | 0.406 | 0.360 | 0.371 |
| corrected_w8 | isolated | 194 | -0.003 | 0.423 | 0.299 | 0.325 |
| legacy_w0 | direct | 2280 | -0.036 | 0.392 | 0.282 | 0.275 |
| legacy_w0 | feeder | 286 | -0.052 | 0.343 | 0.448 | 0.304 |
| legacy_w0 | isolated | 194 | -0.046 | 0.314 | 0.361 | 0.351 |

## 3. Elección frente a la verdad (solo diagnóstico)

Arrastre geométrico verdadero: correlación de rangos entre el α elegido y el verdadero.

| fit | n_canales_geom | corr_alpha_sel_true | alpha_sel_medio | alpha_true_medio |
|---|---|---|---|---|
| corrected_w8 | 1219.000 | 0.156 | 0.464 | 0.496 |
| legacy_w0 | 1219.000 | 0.193 | 0.490 | 0.496 |

Saturación verdadera frente a la forma elegida:

| fit | true_saturation | n | frac_lineal_elegida | kappa_mediano |
|---|---|---|---|---|
| corrected_w8 | hill | 512 | 0.373 | 0.500 |
| corrected_w8 | linear | 446 | 0.518 | 0.500 |
| corrected_w8 | logistic | 475 | 0.358 | 0.250 |
| corrected_w8 | michaelis_menten | 453 | 0.413 | 0.250 |
| corrected_w8 | root | 440 | 0.427 | 0.500 |
| corrected_w8 | tanh | 434 | 0.293 | 0.250 |
| legacy_w0 | hill | 512 | 0.363 | 0.500 |
| legacy_w0 | linear | 446 | 0.534 | 1.000 |
| legacy_w0 | logistic | 475 | 0.339 | 0.500 |
| legacy_w0 | michaelis_menten | 453 | 0.351 | 0.250 |
| legacy_w0 | root | 440 | 0.427 | 0.500 |
| legacy_w0 | tanh | 434 | 0.276 | 0.250 |

## 4. Sesgo de contribución directa según la forma elegida

| fit | forma | arrastre | n | sesgo_medio | sesgo_mediano |
|---|---|---|---|---|---|
| corrected_w8 | lineal (κ=∞) | α=0 | 211 | -0.0621 | -0.0550 |
| corrected_w8 | lineal (κ=∞) | α>0 | 685 | -0.0306 | -0.0285 |
| corrected_w8 | saturada (κ finito) | α=0 | 339 | -0.0255 | -0.0256 |
| corrected_w8 | saturada (κ finito) | α>0 | 1045 | 0.1064 | 0.0451 |
| legacy_w0 | lineal (κ=∞) | α=0 | 176 | -0.0605 | -0.0521 |
| legacy_w0 | lineal (κ=∞) | α>0 | 717 | -0.0368 | -0.0348 |
| legacy_w0 | saturada (κ finito) | α=0 | 327 | -0.0166 | -0.0199 |
| legacy_w0 | saturada (κ finito) | α>0 | 1060 | -0.0384 | -0.0203 |

Por escenario y T:

| fit | scenario_id | T | sesgo | frac_lineal | alpha_medio |
|---|---|---|---|---|---|
| corrected_w8 | S0 | 52 | 0.0103 | 0.3812 | 0.4122 |
| corrected_w8 | S0 | 104 | 0.0457 | 0.4125 | 0.4731 |
| corrected_w8 | S0 | 208 | 0.0445 | 0.3937 | 0.5359 |
| corrected_w8 | S1 | 52 | 0.0173 | 0.3812 | 0.4522 |
| corrected_w8 | S1 | 104 | 0.0507 | 0.4125 | 0.5144 |
| corrected_w8 | S1 | 208 | 0.0283 | 0.4313 | 0.5087 |
| corrected_w8 | S2 | 52 | 0.0189 | 0.4437 | 0.4647 |
| corrected_w8 | S2 | 104 | 0.0141 | 0.3563 | 0.4763 |
| corrected_w8 | S2 | 208 | 0.0407 | 0.3688 | 0.4437 |
| corrected_w8 | S3 | 52 | 0.0293 | 0.3833 | 0.4346 |
| corrected_w8 | S3 | 104 | 0.0052 | 0.3833 | 0.4483 |
| corrected_w8 | S3 | 208 | 0.0226 | 0.4000 | 0.4508 |
| corrected_w8 | S4 | 52 | 0.0611 | 0.3875 | 0.4278 |
| corrected_w8 | S4 | 104 | 0.0275 | 0.3500 | 0.5112 |
| corrected_w8 | S4 | 208 | 0.0262 | 0.4062 | 0.4906 |
| legacy_w0 | S0 | 52 | -0.0572 | 0.3563 | 0.4700 |
| legacy_w0 | S0 | 104 | -0.0529 | 0.4188 | 0.4831 |
| legacy_w0 | S0 | 208 | -0.0248 | 0.3312 | 0.5344 |
| legacy_w0 | S1 | 52 | -0.0498 | 0.3875 | 0.4609 |
| legacy_w0 | S1 | 104 | -0.0580 | 0.4062 | 0.5184 |
| legacy_w0 | S1 | 208 | -0.0275 | 0.3937 | 0.5294 |
| legacy_w0 | S2 | 52 | -0.0420 | 0.3563 | 0.4612 |
| legacy_w0 | S2 | 104 | -0.0557 | 0.3688 | 0.4728 |
| legacy_w0 | S2 | 208 | -0.0163 | 0.3812 | 0.4322 |
| legacy_w0 | S3 | 52 | -0.0324 | 0.4917 | 0.4446 |
| legacy_w0 | S3 | 104 | -0.0383 | 0.4000 | 0.5400 |
| legacy_w0 | S3 | 208 | -0.0193 | 0.4167 | 0.4446 |
| legacy_w0 | S4 | 52 | -0.0184 | 0.3812 | 0.4541 |
| legacy_w0 | S4 | 104 | -0.0261 | 0.3250 | 0.4938 |
| legacy_w0 | S4 | 208 | -0.0234 | 0.4938 | 0.4953 |

## 5. ¿Favorece la búsqueda modelos que predicen bien y atribuyen mal?

Correlaciones entre mundos, dentro de cada ajuste:

| fit | n_mundos | Spearman(nº canales saturados, |sesgo|) | Spearman(val_rmse, |sesgo|) | nº medio canales saturados |
|---|---|---|---|---|
| corrected_w8 | 600 | 0.185 | 0.320 | 2.777 |
| legacy_w0 | 600 | 0.176 | 0.371 | 2.847 |

Cambio del sesgo en directos al corregir la ventana, separando canales cuya forma elegida no cambió de los que sí cambió (bootstrap de mundos):

| canales directos | n_canales | n_mundos | Δsesgo (w8 − w0) | IC95 mundos |
|---|---|---|---|---|
| misma forma | 430 | 304 | 0.0272 | [0.0174, 0.0387] |
| forma distinta | 1850 | 597 | 0.0754 | [0.0643, 0.0878] |

Datos por canal: `reports/v1_2/m2_audit/m2_channel_selection.csv`.

## 6. Lectura

1. **La selección es inestable.** Quitar 8 filas iniciales cambia α en 62% de los canales y κ en 61%. Una sola ventana de validación (≈ 20 % de las filas de entrenamiento) discrimina mal entre formas cercanas.
2. **Se usan mucho los extremos de la rejilla**: α = 0,85 y κ_mult = 0,25 (la saturación más fuerte), cada uno en ≈ 30 % de los canales. La rejilla no contiene la región preferida por los datos o la búsqueda compensa una forma con otra.
3. **El α elegido apenas sigue al verdadero** (Spearman ≈ 0.17 en canales geométricos). La forma elegida no es una estimación fiable del mecanismo.
4. **El cambio de signo del sesgo tras la corrección** se concentra en los canales directos con saturación finita y α > 0. Su sesgo medio pasa a positivo con cola larga (media > mediana), y el cambio es mayor donde la forma elegida cambió. En `legacy_w0`, el defecto de inicialización (sesgo negativo) compensaba en parte esta sobreestimación propia de la búsqueda.
5. **No hay un patrón claro de «predice bien y atribuye mal» entre mundos.** El RMSE de validación correlaciona positivamente con |sesgo|: los mundos que se predicen peor también se atribuyen peor. La complejidad elegida correlaciona débilmente con |sesgo|. El problema es de identificación de forma dentro de cada mundo, no de un sesgo sistemático hacia la complejidad.

## 7. Propuesta M2v2 (solo diseño; no ejecutado)

- **Rejilla:** adstock normalizado (pesos con suma 1), para separar el arrastre de la escala del coeficiente; `α ∈ {0, 0,2, 0,4, 0,6, 0,8}` y `κ_mult ∈ {0,5, 1, 2, ∞}`, sin el extremo 0,25 que domina las elecciones.
- **Selección:** validación temporal con 3 orígenes rodantes dentro del entrenamiento (no una sola ventana), aplicando la regla de un error estándar a favor de la forma más simple (lineal y con α menor).
- **Presupuesto:** las mismas 2 pasadas de coordenadas por canal.
- **Desarrollo:** F2 réplicas 0–2, donde se fija la rejilla y la regla sin mirar la verdad, salvo para este diagnóstico ya hecho.
- **Evaluación:** F3 réplicas 10–39, nunca usadas para decidir. M2 se mantiene publicado como referencia; M2v2 sería un modelo adicional.
