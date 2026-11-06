# Auditoría del generador instalado (H0 / E00)

Fecha: 2026-11-05. Fuente de verdad: **código instalado**, no la documentación de `main`.

## Entorno

| Elemento | Valor |
|---|---|
| Python | 3.13.7 (`.venv` gestionado por uv 0.10.6, cooldown 7 días en `pyproject.toml`) |
| pymc-generator | 0.0.2, Git `fb9549d78f0515d89c739c6d4c9f3a29d4a47c26` (fijado en `[tool.uv.sources]`) |
| pymc / pytensor / pymc-marketing | 6.3.2 / 3.3.4 / 1.3.0 |
| numpy / scipy / pandas / scikit-learn | 2.4.6 / 1.18.1 / 3.1.0 / 1.9.1 |
| nutpie / arviz | 0.16.11 / 1.3.0 |
| xgboost-cpu / lightgbm | 3.4.1 / 4.7.0 |
| Sistema | WSL2, 14 CPU lógicas, 15.4 GB RAM, sin GPU |

`python -m mmm_benchmark.cli doctor` imprime y guarda esta huella; cada `manifest.json` la repite junto con el SHA-256 de `uv.lock`, del código y de la configuración.

**Discrepancia con el README upstream:** el lock upstream valida PyMC 6.2.0 / PyTensor 3.2.4 / pymc-marketing 1.1.0; este entorno resuelve versiones más recientes dentro del rango declarado. El propio README advierte que cambiar dependencias puede alterar resultados con las mismas semillas. Los resultados de este banco son reproducibles **con este lock**, no con el upstream.

## API utilizada (verificada en el código instalado)

| Necesidad | API | Notas |
|---|---|---|
| Escenarios | `pg.SCENARIOS` (tupla de `Scenario`), `Scenario.prior(n_time_steps, seed, connect_all=None)` | los 5 presets del protocolo existen con esos nombres |
| Mundo | `pg.sample_scm(cfg, seed, connect_all=scenario.connect_all, name, purpose)` | determinista: misma `cfg` + `seed` → arrays idénticos (test) |
| Verdad | `world.data[...]`, `world.g`, `world.params` | ver [estimands.md](estimands.md) |
| Replay | `SCM.replay()` | reconstruye todas las salidas desde primitivas; **no acepta `do`** |
| Oracle | `pg.sample_oracle(world, OracleSamplingConfig, observed_indices=...)` | `contributions`, `outcome_mu` deterministas de longitud completa |
| Bundles | `pg.write_scm_bundle(world, dir, plots=True)` | sin binario graphviz (render matplotlib) |
| Corpus | `pg.sample_prior_predictive`, `save_corpus`/`load_corpus` | `float32`; **no incluye** `contributions_observed` |

## Hechos verificados empíricamente

1. **Identidad**: `identity_error()` ≤ 4e-15 en todos los mundos (columna `identity_error` de `worlds.csv`). Se cumple además `outcome = baseline + Σ contributions_observed` y `Σ indirect_effects_by_source = indirect_effects` (tests).
2. **`baseline` incluye el ruido de observación**; `baseline_intrinsic` es solo el intercepto. `baseline − outcome_noise` = base sin ruido (D→Y, Z→Y, intercepto).
3. **Burn-in**: `make_scm_prior` fija `carryover_burn_in = 8 = l_max`. El generador simula 8 semanas previas no guardadas; un estimador que arranca con historia cero no puede reproducir la respuesta en las semanas 0–7. Verificado: las transformaciones verdaderas aplicadas al `C` observado reproducen `contributions_observed` con error ≤ 1e-15 **desde la semana 8** y hasta 1.4 unidades de `Y` antes. Todas las métricas de atribución excluyen esas 8 semanas. El oracle descarta por su parte `warmup = 7` filas (`l_max − 1`, según las priors de arrastre).
4. **S0 no es lineal**: `direct_only` muestrea familias de arrastre (`none/geometric/weibull`) y saturación (`linear/hill/logistic/michaelis_menten/tanh/root`) por canal. Ejemplo (T=104, r0): arrastre `[geometric, weibull, none, weibull]`, saturación `[tanh, logistic, hill, hill]`. La API no expone una forma pública de forzar identidad/linealidad por preset; **la configuración adicional «S0 lineal» no se ha construido** (E02 parcial).
5. **Roles de canal**: S0–S2 tienen todos los canales con `C→Y`. S3 (`treatment_halo`, `connect_all=False`) tiene 5 canales, 3 con `C→Y` y 2 *feeders* (solo `C→C`). S4 puede tener *feeders* y nulos aislados. Su respuesta observed-path verdadera es exactamente 0 (test).
6. **Mismo `seed`, distinto `T` ≠ mismo sistema truncado**: en este banco las semillas se derivan de `(escenario, T, réplica)` con SHA-256, así que los mundos de distinto `T` son independientes y **no** se tratan como pares longitudinales.
7. **Shocks de tratamiento** (`n_treatment_shocks`) desactivados por defecto en los presets (0); no se usan en v1.
8. **Persistencia**: el corpus `float32` cumple la identidad con tolerancia relativa 1e-5 y deja a cero los slots de padding (test `test_float32_persistence_tolerance`). Este banco no evalúa desde corpus: guarda el `SCM` completo (pickle local, solo artefactos propios) en `runs/_worlds/` y deriva `ObservedDataset`/`TruthRegistry` en cada carga.

## Contrafactuales (`do`) — implementado y validado

No existe API pública de intervención. [interventions.py](../mmm_benchmark/interventions.py) reconstruye el grafo generativo con `build_world_model`, enlaza **todas** las primitivas (parámetros e innovaciones `eps_*`) igual que `SCM.replay()`, localiza las columnas de tratamiento por canal (entradas del `Join` que forma `treatments`; en PyTensor 3.3.4 el eje es atributo, no entrada) y las sustituye por `switch(mask, valor, natural)` en orden topológico, de modo que los hijos `C→C` ven al padre intervenido. Pruebas por mundo (`engine_validation.csv`):

- intervención nula sobre todos los canales reproduce `Y` (error 0.0);
- canal sin ruta a `Y` → efecto ≤ 1e-9;
- intervención desde la semana `s` no altera `Y_{t<s}`;
- sin `C→C`, `ΔY` = `g·β·(f(a) − f(obs))` con las transformaciones verdaderas (≤ 1e-14);
- con `C→C`, los descendientes cambian y los no descendientes no.

Semántica: `do(C_k)` fija el tratamiento **tras** softplus/clamp, corta sus causas entrantes y deja reaccionar a los descendientes; el ruido exógeno se comparte entre brazos y se cancela exactamente.

## Oracle

`latent="marginal"` (por defecto) marginaliza `D` y la base aleatoria; su `contributions` es la respuesta observed-path y se compara con `contributions_observed` en filas reproducibles (≥ 8). Para impedir fugas, el banco sustituye `Y` de test por la media de train **y** restringe la verosimilitud con `observed_indices = 0 … n_train − warmup − 1`. Es una referencia `oracle_structure_known_plugin`: conoce DAG, familias y priors del generador; no es la posterior del SCM completo. Coste medido (S0, T=104, 2×(500+500)): 478 s, 765 MB de RSS máx.; R-hat 1.020, ESS 207 → no convergido según el criterio estricto.
