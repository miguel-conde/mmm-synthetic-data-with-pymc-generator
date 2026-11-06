# Protocolo P1B registrado (v1.2) — tras la revisión de la Entrega A

**Registrado antes de ejecutar cualquier bloque de P1B.** Autorización: `docs/RESPUESTA_AL_AGENTE_MMM_POST_P1_ENTREGA_A.md`. Estado previo congelado:
- `reports/v1_2/FREEZE_MANIFEST_P1A.json`: Entrega A, líneas base corregidas, E10A, configuraciones y snapshot de código `reports/v1_2/code_snapshot_P1A/`;
- P0, v1 y v1.1: sin cambios.

**Etiquetas de todas las tablas nuevas:**
- `legacy_w0`: ajuste desde la semana 0;
- `corrected_w8`: verosimilitud en `[8, n_train)`;
- `privileged` / `blind`;
- `converged_strict`: R-hat ≤ 1,01, ESS bulk ≥ 400 y 0 divergencias;
- `exploratory`.

## 1. P1a.0 — Control A/B/C: enmascaramiento frente a escala

| Brazo | Verosimilitud | Escala de `Y` | Etiqueta de modelo |
|---|---|---|---|
| A, histórico | `[0, n_train)` | `max Y[0:n_train)` (derivada de datos, como v1.1) | `M3_pymc_marketing@A` |
| B, control de escala | `[0, n_train)` | `FixedScaling(max Y[8:n_train))` | `M3_pymc_marketing@B` |
| C, corrección | `[8, n_train)` (máscara) | `FixedScaling(max Y[8:n_train))` | `M3_pymc_marketing@C` |

Los tres brazos usan V3 (`lam ~ Gamma(6, 2)`), el muestreo S0 (1000 + 1000, 4 cadenas, `target_accept 0.99`) y la misma semilla. La escala de canales es la misma en todos (max sobre `[0, n_train)`).

**Hallazgo previo a cualquier ajuste**, obtenido sin MCMC con los datos observados:
- En los 10 mundos del piloto de la Entrega A, `max Y[0:n_train) = max Y[8:n_train)`. Ahí B ≡ A matemáticamente y C − A ya aísla el enmascaramiento.
- La escala difiere en **6 de los 45** mundos de `v1_1_m3` (cociente 0,89–0,98):
  - `S0_direct_only_T52_r01`, `S0_direct_only_T208_r01` (desarrollo V3);
  - `S1_confounded_treatment_T208_r02`;
  - `S2_promo_drives_treatment_T104_r02` (desarrollo V3);
  - `S2_promo_drives_treatment_T208_r02`, `S3_treatment_halo_T52_r02`.
- En la muestra F2 (150 mundos) difiere en 26.

**Muestra del control:** esos 6 mundos, con A, B y C por MCMC (`configs/v1_2_p1b_abc_w0.yaml` y `configs/v1_2_p1b_abc_w8.yaml`). Es un control de identificación, no una evaluación.

**Comprobaciones deterministas (tests):**
- B y C tienen escala idéntica;
- B y A difieren solo en el valor de la escala;
- logp(C) = logp(B) − Σ_{t<8} términos;
- en los 10 mundos piloto, logp(B) = logp(A) en puntos aleatorios.

**Priors en unidades originales:** la escala multiplica las priors de `intercept`, `saturation_beta`, `gamma_control` y `y_sigma`. Se informa el cociente `s_B/s_A` por mundo como cambio de la prior en unidades de `Y`.

**Contrastes:** B − A (escala) y C − B (máscara) en el sesgo y la cobertura de directos, por mundo. Con 6 mundos son descriptivos.

## 2. P1a.1 — Muestreo (sin tocar la posterior objetivo)

**Mundos de desarrollo:** los 10 del piloto de la Entrega A (lista en `protocolo_P1_registrado.md` §3).
- Ninguno está entre los 10 usados para elegir V3.
- Todos pertenecen a los 45 de `v1_1_m3` consultados en las auditorías de P0 y en la Entrega A: **no son una muestra independiente**.

**Brazo:** C (`corrected_w8`), V3.

| Variante | Cambio | Misma posterior |
|---|---|---|
| S0, referencia | 1000 tune + 1000 draws, 4 cadenas, `target_accept 0.99`, matriz de masa diagonal | — |
| S1 | 2000 tune + 2000 draws (más adaptación y más extracciones) | sí |
| S2 | matriz de masa de rango bajo de nutpie (`low_rank_modified_mass_matrix=True`), 1000 + 1000 | sí: solo cambia la adaptación |

