---
title: Programa de experimentación con pymc-generator para MMM
author: Protocolo técnico para ejecución mediante GitHub Copilot
date: 2026-11-05
status: Especificación v1.0
language: es-ES
---

# Programa de experimentación con `pymc-generator` para MMM

> **Encargo operativo para el agente de GitHub Copilot en VS Code / WSL2.**
>
> Implementa un banco de pruebas reproducible en el workspace que ya dispone de `pymc-generator` y funciona. No hay acceso al modelo fundacional River. El producto es **código Python ejecutable, datos sintéticos, resultados y un informe técnico**, no solo notebooks ni una propuesta teórica. Avanza de forma autónoma por las fases y registra las limitaciones. No modifiques el código fuente ni el entorno funcional del generador sin necesidad. Usa la API realmente instalada, no supongas que todas las firmas de la documentación siguen vigentes.

## 0. Resumen ejecutivo

**Pregunta principal:** ¿hasta qué punto los modelos MMM habituales y otros enfoques de ML/DL recuperan correctamente la atribución, los efectos de intervención y las decisiones de inversión cuando el proceso causal que generó las ventas es conocido, pero el analista solo ve los datos habituales?

El estudio combina dos vías previas:

1. **Vía River / generador:** estudiar mundos sintéticos de PyMC Labs y los fallos de recuperación de contribuciones, aun sin disponer de River.
2. **Vía revisión MMM / Joao Vieira:** comparar regresión, MMM bayesiano, aprendizaje automático, técnicas causales y modelos neuronales; distinguir predicción, atribución, identificación y optimización.

**Resultado buscado:** una matriz de desempeño por escenario y longitud de serie, con errores, incertidumbre, robustez y coste de cómputo, más casos concretos de éxito o fallo con su DAG y series.

**No se pretende:** reproducir los resultados numéricos del paper de River, entrenar River, inferir su arquitectura de pesos, ni demostrar que un modelo identifica una causa solo porque predice bien.

### Principios no negociables

- Un mismo conjunto de mundos se reutiliza para comparar métodos; no se cambia el generador según quién se evalúa.
- La verdad causal nunca entra en los modelos «a ciegas». Se reserva para generar, evaluar o construir referencias explícitamente privilegiadas.
- Se separan **predicción**, **descomposición observada**, **atribución estructural**, **intervención** y **decisión**.
- No se comparan magnitudes que expresan efectos distintos, aunque tengan el mismo nombre («contribución», «ROAS», «efecto»).
- Los modelos que no devuelven cierto tipo de estimación reciben `not_applicable`; no se fabrican contribuciones causales a partir de SHAP o ablation.
- No se declaran efectos causales identificados en presencia de confusión latente sin hipótesis o información adicional.
- Los resultados deben reproducirse a partir de configuraciones, semillas, versiones y registros guardados.
- Un fallo de ajuste o de convergencia se informa como tal; jamás se elimina sin dejar constancia.
- El estudio debe funcionar en WSL2 sin GPU. Las fases caras tienen límites de memoria, tiempo y paralelismo ajustables.

---

## 1. Contexto técnico y límites del generador

Repositorio: <https://github.com/pymc-labs/pymc-generator>.

El generador produce **modelos causales estructurales** (SCM) como grafos acíclicos dirigidos (DAG) con nodos de demanda latente `D`, controles observados `Z`, canales/tratamientos `C`, base `B` y ventas `Y`. Puede incluir vínculos `D→C`, `D→Z`, `D→Y`, `Z→C`, `Z→Y`, `C→C`, `C→Y` y los vínculos de base previstos en su versión. Soporta transformaciones de arrastre (*adstock*) y saturación, y ofrece la verdad generadora.

En la versión documentada el resultado se construye mediante una estructura aditiva; hay no linealidad en la respuesta de los canales y en la transformación de sus niveles. **No hay términos explícitos multiplicativos `C_i × C_j` ni `C_i × Z_j`, ni enlace logarítmico para el resultado.** El tratamiento de interacciones multiplicativas se deja para una ampliación separada; no se atribuye esa capacidad al generador actual.

Escenarios predefinidos que debe usar la primera fase:

| ID | Escenario de `pg.SCENARIOS` | Mecanismo predominante | Riesgo que se evalúa |
|---|---|---|---|
| S0 | `direct_only` | `C→Y`, sin rutas indirectas | Error básico de respuesta y asignación |
| S1 | `confounded_treatment` | `D→C` y `D→Y` | Confusión no observada / endogeneidad |
| S2 | `promo_drives_treatment` | `Z→C`, `Z→Y`; `D→Z` | Control observado, mediación y sesgo por especificación |
| S3 | `treatment_halo` | `C→C` | Efectos transmitidos entre canales y canales nulos |
| S4 | `kitchen_sink` | Mezcla escasa de rutas | Robustez ante estructura compleja |

**Precisión:** S0 no significa necesariamente «respuesta lineal sin adstock». Verificar las funciones de respuesta realmente muestreadas. Para aislar identidad/linealidad, diseñar una configuración adicional y documentar la API precisa con la que se impone.

**Precisión sobre la base:** `baseline` en la descomposición guardada incluye factores no publicitarios **y ruido de resultado**; no equivale sin más a la venta orgánica latente. Comparar una media estimada con una serie que incluye ruido da una métrica engañosa.

**Precisión sobre el «oracle»:** `world.oracle_model()` es una referencia bayesiana que conoce la estructura, los tipos de respuesta y sus priors; condiciona los canales y controles observados como entradas fijas. **No es la posterior exacta del SCM completo ni una cota universal de error.** Se debe informar como `oracle_structure_known_plugin` y mantenerlo separado de la propia verdad generadora.

**Precisión sobre persistencia:** los corpus pueden guardar números como `float32`, mientras que el mundo se genera con mayor precisión. Ajustar las tolerancias de identidad al formato, no exigir igualdad bit a bit tras guardar/cargar.

**Inspección inicial obligatoria:** documentar la versión de `pymc_generator`, `pymc`, `pymc_marketing`, `numpy`, `pytensor`, `sklearn`, el Python activo y el commit instalado si procede. Consultar la API local y las guías `README`, `docs/guide/scenarios.md`, `docs/guide/decomposition.md`, `docs/guide/corpus.md`, `docs/guide/oracle.md`, los ejemplos y el `CHANGELOG` antes de implementar adaptadores.

---

## 2. Preguntas de investigación e hipótesis contrastables

Las hipótesis deben figurar en el informe **antes de analizar resultados**. Escribir por separado el resultado empírico; no modificar una hipótesis a posteriori.

