# P1a — Validación de la ventana de ajuste de M3 (verosimilitud enmascarada)

Protocolo: `docs/protocolo_P1_registrado.md` §1–§3. Código: `mmm_benchmark/models/bayes.py` (`PyMCMarketingMMM.build`, `_mask_history_likelihood`), referencia independiente y análisis en `mmm_benchmark/p1a.py`, tests en `tests/test_p1a_masking.py`. Versiones: pymc-marketing 1.3.0, pymc 6.3.2, pytensor 3.3.4, nutpie 0.16.11; `uv.lock` SHA-256 `fe2107a886de1297…`.

## 1. Arquitectura (propiedad 6)

**M3 sigue siendo la clase estándar `pymc_marketing.mmm.MMM` 1.3.0 con una modificación controlada de la verosimilitud.** No es un modelo PyMC propio. Con ventana de ajuste `[w, n_train)` y `w = 8`:

1. **Entradas:** `MMM.build_model` recibe las filas `[0, n_train)`. Canales y controles desde la semana 0, de modo que el adstock (`GeometricAdstock(l_max=8)`, `normalize=True`) se calcula sobre la secuencia completa.
2. **`Y` de las semanas 0–7** se sustituye, antes de entrar al modelo, por un marcador constante (media de `Y[8:n_train)`). El `Y` real de esas semanas no llega a ningún objeto del modelo.
3. **Escala de `Y`:** `Scaling(target=FixedScaling(value=max Y[8:n_train)))` con la API oficial. La escala de canales sigue siendo la de siempre (`max` por canal sobre `[0, n_train)`): **uso permitido de canales de la fase inicial, documentado aparte** según D1.
4. **Máscara:** tras `build_model`, se añade `pm.Potential("y_history_likelihood_mask", -Σ_{t<8} log p(y_t | μ_t, σ))`.
   - Los términos son los del propio grafo: `model.logp(vars=[y], sum=False)[0][:8]`.
   - La densidad conjunta solo contiene la verosimilitud de `[8, n_train)`, con una única variable observada `y`.
   - `MMM.fit` reutiliza el modelo ya construido (`if not hasattr(self, "model")`) y muestrea `freeze_dims_and_data(self.model)`, que conserva el `Potential`.
5. **Ventana `w = 0`:** sin máscara, el modelo es idéntico al de v1/v1.1, con escala derivada de los datos sobre `[0, n_train)`.

**Cambios de API respecto a P0:**
- `PyMCMarketingMMM.fit` ya no rechaza ventanas que empiezan en `w > 0`; las enmascara.
- Nuevo método `build(obs)`, para construir sin muestrear.
- Diagnósticos nuevos: `likelihood_window` y `architecture`.
- Con `keep_posterior`, se guarda por draw la contribución media en `[8, n_train)` (estimando ROPE).
- El test P0 `test_pymc_marketing_refuses_fit_window_without_history` se sustituye por `test_pymc_marketing_late_window_is_masked_not_restarted`.

**Defecto adicional encontrado y corregido en P1:** `causal.horizon` y el oráculo M4 usaban `len(train_idx)` como fin del entrenamiento. Con `fit_scope=train_after_warmup` esa ventana habría encogido 8 semanas. Ahora usan `train_idx[-1] + 1` (test `test_causal_horizon_does_not_shrink_with_late_fit_window`). No afecta a resultados previos: P0 no ejecutó E08/E09 con ventana tardía y M4 siempre se ajustó desde 0.

## 2. Pruebas deterministas (propiedades 1–5)

| Propiedad | Test | Resultado |
|---|---|---|
| 1. Arrastre sobre la secuencia completa; el estado previo alcanza semanas ≥ 8 | `test_adstock_uses_full_input_sequence` (S0 y S4) | pasa: `channel_contribution` = numpy independiente (rtol 1e-10) y ≠ arrastre reiniciado en la semana 8 |
| 2. logp = suma manual de `[8, n_train)`; una sola verosimilitud | `test_logp_is_manual_sum_over_permitted_weeks_only`, `test_target_scale_uses_permitted_weeks_only` | pasa (5 puntos aleatorios × 2 mundos, rel 1e-12) |
| 3. `Y[0:8]` no cambia logp ni gradiente; los canales de 0–7 sí | `test_history_y_does_not_change_logp_or_gradient`, `test_history_channels_do_change_logp` | pasa: igualdad **exacta** (bit a bit) de logp, gradiente y datos del modelo con `Y[0:8]·5 + 100` |
| 4a. Igualdad determinista frente a referencia independiente | `test_masked_m3_equals_independent_reference` | pasa: densidad conjunta igual salvo una constante (≈ 1,2e-7) y gradiente igual (≤ 1e-9) en 10 puntos aleatorios |
| 5. Contribuciones, escala, predicción, intervalos, respuesta compilada, posterior | `test_masked_fit_end_to_end` (slow, MCMC corto) | pasa |
| — | `test_full_window_path_is_unchanged`, `test_non_contiguous_window_rejected` | pasa |