No se cambia ninguna prior ni ninguna parametrización.

**Diagnósticos por parámetro y mundo:**
- R-hat (rank) y ESS bulk/tail;
- divergencias;
- E-BFMI mínimo por cadena;
- fracción de iteraciones con profundidad máxima del árbol;
- profundidad media y tamaño de paso;
- correlación posterior log λ – log β;
- tiempo y RSS.

**Regla de selección (sin verdad):**
1. mayor número de ajustes `converged_strict`;
2. en caso de empate, menor tiempo mediano.

La cobertura y los errores frente al SCM **no se calculan** para las variantes hasta que se selecciona una.

**Puerta:** la variante elegida debe tener ≥ 8/10 ajustes `converged_strict` y ningún escenario con 0/2. Si no se cumple, M3 se cierra como **no concluyente en convergencia**, no se hace la evaluación confirmatoria y siguen los experimentos rápidos.

**Sensibilidad secundaria:** R-hat ≤ 1,015, etiquetada como tal. No cambia la regla principal.

## 3. P1a.1/P1a.2 — Conjunto confirmatorio (solo si pasa la puerta)

**Mundos:** F2 `core`, réplicas 3, 4 y 5 de los 5 escenarios × 3 T, es decir, 45 mundos.
- Nunca se ajustaron con M3 ni se usaron en decisiones sobre M3. Solo tienen modelos rápidos de v1 y v1.2.
- No se solapan con `v1_1_m3` (réplicas 0–2) ni con los mundos de desarrollo.
- Semillas: las de siempre (`derive_seed`), ya fijadas por `WorldSpec`.

**Brazos:** A (`legacy_w0`) y C (`corrected_w8`) con la variante de muestreo elegida, la misma para ambos.

**Inferencia:**
- Unidad: el mundo. Métricas promediadas primero sobre los canales del mundo.
- Bootstrap de mundos y, como sensibilidad, de células DAG.
- **Principal:** intersección de mundos `converged_strict` en A y en C. Conclusión confirmatoria solo con **≥ 20 pares válidos**; con menos, «no concluyente».
- Descriptivo: todos los ajustes, por separado.

**Métricas:**
- cobertura de intervalos al 50/80/95 %, anchura, sesgo y MAE de la contribución directa (`historical_observed_path`, ventana `[8, n_train)`, misma normalización media|Y| de la ventana en ambos brazos);
- desglose por `direct`/`feeder`/`isolated`, escenario y T.

**ROPE (regla revisada por el diseñador; sustituye a la de la Entrega A para P1B):**
- **Estimando:** contribución directa media semanal en `[8, n_train)`, en unidades de `Y`.
- **Umbral:** `δ = 0,005 · media|Y[8:n_train)|`, fijo por mundo e igual en ambos brazos.
- **Decisión:** «relevante» si `P(c > δ) ≥ 0,95`; «no relevante» si `P(c ≤ δ) ≥ 0,95`; en otro caso, «indeterminado».
- M3 tiene contribuciones ≥ 0 por construcción (`beta ~ HalfNormal`), así que el criterio unilateral es suficiente.
- Se informan precisión, sensibilidad, falsos positivos y abstenciones con sus denominadores por rol, primero por mundo.

## 4. E10A — cierre analítico (sin nuevos ajustes)

Sobre los 360 mundos de `runs/v1_2_p1b_e10a_*`:
1. **Tabla de parámetros fijados por mecanismo,** extraída de cada mundo: valores de `w_dc`, `delta_dy` y `confounding_strength`, número de aristas D→C, D→Y y Z→C, y célula DAG.
2. **Confusión por canal desde el DAG:** un canal está confundido por D si existe un D_j con D_j→C_k y D_j→Y (aristas activas, coeficiente ≠ 0). El contraste se separa por canal confundido o no; en `dc000` y `dy000` ningún canal lo está.
3. **Contrastes pareados** con efecto verdadero, estimación, sesgo y cambio del sesgo:
   - en unidades originales;
   - normalizados por Σ|Y| del propio mundo;
   - normalizados con un denominador fijo (Σ|Y| del mundo de nivel 0 del par).