| Código | Hipótesis | Comparación o prueba principal |
|---|---|---|
| H1 | Un buen ajuste o pronóstico de `Y` no garantiza recuperar bien las contribuciones | Ranking de error predictivo frente a error de contribuciones dentro de los mismos mundos |
| H2 | Mayor duración (52 → 104 → 208 semanas) mejora la recuperación media, sin garantizar la identificación causal | Curvas de error y cobertura por horizonte, condicionadas al escenario |
| H3 | La confusión latente deteriora el rendimiento causal de modelos que no la representan | S1 frente a S0; tamaño del sesgo y cobertura |
| H4 | Incluir controles relevantes ayuda, pero ajustar mal por mediadores o confundir `Z→C` con `C→Y` puede sesgar resultados | S2 y variantes de inclusión/omisión deliberada de controles |
| H5 | La correlación entre canales reduce la estabilidad de los efectos separados, incluso sin confusión latente | Estratos de dependencia observada, idealmente intervención controlada del generador |
| H6 | Corregir la forma funcional (adstock/saturación) mejora la recuperación, pero no soluciona por sí mismo la confusión | Modelo ingenuo frente a modelo con transformaciones y misma información causal |
| H7 | Las relaciones `C→C` hacen divergentes la atribución a canales observados y el efecto de intervenir sobre el canal que inicia la cadena | S3, diferencias entre atribución y efectos de `do` |
| H8 | XGBoost/LightGBM pueden mejorar la predicción sin mejorar la validez causal ni la calidad de una política | Error predictivo, error causal y pérdida de valor de decisión |
| H9 | Los intervalos de modelos mal especificados suelen tener cobertura inferior a la nominal; los intervalos del oracle también pueden fallar | Cobertura 50/80/95 %, CRPS/WIS, diagnósticos de muestreo |
| H10 | Una decisión de presupuesto basada en el mejor predictor puede ser peor que otra basada en un modelo con menor error predictivo | Regret sobre escenarios con intervenciones verificables |
| H11 | Cambios de prior o de mecanismo degradan el rendimiento de formas distintas según el método | Evaluación con distribución desplazada respecto a la usada para elegir hiperparámetros |

No asumir que las hipótesis serán confirmadas. Informar también de los resultados contrarios y de la incertidumbre.

---

## 3. Definir primero los estimandos (el punto más importante)

Antes de programar métricas, crear `docs/estimands.md` y reflejar estas definiciones en un esquema de datos tipado.

### 3.1 Identidad del resultado

Para un mundo `w` y semana `t`, el generador ofrece una identidad del tipo:

\[
Y_t = B_t^{\mathrm{full}} + \sum_{k=1}^{K} C_{k,t}^{\mathrm{direct\ isolated}} + I_t,
\]

con `I_t` como suma de efectos indirectos de las entradas que modifican el tratamiento; `B_full` incluye el ruido de `Y`. Es una **partición exacta construida por el generador**, no una prueba de que esas partes puedan recuperarse solo con datos observados.

### 3.2 Familias de magnitudes, nombres inequívocos

1. **`historical_direct_isolated`**: contribución directa que calcula el generador con las entradas que alimentan los tratamientos separadas según su convención (`contributions` / `treatment_contribution_raw`). No es automáticamente el efecto marginal de recortar el gasto observado.
2. **`historical_indirect_total`**: término indirecto agregado `indirect_effects`. La partición `(cc, zc, dc)` depende del orden de anulación; no es una atribución causal única por fuente.
3. **`historical_observed_path_response[k,t]`**: respuesta de `C_k→Y` evaluada sobre el canal **tal como se observó** (`world.data["contributions_observed"]`, cuando esté disponible). Esta es la verdad pertinente para evaluar la respuesta por canal de un MMM que trata los canales observados como entradas. Incluye el cambio de nivel del propio canal debido a causas ascendentes; no convierte al canal receptor en el origen de toda la demanda que lo alteró.
4. **`historical_baseline_full`**: resto completo de la identidad, **con ruido**; reservar también `baseline_no_observation_noise` si es reconstruible.
5. **`interventional_total_effect`**: efecto de una intervención explícita que fija un canal y deja que el resto del sistema causal responda según el DAG. Ejemplo, para `k` y una política `a`:

   \[
   \Delta_k(a)=\sum_{t\in H}\{Y_t[do(C_k=a_t)]-Y_t[do(C_k=C_{k,t}^{obs})]\}.
   \]

   Especificar el horizonte `H`, qué ruta queda fija, qué otras rutas reaccionan y si se evalúa el resultado sin ruido o con ruido común entre los dos mundos.
6. **`marginal_effect` / `marginal_roi`**: diferencia incremental para una perturbación pequeña y explícita; no deducirla del cociente entre contribución histórica y gasto.
7. **`decision_value`**: resultado esperado bajo una política de inversión, teniendo en cuenta coste y límites presupuestarios.

### 3.3 Matriz de comparabilidad: obligatoria en el código

| Modelo o estimador | Observed-path por canal | Direct-isolated | `do` total | Pronóstico de `Y` | Intervalos |
|---|---|---|---|---|---|
| Regresión MMM con entradas observadas | Sí, bajo una descomposición definida | Solo con supuestos extra o referencia privilegiada | Solo si existe motor contrafactual válido | Sí | Según método |
| MMM bayesiano convencional | Sí | No de forma automática | Solo bajo supuestos y simulación de intervención adecuada | Sí | Sí |
| XGBoost / LightGBM | No de forma causal; solo explicación predictiva etiquetada como tal | No | No de forma automática | Sí | Solo si se construyen y validan |
| DML / Causal Forest | Estiman sus propios contrastes; no una descomposición que sume ventas | No en general | Sí **solo para estimandos identificables y con el diseño apropiado** | No es su objetivo principal | Según estimador |
| `oracle_structure_known_plugin` | Sí | No necesariamente | No necesariamente | Sí | Sí |
| SCM generador y replay validado | Verdad | Verdad | Verdad, si existe repetición contrafactual fiel | Verdad | No es un modelo estimado |

Cada salida debe incluir `estimand_id`, `units`, `truth_source`, `model_information_set`, `supports_intervention` y `validity_notes`. Está prohibido unir métricas de columnas distintas en un único ranking.

### 3.4 ROAS, unidades y signo

Los canales del generador son tratamientos numéricos no negativos; **no suponer que una unidad equivale a un euro invertido**. Por defecto calcular `incremental_response_per_treatment_unit` y no llamarlo ROAS. Solo usar ROAS monetario cuando se defina, documente y valide una correspondencia coherente entre gasto, ventas, moneda y posible precio/margen. Separar ROAS histórico descriptivo, incremental y marginal; no usar las tres expresiones como sinónimos. Cuando el efecto puede ser negativo o el denominador muy pequeño, evitar porcentajes inestables y marcar el caso.

### 3.5 Contrafactuales pareados y restricciones

Para medir el efecto real de `do` se deben comparar dos trayectorias **del mismo SCM, con los mismos parámetros y perturbaciones exógenas**, cambiando solo la intervención. Cambiar la semilla y comparar dos mundos distintos **no es** un contrafactual válido.

Plan técnico:

1. Auditar si la versión instalada expone una forma documentada de replay/contrafactual o si se puede reconstruir fielmente mediante su SCM. `SCM.replay()` puede servir para repetir la generación, pero **no implica por sí solo** que acepte `do`.
2. Ejecutar una intervención nula y comprobar que reproduce la trayectoria original dentro de tolerancias.
3. Ejecutar un caso sin `C→C`, donde el efecto sea coherente con la respuesta del canal intervenido, y otro con `C→C`, donde puedan propagarse efectos.
4. Verificar que no hay efectos temporales hacia el pasado, que se respeta el arrastre, que las perturbaciones y escalas no cambian entre brazos, y que el grafo sigue siendo el mismo.
5. Solo tras pasar estas pruebas etiquetar una medida como `true_interventional_effect`.

