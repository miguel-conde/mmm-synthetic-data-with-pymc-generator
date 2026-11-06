# Auditoría de políticas E09 (v1.2 P0)

Fuente: `runs/v1_1_e09` (45 mundos causales de F2, réplicas 0–2). **No se reajusta ningún modelo**: las políticas de los modelos son los multiplicadores guardados. Se re-evalúan con el motor `do` (`counterfactual_engine=research_validated_private_api`). Unidades: presupuesto adimensional en unidades de tratamiento, valor en unidades de `y` sobre `[8, n_train)` normalizado por Σ\|y\|. **No es ROAS.**

## 1. Familia principal: `all_channels_clamped_policy`

Todas las políticas fijan todos los canales con multiplicadores en [0,5; 1,5] y gasto total igual al observado (factibles por construcción: violación máxima registrada 9.5e-11). *Regret* = valor del óptimo verdadero − valor de la política.

| policy | label | n_worlds | regret_norm_mean | ci95 | max_budget_violation |
|---|---|---|---|---|---|
| oracle_interventional | oracle_interventional_policy | 45 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| M2p_true_transforms | model_implied_under_exogeneity_assumption | 45 | 0.0136 | [0.0087, 0.0192] | 0.0000 |
| M3_pymc_marketing | model_implied_under_exogeneity_assumption | 45 | 0.0208 | [0.0131, 0.0301] | 0.0000 |
| M1_ridge | model_implied_under_exogeneity_assumption | 45 | 0.0322 | [0.0213, 0.0446] | 0.0000 |
| M2_adstock_sat | model_implied_under_exogeneity_assumption | 45 | 0.0350 | [0.0215, 0.0499] | 0.0000 |
| M0_ols | model_implied_under_exogeneity_assumption | 45 | 0.0362 | [0.0235, 0.0503] | 0.0000 |
| M5_xgboost | naive_predictive_plugin_policy | 45 | 0.0397 | [0.0316, 0.0479] | 0.0000 |
| M6_lightgbm | naive_predictive_plugin_policy | 45 | 0.0398 | [0.0316, 0.0480] | 0.0000 |
| equal_allocation | reference_equal_allocation_bounded | 45 | 0.0410 | [0.0326, 0.0500] | 0.0000 |
| current | reference_current_plan | 45 | 0.0630 | [0.0502, 0.0771] | 0.0000 |
| random_feasible | reference_random_feasible | 45 | 0.0691 | [0.0557, 0.0836] | 0.0000 |

**Verificación del optimizador** (búsqueda multi-arranque: plan actual + 10 arranques aleatorios con semilla fija por mundo, SLSQP, tolerancia `ftol=1e-12`, restricción de presupuesto ≤ 1e-6). Mundos donde el multi-arranque encuentra un valor mejor que el óptimo guardado: **0 de 45**; mejora máxima 1.30e-09 de Σ\|y\|. Mediana de arranques que alcanzan el mejor valor (±1e-6 relativo): 11 de 11. No es una prueba de óptimo global; es el mejor valor encontrado con esa búsqueda. Detalle: `reports/v1_2/e09_clamped_optimizer_check.csv`.

## 2. Familia secundaria (exploratoria): `selected_channels_do_policy`

Solo los canales sin padres `C→C` son accionables; los descendientes reaccionan según el SCM y el presupuesto se mide sobre **todos** los tratamientos realizados (18 mundos S3/S4). Tolerancia de factibilidad fijada antes de este cálculo: \|gasto realizado / presupuesto − 1\| ≤ 1e-03. La brecha con el óptimo solo se calcula para políticas factibles; las infactibles **no se comparan** por valor.

Niveles de información:
- `model_infeasible_as_proposed`: política del modelo sin tocar (supone exogeneidad: cree que los descendientes no se mueven).
- `model_feasible_data_projection`: **aplicable sin verdad**. Regresión lineal contemporánea de cada canal no accionable sobre los accionables en la ventana de train observada, que predice cuánto se moverán los descendientes; se reescala el plan para que el gasto *predicho* iguale el presupuesto. Después se comprueba la factibilidad *real* con el motor y se conservan los fallos.
- `oracle_ex_post_budget_equalization`: reescalado con el SCM verdadero. **Solo diagnóstico, no desplegable.**
- `oracle_optimum`: óptimo del SCM en el mismo conjunto factible, horizonte y criterio, verificado con multi-arranque.

