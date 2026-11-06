# Reporte al diseñador del programa de experimentación

**Asunto:** ejecución del ciclo v1 del *Programa de experimentación con pymc-generator para MMM* (especificación v1.0)
**Fecha:** 2026-11-05
**Entorno:** WSL2, 14 CPU lógicas, 15 GB RAM, sin GPU; `pymc-generator 0.0.2` (commit `fb9549d`), PyMC 6.3.2, pymc-marketing 1.3.0
**Artefactos:** informe [reports/benchmark_report.md](../reports/benchmark_report.md) · auditoría [generator_audit.md](generator_audit.md) · límites [assumptions_and_limits.md](assumptions_and_limits.md) · registro [experiment_log.md](experiment_log.md)

## 0. Resumen

El banco está implementado y ejecutado: 600 mundos (5 escenarios × T ∈ {52, 104, 208} × 40 réplicas) y 8 057 ajustes registrados, sin fallos. Hay 61 tests automáticos. La rama contrafactual (E08/E09) **no** quedó bloqueada: se construyó y validó un motor `do` con innovaciones exógenas compartidas (45/45 mundos validados). Varios supuestos del protocolo no se cumplen con la versión instalada del generador (§1), se tomaron decisiones propias donde la especificación era ambigua (§2) y algunas partes quedan sin ejecutar (§3). Se piden siete decisiones al diseñador (§5).

## 1. Supuestos del protocolo que no se cumplen con el generador instalado

| # | Tema | Supuesto del programa | Hallazgo | Consecuencia / acción tomada |
|---|---|---|---|---|
| 1.1 | Arrastre inicial | Precaución genérica (§5.1, «vigilar periodos iniciales») | `make_scm_prior` fija `carryover_burn_in = 8 = l_max`: se simulan 8 semanas previas que no se guardan. Con historia cero, las transformaciones **verdaderas** reproducen `contributions_observed` con error ≤ 1e-15 desde la semana 8 y hasta 1,4 unidades de `Y` antes. | Las semanas 0–7 se excluyen de toda métrica de atribución. **Propuesta:** convertirlo en regla obligatoria del protocolo. |
| 1.2 | Confusión en S1 | S1 representa «confusión no observada / endogeneidad» relevante | `confounding_strength = 0` en los cinco presets; la confusión de S1 actúa solo por aristas `D→C` y `D→Y`. | H3 sale nula (ningún IC95 de S1 − S0 excluye 0 salvo casos con N muy pequeño). **No** es evidencia de que la confusión sea inocua. Ver pregunta 5.6. |
| 1.3 | S0 «recuperación fácil» | Primero versión lineal/identidad «cuando la API lo permita» | `direct_only` muestrea por canal familias de arrastre (`none/geometric/weibull`) y de saturación (`linear/hill/logistic/michaelis_menten/tanh/root`). No hay API pública por preset para imponer linealidad. | E02 queda **parcial**; la variante lineal requiere una configuración propia de `make_scm_prior`, no construida en v1. |
| 1.4 | Contrafactuales | «Auditar si existe replay/contrafactual» (§3.5) | `SCM.replay()` existe pero **no** acepta `do`. Se implementó un motor que reconstruye el grafo con `build_world_model`, enlaza todas las primitivas (parámetros e innovaciones `eps_*`) y sustituye las columnas de tratamiento por canal en orden topológico. | Validado en 45/45 mundos: nulo exacto, sin efectos hacia el pasado, `C→C` solo a descendientes, coincidencia 1e-15 con la respuesta del canal sin mediación. **Riesgo:** depende de funciones privadas (`_carryover_col`, `_saturate_col`) y de la estructura interna del grafo, así que es frágil ante cambios de versión. |
| 1.5 | Corpus | Fuente posible de la verdad | El corpus `.npz` no incluye `contributions_observed`. | Se guarda el `SCM` completo por mundo (caché local) y se derivan observados y verdad en cada carga. |
| 1.6 | Presupuesto MCMC | 2 cadenas × (500 + 500) como exploración (§5.2) | Sonda en S0, T=104: M3 R-hat 1,025 / ESS 132; M4 R-hat 1,020 / ESS 207. Con 4 × (1000 + 1000), M3 cumple el criterio estricto solo en el **24 %** de 45 mundos y el **62 %** presenta alguna divergencia. | Los resultados de M3 se reportan con su estado de convergencia. La infra-cobertura de M3 no se explica por la convergencia (§4). |
| 1.7 | Coste del oracle | Viable en la muestra costosa de F2 | 8–15 min por mundo en CPU (mediana 575 s, máximo 914 s; 2 × (1000 + 1000)); 0 % convergencia estricta, 60 % con el criterio piloto. | M4 solo en 5 mundos (T=104, réplica 0). La cola de F2 (45 mundos) queda preparada en `configs/core_oracle.yaml`. |
| 1.8 | Versiones | Lock upstream: PyMC 6.2.0, PyTensor 3.2.4, pymc-marketing 1.1.0 | Este entorno resuelve PyMC 6.3.2, PyTensor 3.3.4, pymc-marketing 1.3.0 (cooldown de 7 días). | Reproducible **con este** `uv.lock`; no bit a bit con el lock upstream, como advierte el propio README del generador. |

