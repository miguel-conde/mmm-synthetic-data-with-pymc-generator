# Respuesta del diseñador — revisión de v1.1 y encargo v1.2

**Proyecto:** benchmark de MMM con `pymc-generator`, sin acceso a River  
**Fecha:** 2026-11-05  
**Documento de partida:** `respuesta_v1_1_al_disenador.md`  
**Estado:** aprobación metodológica provisional de v1.1; nuevas verificaciones y diseño de una ampliación controlada  
**Destinatario:** agente GitHub Copilot en el workspace actual de VS Code / WSL2.

> **Instrucción general.** Conserva intactas las versiones v1 y v1.1, sus datos, configuraciones, diagnósticos y resultados. No emprendas una campaña masiva de cómputo hasta terminar las tareas P0. No uses la verdad generadora para elegir hiperparámetros, modelos, umbrales o políticas que deban ser aplicables por un analista real. Documenta las excepciones privilegiadas. Ejecuta código y pruebas, no te limites a redactar propuestas.

## 1. Dictamen sobre v1.1

El resumen acredita, **según lo declarado por el agente**, que se han aplicado las decisiones D1–D7, que el motor de intervenciones tiene más pruebas y que se han corregido errores de análisis. Acepto v1.1 como **hito de ingeniería y auditoría**, condicionado a revisar los informes y datos que todavía no se han adjuntado al diseñador. No acepto aún como resultados definitivos las afirmaciones sobre validez causal de un modelo, cobertura general de M3 ni superioridad de políticas. El documento `respuesta_v1_1_al_disenador.md` es un resumen, no una auditoría independiente del código ni de los resultados detallados.

### Conclusiones que podemos conservar, con esta redacción

1. **Predicción vs. atribución:** en los métodos y mundos evaluados, el mejor predictor coincide con el mejor atribuidor en el 26,7 % [23 %; 30 %] frente a un 25 % esperado bajo una selección aleatoria con cuatro métodos comparables. **No hay evidencia clara de que la coincidencia supere el azar en esa métrica.** Esto no demuestra que todas las métricas de predicción y atribución sean independientes: analizar también la correlación de rankings (en v1 se obtuvo 0,19) y su variación por escenario.
2. **Predicción vs. valor de política:** la correlación *dentro de mundo* entre RMSE y pérdida de decisión es 0,095 [−0,05; 0,23]. La evidencia es compatible tanto con una relación nula como con una relación positiva débil o moderada. No afirmar que la relación causal o predictiva sea exactamente cero.
3. **MCMC de M3:** la tasa de ajustes con diagnóstico estricto válido mejora del 24 % al 69 % con V3, pero la cobertura descriptiva sigue siendo baja. Esto separa un problema de cálculo de otros de especificación, identificación o estimando; aún no identifica cuál explica cada parte del error.
4. **Canales nulos:** los modelos con contribuciones estrictamente positivas pueden atribuir un valor positivo a canales sin efecto directo. **No confundir canal feeder (efecto directo nulo, efecto total potencialmente no nulo) con canal aislado (efecto total nulo)**.
5. **Política E09:** la política `all_channels_clamped_policy` sigue siendo el experimento principal. La política `selected_channels_do_policy` requiere una nueva revisión de la factibilidad presupuestaria antes de interpretar su rendimiento relativo.

## 2. Correcciones conceptuales obligatorias

### C1. Priors continuas y efectos exactamente nulos

La frase «`HalfNormal` no admite el valor cero» es **imprecisa matemáticamente**. Su soporte incluye el cero como frontera, pero una variable continua da probabilidad exactamente cero a cualquier valor puntual, y las extracciones posteriores de un coeficiente positivo son positivas casi con seguridad. Por ello un intervalo posterior igual-cola del 95 % calculado con esa parametrización no suele contener el cero aunque la verdad sea un efecto exactamente nulo. **Una prior horseshoe continua también asigna probabilidad cero al punto exacto cero:** su uso no garantiza que un intervalo igual-cola incluya cero.