| policy | information_level | n_worlds | feasible_rate | mean_realized_dev | mean_abs_realized_dev | mean_overspend | value_vs_current_norm | value_gap_to_optimum_norm_feasible_only | n_feasible |
|---|---|---|---|---|---|---|---|---|---|
| M0_ols | model_feasible_data_projection | 18 | 0.8333 | -0.0059 | 0.0060 | 0.0001 | -0.0014 | 0.0624 | 15 |
| M1_ridge | model_feasible_data_projection | 18 | 0.8333 | -0.0059 | 0.0061 | 0.0001 | -0.0022 | 0.0633 | 15 |
| M2_adstock_sat | model_feasible_data_projection | 18 | 0.7778 | -0.0058 | 0.0062 | 0.0002 | -0.0017 | 0.0667 | 14 |
| M2p_true_transforms | model_feasible_data_projection | 18 | 0.8889 | -0.0060 | 0.0060 | 0.0000 | 0.0016 | 0.0609 | 16 |
| M3_pymc_marketing | model_feasible_data_projection | 18 | 0.8333 | -0.0111 | 0.0111 | 0.0000 | 0.0008 | 0.0644 | 15 |
| M0_ols | model_infeasible_as_proposed | 18 | 0.0556 | 0.0014 | 0.0143 | 0.0078 | 0.0154 | 0.1528 | 1 |
| M1_ridge | model_infeasible_as_proposed | 18 | 0.0556 | 0.0028 | 0.0128 | 0.0078 | 0.0183 | 0.1528 | 1 |
| M2_adstock_sat | model_infeasible_as_proposed | 18 | 0.0000 | 0.0034 | 0.0136 | 0.0085 | 0.0315 |  | 0 |
| M2p_true_transforms | model_infeasible_as_proposed | 18 | 0.0556 | 0.0017 | 0.0156 | 0.0087 | 0.0484 | 0.0001 | 1 |
| M3_pymc_marketing | model_infeasible_as_proposed | 18 | 0.0556 | 0.0018 | 0.0136 | 0.0077 | 0.0436 | 0.0206 | 1 |
| M0_ols | oracle_ex_post_budget_equalization | 18 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0152 | 0.0407 | 18 |
| M1_ridge | oracle_ex_post_budget_equalization | 18 | 1.0000 | -0.0000 | 0.0000 | 0.0000 | 0.0175 | 0.0384 | 18 |
| M2_adstock_sat | oracle_ex_post_budget_equalization | 18 | 1.0000 | -0.0000 | 0.0000 | 0.0000 | 0.0306 | 0.0253 | 18 |
| M2p_true_transforms | oracle_ex_post_budget_equalization | 18 | 1.0000 | -0.0000 | 0.0000 | 0.0000 | 0.0474 | 0.0085 | 18 |
| M3_pymc_marketing | oracle_ex_post_budget_equalization | 18 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0428 | 0.0131 | 18 |
| SCM_optimum | oracle_optimum | 18 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0559 | -0.0000 | 18 |
| current | reference | 18 | 1.0000 | -0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0559 | 18 |

Óptimo: el multi-arranque mejora el óptimo guardado en 0 de 18 mundos (máximo 6.51e-10 de Σ\|y\|). Las brechas se miden frente al mejor valor encontrado.

**Lectura.**
- Las políticas de los modelos tal como se proponen son **infactibles** en 17–18 de 18 mundos: se desvían del presupuesto realizado un 1,3–1,6 % en valor absoluto, porque los descendientes reaccionan.
- La regla aplicable sin verdad (`model_feasible_data_projection`) es factible en el 78–89 % de los mundos, pero para lograrlo **encoge** la reasignación del modelo (\|m − 1\| medio de 0,42 a 0,085) y queda por debajo del presupuesto (−0,6 %). Su valor queda **en torno al del plan actual** (−0,2 % a +0,2 % de Σ\|y\|), y su brecha con el óptimo (≈ 0,06) es igual o mayor que la del plan actual (0,056).
- **Ninguna estrategia realizable probada mejora al plan actual** en esta familia. Las mejoras de `oracle_ex_post_budget_equalization` dependen del SCM verdadero y no son desplegables.
- **Decisión:** la familia secundaria queda **exploratoria**, sin ranking. Detalle por mundo: `reports/v1_2/e09_selected_policy_audit.csv`.