4. **Innovaciones:** primitivas (`eps_*`) idénticas por construcción (test). Las series resultantes que cambian (`treatments`, `baseline`…) se cuantifican por nivel.
5. **Sensibilidad local:** `do_reduce_10` y `do_increase_10`, ya calculados con la misma verdad. No sustituyen a `do_zero`.
6. **Incertidumbre:** bootstrap por mundo y por célula DAG, con el número de pares por contraste. Variación de la correlación observada por mundo.

## 5. M2 — auditoría (sin modificar M2)

Sin usar la verdad para elegir:
- rejilla `ALPHA_GRID × KAPPA_GRID` y frecuencia de formas elegidas por canal;
- métrica de validación temporal elegida;
- comparación `legacy_w0` / `corrected_w8`;
- desglose por escenario, rol y T.

**Diagnóstico con la verdad (solo auditoría):** relación entre la puntuación de validación, la complejidad elegida y el error de atribución.

**M2v2:** si se propone, solo como diseño (rejilla y presupuesto fijados en desarrollo, evaluación separada). No se ejecuta en P1B sin aprobación.

## 6. E14 — puerta de calidad de diseño (solo generación, sin ajustes)

**Mundos:** 30 semillas × niveles `zc ∈ {0, 1,5, 3,0}`, T = 104, estructura del Anexo B.

**Comprobaciones por mundo:**
- en el DAG: Z→Y = 0, D→C = 0, C→C = 0, `confounding_strength` = 0, y ningún camino Z→…→Y que no pase por C;
- correlación lograda;
- media, desviación típica y cuantiles de cada canal;
- señal (cuota de medios), efecto verdadero `do_zero` por canal, ruido/SNR;
- número de condición, crudo y estandarizado.

**Puerta de márgenes:** las medianas pareadas de la desviación típica de los canales, la cuota de medios y |efecto `do_zero`|/Σ|Y| deben variar ≤ 20 % entre el nivel 0 y el 3,0.
- Si se cumple, E14 puede llamarse «correlación entre canales con márgenes aproximadamente constantes».
- Si no, se llama «correlación inducida por Z con cambios de distribución», **no se ajustan los 90 mundos** y se propone un control con márgenes fijados.

## Anexo — precisiones registradas antes de lanzar MCMC

- **S0 re-ejecutada (`S0r`)** con los mismos ajustes y la misma semilla, porque el piloto de la Entrega A no guardó E-BFMI ni la profundidad del árbol. La selección S0r/S1/S2 usa las tres re-ejecuciones con diagnósticos completos. La validez del piloto original (7/10) se informa aparte como medida del ruido del muestreador.
- **Configuraciones:** `configs/v1_2_p1b_abc_w0.yaml` (A, B), `configs/v1_2_p1b_abc_w8.yaml` (C), `configs/v1_2_p1b_samp_{S0r,S1,S2}.yaml`. Semilla de ajuste: `derive_seed(world_id, "M3_pymc_marketing", "fit")`, igual para todos los brazos y variantes.

## Anexo — selección de muestreo y lanzamiento confirmatorio (registrado antes de calcular métricas frente a la verdad)

- Resultado de la puerta (`reports/p1a_m3_sampling_diagnostics.md`): S0r 7/10, **S1 9/10**, S2 5/10 `converged_strict`. **Se elige S1** y la puerta pasa (≥ 8/10, sin escenario con 0/2).
- **Configuración congelada para la evaluación confirmatoria:** V3, 2000 tune + 2000 draws, 4 cadenas, `target_accept 0.99`, matriz de masa diagonal, la misma semilla por mundo, en los brazos A (`legacy_w0`) y C (`corrected_w8`).
- **Mundos:** `core` réplicas 3, 4 y 5 (45). Se reparten en dos ejecuciones por brazo solo para paralelizar: T ∈ {52, 104} y T = 208. El análisis las une.
- Configuraciones: `configs/v1_2_p1b_conf_{A,C}_{t52_104,t208}.yaml`.
- **Paralelización adicional (sin cambiar diseño):** un segundo proceso ajusta los mundos S4 y S3 (T52/104) del brazo C en el mismo directorio `runs/v1_2_p1b_conf_C_t52_104`, en orden inverso. Usa `configs/v1_2_p1b_conf_C_t52_104_tail.yaml`, con el mismo modelo, kwargs y semilla. El runner omite los mundos ya completados. Si un mundo se ajustara dos veces, se conserva el último resultado escrito, porque son equivalentes salvo ruido Monte Carlo.
