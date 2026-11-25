# Evidencias y pruebas de la práctica

## Alcance de la comprobación

Se ejecutó `cierre_hotel.kjb` con Kitchen 9.4.0.0-343 y Java 8. Los dos CSV provisionales se generaron, las validaciones terminaron correctamente y el job publicó las salidas en `salida/`. Después se repitió la ejecución con las mismas entradas para comprobar que los ficheros se sobrescriben y no acumulan filas.

El contraste independiente obtuvo 13 grupos, 15 reservas con cobro, 3.965,50 euros y cinco reservas sin cobro con identificadores 4, 9, 11, 15 y 18. [`comparacion_resultados.csv`](comparacion_resultados.csv) contrasta cada combinación de hotel y canal. [`resultado_pruebas_kitchen.csv`](resultado_pruebas_kitchen.csv) y [`resultado_pruebas_independientes.csv`](resultado_pruebas_independientes.csv) resumen los dos métodos de comprobación.

## Resultado de las seis pruebas

| Prueba | Esperado | Obtenido | Conclusión y evidencia |
|---|---|---|---|
| Primera ejecución | Dos salidas correctas y estado final de éxito. | Kitchen generó, validó y publicó los dos CSV. | Cumple. [`kitchen_01_primera_ejecucion.log`](kitchen_01_primera_ejecucion.log). |
| Repetición | Mismos grupos, filas y totales, sin añadir duplicados. | Se obtuvieron de nuevo 13 filas en el informe y 5 en el control, con los mismos totales. | Cumple: las salidas se sobrescriben. [`kitchen_02_repeticion.log`](kitchen_02_repeticion.log). |
| Falta de entrada | Job con error y sin publicación de resultados nuevos. | Al retirar `cobros_pdi.csv` de una copia aislada, Kitchen terminó con errores y no publicó salidas. | Cumple: un error de preparación impide llegar a la publicación. [`kitchen_03_falta_entrada.log`](kitchen_03_falta_entrada.log). |
| Informe solo con cabecera | La validación debe fallar aunque el archivo exista. | El validador detectó campos vacíos, cero grupos y totales ausentes; los pasos de aborto registraron error. | Cumple: no basta con que exista el CSV. [`kitchen_04_informe_vacio.log`](kitchen_04_informe_vacio.log). |
| Total incorrecto | La validación debe rechazar cualquier total distinto de 3.965,50 euros. | Tras aumentar 1 euro en una copia, el control obtuvo 3.966,50 euros y abortó. | Cumple: el total alterado no puede publicarse. [`kitchen_05_total_incorrecto.log`](kitchen_05_total_incorrecto.log). |
| Recuperación | Tras restaurar las entradas, el job debe volver a publicar las salidas correctas. | Kitchen generó y publicó 13 grupos, 15 reservas cobradas, 3.965,50 euros y cinco reservas sin cobro. | Cumple: el proceso se recupera al restaurar las fuentes. [`kitchen_06_recuperacion.log`](kitchen_06_recuperacion.log). |

Las pruebas que alteran o eliminan datos se ejecutaron sobre copias temporales. Los tres CSV originales conservan las huellas registradas en `asignacion.json`.

## Repetición y publicación

Las transformaciones escriben resultados provisionales nuevos en cada ejecución. El job valida ambos CSV antes de copiar ninguno a `salida/`, por lo que un fallo de preparación o validación no inicia la publicación. Las copias finales no forman una operación atómica: si la primera termina y la segunda falla, puede quedar una salida nueva junto a otra anterior. En ese caso el job debe terminar con error y registrar una advertencia de posible publicación parcial.

## Observación sobre los logs

Los seis casos se repitieron el 25 de noviembre de 2026 con PDI 9.4.0.0-343 y Java 8 Temurin 1.8.0_514. Los logs 01 a 06 sustituyen a los registros anteriores: ya no contienen los avisos ambientales de Log4j ni errores de permisos del entorno. Para facilitar su lectura, cada archivo comienza con el nombre de la prueba, el entorno, el comando reproducible y el código de salida. Los códigos 1 de las pruebas 03, 04 y 05 son intencionados y demuestran que los controles rechazan los casos incorrectos.

Como prueba adicional, en una copia temporal se cambió únicamente el destino de la segunda copia por una ruta no escribible. Kitchen devolvió código 1, ejecutó `Abortar publicación parcial` y registró el aviso exigido; la evidencia está en [`kitchen_08_publicacion_parcial.log`](kitchen_08_publicacion_parcial.log). La ruta errónea solo existió en la copia temporal.

## Archivos auxiliares

- [`cierre_kitchen.log`](cierre_kitchen.log): ejecución completa de Kitchen después de corregir la configuración del paso Abort.
- [`verificar_practica.py`](verificar_practica.py): recomputación independiente a partir de los CSV originales.
- [`ejecutar_pruebas_kitchen.py`](ejecutar_pruebas_kitchen.py): guion utilizado para lanzar los seis casos y guardar sus logs.
- [`resultado_pruebas_independientes.csv`](resultado_pruebas_independientes.csv): resultado de los escenarios lógicos independientes de Kitchen.