Si el replay causal no puede implementarse con fiabilidad, **no improvisar**: se sigue con predicción/atribución y se marca la rama de intervención/optimización como `blocked_counterfactual_not_validated`. Los choques exógenos programados que incluye el generador sirven para pruebas adicionales de variación de tratamiento, pero no sustituyen por sí solos un par contrafactual si el programa no ofrece la trayectoria alternativa con perturbaciones compartidas.

---

## 4. Diseño experimental

### 4.1 Factores del diseño principal

- **Escenarios**: S0–S4 (los cinco presets).
- **Historia semanal** `T`: **52, 104 y 208** semanas.
- **Métodos**: varias familias descritas en §5.
- **Réplicas**: diferentes semillas/mundos, manteniendo el mismo registro de datos para todos los métodos.
- **Ventana predictiva**: últimas aproximadamente 20–25 % de las semanas, siempre posterior a la ventana de ajuste. Escribir el corte exacto y el periodo de arrastre disponible por serie.
- **Subgrupos**: ruido, grado de dependencia entre tratamientos, tamaños de efecto, número de canales activos y nulos, composición del DAG y tipos de adstock/saturación realmente observados.

**No confundir estructuras con geografía:** `n_cells` genera células de estructura compartida para distintas réplicas; **no** son ciudades, regiones ni tiendas. No anunciar un experimento geo-jerárquico sin generar explícitamente jerarquía geográfica y datos correspondientes.

### 4.2 Tamaño por fase y coste

| Fase | Diseño | Mundos | Ejecución |
|---|---|---:|---|
| F0: inspección | 5 escenarios × 1 mundo × 104 semanas | 5 | Obligatoria; rápida |
| F1: piloto | 5 escenarios × 3 tamaños × 3 mundos | 45 | Obligatoria; todos los métodos de bajo coste, 1–2 pilotos bayesianos |
| F2: comparativa común | 5 × 3 × 10 mundos | 150 | Comparación pareada de modelos; los costosos solo si son viables |
| F3: extensión estadística | 5 × 3 × 40 mundos | 600 en total, **incluye** F2 si se conserva el subconjunto | Métodos rápidos; no volver a generar ni duplicar el subconjunto F2 |
| F4: estrés y extensiones | Conjuntos nuevos, declarados aparte | Según diseño | Se inicia cuando F0–F2 estén validadas |

**Nota sobre cómputo:** 150 ajustes de PyMC, más un oracle por mundo, pueden resultar caros en CPU. Usar una muestra estratificada y publicada de F2 (p. ej., 3 de los 10 mundos de cada celda = 45) como mínimo viable para los métodos costosos, con el resto en cola ejecutable y trazada. Registrar qué métodos se han evaluado en qué mundos. **Comparar modelos solo sobre la intersección de mundos procesados** y mostrar el tamaño muestral real; no mezclar 600 resultados de OLS con 45 de un MMM para construir un ranking único.

Para el informe principal del primer ciclo, dar prioridad a completar F0 + F1 + la muestra común viable de F2. F3 y F4 amplían potencia y cobertura; su ausencia no se debe encubrir.

### 4.3 Aleatoriedad y separación de conjuntos

- Semilla maestra propuesta: `20261105`; derivar semillas de manera estable a partir de `(scenario_id, T, replicate_id, purpose)` mediante un algoritmo documentado, no del `hash()` aleatorio de Python.
- **Generación**: guardar `recipe.json`, DAG, versiones, métricas de señal y receta efectiva para cada mundo o su equivalente de corpus.
- **Selección de modelos / hiperparámetros**: usar exclusivamente una partición de mundos destinada a desarrollo y, dentro de cada mundo, una partición temporal de ajuste/validación. Reservar mundos de evaluación que nunca guíen decisiones de ajuste.
- **Modelos que aprenden entre mundos** (red neuronal preentrenada, posible futuro modelo fundacional): partir por **célula de estructura DAG**, no por filas ni por réplicas de la misma estructura.
- **Modelos ajustados por mundo** (OLS, Ridge, MMM típico): usar pasado de cada mundo para ajustar; evaluar pasado y futuro por separado. La separación por DAG se usa además para que la evaluación y las decisiones de diseño no reutilicen mundos de desarrollo.
- Los mundos de distinto `T` con la misma semilla **no son automáticamente el mismo sistema causal truncado**; evitar llamarlos pares longitudinales salvo que se demuestre.
- No usar el resultado real, la descomposición verdadera, la demanda latente, los coeficientes o la receta del mundo como entradas de métodos no privilegiados.
- Guardar la selección del subconjunto costoso **antes** de ver sus métricas; estratificar por escenario y horizonte, no elegir casos «interesantes» a posteriori.

### 4.4 Dos modos de evaluación que no deben confundirse

**Modo A — Atribución histórica:** el analista conoce todas las series `C` y `Z` y las ventas usadas para ajustar, estima componentes por semana y los compara con la verdad pertinente. Se permite que el modelo use `Y` de esas semanas, igual que en un MMM real de atribución histórica.

**Modo B — Predicción futura:** se ocultan las ventas futuras. Las series futuras `C` y `Z` se entregan a los métodos **solo** en el submodo `conditional_future_inputs_known`. Si se quiere pronosticar sin conocer las futuras inversiones ni controles, debe definirse otro ejercicio que las prediga o proporcione un plan de medios. Jamás ocultar esta distinción.

Para la evaluación de componentes en la ventana futura, indicar si se ha estimado la contribución mediante la respuesta del modelo a los futuros `C/Z` sin observar `Y` futuro o si se hace atribución retrospectiva con ese `Y` ya disponible. Guardar ambos protocolos como tareas diferentes.

### 4.5 Diseño por escenario, incluidos controles de sensibilidad

**S0: respuesta directa**
- Primero versión mínima con respuesta casi lineal o lineal/identidad cuando la API permita fijarla; después respuesta no lineal y arrastre.
- Medir recuperación de respuesta por canal, ruido y calibración.
- Comparar modelos con gasto crudo frente a modelos con transformaciones de publicidad.

**S1: demanda latente y endogeneidad**
- Mantener `D` fuera de la vista del modelo ordinario.
- Calcular sesgo respecto a efectos en el camino observado y, **si es válido**, contrastes causales de intervención.
- Ejecutar control metodológico **privilegiado**, separado del ranking, con `D` observable para estimar cuánto sesgo desaparece si el analista pudiera medirla.

**S2: controles y promociones**
- Variantes: controles observados incluidos; controles omitidos; inclusión selectiva errónea; especificación con rutas observadas compatibles con el DAG.
- Analizar si un control es causa común, mediador o descendiente y qué estimando se busca antes de ajustarlo.
- No asumir que «más controles» siempre mejora la identificación.

**S3: halo canal→canal y nulos**
- Separar canal causante, canal receptor, canal con `C→Y`, canal sin efecto directo pero con ruta mediada y canal totalmente aislado.
- Calcular error por tipo y falsas atribuciones de nulos.
- Comparar la respuesta observada asignada al receptor con el efecto total de cambiar el canal origen (si hay contrafactual validado).

**S4: mezcla compleja**
- Evaluar el fallo combinado, no intentar atribuir causalmente el error a una sola fuente sin variaciones controladas adicionales.
- Conservar DAG, contribuciones y explicaciones por cada caso extremo.

