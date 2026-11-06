# Registro de experimentación

## 2026-11-05 — H0: auditoría del entorno y API

- Entorno uv: `pymc-generator` fijado a `fb9549d`, cooldown 7 días. Dependencias nuevas aprobadas por el usuario tras evaluación (PyPI + OSV): `xgboost-cpu 3.4.1` (sin NCCL/GPU), `lightgbm 4.7.0`, `pytest 9.2.0`; declaradas sin cambio de versión: scikit-learn, pyyaml, pyarrow, psutil. `uv audit` no existe en uv 0.10.6 → OSV sobre todo el lock: sin hallazgos.
- Auditoría de API y semántica de verdad: [generator_audit.md](generator_audit.md). Estimandos y pre-registro: [estimands.md](estimands.md), [methods.md](methods.md) (escritos **antes** de ajustar modelos).
- Hallazgos clave: burn-in de 8 semanas (excluir semanas 0–7), `baseline` con ruido, S0 no lineal, S3 con 2 *feeders* sin `C→Y`, ninguna API `do`.

## H1 — datos, verdad y sanidad

- `generator_adapter.py`: semillas `SHA-256(20261105|escenario|T|réplica|propósito)`, caché `runs/_worlds/` (pickle local), `ObservedDataset` / `TruthRegistry`.
- `interventions.py`: motor `do` por sustitución de grafo con primitivas compartidas. Validado en S0/S3/S4 (null exacto, causalidad temporal, `C→C` solo a descendientes, coincidencia 1e-15 con la respuesta del canal).
- Tests (`pytest -q`): 61 (contrato del generador, fugas, reproducibilidad, métricas, intervenciones).
- F0 (`configs/smoke.yaml`): 5 mundos T=104, bundles en `runs/smoke/bundles/`, 50 ajustes rápidos `ok`, motor `do` validado en 5/5.

## H2–H4 — modelos y evaluación

- Implementados N0, N1, M0, M1, M2, M2_noZ, M2p, M2p_D, M3 (PyMC-Marketing 1.3.0: GeometricAdstock(8) + LogisticSaturation, controles + tendencia + Fourier 2), M4 (`pg.sample_oracle`, marginal), M5 (xgboost-cpu), M6 (LightGBM).
- Sonda de coste (`configs/bayes_probe.yaml`, S0 T=104, 2×(500+500)): M3 13.5 s / 521 MB, R-hat 1.025, ESS 132; M4 478 s / 765 MB, R-hat 1.020, ESS 207. **Ninguno convergido** con el criterio estricto → piloto con M3 4×(1000+1000) y M4 2×(1000+1000).
- Coste de memoria: el RSS crece ~200 MB por mundo dentro de un proceso (cachés de compilación PyTensor). Se añade `--max-worlds` y `scripts/run_phase.sh` para ejecutar en bloques reanudables.

## H5 — contrafactuales

- E08: `do_null`, `do_zero`, `do_reduce_10/20`, `do_increase_10` sobre `[8, n_train)` y `do_pulse` (+nivel medio, una semana) a mitad de ventana; efecto acumulado en la misma ventana en ambos brazos.
- E09: multiplicadores por canal en [0.5, 1.5] con presupuesto total fijo en unidades de tratamiento; valor verdadero vía `do` sobre todos los canales; oracle por SLSQP sobre el motor.
- Optimización durante el piloto (resultados idénticos, verificado): la respuesta verdadera de M2p se compila una vez por mundo (≈1 ms/llamada; antes ≈1.5 s) y la respuesta de M3 se compila desde el grafo del modelo y se evalúa sobre los draws posteriores (coincide con `sample_posterior_predictive` a 2e-15; test añadido). El primer bloque del piloto usó la versión lenta; el `code_sha256` de cada sesión queda en `runs/pilot/manifest.json`.

## Ejecuciones

| Fase | Config | Estado |
|---|---|---|
| F0 | smoke.yaml | completada: 5 mundos, 50 ajustes, bundles en `runs/smoke/bundles/` |
| sonda | bayes_probe.yaml | completada: M3 13.5 s, M4 478 s |
| F1 | pilot.yaml | completada: 45 mundos, 460 ajustes, 0 fallos; M3/M4 en 5; E08/E09 en 15 |
| F2 | core.yaml | completada: 150 mundos, 1 545 ajustes, 0 fallos; M3 en 45; E08/E09 en 45 (motor validado 45/45) |
| F2-oracle | core_oracle.yaml | **en cola, no ejecutada** (≈6–15 min/mundo) |
| F3 | extended.yaml | completada: 600 mundos (incluye F2), 6 000 ajustes, 0 fallos |
| Informe | `cli report ...` | [reports/benchmark_report.md](../reports/benchmark_report.md); narrativa en [report_narrative.md](report_narrative.md) |