Distinguir dos objetivos:

- **Identificación de ausencia exacta de efecto:** usar, si es viable y está bien implementado, un modelo con masa explícita en `beta=0` (*spike-and-slab* con selección marginalizada o alternativa compatible con el muestreador), o un procedimiento de selección explícito. No confundir esta tarea con cobertura de intervalos continuos.
- **Ausencia de efecto relevante para el negocio:** usar una región de equivalencia práctica (`ROPE`, `0 ≤ efecto < delta` o su versión bilateral si el modelo admite signos) y calcular probabilidades posteriores de estar dentro de ella; definir `delta` con unidades y regla **antes** de mirar los resultados nuevos. Prior horseshoe o priors de contracción pueden servir aquí, pero no prueban nulidad exacta.

Informar tasa de falsos positivos, sensibilidad/precisión, error de contribución e intervalo para **directos, feeders y aislados por separado**. Para feeders, una estimación directa distinta de cero puede ser un error, pero el efecto total `do` verdadero puede ser positivo.

### C2. Cobertura del 33 %: separar origen del problema

La cobertura global junta canales nulos y con efecto, mundos con diferente dificultad y ajustes que pueden converger de manera distinta. Es obligatorio presentar, al menos:

- Cobertura 50/80/95 % y anchura por **tipo de canal** (`direct`, `feeder`, `isolated`), escenario S0–S4 y tamaño T.
- Desglose de `direct` frente a nulos; no usar «cobertura 0 % en nulos» como prueba autónoma de que los intervalos de canales realmente activos están mal calibrados.
- Cobertura de la **misma magnitud** (estimando, escala, semanas, historia de adstock) en verdad y posterior; comparación con las mismas ventanas y unidades.
- Estadísticas resumidas **por mundo y canal** antes de construir intervalos entre mundos; no tratar las semanas correlacionadas de un canal como replicaciones independientes.
- Sesgo y anchura de intervalo, además de cobertura. Comprobar si el sesgo casi constante por canal se relaciona con una familia de respuesta equivocada, un control omitido, `D`, escalado, adstock o débil identificabilidad.
- Porcentaje de ajuste válido por escenario. S2 tiene solo un 22 % según el resumen: no presentar sus cifras de cobertura como representativas sin advertir la selección por convergencia.
- Comparación V0 y V3 en el mismo subconjunto de mundos **convergidos en ambas variantes** y, aparte, en todos los ajustes como análisis descriptivo. Mantener explícito el sesgo de selección.

### C3. No sobreinterpretar los resultados de rankings

Volver a mostrar denominador, número y nombres de métodos, reglas para empates y correlaciones (Spearman entre rankings, tasa de coincidencia de los mejores y relación RMSE–pérdida de política). La coincidencia del 26,7 % es compatible con el 25 % aleatorio: se debe evitar la frase «el mejor predictor suele ser el mejor atribuidor». La correlación positiva de Spearman de v1 (si sigue siendo válida) es otro resultado y no debe ignorarse.

### C4. Replicación y unidades estadísticas

Si S0 procede de una única célula DAG, sus intervalos reflejan variación de mundos **condicionada a esa estructura** y no variación entre estructuras de S0. Declarar de forma visible qué estimación generaliza a una receta, a estructuras DAG o a todos los mundos posibles. Si hay dependencia entre réplicas, remuestrear a nivel que corresponda al proceso generador. Mantener `n_worlds`, `n_DAG_cells`, `n_channels`, `n_valid_fits` en todas las tablas centrales.

### C5. Calidad de datos: el marcador literal `null`

La corrección de `pd.read_csv` demuestra un fallo real de clasificación. Además de reparar el informe, incorporar una prueba automática de ida y vuelta entre el DAG y las tablas guardadas. Usar tipos categóricos explícitos y evitar la conversión silenciosa del literal `"null"` a NaN. Verificar que las 194 parejas canal–mundo aisladas se clasifican igual al leer archivos nuevos y al recuperar v1.

