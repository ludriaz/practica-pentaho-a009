# Práctica Pentaho Data Integration

## Identificación

- Código: A009; conjunto `cierre_aula_01`, versión 1.
- Pentaho Data Integration: 9.4.0.0-343; Java 8.
- Asignación: `asignacion.json`.

## Estructura

- `entrada/`: CSV originales; no se modifican.
- `procesos/`: transformaciones `.ktr` y job `cierre_hotel.kjb`.
- `temporal/`: ficheros provisionales que se regeneran en cada ejecución; no se versionan.
- `salida/`: los dos informes finales.
- `evidencias/`: comparación de datos, casos de prueba y registros de Kitchen/Pan.

## Qué hace el proceso

`informe_cobros.ktr` relaciona reservas, cobros y hoteles y resume los cobros por hotel y canal. `reservas_sin_cobro.ktr` obtiene las reservas que no tienen un ID relacionado en el CSV de cobros y añade el hotel y un motivo. Los dos guardan primero sus resultados en `temporal/`.

`validar_informe.ktr` verifica los campos y los controles del resumen: 13 grupos, 15 reservas y 3.965,50 €. `validar_sin_cobro.ktr` comprueba que los cinco IDs son 4, 9, 11, 15 y 18, que no se repiten y que los campos obligatorios tienen valor. También detectan los CSV que solo tienen cabecera. `cierre_hotel.kjb` ejecuta los dos procesos, lanza ambas validaciones y copia los CSV a `salida/` solo si todo termina correctamente.

Las rutas de los ficheros de entrada y salida de cada transformación son relativas a su ubicación. Los CSV están separados por `;`, salvo `reservas_pdi.csv`, que usa `,`. Las salidas se sobrescriben, no se anexan a la ejecución anterior.

## Ejecutar

Con Java 8 y una distribución completa de PDI 9.4, abre `procesos/cierre_hotel.kjb` en Spoon y ejecuta el job. Desde PowerShell, situado en la carpeta `data-integration` de PDI:

```powershell
$env:JAVA_HOME = 'C:\ruta\a\jdk8'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
.\Kitchen.bat /file:'C:\ruta\al\repositorio\procesos\cierre_hotel.kjb' /level:Basic /logfile:'C:\ruta\al\repositorio\evidencias\cierre.log'
```

Al terminar, Kitchen debe indicar que el job ha finalizado sin errores. Los CSV publicados quedan en `salida/`. Para probar fallos, usa copias de la carpeta y conserva intactos los originales.

## Resultados esperados

- 20 reservas recibidas: 15 con cobro asociado y 5 sin cobro asociado.
- 13 grupos en el informe, 15 reservas agrupadas y 3.965,50 € cobrados.
- Laredo por web: 2 reservas y 496,50 €.
- IDs sin cobro asociado: 4, 9, 11, 15 y 18; suma de IDs: 57.
- Conciliación: 15 + 5 = 20.

“Sin cobro asociado” indica que el ID no aparece en el fichero recibido de cobros. Por sí solo, no demuestra que el cliente no pagara. No se incluye aquí una fuente adicional para contrastar pagos u ocupación.

## Comprobación

Las seis pruebas con Kitchen/Pan y la comparación independiente con los CSV originales están documentadas en `evidencias/pruebas_y_comprobacion.md`. Los logs de cada caso están guardados junto a ese documento.
