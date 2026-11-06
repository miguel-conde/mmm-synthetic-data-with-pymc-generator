# Revisión v1.1 — registro previo de cambios y experimentos

**Fecha de registro:** 2026-11-05, **antes** de ejecutar cualquier experimento v1.1.
**Origen:** decisiones D1–D7 y correcciones 1–10 de [RESPUESTA_AL_AGENTE_MMM_V1_1.md](RESPUESTA_AL_AGENTE_MMM_V1_1.md).
**v1 congelada:** `reports/v1/` (informe, tablas, figuras, narrativa, reporte al diseñador) y `reports/v1/FREEZE_MANIFEST.json` (SHA-256 de 18 233 artefactos de `runs/{smoke,bayes_probe,pilot,core,extended,_worlds}` y de `reports/v1`). Ningún artefacto v1 se modifica; v1.1 escribe en `runs/v1_1_*` y `reports/*_v1_1.md`.

## 1. Anomalía detectada en v1 al preparar esta revisión

- **Canales aislados omitidos en v1.** El rol `"null"` se leía como `NaN` (`pd.read_csv` por defecto), de modo que la tabla v1 de falsas atribuciones solo mostraba *feeders*; los 194 canal-mundo aislados de S3/S4 desaparecían de la agregación. El dato existe en los JSON por mundo; v1.1 corrige la lectura (`keep_default_na=False`) y renombra el rol a `isolated`.

## 2. Cambios de definición (sin nuevos ajustes de modelos)

| Decisión | Cambio |
|---|---|
| D1 | Tres clases de canal: `direct` (`C→Y`), `feeder` (sin `C→Y`, con ruta a `Y`), `isolated` (sin ruta). Métricas: `false_direct_attribution_rate` (feeder + isolated, estimando *observed-path*, umbral 2 % de Σ\|y\| ya registrado) y `false_total_effect_rate` (solo isolated, estimando `interventional_total_effect` vía `do_zero` implicado por el modelo, mismo umbral). Para feeders se informa además el efecto total verdadero y el estimado, sin llamarlos «nulos». |
| D2 | Etiquetas: `historical_in_sample_fit` (antes `attribution_historical`), `future_conditional_on_known_CZ` (antes `prediction_conditional_future_inputs_known` / `attribution_future_response`). Sensibilidad `historical_full_refit` (§3.4). |
| D3 | Filas E08/E09 etiquetadas `counterfactual_engine=research_validated_private_api`. Nuevas pruebas (§4). |
| D4 | Criterio estricto vinculante; resultados no conformes marcados `nonconverged`. Cobertura en tres bloques: tasa válida, cobertura condicional en válidos, descriptiva en no válidos (con aviso). Nunca cobertura global mezclada. |
| D5 | Política v1 renombrada `all_channels_clamped_policy`. Se añade política `random_feasible` y sensibilidad `selected_channels_do_policy` (§3.5). |
| Corr. 1 | Repetir métricas principales con exclusión mínima por mundo `response_warmup_weeks` = soporte realizado del núcleo de arrastre de los canales directos (misma regla que `signal_diagnostics.summarize_signal_metrics` del generador), recalculando desde los `.npz` v1 sin reajustar. Se verifica empíricamente que las transformaciones verdaderas reproducen la verdad desde esa semana. |
| Corr. 3 | Tablas principales con `n_worlds`, `n_models` y N por celda; M3 solo comparado en sus 45 mundos. |
| Corr. 4 | Bootstrap por mundo (principal) y por célula DAG (sensibilidad; S0 tiene una única célula, por lo que no es aplicable allí). RMSE–pérdida de decisión: correlación de Spearman **dentro de cada mundo** promediada, con IC por bootstrap de mundos. |
| Corr. 5 | Diagnóstico de M2: hiperparámetros elegidos, presupuesto de búsqueda, comparación con familias verdaderas (solo diagnóstico, nunca para seleccionar). |
| Corr. 6 | Clasificación de cada `Z` según DAG: causa común de `C` e `Y`, solo `Z→Y`, solo `Z→C`, descendiente de `D`. El generador no tiene aristas `C→Z`: **mediador o descendiente de `C` no representable** (`blocked_design_not_supported`). |
| Corr. 8 | Tasa «mejor predictor = mejor atribuidor» comparada con el azar 1/N del conjunto de métodos de cada mundo. |
| Corr. 9 | Tabla de tipos de intervalo y fuentes de incertidumbre. |

## 3. Experimentos v1.1 (registrados antes de ejecutarlos)

### 3.1 Diagnóstico MCMC de M3 (D4) — `runs/v1_1_m3_diag`