## 2. Decisiones propias donde la especificación era ambigua (requieren validación)

| # | Punto | Decisión tomada | Alternativa |
|---|---|---|---|
| 2.1 | Modo A (atribución histórica) | Se evalúa en las semanas de train (≥ 8) del mismo ajuste que se usa para predecir; no se reajusta sobre las T semanas. | Reajustar sobre T completas para el modo A (duplica el coste de M3/M4). |
| 2.2 | Umbral de falsa atribución | 2 % de Σ\|y\| en la ventana, fijado en [methods.md](methods.md) antes de ejecutar. | Otro umbral o métrica continua sin umbral. |
| 2.3 | Canales *feeder* (sin `C→Y`, con ruta `C→C`) | Su verdad *observed-path* es 0, así que asignarles crédito cuenta como falsa atribución. Pero `do_zero` sobre ellos reduce las ventas un 0,9–1,0 % de Σ\|y\| (S3/S4). | Evaluarlos frente al efecto total de `do` o reportar ambos estimandos por separado (H7). |
| 2.4 | Protocolo E08 | Ventana `[8, fin de train)`; `do_zero`, ±10 %, −20 % sobre toda la ventana; pulso = +1 × nivel medio del canal en una semana a mitad de ventana; efecto acumulado hasta el fin de la ventana en ambos brazos. | Otras ventanas, magnitudes de pulso o horizontes posteriores al train. |
| 2.5 | Política E09 | Multiplicadores constantes por canal en [0,5; 1,5], presupuesto total fijo en unidades de tratamiento (no euros). El valor verdadero fija **todos** los canales («plan de medios completo»), lo que corta `C→C` hacia los canales planificados. | Fijar solo los canales «ajustables», dejar reaccionar a los descendientes, o usar políticas variables en el tiempo. |
| 2.6 | Convergencia | Estricto: R-hat ≤ 1,01, ESS bulk ≥ 400, 0 divergencias. Piloto: ESS ≥ 100. Los no convergidos se reportan pero no se excluyen de la cobertura. | Excluir los no convergidos de la cobertura, o exigir más muestras. |
| 2.7 | Semillas | SHA-256 de `(20261105, escenario, T, réplica, propósito)`. Mundos de distinto T son independientes (no pares longitudinales). | Diseñar truncamientos del mismo SCM si se quieren pares por horizonte. |
| 2.8 | Estructura del código | Paquete `mmm_benchmark/` en el raíz en lugar de `src/`, para no añadir un backend de construcción. | — |

## 3. No ejecutado y motivo

| Elemento | Estado | Motivo |
|---|---|---|
| M4 oracle en F2 (45 mundos) | En cola | Coste: 6–11 h de CPU estimadas. |
| E10 cambio de distribución (H11) | No ejecutado | Fuera del alcance de v1; es el siguiente paso más informativo (§5.6). |
| E11 DML / Causal Forest (M7, M8) | No implementado | Requiere definir contrastes identificables por DAG. |
| E12 MMM neuronal (M9), M10 | No implementado | Prioridad P2. |
| E14 multicolinealidad controlada | Parcial | Solo estratos de correlación observada. Los presets no permiten fijar la correlación entre canales sin abrir rutas de confusión. |
| E02 variante lineal de S0 | Parcial | Ver 1.3. |
| E13 | No aplicable | Fuera del generador (aditivo, sin geografía). |

