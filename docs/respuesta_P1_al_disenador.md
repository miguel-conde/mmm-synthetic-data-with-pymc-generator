# Respuesta al diseñador tras P1 (v1.2) — Entrega A, líneas base corregidas y E10A

**Fecha:** 2026-11-06. **En respuesta a:** `docs/RESPUESTA_AL_AGENTE_MMM_TRAS_P0_V1_2.md`. **Protocolo seguido:** `docs/protocolo_P1_registrado.md` (registrado antes de cada ejecución; anexos A y B). Índice de artefactos: `reports/review_package_index_P1.md`.

## 1. Resultados ejecutados

**Congelación.**
- P0: `reports/v1_2/FREEZE_MANIFEST_P0.json` (3 220 hashes), con snapshot de código, que pasa los 87 tests de P0.
- v1 y v1.1: intactos (manifiestos verificados). Fe de erratas añadidas como ficheros nuevos.
- `review_package_index.md` y los informes P0 no se han modificado.

**M3 con verosimilitud enmascarada** (`reports/p1a_warmup_validation.md`).
- **Arquitectura:** sigue siendo la **clase estándar `pymc_marketing.mmm.MMM` 1.3.0**, con una modificación controlada:
  - un `pm.Potential` resta los términos de log-verosimilitud de `y` de las semanas 0–7, tomados del propio grafo;
  - la escala de `Y` usa `FixedScaling` sobre `[8, n_train)`;
  - `Y[0:8]` se sustituye por un marcador antes de entrar al modelo.
  
  No es un modelo PyMC propio.
- **Propiedades 1–3 y 5:** pasan con tests deterministas.
  - logp coincide con la suma manual de `[8, n_train)` (rel 1e-12);
  - la invariancia a `Y[0:8]` es exacta, bit a bit, en logp, gradiente y datos;
  - los canales de 0–7 sí cambian el logp, como corresponde;
  - el adstock usa la secuencia completa.
- **Propiedad 4:**
  - La densidad conjunta es igual, salvo una constante (≈1e-7), a la de una referencia PyMC escrita a mano sin código de pymc-marketing.
  - Por MCMC, la concordancia con esa referencia es de ≤ 0,10 SD en E02 lineal y ≤ 0,05 SD en S4 con Weibull (criterio fijado: ≤ 0,3).
- **Tests:** 105 de 105 pasan (`reports/v1_2/p1a/pytest_p1a.txt`).

**Ensayo y piloto de M3** (`reports/p1a_m3_rebaseline.md`).
- **Ensayo (4 mundos, incluido E02):** 3 de 4 ajustes válidos. El cuarto es E02 r00, con R-hat 1,013 y 0 divergencias.
- **Piloto pareado (10 mundos registrados):** V3 histórica (semana 0, re-ejecutada con la misma semilla para guardar la posterior) frente a V3 enmascarada.

| | V3 histórica (w0) | V3 enmascarada (w8) |
|---|---|---|
| ajustes válidos (R-hat ≤ 1,01, ESS ≥ 400, 0 div.) | 6/10 | 7/10 |
| sesgo medio en directos, `[8, n_train)`, 10 mundos (descriptivo) | −0,022 | +0,001 (dif. +0,023, IC95 [0,012, 0,037]) |
| cobertura IC95 en directos, 10 mundos (descriptivo) | 0,43 | 0,43 |
| sesgo / cobertura IC95, 4 mundos con ambos válidos | −0,020 / 0,46 | −0,002 / 0,61 |
| tiempo mediano por ajuste | 98 s | 174 s |

**Pregunta de la Entrega A — «¿La corrección de la ventana explica una parte importante del sesgo negativo y la baja cobertura en directos?» → NO CONCLUYENTE.**
- Por la regla registrada: solo 4 mundos tienen ambos ajustes válidos, y se exigían ≥ 8.
- Descriptivamente:
  - el **sesgo negativo desaparece casi por completo** con el enmascaramiento;
  - la **cobertura global no mejora** (0,43 en ambos);
  - en el subconjunto pequeño válido mejora en +0,14, con IC95 [0,05, 0,24].
- Lectura provisional: el enmascaramiento corrige el sesgo, pero la baja cobertura tiene otra causa. Los candidatos son la forma funcional o la prior, sin verificar.

**Líneas base corregidas** (`reports/p1_corrected_baselines.md`). Mismos mundos, semillas y modelos; 0 fallos en 6 750 ajustes.
- **M2p (privilegiado):** el sesgo en directos pasa de −0,039 a −0,001 en 600 mundos F3. El MAE de contribución se reduce a la mitad (0,047 → 0,023).
- **M2 (ciego):** pasa a sobreestimar (−0,036 → +0,030) y su MAE empeora un poco (0,099 → 0,108). El defecto enmascaraba un sesgo positivo propio de su selección de formas.
- **M0/M1** no cambian en atribución. M0 empeora en predicción futura (RMSE 0,072 → 0,095), por usar 8 filas menos.
- **E08, error del efecto `do_zero`:**
  - M2p mejora mucho (|err| 0,042 → 0,018 en 45 mundos);
  - M2 cambia de signo;
  - la verdad es idéntica entre runs.
- **E09, regret:** mejoran M2 (0,035 → 0,023) y M2p (0,014 → 0,004). Las políticas de M3 no se recalculan.

**E10A (P1b)** (`reports/p1b_e10a_confounding.md`).