## 3. Revisión específica de políticas E09

**Decisión:** mantener `all_channels_clamped_policy` como comparativa principal con la restricción común ya establecida. **No aceptar todavía `selected_channels_do_policy` como una clasificación de decisiones operativas realizables.**

Según el informe, un ajuste posterior del presupuesto con el simulador verdadero corrige las políticas que se habían pasado de gasto. Esa normalización es útil como **sensibilidad ex post con información privilegiada**, pero un modelo real no conoce la respuesta causal exacta de sus canales descendientes y no puede efectuarla así. No incluir estas políticas corregidas con el verdadero SCM en una clasificación de estrategias que pueden aplicarse.

Para esta política secundaria, informar por separado:

1. **Política calculada por el modelo**, sin tocarla: valores propuestos, respuesta y gasto **realizados** bajo `do`, tasa de incumplimiento, sobrecoste y valor logrado.
2. **Política que pueda aplicarse sin verdad generadora**, con una regla de proyección o de margen de seguridad basada solo en datos disponibles al analista. Especificar la regla, comprobar factibilidad real y conservar los fallos.
3. **Política corregida con el SCM verdadero**, marcada `oracle_ex_post_budget_equalization`: solo diagnóstico, no solución desplegable.
4. **Óptimo del SCM**, calculado sobre **el mismo conjunto factible, horizonte y criterio de costes**. Verificar si el optimizador ha encontrado un óptimo global o solo el mejor valor encontrado; guardar semillas, reinicios, cota o tolerancia. No llamar `regret` a una comparación con políticas infactibles sin una penalización o regla común predefinida.

No llamar ROAS monetario a resultados en unidades sintéticas de tratamiento. Si el procedimiento de la política realizable resulta demasiado costoso, mantener la política secundaria como exploratoria, sin forzarla.

## 4. Plan de trabajo autorizado

### P0 — Cierre científico y de calidad de v1.1 (obligatorio, antes de v2)

1. **Paquete de revisión completo y pequeño:** entregar `reports/quality_gate_v1_1.md`, `reports/benchmark_report_v1_1.md`, `reports/mcmc_diagnostics.md`, `docs/estimands.md`, `docs/methods.md`, `docs/revision_v1_1.md`, más las tablas agregadas de los 45 mundos M3 y el detalle por mundo/canal o una muestra rastreable. Si los archivos ya existen, preparar un índice con enlaces y no volver a calcular.
2. **Rehacer las tablas de M3** según C1 y C2: directos/nulos, escenarios, T, validez inferencial, error puntual, sesgo, anchura y cobertura. Aprovechar resultados existentes; no lanzar MCMC por defecto.
3. **Revisar E09** con los tres niveles de información (`model_feasible`, `model_infeasible`, `oracle_ex_post`) y optimizador comparativo justo.
4. **Refuerzo de pruebas de serialización y estadísticas** según C4/C5. Probar los tests y guardar su resultado.
5. **Revisar los resultados principales** con redacción prudente según §1. Volver a etiquetar cualquier conclusión que dependa de un ajuste no válido, de una comparación no pareada o de un estimando diferente.
6. **Registrar la separación entre desarrollo y evaluación.** Identificar cuáles de los 10 mundos usados para elegir V3 reaparecen en la evaluación de 45 mundos. Dar métricas en la muestra no usada para escoger la prior; no proclamar validación independiente si no existe.

**Criterio de salida P0:** informe único con tabla de hipótesis H1–H11, estatus (`supported`, `not_supported`, `inconclusive`, `not_run`), estimando, métodos, subconjunto de mundos, intervalo, y principales límites. No recalcular ajustes caros salvo error concreto demostrado.

### P1 — v1.2: tres experimentos controlados, en este orden

**P1a. M3: ensayo de especificación separado en dos ejes (P1 principal).** En los mismos mundos de M3 previamente fijados, comparar:

- V3 como referencia congelada.
- Una variante que **no imponga efectos directos estrictamente positivos en todos los canales**, usando un mecanismo de masa en cero, o si no es viable, contracción continua con decisión ROPE claramente etiquetada. Informar lo que cada alternativa puede y no puede demostrar.
- Una variante que cambie **solo las familias de respuesta** (arrastre/saturación) para acercarlas a la variedad del generador.
- Solo si el coste lo permite, una variante que combine ambas mejoras. Así se estima qué corrige cada cambio y se evita atribuir todo el avance a una modificación conjunta.

Seleccionar hiperparámetros con mundos de desarrollo, sin la verdad. Congelar criterios antes de correr la muestra evaluadora. Comenzar con 5–10 mundos estratificados, avanzar a 45 solo si el muestreo converge, con una tasa y coste aceptables. Si una variante exige una arquitectura propia, documentar que ya no es el MMM estándar de PyMC-Marketing.

**P1b. E10A: confusión, dos mecanismos separados.** Extender el piloto con mundos pareados, variando por separado: intensidad de `D→C` / `D→Y` y correlación de perturbaciones `rho`. No confundir «mismo DAG» con «mismo tratamiento causal». Mantener los demás parámetros e innovaciones cuando sea posible y demostrarlo. Usar `D` observable solo como control privilegiado, nunca entre modelos ciegos. Para reducir coste empezar con T=104 y una ampliación pareada con potencia calculada según el piloto, y solo después añadir T=52 y 208. Distinguir el sesgo en efecto directo observado del sesgo de intervención, y declarar si la falta de identificación sigue impidiendo recuperar el efecto incluso con un mejor predictor.

**P1c. E14: multicolinealidad sin confusión causal.** Crear control con canales correlacionados a través de una causa **observada** `Z`, sin efecto `Z→Y` y sin rutas ocultas `D→C`, `D→Y` ni interacciones `C→C` que alteren la interpretación. Verificar DAG y ausencia de sendas alternativas en cada mundo, medir correlación lograda, rango/condición de matriz y recuperación de coeficientes y atribución. Mantener fijo, en lo posible, el grado de señal y el número de canales. Después, comparar el daño de la correlación pura con el de la confusión estructural de E10A. Los controles `Z` compartidos pueden generar dependencia entre canales **sin ser por ello un confusor del efecto sobre Y**.

### P2 — v2 después de P0/P1, sin ejecución automática masiva

- **E10B — cambio de distribución:** preregistrar qué cambia (familias, fuerzas, número de canales, DAG, ruido). Separar claramente dos experimentos distintos: generalización **entre mundos** (entrenamiento/selección en unas recetas, evaluación en otras) y cambio **dentro de un mismo mundo a lo largo del tiempo**. No llamarlos una sola cosa. Para modelos entrenados en varios mundos, separar por célula DAG.
- **E11 — DML/Causal Forest:** primero demostrar supuestos de identificación y **solapamiento del tratamiento**. Una intervención `do_zero` sobre un canal siempre positivo puede estar fuera del soporte observado y no quedar identificada de forma fiable por un estimador flexible. Preferir inicialmente perturbaciones locales dentro del soporte, con controles temporales, arrastre y contraste verdadero del SCM. No presentar un Causal Forest estándar como estimador automático de respuestas dinámicas con adstock.
- **M4 oracle:** queda suspendido mientras no haya convergencia fiable. No dedicar más CPU sin propuesta de parametrización fundada.
- **E12 neuronal:** no es la prioridad inmediata, pero **no eliminarlo del plan maestro**. Tras P1 decidir un contraste justo de predicción frente a efecto/decisión y la necesidad de preentrenamiento entre mundos.
- **Motor `do`:** mantener API privada fijada por commit y pruebas. Una API oficial sería deseable, pero no es condición para continuar la investigación interna si las pruebas siguen pasando. No actualizar el generador en mitad de la fase.