La referencia independiente (`p1a.reference_model`) es un modelo PyMC escrito a mano sin código de pymc-marketing:
- adstock geométrico normalizado con convolución explícita y saturación logística;
- Fourier anual de orden 2 y controles sin escalar;
- verosimilitud Normal escrita **directamente** sobre `y[8:n]/s`, sin `Potential`.

Suite completa: `105 passed in 754.68s (0:12:34)` (`reports/v1_2/p1a/pytest_p1a.txt`).

## 3. Propiedad 4b — concordancia posterior por MCMC (E02 lineal y no lineal con Weibull)

Ambos modelos se muestrearon con la misma configuración (1000 + 1000, 4 cadenas, `target_accept 0.99`) y semillas distintas.

**Criterio fijado antes de comparar:** `|media_M3 − media_ref| / sd_ref ≤ 0,3` (≈ 4 errores Monte Carlo) en cada elemento de `adstock_alpha`, `saturation_lam`, `saturation_beta`, `y_sigma` e `intercept`.

| world_id | n_elementos | max_abs_std_diff | ref_valid | ref_rhat | ref_runtime_s | MAE_rel_contrib_[8,n) | pasa (≤ 0,3) |
|---|---|---|---|---|---|---|---|
| S0_direct_only_T104_r00__linear | 14 | 0.098 | True | 1.009 | 170.040 | 0.001 | True |
| S4_kitchen_sink_T104_r00 | 20 | 0.050 | True | 1.005 | 179.748 | 0.007 | True |

Detalle: `reports/v1_2/p1a/reference_agreement.csv`.

## 4. Ensayo mínimo (4 mundos, V3 enmascarada)

`configs/v1_2_p1a_trial.yaml`. Es una comprobación técnica, no evidencia.

| mundo | estado | R-hat máx | ESS bulk mín | divergencias | válido | ventana verosimilitud | escala Y | tiempo_s | RSS pico MB | arquitectura |
|---|---|---|---|---|---|---|---|---|---|---|
| S0_direct_only_T104_r00 | ok | 1.004 | 722.109 | 0 | True | [8, 83] | 13.044 | 120.461 | 644.102 | pymc_marketing.mmm.MMM standard + Potential masking history likelihood |
| S0_direct_only_T104_r00__linear | ok | 1.013 | 648.174 | 0 | False | [8, 83] | 17.103 | 271.805 | 743.129 | pymc_marketing.mmm.MMM standard + Potential masking history likelihood |
| S0_direct_only_T104_r01__linear | ok | 1.004 | 798.147 | 0 | True | [8, 83] | 14.475 | 263.865 | 781.738 | pymc_marketing.mmm.MMM standard + Potential masking history likelihood |
| S4_kitchen_sink_T104_r00 | ok | 1.006 | 578.283 | 0 | True | [8, 83] | 10.560 | 251.682 | 868.621 | pymc_marketing.mmm.MMM standard + Potential masking history likelihood |

## 5. Reproducibilidad

Una re-ejecución de V3 desde la semana 0, con la misma semilla y el mismo `uv.lock`, no siempre es bit a bit idéntica al ajuste de v1.1: coincide exactamente en 4 de los 10 mundos piloto y en el resto difiere hasta un 3 % del máximo de las contribuciones. Es ruido Monte Carlo del muestreo (nutpie multihilo), no un cambio de modelo. La validez estricta cambia en 3 de 10 mundos con R-hat cerca de 1,01. Por eso el piloto compara V3 enmascarada con la **re-ejecución** de V3 histórica (`runs/v1_2_p1a_hist`, posterior guardada). La comparación con los ajustes originales de v1.1 se da aparte (`p1a_m3_rebaseline.md` §5).

## 6. Coste

Tiempo y memoria por ajuste: tabla del §4 y `p1a_m3_rebaseline.md`. La máscara no añade variables libres; el coste por gradiente es el de calcular 8 términos de verosimilitud adicionales.