---

## 5. Métodos que deben implementarse

Todas las familias tienen una **interfaz común**, pero solo ofrecen resultados para los estimandos que pueden justificar.

| ID | Método | Prioridad | Función |
|---|---|---|---|
| M0 | Regresión OLS sobre canales crudos + controles + términos básicos de tiempo | Obligatorio | Base sencilla, mostrar sesgo por especificación |
| M1 | Ridge (y, si interesa, Elastic Net) con normalización en train | Obligatorio | Aislar efecto de regularización y multicolinealidad |
| M2 | Regresión con adstock/saturación ajustados mediante selección de parámetros en validación | Obligatorio | Separar error de forma funcional de error causal |
| M2p | Regresión con **transformaciones verdaderas del generador** | Referencia privilegiada | Diagnóstico de error por forma funcional; **fuera de ranking justo** |
| M3 | MMM bayesiano convencional con PyMC-Marketing (familias disponibles) | Obligatorio | Contribuciones, incertidumbre y estimación paramétrica |
| M4 | `oracle_structure_known_plugin` del generador | Referencia | Límite diagnóstico condicionado a estructura y supuestos del plugin |
| M5 | XGBoost | Obligatorio si instalable sin alterar el generador | Predicción flexible y explicaciones **no causales** |
| M6 | LightGBM | Recomendado | Segunda familia de árboles y coste |
| M7 | Double/Debiased ML (DML), para contraste definido e identificable | Extensión prioritaria | Contraste causal con supuestos explícitos y validación temporal |
| M8 | Causal Forest (donde tenga sentido) | Extensión | Heterogeneidad de un contraste causal identificable |
| M9 | Modelo neuronal MMM estructurado y pequeño, con adstock/saturación y positividad | Extensión | Flexibilidad restringida y salida interpretable; CPU primero |
| M10 | Forest/MLP predictivo adicional | Opcional | Comprobar si las mejoras son propias de la familia o de su ajuste |

### 5.1 Reglas para igualdad de condiciones

- Todos los modelos «ciegos» reciben los mismos `Y`, `C`, `Z` y calendario autorizados por el protocolo.
- Especificar de forma explícita qué información extra utiliza cada variante. Las versiones `privileged_*` no compiten contra modelos que no ven el DAG ni los parámetros.
- Escalar variables **solo con estadísticas del tramo de ajuste** y guardar los transformadores; invertir bien las escalas al medir contribuciones en unidades de `Y`.
- No introducir tendencia, estacionalidad, rezagos, adstock o transformaciones de datos futuros que utilicen `Y` futuro.
- Tratar la respuesta causal de árboles y redes como **no demostrada** si solo se obtiene mediante SHAP, permutación o borrado de una columna. Guardar SHAP bajo `predictive_explanation`.
- Para DML y Causal Forest, documentar tratamiento, contraste, confusores válidos según DAG, condición de solapamiento/variación, diseño de corte temporal y método de ajuste. Si no hay identificación, reportar `identification_not_supported` en vez de forzar una estimación interpretable.
- Para series dependientes, usar separación temporal o bloques para validación cruzada de componentes auxiliares; no aplicar `KFold` aleatorio a semanas contiguas como si fueran IID.
- El MMM bayesiano debe tener **diagnósticos de convergencia** (R-hat, ESS, divergencias, tasa de fallos). Una estimación no convergida se presenta con su estado y no contribuye sin más a métricas fiables de cobertura.
- El oracle no tiene acceso a una posterior completa sobre todas las ecuaciones del SCM; anotar qué sabe y qué omite. Comparar su salida `contributions` contra `contributions_observed` en la **ventana reproducible** indicada por su documentación, no contra `contributions` aisladas del generador.
- Para comparar base/ruido del oracle, usar la verdad **sin ruido de observación** y su modo correspondiente (`marginal` o `sampled`); no comparar por defecto dos variables llamadas `baseline` pero distintas.
- Vigilar los **periodos iniciales de arrastre**: la generación puede usar historia anterior a las semanas guardadas mientras el estimador parte de ceros. Documentar `burn-in`, recorte de evaluación y sesgo en las primeras semanas.

### 5.2 Presupuesto de inferencia orientativo, configurable

Probar primero con un caso del piloto. Para el MMM bayesiano, configuración inicial de exploración: dos cadenas, 500 muestras de ajuste y 500 posteriores por cadena, `target_accept≈0.9`, semilla fija. **No se considera validada por el mero hecho de ejecutar.** Si R-hat, ESS y divergencias son malos, ampliar ajustes o mejorar el modelo y conservar ambos registros. Para la comparativa final, presupuestar cuatro cadenas y más muestras si el ordenador lo permite; anotar costes y cambios.

El oracle puede usar un modo con marginalización de latentes y operaciones matriciales costosas en `T=208`. Medir su consumo antes de lanzarlo en serie. Limitar el número de procesos de inferencia simultáneos para evitar que WSL agote la memoria; usar un perfil por defecto `cores=1` o `2` según recursos detectados, nunca asumir GPU.

---

## 6. Catálogo de experimentos y orden de ejecución

| Experimento | Prioridad | Diseño y ejecución | Qué se comprueba | Salida exigida |
|---|---|---|---|---|
| E00 — Sanidad del generador | **P0** | 5 presets, inspección de API, DAG, CSV, máscaras y `identity_error()` | Identidad, reproducibilidad, esquema, mecanismos realmente presentes | `generator_audit.md`, tablas y figuras |
| E01 — Recuperación fácil | **P0** | S0, 52/104/208; M0/M1/M2/M3/M4 en subconjunto | Regresión y MMM frente a verdad por canal, ruido y longitud | Errores y bandas por canal |
| E02 — Adstock y saturación | **P0** | Variar familias y fuerza dentro de rangos soportados; M0/M1/M2/M2p/M3 | Sesgo por función mal especificada y por memoria | Matriz de transformaciones y error |
| E03 — Confusión latente | **P0** | S1; M0/M1/M2/M3/M4; variante privilegiada con `D` | Sesgo causal, incertidumbre y diferencia al medir confusor | Curvas de sesgo, cobertura y ejemplos DAG |
| E04 — Control observado y mediación | **P0** | S2, controles incluidos/omitidos/correctos según estimando | Sesgo por omitir controles o ajustar mediadores | Tabla de estimandos frente a especificaciones |
| E05 — Halo y canales nulos | **P0** | S3 y S4; clasificar rutas directas/indirectas/nulas | Attribution traps, créditos falsos, origen frente a receptor | Matriz de errores por tipo de canal |
| E06 — Predicción frente a atribución | **P0** | Sobre el mismo subconjunto F2, M0/M1/M2/M3/M5/M6 | Divergencia de rankings predictivo y de contribución | Diagrama de dispersión y correlaciones por escenario |
| E07 — Incertidumbre y robustez | **P1** | M3/M4 y métodos con intervalos validados; 50/80/95 % | Cobertura, anchura, score y fallos de inferencia | Diagramas de calibración y fiabilidad |
| E08 — Intervención real | **P1, con puerta técnica** | Cambios fijados: `0`, `-10 %`, `-20 %`, `+10 %` y pulso de un canal, con replay fiel | Errores de efecto total, respuesta marginal y propagación temporal | Pares contrafactuales auditados y errores |
| E09 — Valor de las decisiones | **P1, depende de E08** | Redistribuir presupuesto fijo entre canales; evaluar en SCM | Regret y riesgo frente a políticas de referencia | Fronteras de valor, regret y restricciones |
| E10 — Cambio de distribución | **P2** | Cambiar fuerza de confusión, ruido, correlación, adstock, K; rango soportado | Generalización fuera de distribuciones usadas para diseño | Tabla de caída relativa y casos límite |
| E11 — DML y Causal Forest | **P2** | Solo estimandos y mundos con hipótesis de identificación defendibles | ¿Mejoran estimación de contrastes causales? | Tabla por estimando, `N/A` en lo no identificable |
| E12 — MMM neuronal estructurado | **P2** | Modelo pequeño CPU; restricciones y regularización | Recuperación y coste frente a M3/M5 | Curva predicción-atribución-coste |
| E13 — Modelo generador fuera de alcance | **P3** | Interacciones multiplicativas explícitas o geografía, **con generador externo/extendido** | Límites de extrapolación del banco actual | Protocolo independiente; no mezclar con los cinco presets |
| E14 — Multicolinealidad sin confusión latente | **P1** | Mundos con canales muy correlacionados, sin rutas de confusión **no observada** hacia `Y`; controles completos y DAG auditado | Efecto de la correlación sobre recuperación y estabilidad, sin atribuirlo todo a endogeneidad | Error por correlación, matrices de dependencia e intervalos |

