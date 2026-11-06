# Respuesta al diseñador tras P1B (v1.2)

**Fecha:** 2026-11-06. **En respuesta a:** `docs/RESPUESTA_AL_AGENTE_MMM_POST_P1_ENTREGA_A.md`.

- **Protocolo:** `docs/protocolo_P1B_registrado.md`, registrado antes de cada bloque, con anexos de lanzamiento y selección.
- **Índice:** `reports/review_package_index_P1B.md`.
- **Estado congelado:** `reports/v1_2/FREEZE_MANIFEST_P1B.json` (con snapshot de código). Los manifiestos de P1A, P0, v1 y v1.1 se verifican sin diferencias. No afirmo que el diseñador haya auditado estos artefactos.

## Respuestas a las seis preguntas

**(i) Enmascaramiento frente a escalado.** Todo el cambio de M3 proviene del enmascaramiento; el escalado no contribuye (`reports/p1a_mask_vs_scale.md`).
- **Tests deterministas:**
  - B y C tienen escala idéntica;
  - `logp(B) − logp(C)` es exactamente la suma de los términos de `y` de las semanas 0–7;
  - B ≡ A cuando el máximo de `Y` no cae en 0–7.
- **Consecuencia:** en los 10 mundos del piloto de la Entrega A, la escala era la misma en A y C, así que esa comparación ya aislaba el enmascaramiento. La escala solo difiere en 6 de los 45 mundos de `v1_1_m3`.
- **MCMC en esos 6 mundos (`exploratory`):**
  - B − A ≈ 0 en sesgo, cobertura y anchura (sesgo 0,0000 [−0,0003, 0,0003]), aunque la prior en unidades de `Y` se estrecha un 2–11 %;
  - C − B: sesgo +0,035 [0,013, 0,055] y anchura +0,048.

**(ii) Convergencia sin cambiar el modelo** (`reports/p1a_m3_sampling_diagnostics.md`). Diez mundos de desarrollo: los del piloto, que no son independientes.
- **Variantes:**

  | Variante | Configuración | `converged_strict` |
  |---|---|---|
  | S0r | referencia | 7/10 |
  | S1 | 2000 + 2000 | **9/10** |
  | S2 | masa de rango bajo | 5/10 |

- **Selección:** se eligió S1 solo por convergencia y coste. Pasa la puerta (≥ 8/10, ningún escenario con 0/2).
- **Re-ejecución de S0:** reprodujo exactamente la validez del piloto (7/10 en los mismos mundos).
- **Mundos reservados (45):**
  - `legacy_w0` con S1: 44/45 válidos;
  - `corrected_w8` con S1: 37/45. La verosimilitud enmascarada converge peor. Los fallos son marginales (R-hat 1,010–1,020) salvo uno (1,04).

**(iii) Mejora de cobertura en mundos válidos pareados: sí, fiable pero parcial** (`reports/p1a_m3_confirmatory.md`). Hay 37 pares `converged_strict` en mundos nunca usados para decidir (F2, réplicas 3–5; umbral ≥ 20).

| Directos, `[8, n_train)` | `legacy_w0` | `corrected_w8` | Diferencia, IC95 mundos | IC95 células |
|---|---|---|---|---|
| sesgo | −0,045 | −0,021 | +0,023 [0,017, 0,030] | [0,015, 0,030] |
| cobertura 95 % | 0,42 | 0,56 | +0,15 [0,07, 0,22] | [0,06, 0,26] |
| cobertura 80 % | 0,25 | 0,37 | +0,12 [0,05, 0,20] | — |
| anchura 95 % | 0,068 | 0,106 | +0,038 [0,025, 0,051] | — |

- La corrección **explica una parte**: reduce el sesgo a la mitad y sube la cobertura 15 puntos.
- **No lleva a una calibración aceptable**: el 95 % nominal cubre el 56 %.
- **Coste:** en aislados aumenta la contribución espuria (+0,025 [0,008, 0,043]).
- **ROPE (regla revisada):**
  - sensibilidad en directos de 0,66 → 0,77;
  - en feeders y aislados, M3 **nunca** declara «no relevante» (0 de 26 canales): `HalfNormal` hace la contribución estrictamente positiva;
  - con 26 canales nulos en pares válidos no hay base para evaluar la detección de nulos.

**(iv) Lo que E10A demuestra sin depender de `do_zero`** (`reports/p1b_e10a_robustness.md`).
- La confusión se comprueba **en el DAG**: los canales con ruta C_k←D_j→Y se identifican estructuralmente.
- Con intervenciones locales ±10 % dentro del soporte observado:
  - en los canales confundidos, los modelos que no observan D **sobreestiman la magnitud del efecto**: M0 +7 %, M2p +11–13 %, M2 +16–25 % del efecto verdadero (IC95 excluyen 0);
  - M2p_D, que observa D, ≈ 0;
  - en los canales no confundidos, M2p no cambia.