## 4. Resultados principales

Unidad de repetición: el mundo. IC95 por bootstrap de mundos. Los errores de contribución se miden frente a `historical_observed_path_response` y se normalizan por media\|y\|.

1. **H1 / E06:** la correlación de Spearman entre el ranking predictivo y el de atribución de los modelos ciegos es **0,19** [0,14; 0,23] (600 mundos). El mejor predictor es el mejor atribuyendo en el 21–34 % de los mundos.
2. **H6:** la regresión con adstock/saturación elegida por validación predictiva (M2) atribuye **peor** que OLS con canales crudos: +0,031 [0,026; 0,036]. Asigna crédito al 65 % de los *feeders* (OLS: 8 %). Con las transformaciones verdaderas (M2p, privilegiado) el error baja a 0,047 de mediana (OLS: 0,075).
3. **M3 (PyMC-Marketing):** mejor modelo ciego en atribución (−0,018 [−0,023; −0,014] frente a OLS en los mismos 45 mundos), indistinguible de M2p. Su intervalo del 95 % cubre solo el **38 %** de las contribuciones verdaderas (30 % en el subconjunto convergido).
4. **H8:** XGBoost y LightGBM predicen mejor que M2 (−0,021 [−0,027; −0,015]) y de forma comparable a Ridge. Usados como regla de asignación no causal, su pérdida (4,0 %) iguala al reparto igualitario (4,1 %).
5. **H10 / E09:** el óptimo verdadero mejora el valor un 6,3 % de Σ\|y\|. La pérdida frente a él es: M2p 1,4 %, M3 2,1 %, Ridge 3,2 %, M2 3,5 %, OLS 3,6 %. La correlación entre RMSE predictivo y pérdida es **0,08** (315 pares mundo × modelo).
6. **H4:** quitar los controles `Z` empeora M2 en todos los escenarios; el efecto es máximo en S2: +0,059 [0,041; 0,079].
7. **H3:** nula, condicionada a 1.2. M2p_D (privilegiado con `D`) mejora a M2p sobre todo en S1: −0,009 [−0,013; −0,006].
8. **E08:** el error del efecto `do_zero` implicado por los modelos (bajo exogeneidad) va de 0,040 (M3) a 0,092 (M2) de Σ\|y\|.

## 5. Decisiones que se solicitan

1. **Estimando para canales *feeder*:** ¿*observed-path* (verdad = 0), efecto total de `do`, o ambos reportados por separado? (2.3)
2. **Modo A:** ¿se mantiene la evaluación sobre la ventana de train o se exige un reajuste sobre las T semanas? (2.1)
3. **Motor `do`:** ¿se acepta una implementación basada en funciones privadas del generador para publicar E08/E09, o se requiere antes una API oficial de PyMC Labs? (1.4)
4. **MCMC:** ¿qué presupuesto y criterio de convergencia son vinculantes? ¿Se excluyen los ajustes no convergidos de la cobertura? (1.6, 2.6)
5. **E09:** ¿se confirma el espacio de políticas (multiplicadores en [0,5; 1,5], plan completo) o se define otro? (2.5)
6. **Prioridad de v2:** ¿se prioriza E10 aumentando `confounding_strength_range` para que H3 sea informativa? (1.2)
7. **Cómputo:** ¿hay recursos para ejecutar el oracle en F2 (≈ 6–11 h de CPU) o se acepta como referencia en 5 mundos? (1.7)

## 6. Reproducción

```bash
uv sync --locked
uv run --locked pytest -q
scripts/run_phase.sh configs/pilot.yaml 8
scripts/run_phase.sh configs/core.yaml 10
scripts/run_phase.sh configs/extended.yaml 40
MPLBACKEND=Agg uv run --locked python -m mmm_benchmark.cli report \
  --run-dir runs/smoke runs/bayes_probe runs/pilot runs/core runs/extended --out reports
```

Cada `runs/<fase>/manifest.json` registra la configuración expandida, los hashes de configuración, código y `uv.lock`, las versiones, el commit del generador y los subconjuntos costosos pre-registrados.