La numeración E00–E14 es fija en código, configuraciones, tablas e informe. E14 constituye una prueba **independiente** de S1: la dependencia entre regresores puede causar estimaciones inestables incluso cuando no hay confusión latente.

### 6.1 E14: separar correlación entre canales de confusión latente

Diseñar, si lo admite la API, al menos tres grados de correlación entre canales (baja, media, alta) **sin abrir una vía de confusión no observada** para el efecto que se evalúa. Una opción es compartir un factor **observado** que mueva varios canales, con las variables necesarias para bloquear los caminos no causales disponibles en los datos; hay que verificar el DAG, no deducir identificación de la ausencia de una flecha `D→Y`. Un factor latente que cause dos canales que influyen en ventas puede producir confusión por el camino que pasa por el segundo canal, aunque no apunte directamente a `Y`.

Para cada mundo, registrar matriz de correlación, números de condición/VIF cuando sean aplicables, DAG y conjuntos de ajuste. Comparar OLS, Ridge y MMM bayesiano: estabilidad de contribución por canal, errores de signos, intervalos, correlación posterior de parámetros y suma de efectos frente al desglose por canal. Comparar después con S1, donde sí hay confusión latente. Si no puede generarse un diseño limpio con la versión actual, declarar E14 `blocked_design_not_supported` y no etiquetar un caso confuso como «solo colinealidad».

### 6.2 E08: protocolos de intervención concretos

Definir los escenarios al menos así:

- `do_zero`: fijar el tratamiento del canal elegido a cero durante una ventana válida; incluir arrastre y posibles canales descendientes.
- `do_reduce_10`: fijar a 90 % su serie original; lo mismo para 80 %.
- `do_increase_10`: fijar al 110 %; vigilar soporte y posibles extrapolaciones.
- `do_pulse`: perturbación de una semana; medir trayectoria acumulada durante semanas posteriores para captar adstock.
- `do_null`: no cambiar nada. Debe reconstruir exactamente la trayectoria original con perturbaciones compartidas, sujeto a tolerancia.

Guardar **nivel inicial, tratamiento alternativo, periodo, variable intervenida, descendientes, horizonte de evaluación, media con/sin intervención y diferencia**, además de un `intervention_validation_status`. La comparación debe utilizar las mismas innovaciones exógenas en ambos brazos. Separar perturbación de un canal exógeno de intervención que fija un canal endógeno y anula sus causas entrantes, pues cambian las preguntas causales.

### 6.3 E09: optimización de presupuesto (solo tras E08)

Fijar explícitamente unidades y horizonte. Como la escala monetaria de `C` no está garantizada, empezar con un **presupuesto adimensional en unidades de tratamiento**, y no con euros.

Políticas mínimas:

1. **Actual / constante:** mantener el plan de referencia.
2. **Reparto igual:** igualar el nivel total entre canales ajustables.
3. **Optimización según modelo:** maximizar el resultado previsto bajo el mismo total, cotas por canal y restricciones temporales. Si se optimiza XGBoost/LightGBM mediante cambios de entradas, identificar la política como `naive_predictive_plugin_policy`: es un **ensayo deliberado de una regla no causal**, no una intervención que el árbol haya identificado. Si se optimiza un MMM que presupone gasto exógeno en S1, etiquetar la política como `model_implied_under_exogeneity_assumption`.
4. **Oracle interventional policy:** política calculada con la respuesta causal verdadera, solo como techo de referencia y usando el **mismo conjunto de restricciones**.

Medidas: ventas esperadas bajo política, mejora frente a referencia, `regret = value(oracle_policy) - value(model_policy)`, variación del coste del tratamiento, volatilidad, violaciones de restricciones y sensibilidad a ruido. Si la política estimada exige actuar fuera del soporte observado, reportarlo. No optimizar usando contribución histórica dividida por nivel histórico como si fuera una derivada.

Usar un motor **validado** que propague los efectos `C→C`; si no existe, E09 queda pendiente y el resto sigue.

---

## 7. Métricas y análisis estadístico

### 7.1 Predicción (en unidades originales de `Y`)

- MAE, RMSE y, de forma opcional, error escalado por media/variabilidad de `Y`; especificar denominador.
- Comparación contra referencia ingenua (último valor / media móvil), siempre calculada sin mirar `Y` futuro.
- Error en entrenamiento y en futuro condicionado a `C/Z` futuros conocidos, por separado.
- Tiempo de ajuste, tiempo de predicción, memoria máxima y proporción de ejecuciones válidas.

### 7.2 Atribución histórica y efecto de canal

- MAE y RMSE **por canal/semana** frente a `historical_observed_path_response`; normalizar por un denominador estable (p. ej., media de `|Y|` del mundo) y reportar también cifras absolutas.
- Sesgo de contribución acumulada por canal y error en participación sobre ventas, evitando divisiones por contribuciones verdaderas cercanas a cero.
- Error en la suma de componentes y en el total atribuido.
- Error del `historical_direct_isolated` **solo** para modelos cuyo método realmente apunte a ese estimando.
- Error del total indirecto si hay un estimador válido; en otro caso `N/A`.
- Para controles nulos: tasa de falsas atribuciones usando umbrales definidos **antes** de ejecutar, en escala comparable; distinguir `C→Y` directo frente a ruta total a `Y`.
- Si se estima probabilidad de actividad, usar precisión, sensibilidad, tasa de falsos positivos, Brier y curva PR cuando la frecuencia lo permita.

**Importante:** si un modelo de árboles calcula SHAP, guardar error de SHAP como explicación predictiva, **no** como error de efecto causal salvo que se demuestre una identificación que no suele darse.

### 7.3 Intervenciones y valor