- **Submuestra fijada sin usar la verdad:** de los 45 mundos M3 de F2, los dos primeros por `world_id` de cada escenario que no cumplen el criterio estricto: `S0_direct_only_T208_r00`, `S0_direct_only_T208_r01`, `S1_confounded_treatment_T104_r00`, `S1_confounded_treatment_T104_r01`, `S2_promo_drives_treatment_T104_r01`, `S2_promo_drives_treatment_T104_r02`, `S3_treatment_halo_T104_r00`, `S3_treatment_halo_T104_r02`, `S4_kitchen_sink_T104_r00`, `S4_kitchen_sink_T104_r01`.
- **Variantes:** V0 = v1 (4×(1000+1000), `target_accept=0.9`) re-ejecutada guardando `idata`; V1 = `target_accept=0.95`; V2 = `0.99`; V3 = cambio de prior/parametrización **decidido a partir de la geometría posterior de V0** (divergencias, correlaciones, parámetros en frontera) y documentado en `reports/mcmc_diagnostics.md` antes de lanzarse.
- **Regla de selección (sin verdad):** mayor fracción de ajustes que cumplen el criterio estricto en la submuestra; empate → menor tiempo. La variante elegida se aplica a los 45 mundos M3 en `runs/v1_1_m3` y se compara con v1 en el mismo conjunto.

### 3.2 Oracle (D7) — `runs/v1_1_m4_diag`

Tres de los cinco mundos M4 de v1 con mayor `rhat_max` en v1. Variantes: `marginal` con `target_accept=0.95` y `latent="sampled"`. Sin ampliar M4 salvo mejora clara de convergencia.

### 3.3 Control lineal E02 — `runs/v1_1_e02_linear`

`direct_only` con `nonlinearity="linear"` (verificado en `fb9549d`: arrastre `none` **y** saturación identidad). T ∈ {52, 104, 208} × réplicas 0–9 (30 mundos), modelos rápidos; M3 (variante elegida en 3.1) en réplicas 0–2; E08 en réplicas 0–2.

### 3.4 Sensibilidad `historical_full_refit` (D2) — `runs/v1_1_full_refit`

Modelos rápidos ciegos (M0, M1, M2, M2_noZ) reajustados sobre las T semanas en los 45 mundos de F2 réplicas 0–2; atribución evaluada en `[8, T)`. Se reporta separada del análisis principal.

### 3.5 E09 sensibilidad (D5) — `runs/v1_1_e09`

En los mundos de F2 réplicas 0–2 de S3 y S4 (18 mundos, los que tienen `C→C`): `selected_channels_do_policy` = el agente fija solo los canales sin padres `C→C`; los descendientes reaccionan según el SCM; el presupuesto se mide sobre **todos** los tratamientos realizados. La política óptima verdadera respeta esa restricción; las políticas de modelos (que suponen exogeneidad) se evalúan tal cual y se informa su violación de presupuesto realizada. En todos los mundos causales se añade `random_feasible` (media de 20 políticas aleatorias factibles, semilla fija).

### 3.6 E10A confusores (D6) — `runs/v1_1_e10a`

Factores separados, mundos **pareados** (misma semilla ⇒ mismo DAG, mismos parámetros e innovaciones; verificado):

- **`E10A_D`**: estructura `confounded_treatment` con `dc_coeff_range` ∈ {(0,0), (0.25,0.25), (0.5,0.5)}; `rho` fijo en 0 (v1: 0.1–0.5).
- **`E10A_rho`**: estructura `direct_only` (sin `D→C`) con `confounding_strength_range` ∈ {(1e-6,1e-6), (0.3,0.3), (0.6,0.6)}. El nivel «0» usa 1e-6 porque `rho=0` exacto cambia el flujo de innovaciones (verificado), y con 1e-6 los tres niveles comparten innovaciones.
- T = 104, réplicas 0–9 por nivel (60 mundos). Modelos rápidos + M2p + M2p_D; E08 en todos. Contraste principal: diferencias emparejadas por nivel en error *observed-path* y en error del efecto `do_zero` implicado.

E10B (cambio de distribución) queda para v2.

## 4. Pruebas adicionales del motor `do` (D3)

1. Validación en mundos con todas las familias de arrastre y saturación presentes y en las 5 topologías (≥ 30 mundos), con inventario de familias cubiertas.
2. Ruta independiente: para `C→C`, contrafactual analítico (softplus inverso del canal observado + término lineal del padre + transformaciones verdaderas) frente al motor — verificado previamente en 6 mundos S3/S4 con error ≤ 2e-15; se convierte en test.
3. Intervenciones múltiples simultáneas (ascendente y descendente), pulsos en la primera semana reportada y en la última, intervención en ventanas que tocan el borde.
4. Mundos con choques de tratamiento (`n_treatment_shocks=2`): nulo exacto y `do` sobre ventanas de choque.
5. Innovaciones exógenas y primitivas idénticas antes y después de evaluar intervenciones.