## Cierre del ciclo v1 (2026-11-05 20:20)

- Tiempo de pared: piloto ≈ 1 h (dominado por M4), F2 ≈ 32 min, F3 ≈ 44 min. RSS máx. por proceso ≤ 1.2 GB con bloques de 8–40 mundos.
- Correcciones de informe tras la primera generación (no afectan a resultados): conteo de `N` ignoraba NaN de `stack()` en pandas 3; se añaden tablas H2 y submuestra común de M3; filas de verdad E08 sin `model_id` en `runs/smoke` re-etiquetadas (mismos valores).
- Observación no prevista: `confounding_strength = 0` en todos los presets (la confusión de S1 actúa solo por aristas `D→C`/`D→Y`); se cita en la interpretación de H3.
- Pendiente: ver §13 del informe.

## 2026-11-05 — Revisión v1.1 (respuesta del diseñador D1–D7)

- v1 congelada (`reports/v1/`, `FREEZE_MANIFEST.json`, 18 233 hashes). Registro previo en [revision_v1_1.md](revision_v1_1.md) antes de ejecutar.
- **Error de v1 encontrado:** `pd.read_csv` convertía el rol `"null"` en NaN y los canales aislados faltaban en la tabla de falsas atribuciones. Rol renombrado `isolated`; lectura con `keep_default_na=False`.
- Código: variantes pareadas en `WorldSpec` (las semillas ignoran la variante), `response_warmup_weeks`, `fit_scope: full`, etiquetas D2, `random_feasible` y `selected_channels_do_policy`, posterior y geometría de M3, prior V3, `revision.py` + `cli revise`. Tests: 79 pasan.
- Runs v1.1, 0 fallos: `v1_1_m3_diag` (40), `v1_1_m3` (45), `v1_1_m4_diag` (6), `v1_1_e02_linear` (309), `v1_1_full_refit` (180), `v1_1_e10a_D` (240), `v1_1_e10a_rho` (240), `v1_1_e09` (45 mundos). Motor `do` validado en 114/114 mundos distintos.
- Elección de M3 V3 por regla pre-registrada (9/10 frente a 7/10 de V2), sin usar la verdad.
- Entregables: `reports/benchmark_report_v1_1.md`, `reports/quality_gate_v1_1.md`, `reports/mcmc_diagnostics.md`, `docs/respuesta_v1_1_al_disenador.md`.

## 2026-11-06 — v1.2 P0 (respuesta del diseñador RESPUESTA_AL_AGENTE_MMM_V1_2.md)

- v1.1 congelada (`reports/v1_1/`, `FREEZE_MANIFEST.json`, 4 616 hashes). `bayes.py` evolucionó (guarda nueva); su versión v1.1 está reconstruida y verificada en `reports/v1_1/code_snapshot/`.
- C5: `tables_io.read_table` (roles categóricos, sin conversión silenciosa de `null`); tests de ida y vuelta y de las 194 parejas aisladas de v1.
- **Error de protocolo demostrado:** ajuste desde la semana 0 con *burn-in* no reproducible ⇒ sesgo negativo de los coeficientes de medios (M2p: −0,036 → +0,004 al ajustar desde la semana 8). Corregido para los modelos rápidos (`fit_scope: train_after_warmup`, `runs/v1_2_warmfit`, 150 mundos, 1 500 ajustes, 0 fallos). M3 rechaza ahora esa ventana (falta verosimilitud enmascarada).
- Auditorías sin reajuste: cobertura de M3 (`reports/m3_coverage_audit.md`), políticas E09 con 4 niveles de información y multi-arranque (`reports/e09_policy_audit.md`).
- Estado de H1–H11: `reports/scientific_status_v1_2.md`. Quality gate: `reports/quality_gate_v1_2.md` (87 tests pasan).
- Protocolo P1 en borrador, **no ejecutado**: `docs/protocolo_v1_2_P1.md`. Respuesta: `docs/respuesta_v1_2_al_disenador.md`.

## 2026-11-06 — v1.2 P1 (respuesta del diseñador RESPUESTA_AL_AGENTE_MMM_TRAS_P0_V1_2.md)