- Sesgo, MAE, RMSE y error relativo robusto de `ΔY` **solo tras validar el contrafactual**.
- Error de la ganancia acumulada por pulso / periodo de arrastre.
- Error del efecto marginal para un cambio predefinido; separar respuesta de nivel y margen.
- `regret` y valor de política frente a referencias, por escenario, intensidad de confusión y longitud de serie.

### 7.4 Incertidumbre

- Cobertura empírica de intervalos al 50, 80 y 95 % de contribuciones históricas y de contrastes de intervención, **por estimando**.
- Anchura media y score de intervalo; CRPS o WIS solo para métodos que entreguen distribuciones/intervalos adecuados.
- Calibración tanto por mundo como por canal; indicar si el intervalo incluye incertidumbre de parámetros, ruido futuro, estructura del DAG o solo una parte.
- Fracción de ajustes bayesianos con divergencias, R-hat fuera de objetivo o ESS insuficiente.

### 7.5 Resúmenes y significación

- **Unidad primaria de repetición: el mundo generado, no la semana.** Las semanas del mismo mundo están correlacionadas.
- Comparar métodos en pares sobre los **mismos mundos**; reportar mediana y media del diferencial, dispersión e intervalos del diferencial por remuestreo de mundos o de células DAG (según el diseño).
- En aprendizaje entre mundos, agrupar el remuestreo por célula DAG para evitar pseudorreplicación.
- Intervalos de confianza del 95 % para efectos agregados; distinguirlos de intervalos creíbles posteriores del MMM.
- Reportar heterogeneidad por escenario, `T`, correlación, calidad de señal y presencia de nulos.
- No seleccionar el «mejor método» a partir de una sola métrica agregada o de una sola réplica.
- **No imponer umbrales de victoria inventados.** Los umbrales en pruebas unitarias son numéricos; los resultados empíricos se contrastan con intervalos y tamaños de efecto.

### 7.6 Un ejemplo de conclusión válida y otra inválida

Válida: «En S1, con 104 semanas y estos 40 mundos, Ridge predice igual que el MMM bayesiano, pero su error en contribuciones observadas es superior; la diferencia media emparejada es X y su intervalo es Y».

Inválida: «XGBoost explica mejor las ventas y por tanto tiene el ROAS más correcto».

---

## 8. Estrés, falsación y límites de validez

Sin cambiar el contrato del programa:

1. **Muestras cortas**: T=52, varias respuestas muy parecidas, canales nulos.
2. **Multicolinealidad**: medir dependencias efectivas entre series y aumentar correlación desde parámetros soportados, separando dependencia por decisiones comunes de inversión de confusión no observada.
3. **Saturación y arrastre**: combinaciones en las que identificar parámetros resulta difícil; registrar soporte real de gasto.
4. **Cambio de prior**: otro rango de confusión, saturación, ruido, tipos de mecanismo y número de canales; señalar si el cambio sigue dentro de la familia del generador.
5. **Choques de tratamiento**: evaluar si variación más exógena ayuda a recuperar efectos y si la respuesta de memoria temporal se ajusta.
6. **Omisión de una variable observada**: ocultar un `Z` o un canal para probar el efecto del fallo de medición; diferenciar esta prueba de la confusión verdaderamente latente.
7. **Desajuste de forma funcional**: modelo de regresión lineal contra simulador no lineal; después MMM con función mal elegida.
8. **Escenarios deliberadamente imposibles de identificar**: comprobar que el banco muestra incertidumbre o sesgo, en vez de declarar «éxito» por reconstruir `Y`.
9. **Multiplicatividad / interacción explícita / geo-jerarquía**: quedan fuera del generador original tal como se documenta; diseñar otro experimento y versionarlo como `external_dgp` o `generator_extension`, sin mezclar resultados ni asumir que reproduce River.

No medir causalidad por la sola capacidad de un algoritmo de aproximar una función de predicción.

---

## 9. Arquitectura que debe construir el agente

### 9.1 Estructura propuesta del workspace

```text
README.md
pyproject.toml                   # solo si conviene; no romper instalación actual
configs/
  smoke.yaml
  pilot.yaml
  core.yaml
  extended.yaml
  stress.yaml
src/mmm_benchmark/
  __init__.py
  cli.py
  config.py
  provenance.py
  data/
    generator_adapter.py
    schema.py
    inspect.py
    splits.py
    truth_registry.py
    interventions.py
  models/
    base.py
    ols.py
    ridge.py
    engineered.py
    pymc_marketing.py
    oracle.py
    xgboost.py
    lightgbm.py
    dml.py               # extensión
    causal_forest.py     # extensión
    structured_neural.py # extensión
  evaluation/
    estimands.py
    predictions.py
    attribution.py
    causal_effects.py
    uncertainty.py
    decisions.py
    metrics.py
    aggregation.py
    diagnostics.py
  reporting/
    figures.py
    tables.py
    report.py
scripts/
  check_environment.py
  run_smoke.py
  run_pilot.py
  run_core.py
  generate_report.py
tests/
  test_generator_contract.py
  test_data_leakage.py
  test_estimands.py
  test_metrics.py
  test_interventions.py
  test_model_contract.py
  test_reproducibility.py
docs/
  estimands.md
  generator_audit.md
  methods.md
  assumptions_and_limits.md
  experiment_log.md
reports/
  figures/
  tables/
  benchmark_report.md
runs/                          # generados, no subir todo al git
```

El agente puede simplificar archivos si conserva las separaciones conceptuales. Evitar un único notebook gigante. Notebooks solo para explorar y leer resultados ya calculados, no como origen exclusivo del pipeline.

### 9.2 Contratos de datos

**`ObservedDataset`**
- `world_id`, `scenario_id`, `structure_cell_id`, `T`, `seed`, `week`.
- `y`, matriz de canales observados `C`, controles observados `Z`, máscaras de canales activos, información observable de choques y calendario.
- `train_idx`, `validation_idx`, `test_idx` con orden temporal y memoria de adstock.
- No contiene demanda latente ni verdad generadora.

**`TruthRegistry`** (acceso exclusivo del evaluador y de referencias privilegiadas)
- DAG, parámetros y receta, máscaras de rutas y nulos, `historical_direct_isolated`, `historical_observed_path_response`, `historical_indirect_total`, `historical_baseline_full`, `outcome_noise`, fuentes latentes y contrastes `do` validados.
- Guardar esquema y `truth_semantics_version`. Si el corpus por sí solo no ofrece `contributions_observed`, obtenerlo del objeto `world` o su bundle; **no inventarlo** a partir de una distribución arbitraria de `indirect_effects`.
- Gestionar acceso para impedir que el modelado lea estos datos por accidente.

**`ModelResult`**
- `model_id`, `world_id`, `fit_status`, `fit_runtime_seconds`, `peak_memory_mb`, `seed`, `environment_id`.
- Predicciones `Y` y, si las ofrece, distribuciones predictivas.
- Contribuciones con `estimand_id`, fechas, canal y unidad; intervalos, si existen.
- Contrastes de intervención solo con `intervention_validation_status` y `supports_intervention=true`.
- Diagnósticos, registros de errores y motivos de `not_applicable`.

### 9.3 Interfaz mínima sugerida

