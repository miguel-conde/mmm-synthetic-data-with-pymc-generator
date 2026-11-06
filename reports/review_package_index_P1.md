# Índice del paquete de revisión — v1.2 P1

El índice P0 (`review_package_index.md`) se conserva sin cambios. Este índice enumera los artefactos de P1 para una auditoría externa. Ningún artefacto ha sido auditado por el diseñador.

## Protocolo y congelación

| Artefacto | Contenido |
|---|---|
| [../docs/protocolo_P1_registrado.md](../docs/protocolo_P1_registrado.md) | Protocolo P1 (D1–D3) y regla de respuesta de la Entrega A; anexos A (E10A) y B (E14) registrados antes de ejecutar |
| `v1_2/FREEZE_MANIFEST_P0.json` | 3 220 hashes de P0 (informes, `reports/v1_2`, `runs/v1_2_warmfit`, configuración, borrador, snapshot de código) |
| `v1_2/code_snapshot_P0/` | Código, tests, configuraciones y `uv.lock` del estado P0 (pasa los 87 tests de P0) |
| [v1/ERRATA.md](v1/ERRATA.md), [v1_1/ERRATA.md](v1_1/ERRATA.md) | Fe de erratas del defecto de inicialización (ficheros nuevos; los congelados no cambian) |

## Entrega A — M3 con verosimilitud enmascarada

| Artefacto | Contenido |
|---|---|
| [p1a_warmup_validation.md](p1a_warmup_validation.md) | Arquitectura, pruebas 1–6, concordancia con la referencia independiente, ensayo, reproducibilidad |
| [p1a_m3_rebaseline.md](p1a_m3_rebaseline.md) | V3 histórica frente a V3 enmascarada en 10 mundos, respuesta (no concluyente), indicadores ROPE |
| `v1_2/p1a/` | `pilot_world_channel.csv`, `pilot_paired_direct.csv`, `pilot_rope_by_role.csv`, `reference_agreement.csv`, `trial_fits.csv`, `reproduction_v1_1_vs_rerun.csv`, `pytest_p1a.{txt,xml}`, pickles de las referencias |
| Código | `mmm_benchmark/models/bayes.py` (`build`, `_mask_history_likelihood`), `mmm_benchmark/p1a.py`, `tests/test_p1a_masking.py` |
| Configuraciones / runs | `configs/v1_2_p1a_{trial,hist,pilot}.yaml` → `runs/v1_2_p1a_{trial,hist,pilot}/` |

## Líneas base corregidas

| Artefacto | Contenido |
|---|---|
| [p1_corrected_baselines.md](p1_corrected_baselines.md) | Histórico (semana 0) frente a corregido (semana 8): atribución, predicción, E08 y E09 |
| `v1_2/p1_corr/` | `metrics_hist_vs_corr.csv`, `e08_hist_vs_corr.csv`, `e09_hist_vs_corr.csv` |
| Configuraciones / runs | `configs/v1_2_corr_{f3,e0809,e10a_D,e10a_rho}.yaml` → `runs/v1_2_corr_*/` |

## P1b — E10A

| Artefacto | Contenido |
|---|---|
| [p1b_e10a_confounding.md](p1b_e10a_confounding.md) | Sesgo `do_zero` pareado por mecanismo, métricas secundarias, correlaciones logradas |
| `v1_2/p1b/` | `primary_do_zero_bias.csv`, `secondary.csv`, `descriptors.csv`, `latent_corr.csv` |
| Configuraciones / runs | `configs/v1_2_p1b_e10a_{dc,dy,rho}.yaml` → `runs/v1_2_p1b_e10a_*/` |
| Código / test | `mmm_benchmark/p1b.py`; `tests/test_generator_contract.py::test_e10a_mechanisms_are_paired` |

## P1c — E14

Solo la sonda de diseño y la propuesta (Anexo B del protocolo). No se ha ejecutado.

## Respuesta

[../docs/respuesta_P1_al_disenador.md](../docs/respuesta_P1_al_disenador.md)
