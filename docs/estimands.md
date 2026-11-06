# Estimandos del banco MMM (pre-registro)

Fecha de fijación: 2026-11-05, **antes de entrenar ningún modelo**. Versión de semántica de verdad: `truth_semantics_version = "1.0"`.
Generador: `pymc-generator 0.0.2`, commit `fb9549d78f0515d89c739c6d4c9f3a29d4a47c26`. Definiciones de código: [mmm_benchmark/schema.py](../mmm_benchmark/schema.py).

## Identidad del resultado (verificada en `symbolic_graph.py`)

$$Y_t = \underbrace{B^{int}_t + \varepsilon_t + \textstyle\sum_j D\!\to\!Y_{j,t} + \sum_m Z\!\to\!Y_{m,t}}_{\texttt{baseline}} + \sum_k \texttt{contributions\_observed}_{k,t}$$

$$\sum_k \texttt{contributions\_observed}_{k,t} = \sum_k \texttt{contributions}_{k,t} + \texttt{indirect\_effects}_t$$

con `contributions_observed[k] = g_cy[k]·β_k·f_k(adstock_k(C_k^{obs}))` y `contributions[k]` la misma función sobre `C_k^{base}` (canal sin entradas `D→C`, `Z→C`, `C→C`). La escala de saturación es **solo paramétrica** (`saturation_scale`), idéntica para todas las variantes.

## Estimandos

| `estimand_id` | Definición | Fuente de verdad | Unidades |
|---|---|---|---|
| `historical_observed_path_response` | Respuesta `C_k→Y` evaluada sobre el canal observado | `world.data["contributions_observed"]` | unidades de `Y` por semana |
| `historical_direct_isolated` | Respuesta sobre `C_k^{base}` | `world.data["contributions"]` | unidades de `Y` |
| `historical_indirect_total` | Suma de efectos indirectos (`obs − base`) | `world.data["indirect_effects"]` | unidades de `Y` |
| `historical_baseline_full` | Resto completo (incluye ruido `ε`) | `world.data["baseline"]` | unidades de `Y` |
| `baseline_no_observation_noise` | `baseline − outcome_noise` | derivado | unidades de `Y` |
| `interventional_total_effect` | $\Delta_k(a)=\sum_{t\in H} Y_t[do(C_k=a)] − Y_t[do(C_k=C_k^{obs})]$ con **mismas innovaciones exógenas** | motor `do` validado ([interventions.py](../mmm_benchmark/interventions.py)) | unidades de `Y` acumuladas en `H` |
| `incremental_response_per_treatment_unit` | $\Delta_k / \sum_{t\in H}(a_t - C^{obs}_{k,t})$ | derivado del anterior | `Y` por unidad de tratamiento (**no ROAS**) |
| `decision_value` | $\sum_{t\in H} Y_t$ bajo una política con presupuesto en unidades de tratamiento | motor `do` | unidades de `Y` |
| `prediction_y` | `Y` en la ventana de test con `C`, `Z` futuros conocidos | `world.data["outcome"]` | unidades de `Y` |
| `predictive_explanation` | SHAP de árboles agregado por canal | — (no causal) | sin verdad causal |

**Prohibido** mezclar en una misma métrica o ranking `historical_observed_path_response` con `historical_direct_isolated` o con efectos `do`. La partición `indirect_effects_by_source` (`cc, zc, dc`) depende del orden de anulación y **no** se usa como atribución por fuente.

**ROAS.** Los canales son tratamientos no negativos en unidades arbitrarias; no hay correspondencia monetaria. Se informa `incremental_response_per_treatment_unit`; nunca «ROAS».

## Ventanas temporales y arrastre

- Cada mundo tiene `T ∈ {52, 104, 208}` semanas reportadas. El generador simula `carryover_burn_in = 8` semanas previas reales (no guardadas) y `l_max = 8`.
- Los estimadores parten de historia cero, así que las primeras `WARMUP = 8` semanas se **excluyen** de toda métrica de atribución (verificado: con historia cero, las transformaciones verdaderas reproducen `contributions_observed` con error ≤ 1e-15 a partir de la semana 8 y no antes).
- Corte: `train = [0, round(0.8·T))`, `test = [round(0.8·T), T)`. Validación interna para hiperparámetros: último 20 % de `train`. Nunca se usa `Y` de test en ajuste ni transformaciones (`ObservedDataset.fit_view()` lo enmascara con `NaN`).
- Modo A (atribución histórica): contribuciones en `train ∩ [WARMUP, T)` con `Y` de esas semanas disponible.
- Modo B (`conditional_future_inputs_known`): predicción de `Y` en `test` con `C`, `Z` futuros conocidos. La respuesta por canal en `test` (`future_response`) se evalúa como tarea distinta, sin ver `Y` futuro.

## Comparabilidad (codificada en `schema.COMPARABILITY`)

| Modelo | observed-path | direct-isolated | `do` total | Pronóstico | Intervalos |
|---|---|---|---|---|---|
| M0/M1/M2 regresiones | Sí | N/A | Implicado bajo exogeneidad (etiquetado) | Sí | No |
| M2p/M2p_D privilegiados | Sí (fuera de ranking) | N/A | Implicado (fuera de ranking) | Sí | No |
| M3 PyMC-Marketing | Sí | N/A | Implicado bajo exogeneidad | Sí | Sí |
| M4 oracle plug-in | Sí (filas reproducibles) | N/A | N/A | Sí | Sí |
| M5/M6 árboles | N/A (SHAP → `predictive_explanation`) | N/A | N/A | Sí | No |