- La correlación observada entre canales apenas varía (Δ ≤ 0,03; con `dy`, 0 exacto), luego **hay confusión causal sin más correlación**.
- La confusión por `rho` sesga también a M2p_D.
- Límite: la eliminación del sesgo con D ocurre en un modelo privilegiado y no prueba que un MMM ciego identifique el efecto.
- Los parámetros fijados, las innovaciones (primitivas idénticas; series resultantes cuantificadas) y los denominadores fijos se documentan por mecanismo.

**(v) E14: solo «correlación inducida por Z con cambios de distribución»** (`reports/p1c_e14_design_gate.md`).
- **DAG correcto en los 90 mundos:** Z→C, sin Z→Y, D→C, C→C ni `rho`; D→Y se mantiene por conectividad.
- **Lo que no cambia:** la cuota de medios y el efecto verdadero (±4 %).
- **Lo que sí cambia:**
  - la desviación típica de los canales (×1,35 y ×2,06);
  - el cociente ruido/sd(Y) (×0,5–0,6).
- **Separación de la correlación:** el segundo escalón queda justo por debajo del criterio registrado (67 % frente a 70 % de pares).
- **No se ajusta.** Se propone un control con márgenes fijados (reescalar la parte explicada por Z para conservar sd(C)), que requiere intervenir tensores del generador. Pendiente de aprobación.

**(vi) M2: basta mantenerlo como caso de contraste; M2v2 solo como diseño** (`reports/m2_selection_audit.md`, 600 mundos, sin reajuste).
- **La selección de formas es inestable:**
  - quitar 8 filas cambia α en el 62 % de los canales;
  - se eligen con frecuencia los extremos de la rejilla (α = 0,85 y κ = 0,25, ≈ 30 % cada uno);
  - el α elegido apenas sigue al verdadero (Spearman 0,16).
- La sobreestimación tras la corrección se concentra en canales con saturación y arrastre elegidos (media +0,106, mediana +0,045). El defecto de inicialización la ocultaba.
- No hay un patrón entre mundos de «predice bien y atribuye mal»: el RMSE de validación correlaciona positivamente con |sesgo|.
- **M2v2 propuesto, sin ejecutar:**
  - adstock normalizado;
  - rejilla sin extremos;
  - validación con 3 orígenes rodantes y regla de un error estándar;
  - desarrollo en F2 réplicas 0–2 y evaluación en F3 réplicas 10–39.

## Hallazgos y anomalías

- **Defecto propio corregido antes de obtener resultados:** el cálculo de E-BFMI fallaba con arviz 1.x y abortó los primeros ajustes de P1B. Se cambió por la fórmula directa sobre la energía, se borraron solo esos resultados fallidos y se relanzó con la misma configuración y semilla.
- **Paralelización registrada:** un segundo proceso del brazo C compartió directorio. Seis mundos de S3 se ajustaron dos veces y se conserva el último resultado, como estaba registrado.
- **Nota del motor `do`:** la diferencia del 3–5 % entre el efecto `do_zero` del motor y la contribución observada en E14 corresponde al arrastre anterior a la semana 8. No es un error del motor.

## Coste y pruebas

- **Tests:** 108 de 108 pasan, incluidos los tres de A/B/C (`reports/v1_2/p1b_m3/pytest_p1b.txt`).
- **MCMC:**
  - A/B/C: 18 ajustes (≈ 40 min);
  - variantes de muestreo: 30 ajustes (≈ 1 h 50 min de CPU);
  - confirmatorio: 90 ajustes más 6 duplicados (≈ 2 h 15 min de pared).
- **Sin MCMC:** cierre de E10A, auditoría de M2 y generación de los 90 mundos de E14 con el motor `do` (≈ 30 min).
- Sin campañas de 600 mundos MCMC, sin oracle y sin redes neuronales.

## Estado científico

`reports/scientific_status_P1B.md` sustituye como vigente a la tabla de P0, que sigue congelada.
- **Confirmados en este banco:** H3, H6, H7, H9 (parte M3) y la inestabilidad de la selección de M2.
- **No ejecutados:** H5 (E14) y H11.
- Las cifras de M3 de v1 y v1.1 se etiquetan como anteriores a la corrección del ajuste.

## Decisiones pendientes

1. **E14:** aprobar el control con márgenes fijados (requiere intervenir el generador) o ejecutar el diseño actual etiquetado como «correlación inducida por Z con cambios de distribución».
2. **M3:** con la ventana corregida estabilizada (S1), ¿se estudia primero la forma funcional (Weibull/Hill) o la contracción/ROPE? Recomiendo la forma funcional, porque el sesgo residual y la infra-cobertura en directos son el problema principal, y M3 no puede declarar nulos con la prior actual.
3. **M2v2:** ¿se autoriza ejecutar el diseño propuesto?
