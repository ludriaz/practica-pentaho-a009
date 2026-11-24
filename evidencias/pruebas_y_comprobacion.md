# Evidencias y pruebas de la práctica

## Resultado

Se ejecutó `cierre_hotel.kjb` con Kitchen 9.4 y Java 8. Los dos CSV provisionales se generaron, las dos validaciones acabaron correctamente y el job publicó las salidas en `salida/`. La ejecución repetida también terminó bien y sobrescribió los ficheros sin duplicar filas.

El contraste independiente dio 13 grupos, 15 reservas con cobro, 3.965,50 € y cinco reservas sin cobro con IDs 4, 9, 11, 15 y 18. Los resultados comparados están en `comparacion_resultados.csv`.

## Seis pruebas

| Prueba | Qué se hizo | Resultado |
|---|---|---|
| Primera ejecución | Ejecutar el job completo con las entradas originales. | OK; dos salidas publicadas. |
| Repetición | Ejecutar el mismo job otra vez. | OK; las salidas se sobrescriben. |
| Falta de entrada | Quitar `cobros_pdi.csv` en una copia aislada del proyecto. | OK; Kitchen falla y no publica salidas en esa copia. |
| Informe incompleto | Dejar solo la cabecera en el CSV y ejecutar su validador con Pan. | OK; el validador falla. |
| Total incorrecto | Aumentar en 1 € un importe del informe y ejecutar su validador con Pan. | OK; el validador falla por discrepancia. |
| Recuperación | Ejecutar de nuevo el job con las entradas originales. | OK; genera y publica los dos CSV correctos. |

Los casos que alteran o eliminan datos se hicieron sobre copias temporales. No se tocaron los CSV originales. `resultado_pruebas_kitchen.csv` resume la ejecución; `kitchen_01_...log` a `kitchen_06_...log` guardan los registros por caso.

## Archivos adicionales

- `cierre_kitchen.log`: ejecución completa de Kitchen tras corregir el enum del paso Abort.
- `verificar_practica.py` y `resultado_pruebas_independientes.csv`: comparación y escenarios lógicos independientes de Kitchen.
- `ejecutar_pruebas_kitchen.py`: guion usado para lanzar los seis casos y guardar sus logs.