```python
class MMMEstimator(Protocol):
    def fit(self, observed: ObservedDataset, *, seed: int) -> None: ...
    def predict(self, observed: ObservedDataset, *, split: str) -> Prediction: ...
    def estimate_contributions(self, observed: ObservedDataset) -> ContributionEstimate | None: ...
    def estimate_intervention(self, request: InterventionRequest) -> EffectEstimate | None: ...
    def diagnostics(self) -> dict: ...
```

`fit()` jamás debe recibir `TruthRegistry`. El oracle implementará un **adaptador privilegiado separado** y marcado en metadatos; no reutilizar la interfaz `fit` estándar si con ello se abre una fuga de verdad.

### 9.4 CLI, ejecución y registro

Proveer comandos equivalentes a:

```bash
python -m mmm_benchmark.cli doctor
python -m mmm_benchmark.cli generate --config configs/smoke.yaml
python -m mmm_benchmark.cli run --config configs/pilot.yaml
python -m mmm_benchmark.cli run --config configs/core.yaml --resume
python -m mmm_benchmark.cli report --run-dir runs/<run_id>
pytest -q
```

Los nombres finales pueden cambiar; documentarlos. Implementar `--resume`, resultado por mundo/modelo, ejecución idempotente, registro de fallos sin perder el resto, límites de tiempo opcionales y manifest de ejecuciones. Guardar medidas en tablas Parquet o CSV con claves únicas y campos tipados; gráficos PNG/SVG y reporte Markdown. Si se recarga un corpus, revisar máscaras de padding para no evaluar canales inexistentes.

### 9.5 Metadatos y coste computacional

Guardar en `runs/<run_id>/manifest.json`: configuración expandida, semilla, versión de esquema, hash de configuración, hash del código propio, versión de generador, huella del entorno Python (y lockfile si existe), fecha, sistema, CPU/RAM detectadas, métodos solicitados y realizados. Añadir un fichero por ajuste (`status`, duración, memoria, warnings). Usar límites prudentes de concurrencia en WSL; registrar fallos por memoria.

No guardar grandes corpus, trazas MCMC o miles de PNG en Git por defecto: usar `.gitignore` y un resumen con tamaños y ubicaciones.

---

## 10. Implementación por hitos y puertas de calidad

### H0 — Auditoría de la instalación y diseño de interfaces

- Inspeccionar workspace, no reinstalar de forma automática lo que ya funciona.
- Ejecutar el ejemplo mínimo que use `pg.sample_scm`.
- Comprobar variantes y claves disponibles (`world.data`, corpus, bundles, oracle, shocks, replay).
- Crear `docs/generator_audit.md`, documentación de estimandos y contratos tipados.
- **Puerta:** un ejemplo reproducible por escenario y esquema de verdad justificado.

### H1 — Datos, verdad, pruebas de sanidad

- Implementar adaptador, generación por preset, identidades y conservación de DAG/recetas.
- Pruebas de suma de componentes, máscaras de nulos y padding, `float32/float64`, repetibilidad de semilla y cortes temporales.
- Ejecutar F0 y guardar 5 bundles completos.
- **Puerta:** `pytest` pasa y se pueden inspeccionar 5 mundos por separado sin modelos.

### H2 — Modelos sencillos y evaluación

- Implementar M0, M1, M2, M2p y métricas predictivas/de atribución.
- Ejecutar F1 con esos métodos y construir las primeras tablas E01–E06.
- Validar unidades, fechas, transformaciones y ausencia de fuga.
- **Puerta:** un mismo mundo se puntúa de modo idéntico si se vuelve a cargar; ninguna métrica mezcla estimandos.

### H3 — MMM bayesiano y oracle

- Añadir M3 y M4 tras una prueba de un mundo pequeño.
- Diagnósticos de sampler, comparación con verdad observada sobre ventana reproducible, intervalos y coste.
- Ejecutar selección predeterminada de F1; ampliar a F2 si los recursos lo permiten.
- **Puerta:** resultados de al menos un ajuste válido por escenario, o fallos documentados con explicación y trazas.

### H4 — ML predictivo y comparación justa

- Añadir M5/M6 y su selección temporal de hiperparámetros, sin fuga.
- Ejecutar E06 sobre los mismos mundos y mismas ventanas que las regresiones/BBB en el subconjunto común.
- Comparar predicción con atribución solamente para métodos cuya contribución esté bien definida; las explicaciones SHAP se analizan aparte.
- **Puerta:** tablas de tamaños de muestra, cobertura de modelos y costes, sin «leaderboard» incoherente.

### H5 — Contrafactuales y decisiones

- Investigar, implementar y validar replay causal. **No continuar a E09 si no supera la prueba de intervención nula y la prueba de transmisión de efectos.**
- Si es viable, ejecutar E08 y luego E09; si no, producir nota `blocked_counterfactual_not_validated` con las APIs probadas y lo que falta.
- **Puerta:** tests de replay y efectos, o bloqueo técnico trazable y resto del programa operativo.

### H6 — Extensiones y cierre

- F2 completo y F3 para modelos rápidos; introducir E07, E10–E12 solo tras estabilidad de las fases anteriores.
- Generar `reports/benchmark_report.md`, un resumen ejecutivo y un anexo de errores.
- Crear una tabla explícita `planned / completed / blocked / not_applicable` por experimento y método.
- **Puerta:** una tercera persona puede reproducir resultados a partir de README + configuraciones, sin intervención manual en notebooks.

---

## 11. Pruebas automatizadas mínimas

### 11.1 Generador y datos

- `identity_error()` pequeño en la precisión nativa; tolerancia justificada tras persistencia.
- Los cinco presets generan un DAG del tipo esperado o se documenta un cambio de API/versionado.
- En S0, `indirect_effects` nulo salvo que el preset haya cambiado; si cambia, fallar con mensaje de versión y revisar protocolo.
- `sum(indirect_effects_by_source) == indirect_effects` dentro de tolerancia; **nunca** inferir que el reparto sea independiente del orden.
- Los canales verdaderamente aislados tienen contribución causal nula conforme a la convención de verdad que se evalúa.
- Máscaras activas y padding se usan correctamente; ninguna métrica promedia canales inactivos de relleno.
- La carga/guardado conserva valores y estructura dentro de la precisión declarada.

### 11.2 Fugas y modelos

- Si se permutan datos de `TruthRegistry`, el resultado de un modelo a ciegas **no debe cambiar**.
- Si se cambia `Y` futuro, un ajuste entrenado solo con pasado no debe cambiar.
- Escalas y transformaciones de validación/test se ajustan solo sobre train.
- Mismo input + misma semilla + mismo entorno → resultados equivalentes según tolerancia definida.
- La interfaz rechaza los `estimand_id` no soportados o registra `N/A`.

### 11.3 Métricas

- Con predicciones perfectas, el error es cero; con contribuciones perfectas, error de contribución cero.
- Las métricas no hacen división entre cero para nulos.
- Cobertura de intervalos se calcula con la convención correcta de límites.
- Diferenciales emparejados usan las mismas claves `world_id`.
- Agregación no convierte semanas en réplicas independientes.

### 11.4 Intervenciones (si se implementan)

