# Índice del paquete de revisión (v1.2 P0)

## Entregables P0 (v1.2)

| Documento | Contenido |
|---|---|
| [quality_gate_v1_2.md](quality_gate_v1_2.md) | integridad de v1/v1.1, pruebas, roles, unidades, motor `do`, error de *burn-in* |
| [m3_coverage_audit.md](m3_coverage_audit.md) | cobertura, anchura y sesgo de M3 por rol, escenario, T y validez; V0 frente a V3; desarrollo frente a evaluación |
| [e09_policy_audit.md](e09_policy_audit.md) | familia principal (verificación del optimizador) y secundaria con 4 niveles de información |
| [scientific_status_v1_2.md](scientific_status_v1_2.md) | H1–H11 con estado, estimando, mundos e IC; corrección de la ventana de ajuste |
| [../docs/respuesta_v1_2_al_disenador.md](../docs/respuesta_v1_2_al_disenador.md) | respuesta breve y decisiones pedidas |
| [../docs/protocolo_v1_2_P1.md](../docs/protocolo_v1_2_P1.md) | protocolo P1 (borrador para decisión; no ejecutado) |

## Datos de soporte v1.2 (`reports/v1_2/`)

| Fichero | Grano |
|---|---|
| `m3_world_channel.csv` | variante × mundo × canal × ventana (cobertura 50/80/95, anchura, sesgo, MAE, rol, familias verdaderas, validez) |
| `fit_window_correction.csv`, `fit_window_paired.csv` | modelo (150 mundos F2), ajuste desde la semana 0 frente a la semana 8 |
| `privileged_baseline_diagnostic.csv` | canal directo × variante del diagnóstico privilegiado |
| `e09_clamped_optimizer_check.csv`, `e09_selected_policy_audit.csv` | mundo (× política × nivel de información) |
| `hypothesis_status.csv` | hipótesis |
| `pytest_v1_2.xml`, `pytest_v1_2.txt` | resultado de pruebas |

## Versiones congeladas

| Versión | Informe principal | Manifiesto |
|---|---|---|
| v1 | [v1/benchmark_report.md](v1/benchmark_report.md) | `v1/FREEZE_MANIFEST.json` |
| v1.1 | [v1_1/benchmark_report_v1_1.md](v1_1/benchmark_report_v1_1.md), [v1_1/quality_gate_v1_1.md](v1_1/quality_gate_v1_1.md), [v1_1/mcmc_diagnostics.md](v1_1/mcmc_diagnostics.md) | `v1_1/FREEZE_MANIFEST.json` |

## Definiciones y registro previo

[../docs/estimands.md](../docs/estimands.md) · [../docs/methods.md](../docs/methods.md) · [../docs/revision_v1_1.md](../docs/revision_v1_1.md) · [../docs/generator_audit.md](../docs/generator_audit.md) · [../docs/assumptions_and_limits.md](../docs/assumptions_and_limits.md) · [../docs/experiment_log.md](../docs/experiment_log.md)

## Configuraciones y ejecuciones

- v1: `configs/{smoke,bayes_probe,pilot,core,extended}.yaml` → `runs/{smoke,bayes_probe,pilot,core,extended}`
- v1.1: `configs/v1_1_*.yaml` → `runs/v1_1_*`
- v1.2: `configs/v1_2_warmfit.yaml` → `runs/v1_2_warmfit`

Muestra rastreable por mundo: `runs/<run>/results/<world_id>/<model>.json` (métricas, diagnósticos, semilla), `<model>.npz` (predicciones, contribuciones, intervalos) y `_world.json` (DAG, mecanismos, validación del motor). Los mundos se regeneran desde semillas o se leen de `runs/_worlds/`.

Reproducir P0: `MPLBACKEND=Agg uv run --locked python -m mmm_benchmark.cli audit-v1-2`.
