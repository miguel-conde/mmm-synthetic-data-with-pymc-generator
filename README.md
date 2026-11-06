# Banco MMM sobre mundos sintéticos de `pymc-generator`

Banco reproducible que compara OLS, Ridge, regresión con adstock/saturación, PyMC-Marketing, el oracle de `pymc-generator`, XGBoost y LightGBM frente a la **verdad causal conocida** del generador. Evalúa **por separado** la predicción, la recuperación de contribuciones históricas, la incertidumbre y, gracias a un motor contrafactual validado, los efectos de intervención y las decisiones de presupuesto.

> Ningún resultado de este repositorio procede de River.

- Protocolo: [docs/mmm-synthetic-experiments/](docs/mmm-synthetic-experiments/)
- Estimandos (pre-registro): [docs/estimands.md](docs/estimands.md) · Métodos, hipótesis y umbrales: [docs/methods.md](docs/methods.md)
- Auditoría del generador: [docs/generator_audit.md](docs/generator_audit.md) · Límites: [docs/assumptions_and_limits.md](docs/assumptions_and_limits.md)
- Registro de trabajo: [docs/experiment_log.md](docs/experiment_log.md) · Informe: [reports/benchmark_report.md](reports/benchmark_report.md)

## Entorno

Requiere [uv](https://docs.astral.sh/uv/) y Python 3.13. Las dependencias están fijadas en `uv.lock` (cooldown de 7 días, `pymc-generator` fijado a un commit).

```bash
uv sync --locked
uv run --locked python -m mmm_benchmark.cli doctor      # versiones, commit, CPU/RAM
uv run --locked pytest -q                                # 60 tests (≈1 min)
```

## Reproducir cada fase

Cada fase es resumible e idempotente: un JSON + NPZ por (mundo, modelo) en `runs/<fase>/results/`. Los fallos se registran y no detienen la ejecución. Los mundos se generan una sola vez en `runs/_worlds/` y se reutilizan entre fases, de modo que los mundos de F2 están contenidos en F3. `scripts/run_phase.sh` procesa los mundos en bloques para acotar la memoria.

| Fase | Comando | Contenido |
|---|---|---|
| F0 inspección + smoke | `MPLBACKEND=Agg uv run --locked python -m mmm_benchmark.cli run --config configs/smoke.yaml` | 5 mundos (T=104), bundles completos, modelos rápidos, motor `do` |
| Coste MCMC | `... cli run --config configs/bayes_probe.yaml` | M3 y M4 en un mundo, antes de cualquier lote |
| F1 piloto | `scripts/run_phase.sh configs/pilot.yaml 8` | 45 mundos; M3/M4 en 5 (T=104, r0); E08/E09 en 15 |
| F2 común | `scripts/run_phase.sh configs/core.yaml 10` | 150 mundos; M3 en 45 (r0–2); E08/E09 en 45 |
| F2 oracle (cola) | `scripts/run_phase.sh configs/core_oracle.yaml 2` | M4 en 45 mundos: coste alto, no ejecutado en v1 |
| F3 extensión | `scripts/run_phase.sh configs/extended.yaml 40` | 600 mundos, modelos rápidos |
| Informe | `MPLBACKEND=Agg uv run --locked python -m mmm_benchmark.cli report --run-dir runs/smoke runs/bayes_probe runs/pilot runs/core runs/extended --out reports` | tablas, figuras y `reports/benchmark_report.md` |

Opciones de `run`: `--resume` continúa una fase; `--retry-failed` reintenta los fallos; `--max-worlds N` procesa N mundos pendientes y sale con código 3.

### Revisión v1.1

v1 está congelada en `reports/v1/` (con `FREEZE_MANIFEST.json`). Las decisiones del diseñador y el registro previo de v1.1 están en [docs/revision_v1_1.md](docs/revision_v1_1.md).

| Experimento v1.1 | Comando |
|---|---|
| Diagnóstico M3 (V0–V3) | `scripts/run_phase.sh configs/v1_1_m3_diag.yaml 10` |
| M3 con la variante elegida en 45 mundos | `scripts/run_phase.sh configs/v1_1_m3.yaml 15` |
| Diagnóstico del oracle | `scripts/run_phase.sh configs/v1_1_m4_diag.yaml 1` |
| Control lineal E02 | `scripts/run_phase.sh configs/v1_1_e02_linear.yaml 15` |
| `historical_full_refit` | `scripts/run_phase.sh configs/v1_1_full_refit.yaml 15` |
| E10A confusión `D` / `rho` | `scripts/run_phase.sh configs/v1_1_e10a_D.yaml 15` · `scripts/run_phase.sh configs/v1_1_e10a_rho.yaml 15` |
| E09 v1.1 (aleatoria + `selected_channels_do_policy`) | `scripts/run_phase.sh configs/v1_1_e09.yaml 15` |
| Informes v1.1 | `MPLBACKEND=Agg uv run --locked python -m mmm_benchmark.cli revise` |

`revise` genera [reports/benchmark_report_v1_1.md](reports/benchmark_report_v1_1.md), [reports/quality_gate_v1_1.md](reports/quality_gate_v1_1.md) y las tablas de `reports/tables_v1_1/`. El diagnóstico MCMC está en [reports/mcmc_diagnostics.md](reports/mcmc_diagnostics.md).

### Revisión v1.2 (P0)

v1.1 está congelada en `reports/v1_1/`. Todo el paquete de revisión se indexa en [reports/review_package_index.md](reports/review_package_index.md).

```bash
scripts/run_phase.sh configs/v1_2_warmfit.yaml 50                         # modelos rápidos con ajuste en [8, n_train)
MPLBACKEND=Agg uv run --locked python -m mmm_benchmark.cli audit-v1-2     # auditorías P0, pytest, quality gate, índice
```

### v1.2 P1

P0 está congelado en `reports/v1_2/FREEZE_MANIFEST_P0.json`. Protocolo: [docs/protocolo_P1_registrado.md](docs/protocolo_P1_registrado.md). Índice: [reports/review_package_index_P1.md](reports/review_package_index_P1.md).

```bash
# M3 con verosimilitud enmascarada (ensayo, columna histórica, piloto) y referencias independientes
for c in v1_2_p1a_trial v1_2_p1a_hist v1_2_p1a_pilot; do scripts/run_phase.sh configs/$c.yaml 5; done
MPLBACKEND=Agg uv run --locked python -c "from mmm_benchmark import p1a; p1a.run_reference_fits(); p1a.write_rebaseline_report(); p1a.write_validation_report(p1a.run_tests())"
# líneas base corregidas (mismos mundos y semillas, ajuste en [8, n_train))
for c in v1_2_corr_e0809 v1_2_corr_e10a_D v1_2_corr_e10a_rho v1_2_corr_f3; do scripts/run_phase.sh configs/$c.yaml 40; done
MPLBACKEND=Agg uv run --locked python -c "from mmm_benchmark import p1_corr; p1_corr.write_report()"
# E10A (P1b)
for m in dc dy rho; do scripts/run_phase.sh configs/v1_2_p1b_e10a_$m.yaml 40; done
MPLBACKEND=Agg uv run --locked python -c "from mmm_benchmark import p1b; p1b.write_report()"
```

MCMC con la misma semilla no siempre es bit a bit reproducible (diferencias de hasta ≈ 3 % en contribuciones).

## Estructura

```text
mmm_benchmark/
  provenance.py        semillas SHA-256 (maestra 20261105), versiones, hashes, huella del sistema
  schema.py            ObservedDataset (lo que ve el analista) / TruthRegistry (solo evaluador) / ModelOutput, estimandos
  generator_adapter.py única puerta a pymc-generator; caché de mundos; separación observado/verdad
  transforms.py        adstock/saturación ciegos; transformaciones verdaderas (PRIVILEGIADAS)
  interventions.py     motor do() con innovaciones compartidas + validación
  models/              base (interfaz), linear (N0,N1,M0,M1,M2,M2_noZ,M2p,M2p_D), bayes (M3,M4), trees (M5,M6)
  evaluation.py        métricas y puntuación por estimando
  causal.py            E08 intervenciones, E09 presupuesto
  runner.py            ejecución resumible, manifiestos, agregación
  reporting.py         tablas, figuras, informe Markdown
  cli.py               doctor | generate | run | report
configs/               smoke, bayes_probe, pilot, core, core_oracle, extended
tests/                 contrato del generador, fugas, métricas, modelos, intervenciones
```

`runs/` no se versiona (`.gitignore`); se regenera a partir de las configuraciones y las semillas.

## Garantías contra fugas

- `fit()` solo recibe `ObservedDataset.fit_view()`: el `Y` de test está enmascarado con NaN y no contiene la verdad del generador. Los tests comprueban que cambiar el `Y` futuro o permutar la verdad no altera los ajustes ciegos.
- Las escalas y los hiperparámetros se eligen con validación temporal dentro del tramo de train.
- Los modelos privilegiados (`M2p*`, `M4`) reciben el mundo a través de un método separado (`attach_privileged`) y quedan fuera de los rankings ciegos.