- Intervención nula reproduce el resultado del SCM con **idénticos factores exógenos**.
- Un canal sin ruta a `Y` tiene efecto total nulo.
- En un caso sin mediación el efecto intervenido no incluye efectos de canales descendientes inexistentes.
- En S3 los descendientes responden a cambios en canales ascendentes cuando el DAG tiene ruta activa.
- Una intervención tardía no cambia ventas anteriores a la intervención.
- Efecto del pulso incorpora arrastre temporal; comparar el mismo horizonte en ambos brazos.

---

## 12. Figuras y tablas exigidas

**Figuras mínimas:**

1. DAG y series de un mundo representativo de cada escenario, con explicación de efectos directos/indirectos.
2. Para uno o más mundos: `Y` real/prevista; contribución verdadera y estimada por canal, con intervalo cuando exista.
3. Distribución del error de contribución por escenario y `T`, con misma escala cuando proceda.
4. Diagrama `RMSE_predicción` frente a `RMSE_contribución`, identificando método, escenario y subgrupo.
5. Cobertura nominal frente a empírica y anchura de intervalos (cuando exista posterior).
6. Tasas de falsa atribución a canales nulos; separar nulo directo de nulo total.
7. Error de intervención y regret de decisiones (solo si el replay está validado).
8. Fracción de ajustes fallidos y coste de cómputo por familia.

**Tablas mínimas:** matriz escenario × horizonte × método con `N` real, error predictivo, error de contribución, cobertura, tasa de convergencia, segundos/ajuste y estimandos compatibles; comparaciones emparejadas con intervalo; registro de fallos y `N/A`; inventario de configuraciones, versiones y semillas.

**Informe final** `reports/benchmark_report.md`:

1. Resumen ejecutivo: resultados verificables y límites.
2. Diseño, hipótesis y versión del generador.
3. Datos y escenarios con gráficos de DAG.
4. Información disponible para cada método.
5. Resultados de predicción.
6. Resultados de atribución histórica.
7. Incertidumbre y diagnósticos.
8. Efectos de intervención (si están validados).
9. Calidad de decisiones (si hay contrafactuales).
10. Robustez, cambio de distribución y errores extremos.
11. Conclusiones: qué métodos funcionan mejor **para qué estimando y bajo qué supuestos**.
12. Límites: identificación, realismo sintético, prior del generador, posible ventaja del oracle, CPU, tamaño muestral y validez externa.
13. Trabajo pendiente y propuesta de comparación con River cuando exista acceso.

No presentar como «resultado de River» nada producido por este estudio.

---

## 13. Criterios de aceptación

### Mínimo obligatorio para considerar **operativo** el banco

- [ ] Se ejecuta en el WSL2 y entorno Python real sin dañar la instalación existente.
- [ ] Cinco escenarios auditados, con DAG, salida del generador y verdad guardada.
- [ ] Identidades y máscaras verificadas por tests.
- [ ] Separación estricta entre entradas observables y verdad.
- [ ] Estimandos y unidades documentados; nada se etiqueta «ROAS» sin base monetaria.
- [ ] OLS, Ridge y regresión con transformaciones funcionales implementados y probados.
- [ ] Primer piloto 5 × 3 × 3 terminado para métodos rápidos o incidencias detalladas.
- [ ] Al menos un MMM bayesiano y un oracle ajustados con diagnósticos y comparaciones correctas.
- [ ] XGBoost y, si se instala, LightGBM comparados en predicción sin atribuir causalidad a SHAP.
- [ ] Informe parcial automatizado que distinga predicción, atribución e incertidumbre.
- [ ] Manifiestos, semillas, comandos de repetición, tablas y gráficos.
- [ ] Cualquier rama contrafactual no validada bloqueada sin ocultarlo.

### Para considerar **completo el ciclo de investigación v1**

- [ ] F2 común con un subconjunto pareado y transparente de métodos costosos.
- [ ] F3 de hasta 600 mundos para métodos baratos, conservando F2 como subconjunto.
- [ ] Cobertura y scores de incertidumbre para métodos que devuelvan distribuciones.
- [ ] Comparación de rankings predictivo vs atribución con intervalos entre mundos.
- [ ] E08/E09 ejecutados **solo si** la prueba contrafactual está validada, o declarados bloqueados con evidencia.
- [ ] Informe completo con diferencias por escenario, T, actividad real del canal y fallos.
- [ ] Limitaciones y conclusiones que no confundan correlación con intervención.

---

## 14. Instrucciones finales al agente Copilot

1. **Empieza por H0 y H1.** Inspecciona la API local y usa las funciones existentes, no diseñes una capa genérica que impida ejecutar las pruebas.
2. Implementa en módulos pequeños con tests desde el principio. Ejecuta F0 y F1 antes de ampliar métodos.
3. No rompas el entorno instalado. Si falta un paquete, informa qué vas a añadir y usa un entorno aislado o gestión de dependencias que preserve las versiones del generador.
4. Prioriza calidad de estimandos y ausencia de fuga sobre cantidad de algoritmos. Una comparación incorrecta entre `contributions` y `contributions_observed` invalida el estudio.
5. Para el oracle, documenta la ventana de historia reproducible, el `burn-in`, la diferencia entre modo marginal y sampled y la definición de base sin ruido.
6. Para XGBoost/LightGBM, separa predicción y explicaciones predictivas de causalidad. Para DML/Forest, aplica solo en escenarios identificables según DAG e hipótesis.
7. No ejecutes cientos de MCMC sin medir primero un caso. Ajusta lotes a CPU/RAM y guarda resultados parciales reanudables.
8. Guarda los fallos, incluidos problemas de inferencia, y explica por qué ocurrieron.
9. Si una función de replay/`do` no está disponible o no es fiel, no simules un contrafactual con otra semilla: bloquea E08/E09, deja pruebas fallidas y sigue con el resto.
10. Tras cada hito, actualiza `docs/experiment_log.md` con archivos creados, comandos ejecutados, pruebas, resultados y pendientes. Al terminar, deja un `README.md` con un comando de reproducción de cada fase.

**Criterio final de calidad:** poder afirmar con pruebas «este modelo predice mejor, pero asigna peor las contribuciones», «este otro calibra mejor sus intervalos» o «esta política provoca una pérdida de valor» **indicando exactamente el estimando, los mundos, la ventana y los supuestos que sostienen esa frase**.

---

## 15. Referencias técnicas de partida

- PyMC Labs, `pymc-generator`: <https://github.com/pymc-labs/pymc-generator>
- README y límites de forma funcional: <https://github.com/pymc-labs/pymc-generator/blob/main/README.md>
- Escenarios: <https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/scenarios.md>
- Descomposición exacta: <https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/decomposition.md>
- Corpus y metadatos: <https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/corpus.md>
- Oracle y condiciones: <https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/oracle.md>
- Bundles: <https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/bundles.md>
- Nota de PyMC Labs sobre Marketing Foundational Models: <https://www.pymc-labs.com/marketing-foundation-models>
- Ejemplo de PyMC-Marketing sobre recuperación de parámetros con datos sintéticos: <https://www.pymc-marketing.io/en/stable/notebooks/mmm/mmm_data_generator.html>

**Regla de actualización:** la documentación en `main` puede evolucionar; la versión **instalada y registrada en el manifiesto** manda para el código ejecutable. Cualquier diferencia entre ella y este protocolo debe consignarse en `docs/generator_audit.md`.