## 5. Criterios experimentales de aceptación

Para cada experimento nuevo, dejar por escrito antes de ejecutarlo: hipótesis, estimando, verdad del SCM, cambios de configuración, hipótesis de identificación, grupos pareados, número de mundos y células DAG, tamaño temporal, modelos y acceso a información, partición de desarrollo/evaluación, métrica primaria, criterios de validez de ajuste, resumen de coste y regla de interrupción.

- **Validez causal:** no llamar causal a un SHAP, una ablación predictiva ni un efecto `do` predicho por un modelo con endogeneidad sin advertir el supuesto no comprobado.
- **Validez de MCMC:** `R-hat ≤ 1,01`, `ESS bulk ≥ 400` y 0 divergencias en todos los parámetros clave como criterio estricto, además de diagnósticos por escenario. Si la estrategia es muy cara, reducir la muestra **antes** de relajar los diagnósticos.
- **Equidad entre modelos:** los rankings se calculan sobre la misma intersección de mundos y ventanas, con separación visible de cualquier método privilegiado.
- **Estadística:** intervalos que respeten la unidad de repetición; no considerar canal-semana como réplica independiente; declarar selección de mundos y estructura DAG.
- **Reproducibilidad:** versionar experimentos en `configs/v1_2_*`, `runs/v1_2_*`, `reports/v1_2/`, hash de código/entorno y registro previo. Ningún informe previo se reescribe.

## 6. Entregables y formato de respuesta

**Primera entrega (P0; prioritaria y sin grandes ajustes):**

1. `reports/quality_gate_v1_2.md`: verificación del estado v1.1, pruebas, reconstrucción de roles de canales, independencia de muestras y motor `do`.
2. `reports/m3_coverage_audit.md`: tablas de cobertura/anchura/sesgo de M3 por rol, escenario, T y validez, con comparaciones pareadas V0/V3 y advertencias.
3. `reports/e09_policy_audit.md`: comparación clara de plan completo, plan parcial observado, factibilidad, corrección privilegiada y optimizador verdadero.
4. `reports/scientific_status_v1_2.md`: tabla H1–H11 y una síntesis de lo que realmente está apoyado por los datos.
5. `reports/review_package_index.md`: índice navegable de informes, configuración, muestras y gráficos necesarios para revisión externa.

**Segunda entrega (P1; solo tras pasar P0):** `reports/m3_specification_study.md`, `reports/e10a_confounding_study.md` y `reports/e14_collinearity_study.md`, más configs, tests y datos rastreables.

**Respuesta breve al diseñador tras P0:** explicar (i) si la cobertura del 33 % se concentra en nulos o también afecta a canales directos, (ii) qué sesgos concretos siguen en los directos, (iii) qué parte de E09 es realmente realizable sin verdad, (iv) si el hallazgo de predicción vs atribución cambia tras corregir el azar y la agrupación, (v) cuáles son las 3 decisiones que debe adoptar el diseñador para arrancar P1.

**No ejecutar por iniciativa propia** una nueva muestra de 600 mundos bayesianos, los 45 oracle ni toda v2. Cuando P0 termine y el protocolo P1 esté fijado, ejecutar solo pilotos controlados de coste moderado, guardando las decisiones que falten.

## 7. Referencias de contraste

- `pymc-generator`: <https://github.com/pymc-labs/pymc-generator>
- Descomposición del generador: <https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/decomposition.md>
- Alcance del oracle: <https://github.com/pymc-labs/pymc-generator/blob/main/docs/guide/oracle.md>
- PyMC-Marketing, ejemplo de prior `HalfNormal`: <https://www.pymc-marketing.io/en/stable/notebooks/mmm/mmm_example.html>

Las referencias públicas pueden corresponder a revisiones posteriores al commit local `fb9549d`. Para implementar, **manda la API instalada** y se conserva la versión fijada hasta terminar la fase.
