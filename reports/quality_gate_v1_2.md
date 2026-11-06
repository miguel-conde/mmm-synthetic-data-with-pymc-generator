# Quality gate v1.2 (P0)

## 1. Integridad de v1 y v1.1

| Versión | Artefactos con hash | Diferencias no explicadas | Código evolucionado (snapshot verificado) |
|---|---|---|---|
| v1 (`reports/v1/FREEZE_MANIFEST.json`) | 18233 | 0  | — |
| v1.1 (`reports/v1_1/FREEZE_MANIFEST.json`) | 4616 | 0  | mmm_benchmark/models/bayes.py |

Datos, runs, configuraciones e informes de v1 y v1.1 están intactos. El manifiesto v1.1 incluía el hash de tres ficheros de código vivo. `mmm_benchmark/models/bayes.py` cambió en v1.2: se añadió solo la guarda que rechaza ajustes sin historia de arrastre. La versión v1.1 exacta se reconstruyó quitando esa guarda; su SHA-256 coincide con el del manifiesto y está guardada en `reports/v1_1/code_snapshot/bayes.py`. Para re-ejecutar v1.1 bit a bit hay que usar ese snapshot (o el control de versiones). **Pasa.**

## 2. Pruebas

`pytest -q` completo (resultado guardado en `reports/v1_2/pytest_v1_2.xml` y `reports/v1_2/pytest_v1_2.txt`): **87 passed in 109.05s (0:01:49)**.

Nuevas en v1.2:
- `tests/test_serialization_and_units.py`: ida y vuelta del literal `null`; rechazo de roles desconocidos; roles DAG → tablas; recuperación de las 194 parejas canal-mundo aisladas de v1 con su rol verificado frente al DAG guardado; unidad de bootstrap = mundo; bootstrap por célula más ancho con células compartidas.
- `test_fitting_burn_in_weeks_biases_media_coefficients` y `test_pymc_marketing_refuses_fit_window_without_history` (§5).

## 3. Reconstrucción de roles de canal (C5)

`mmm_benchmark/tables_io.read_table` lee solo los campos vacíos como faltantes, mapea el legado `null → isolated` y tipa `role` como categórico `{direct, feeder, isolated}`; cualquier otra etiqueta produce un error. Las 194 parejas aisladas de v1 se recuperan para cada modelo rápido y coinciden con el DAG guardado (test). **Pasa.**

## 4. Independencia de muestras y unidades (C4)

- Unidad de repetición: mundo. Las métricas por canal-semana se resumen por canal y luego por mundo antes de construir intervalos.
- Células DAG por escenario (600 mundos): S0=1, S1=47, S2=112, S3=113, S4=120. **S0 tiene una sola célula**: sus intervalos reflejan variación de mundos **condicionada a esa estructura** (una receta), no variación entre estructuras. S1–S4 tienen casi una célula por mundo; el bootstrap por célula coincide con el bootstrap por mundo (v1.1).
- **Desarrollo frente a evaluación (M3):** los 10 mundos usados para elegir V3 están dentro de los 45 evaluados; la auditoría de cobertura separa los 35 restantes. No hay validación independiente de la elección de prior fuera de esa receta.
- M3 válido: 31/45 mundos en V3. Las cifras en ajustes válidos están **seleccionadas por convergencia**.

## 5. Error de protocolo demostrado y corregido parcialmente (P0)

Ajuste desde la semana 0 con historia de *burn-in* no reproducible: sesgo negativo sistemático en los coeficientes de medios de todos los modelos ajustados por OLS/MCMC sobre esas filas. Corregido para los modelos rápidos (`runs/v1_2_warmfit`). M3 queda pendiente de una verosimilitud enmascarada (P1a). Detalle: [scientific_status_v1_2.md](scientific_status_v1_2.md) §2. **Abierto para M3, E08 y E09.**

## 6. Motor `do`

114 mundos distintos validados en v1/v1.1 (`status`: {'validated': 114}). Sin actualizaciones del generador ni del lock desde la validación (hash de `uv.lock` incluido en el manifiesto v1.1). Etiqueta `research_validated_private_api`. **Pasa con límites** (API privada).