- **Diseño:** 3 mecanismos × 3 niveles × 40 pares, con T = 104. Son 360 mundos, 2 880 ajustes y 0 fallos; el motor `do` está validado en 360 de 360.
- **Pareamiento verificado:** entre niveles solo cambia el parámetro del mecanismo, y el DAG y las innovaciones son idénticos.
- **Métrica primaria:** sesgo `do_zero` en directos, contraste pareado entre el nivel alto y el nivel 0.

| Mecanismo (nivel alto) | M0 | M2 (ciego) | M2p (privil.) | M2p_D (privil. + D) |
|---|---|---|---|---|
| D→C = 0,5 | −0,003 [−0,004, −0,001] | −0,002 [−0,034, 0,030] | **−0,008** [−0,013, −0,005] | 0,000 [−0,002, 0,003] |
| D→Y = 0,5 | −0,003 [−0,005, −0,001] | **−0,062** [−0,093, −0,030] | −0,011 [−0,026, 0,004] | 0,000 [0,000, 0,000] |
| rho = 0,6 | −0,005 [−0,008, −0,002] | −0,016 [−0,039, 0,004] | −0,005 [−0,011, −0,000] | **−0,003** [−0,006, −0,002] |

**Lectura:**
- La confusión por D aparece cuando existen ambas aristas, y observar D la elimina en el modelo privilegiado.
- La confusión por `rho` no pasa por D, así que M2p_D no la corrige.
- M2 no tiene potencia para D→C, como se anticipó.
- La correlación observada apenas cambia entre niveles: media|corr| de 0,16 a 0,19. Correlación observada ≠ confusión causal.

## 2. Hallazgos y anomalías

1. **Defecto corregido en el código causal.** `causal.horizon` (y el oráculo M4) usaban `len(train_idx)` como fin del entrenamiento: con la ventana tardía, E08/E09 se habrían calculado sobre 8 semanas menos. Se detectó antes de ejecutar y tiene test. No afecta a resultados previos.
   - `causal.py` estaba en el manifiesto v1.1 como código vivo. Su versión v1.1 exacta, con el SHA-256 verificado, está ahora en `reports/v1_1/code_snapshot/causal.py`, igual que `bayes.py` en P0. Los ficheros listados en el manifiesto no se modifican.
2. **Riesgo de caché corregido.** La caché de mundos usa solo `world_id` como clave: una etiqueta de variante reutilizada con otros *overrides* habría cargado un mundo antiguo. Ahora se rechaza (test). Las 1 963 entradas existentes coinciden con su especificación.
3. **Reproducibilidad de MCMC.** Con la misma semilla, el mismo `uv.lock` y el mismo hardware, la re-ejecución de V3 no siempre es bit a bit idéntica a v1.1: es idéntica en 4 de 10 mundos piloto y en el resto difiere hasta un 3 % del máximo de las contribuciones. La validez estricta cambia en 3 de 10 mundos cerca de R-hat 1,01 (v1.1: 7/10 válidos; re-ejecución: 6/10). Las tasas de validez de M3 tienen, por tanto, ruido propio del orden de ±1–2 mundos de cada 10.
4. **E14.** La sonda de diseño (solo correlación lograda) muestra que el rango por defecto de `zc_coeff_range` **no** separa la correlación entre canales. Hacen falta niveles de 1,5 y 3,0 para medias|corr| de 0,41 y 0,56. Además, el generador exige D→Y para que el DAG sea conexo (D no es confusor). Registrado en el Anexo B; **no ejecutado**.

## 3. Coste

| Bloque | Ajustes | Tiempo |
|---|---|---|
| Ensayo M3 + referencias | 4 + 2 MCMC | ≈ 15 min |
| Piloto M3 (histórica + enmascarada) | 20 MCMC | ≈ 52 min de ajuste (18 + 33); RSS ≤ 1,0 GB |
| Líneas base corregidas | 6 750 rápidos | ≈ 55 min de ajuste |
| E10A | 2 880 rápidos + motor `do` en 360 mundos | ≈ 23 min de ajuste (3 procesos en paralelo, ≈ 35 min de pared) |

Coste total del P1 hasta aquí: unas 2 h de pared con procesos en paralelo. Sin generación masiva, sin oracle y sin redes neuronales.

## 4. Decisiones pendientes

1. **M3.** Por la regla de interrupción, no amplío la muestra ni inicio las variantes de la Entrega B (ROPE de referencia, contracción y familias flexibles): la V3 enmascarada converge en 7/10 y la respuesta es no concluyente. Opciones:
   - (a) aceptar el piloto actual como base y ampliar a los 35 mundos con la V3 enmascarada;
   - (b) primero, un ajuste de muestreo registrado (más *tune* o reparametrización) para subir la tasa de validez;
   - (c) relajar la validez a R-hat ≤ 1,015 solo para el análisis de sesgo y cobertura, informando de las dos reglas.
2. **ROPE.** El cálculo ya está implementado y los indicadores descriptivos del piloto están en `p1a_m3_rebaseline.md` §5. En directos válidos, «relevante» acierta en 26 de 27 canales; con 4 isolated y feeders válidos no hay base para hablar de nulos. Queda pendiente de la decisión 1.
3. **E14:** confirmar los niveles `zc ∈ {0, 1,5, 3,0}` (muy por encima del rango por defecto) o proponer otros.
4. **M2 corregido** sobreestima. ¿Se revisa su rejilla de formas (selección por validación temporal) como parte de P1 o queda como hallazgo?

No afirmo que el diseñador haya auditado los artefactos. El índice `reports/review_package_index_P1.md` enumera tablas, configuraciones e informes para una auditoría externa.
