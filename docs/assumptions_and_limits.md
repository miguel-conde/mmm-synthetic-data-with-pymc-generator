# Supuestos y límites

- **Generador aditivo.** Sin términos `C_i×C_j`, `C×Z` ni enlace log; verosimilitud gaussiana identidad. E13 (multiplicatividad, geo-jerarquía) queda fuera de este banco y no se simula.
- **`n_cells` no es geografía.** No se construye ningún experimento geo-jerárquico.
- **Escala de tratamiento sin dinero.** Todo efecto por unidad se llama `incremental_response_per_treatment_unit`; nunca ROAS. El presupuesto de E09 es adimensional.
- **Ventanas.** Atribución histórica en `[8, n_train)`; test = último 20 %. Las 8 primeras semanas no son reproducibles por ningún estimador con historia cero (burn-in del generador).
- **Atribución histórica en train.** Modo A se evalúa sobre las semanas de ajuste del mismo modelo (no se reajusta sobre todo `T`); la tarea `attribution_future_response` evalúa la respuesta a `C` futuro sin `Y` futuro.
- **Efectos `do` implicados por modelos** suponen exogeneidad de los canales y no propagan `C→C`; se etiquetan `model_implied_under_exogeneity_assumption`. La política de árboles es `naive_predictive_plugin_policy` (ensayo deliberado de regla no causal).
- **E09.** Política = multiplicadores por canal constantes en el tiempo, `m ∈ [0.5, 1.5]`, presupuesto total fijo en unidades de tratamiento. El valor verdadero fija **todos** los canales (plan de medios completo), cortando `C→C` hacia canales planificados. Políticas fuera de ese soporte no se exploran.
- **Oracle** = plug-in con estructura conocida; no cota universal. Coste alto en CPU (minutos por mundo); en F2 queda en cola trazada.
- **MCMC.** Presupuesto limitado por CPU (WSL2, 2 núcleos para muestreo). Ajustes no convergidos se reportan con su estado; la cobertura se muestra igualmente, señalando la fracción convergida.
- **Privilegiados.** `M2p*` usan las transformaciones verdaderas del generador (funciones privadas `_carryover_col`/`_saturate_col`); `M2p_D` además ve `D`. Ninguno compite en rankings ciegos.
- **SHAP.** Se guarda (`explanation` en los `.npz`) pero no se puntúa contra ninguna verdad causal.
- **No implementado en v1:** M7 DML, M8 Causal Forest, M9 MMM neuronal, M10 MLP; E10 (cambio de distribución), E11, E12; diseño controlado de E14 (solo estratos observacionales de correlación); variante S0 lineal de E02; variantes de omisión selectiva de controles más allá de `M2_noZ`.
- **Validez externa.** Mundos del prior de `pymc-generator`; los resultados describen ese prior, no datos reales ni River.
