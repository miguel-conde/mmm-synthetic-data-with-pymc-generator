# Quality gate v1.1

Generado por `python -m mmm_benchmark.cli revise`. Estado de cada control: **pasa**, **pasa con límites** o **abierto**.

## 1. Congelación de v1

v1 congelada el 2026-11-05T19:50:18+00:00: 18233 artefactos con SHA-256 en `reports/v1/FREEZE_MANIFEST.json`. Los runs v1.1 escriben en `runs/v1_1_*`; la caché de mundos solo añade directorios nuevos (variantes con sufijo `__<variante>`). **Pasa.**

## 2. Motor contrafactual (D3) — `counterfactual_engine=research_validated_private_api`

Usa funciones privadas de `pymc-generator` (`_carryover_col`, `_saturate_col`, estructura `Join` del grafo de `build_world_model`), válido **solo** para el commit `fb9549d` y el `uv.lock` registrado (hashes en cada `manifest.json`). Ante cualquier actualización hay que re-ejecutar `pytest -q` (regresión).

Validación por mundo en todos los runs causales:

| status | n_worlds |
|---|---|
| validated | 114 |

| scenario | variant | status | n_worlds |
|---|---|---|---|
| S0 | - | validated | 9 |
| S0 | linear | validated | 9 |
| S0 | rho000 | validated | 10 |
| S0 | rho030 | validated | 10 |
| S0 | rho060 | validated | 10 |
| S1 | - | validated | 9 |
| S1 | dc000 | validated | 10 |
| S1 | dc025 | validated | 10 |
| S1 | dc050 | validated | 10 |
| S2 | - | validated | 9 |
| S3 | - | validated | 9 |
| S4 | - | validated | 9 |

Comprobaciones (por mundo; `not_testable` cuando el mundo no tiene la estructura necesaria):

| check | passed | failed | not_testable |
|---|---|---|---|
| factual_reproduces_world | 114 | 0 | 0 |
| do_null_all_channels | 114 | 0 | 0 |
| no_path_channel_zero_effect | 13 | 0 | 101 |
| no_effect_before_intervention | 114 | 0 | 0 |
| no_mediation_matches_channel_response | 114 | 0 | 0 |
| cc_propagation | 18 | 0 | 96 |

Familias (arrastre × saturación) presentes en canales de mundos validados:

| carryover | hill | linear | logistic | michaelis_menten | root | tanh |
|---|---|---|---|---|---|---|
| geometric | 19 | 20 | 27 | 41 | 30 | 42 |
| none | 4 | 22 | 7 | 7 | 19 | 13 |
| weibull | 46 | 25 | 29 | 26 | 14 | 27 |

Pruebas independientes añadidas en v1.1 (`tests/test_interventions.py`):

- ruta analítica independiente para `C→C` (softplus inverso + término lineal del padre + transformaciones verdaderas) frente al motor: canales y ΔY con error ≤ 1e-12 en 4 mundos S3/S4;
- intervenciones simultáneas sobre canal ascendente y descendiente;
- pulsos en la primera y en la última semana reportada (borde de ventana; la primera usa la historia de *burn-in*);
- mundo con choques de tratamiento (`n_treatment_shocks=2`): nulo exacto y ausencia de efectos antes de la intervención;
- primitivas e innovaciones exógenas idénticas antes y después de evaluar intervenciones;
- política `selected_channels_do_policy`: presupuesto realizado igual al observado y *regret* ≥ 0.

**Pasa con límites**: depende de API privada y está validado con la propia aritmética del generador más una ruta analítica para `C→C`; no hay una segunda implementación completa e independiente del SCM.

## 3. Fugas de información

- `fit()` recibe solo `ObservedDataset.fit_view()`: `y` de test enmascarado con `NaN`; sin `D`, parámetros, máscaras de verdad ni contribuciones. Tests: cambiar `y` futuro no altera ajustes ciegos (7 modelos); permutar todas las salidas de verdad del mundo no altera ajustes ciegos (7 modelos); escalas de M2 y `α` de Ridge no cambian al alterar el test.
- Selección de hiperparámetros (M1, M2, M5, M6): validación temporal dentro de train, criterio RMSE de `y`; ningún paso lee la verdad (revisión de código: solo `PrivilegedTrueTransform*` y `OracleStructureKnownPlugin` llaman `attach_privileged`, y solo el runner la invoca cuando `privileged=True`).
- Oracle: `y` de test sustituido por la media de train **y** excluido de la verosimilitud por `observed_indices`.
- Selección de submuestras v1.1 (diagnóstico MCMC, oracle): reglas mecánicas sobre diagnósticos del muestreador, registradas antes de ejecutar.

**Pasa.**

## 4. Máscaras temporales y arrastre

- Las transformaciones de los modelos son causales (adstock solo con pasado) y se calculan sobre la serie completa desde la semana 0, de modo que las semanas de test usan la historia de tratamiento previa, no arrancan de cero.
- Exclusión inicial: 8 semanas en v1; en v1.1 sensibilidad con `response_warmup_weeks` por mundo (soporte realizado del núcleo; test: exclusión mínima válida). Diferencias en las métricas principales < 1e-3 (ver informe v1.1, §C). **Pasa.**

## 5. Comparabilidad

- Etiquetas de tarea y estimando explícitas (D2); ninguna tabla mezcla `historical_in_sample_fit` con `historical_full_refit`.
- M3 solo se compara en sus 45 mundos; M4 en sus 5; cada tabla lleva `n_worlds`.
- **Anomalía v1 corregida:** el rol `null` se leía como `NaN` y los canales aislados faltaban en la tabla de falsas atribuciones v1.
- **Pasa con límites:** E10A, E02 y E09-v1.1 se analizan por separado de la matriz principal y no entran en rankings globales.

## 6. Calidad MCMC (D4)

Ver [mcmc_diagnostics.md](mcmc_diagnostics.md). Criterio estricto vinculante; los ajustes no convergidos se conservan con `converged_strict = False` y su cobertura solo se presenta como descriptiva. **Abierto** para M4 (ver informe v1.1, §O).

## 7. Inventario de tests

| file | n_tests |
|---|---|
| tests/test_models_and_metrics.py | 32 |
| tests/test_generator_contract.py | 31 |
| tests/test_interventions.py | 16 |