- **Estado P0 congelado:** `reports/v1_2/FREEZE_MANIFEST_P0.json` (3 220 hashes), con snapshot de código `reports/v1_2/code_snapshot_P0/`, que pasa los 87 tests de P0. Fe de erratas nuevas (sin tocar ficheros congelados): `reports/v1/ERRATA.md` y `reports/v1_1/ERRATA.md`. Protocolo vigente: `docs/protocolo_P1_registrado.md`, con anexos A (E10A) y B (E14), registrados antes de ejecutar.
- **M3 con verosimilitud enmascarada:** clase estándar `pymc_marketing.mmm.MMM` 1.3.0 más un `Potential` que resta los términos de `y` de las semanas 0–7, `FixedScaling` sobre `[8, n_train)` y `Y[0:8]` sustituido por un marcador.
  - Tests deterministas: logp = suma manual; invariancia exacta a `Y[0:8]`; igualdad con una referencia PyMC independiente hasta una constante.
  - MCMC: concordancia con la referencia ≤ 0,10 SD (E02 lineal y S4 Weibull).
- **Defectos encontrados y corregidos:**
  - `causal.horizon` y el oráculo M4 usaban `len(train_idx)`, de modo que la ventana E08/E09 encogía con un ajuste tardío.
  - `WorldStore` reutilizaba un mundo de la caché con el mismo id aunque los *overrides* fueran distintos; ahora lo rechaza.
  - Ninguno de los dos afecta a resultados previos (verificado: 1 963 mundos en caché coinciden con su especificación).
- **Reproducibilidad:** MCMC con la misma semilla y el mismo entorno no siempre es bit a bit reproducible (idéntico en 4 de 10 mundos; en el resto, hasta un 3 % en contribuciones). La validez cambia en 3 de 10 mundos cerca de R-hat 1,01.
- **Runs:**
  - `v1_2_p1a_trial` (4 mundos);
  - `v1_2_p1a_hist` (V3 desde la semana 0, re-ejecutada con posterior, 10);
  - `v1_2_p1a_pilot` (V3 enmascarada, 10);
  - correcciones `v1_2_corr_{e0809,e10a_D,e10a_rho,f3}`;
  - E10A `v1_2_p1b_e10a_{dc,dy,rho}` (3 × 120 mundos).
- **Entrega A:** respuesta **no concluyente** (4 de 10 mundos con ambos ajustes válidos). Por la regla de interrupción, no se amplía M3 y no se inician las variantes de la Entrega B.
- **E14:** sonda de diseño. El rango por defecto de `zc` no separa la correlación; los niveles propuestos (0 / 1,5 / 3,0) están pendientes de confirmación. No se ejecuta.

## 2026-11-06 — v1.2 P1B (respuesta del diseñador RESPUESTA_AL_AGENTE_MMM_POST_P1_ENTREGA_A.md)

- **Congelación previa:** P1A en `reports/v1_2/FREEZE_MANIFEST_P1A.json` (20 597 hashes, con snapshot). Protocolo: `docs/protocolo_P1B_registrado.md`.
- **A/B/C** (6 mundos con escala distinta): la escala no influye (B − A ≈ 0); todo el efecto es del enmascaramiento. En el piloto de la Entrega A la escala ya era idéntica.
- **Muestreo** (10 mundos de desarrollo): S0r 7/10, S1 (2000 + 2000) 9/10, S2 (rango bajo) 5/10. Se elige S1 y la puerta pasa.
- **Confirmatorio** (F2 réplicas 3–5, 37 pares válidos):
  - sesgo en directos −0,045 → −0,021;
  - cobertura 95 % 0,42 → 0,56;
  - aumenta la contribución espuria en aislados;
  - M3 nunca declara «no relevante».
- **E10A, cierre analítico:** la confusión se verifica en el DAG; con ±10 %, sobreestimación de la magnitud del efecto en canales confundidos; M2p_D ≈ 0.
- **E14, puerta de diseño:** no pasa por cambios de márgenes y separación justa. No se ajusta.
- **Auditoría M2:** selección inestable (62 % de formas cambian al quitar 8 filas). M2v2 solo como diseño.
- **Defecto propio corregido:** E-BFMI con arviz 1.x (relanzado). Seis mundos duplicados por la paralelización registrada.
- **Tests:** 108 pasan. Estado: `reports/scientific_status_P1B.md`. Congelado: `reports/v1_2/FREEZE_MANIFEST_P1B.json`. Respuesta: `docs/respuesta_P1B_al_disenador.md`.
