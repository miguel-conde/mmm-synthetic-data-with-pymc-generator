# Índice del paquete de revisión — v1.2 P1B

Los índices anteriores (`review_package_index.md` de P0 y `review_package_index_P1.md` de la Entrega A) se conservan sin cambios. Ningún artefacto ha sido auditado por el diseñador.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Protocolo registrado antes de cada bloque | [../docs/protocolo_P1B_registrado.md](../docs/protocolo_P1B_registrado.md) (incluye los anexos de lanzamiento y la selección de muestreo) |
| Estado congelado previo | `v1_2/FREEZE_MANIFEST_P1A.json` (20 597 hashes) + `v1_2/code_snapshot_P1A/`; P0, v1 y v1.1 intactos |
| Versiones | `uv.lock` sin cambios desde v1 (pymc-marketing 1.3.0, pymc 6.3.2, nutpie 0.16.11, pymc-generator `fb9549d`); huella de entorno en `runs/*/manifest.json` (`sessions`) |
| Semillas | `derive_seed(world_id, "M3_pymc_marketing", "fit")` para M3 (todos los brazos y variantes); mundos: `WorldSpec.config_seed` / `world_seed` |
| Tests | `v1_2/p1b_m3/pytest_p1b.{txt,xml}` |
| Estado científico | [scientific_status_P1B.md](scientific_status_P1B.md) |

## Entregables

| Nº | Informe | Datos | Configuración / runs | Código |
|---|---|---|---|---|
| 1 | [p1a_mask_vs_scale.md](p1a_mask_vs_scale.md) | `v1_2/p1b_m3/abc_*.csv` | `configs/v1_2_p1b_abc_w{0,8}.yaml` → `runs/v1_2_p1b_abc_w*` | `models/bayes.py` (`scale_from`), `p1b_m3.py`, tests `test_abc_*` |
| 2 | [p1a_m3_sampling_diagnostics.md](p1a_m3_sampling_diagnostics.md) | `v1_2/p1b_m3/sampling_fits.csv` | `configs/v1_2_p1b_samp_{S0r,S1,S2}.yaml` | `p1b_m3.py` |
| 3 | [p1a_m3_confirmatory.md](p1a_m3_confirmatory.md) | `v1_2/p1b_confirm/` | `configs/v1_2_p1b_conf_{A,C}_*.yaml` → `runs/v1_2_p1b_conf_*` | `p1b_confirm.py` |
| 4 | [p1b_e10a_robustness.md](p1b_e10a_robustness.md) | `v1_2/p1b_robust/` | runs E10A de P1 (sin reajuste) | `p1b_robust.py` |
| 5 | [p1c_e14_design_gate.md](p1c_e14_design_gate.md) | `v1_2/p1c/` | `configs/v1_2_p1c_e14.yaml` (solo generación) | `p1c.py` |
| 6 | [m2_selection_audit.md](m2_selection_audit.md) | `v1_2/m2_audit/` | runs `extended` y `v1_2_corr_f3` (sin reajuste) | `m2_audit.py` |

## Unidades de inferencia

- **M3:** mundo, con bootstrap de mundos y, como sensibilidad, de células DAG.
- **E10A:** par de mundos, con bootstrap de pares y de células DAG (`rho` tiene una sola célula).
- **E14:** par de mundos.
- **M2:** canal para las frecuencias de formas elegidas y mundo para los contrastes.
