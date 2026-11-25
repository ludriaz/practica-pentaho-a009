# Práctica Pentaho Data Integration

## Identificación y objetivo

- **Autora:** Lucia Ruiz Diaz.
- **Código personal:** A009.
- **Conjunto:** `cierre_aula_01`, versión 1.
- **Entorno utilizado:** Pentaho Data Integration Community 9.4.0.0-343 y Java 8.
- **Asignación del paquete:** [`asignacion.json`](asignacion.json).

El objetivo es generar dos resultados a partir del cierre recibido: un informe con el número de reservas cobradas y el importe cobrado por hotel y canal, y un listado separado de las reservas que no tienen un cobro asociado. El procedimiento prepara ambos CSV, comprueba sus valores y solo inicia la publicación después de superar las dos validaciones.

## Resumen para gerencia

El conjunto `cierre_aula_01` representa un único cierre de aula ya seleccionado; no es un periodo obtenido de las fechas de los cobros, porque los ficheros no contienen esa información. Los resultados entregados se generaron el **25 de noviembre de 2026 a las 18:10:48**. De las 20 reservas recibidas, 15 tienen un cobro asociado y suman **3.965,50 euros**. Las otras cinco reservas, con identificadores 4, 9, 11, 15 y 18, necesitan revisión. La ausencia de una fila en el fichero de cobros no demuestra por sí sola que el cliente no haya pagado: podría existir un pago pendiente, fuera de plazo o registrado en otra fuente. Estos datos tampoco permiten calcular la ocupación. Para responder a esa pregunta se necesitarían, como mínimo, las fechas de estancia, el número de habitaciones disponibles y ocupadas por hotel y periodo, las cancelaciones y el estado o plazo de cada pago.

## Recorrido de los datos

```text
entrada/reservas_pdi.csv ----+
entrada/cobros_pdi.csv ------+--> preparación y uniones --> temporal/*.csv
entrada/hoteles_pdi.csv -----+                              |
                                                            v
                                             validación de ambos resultados
                                                            |
                                                            v
                                             salida/*.csv o estado de error
```

`informe_cobros.ktr` relaciona reservas, cobros y hoteles y agrupa las reservas cobradas por hotel y canal. `reservas_sin_cobro.ktr` conserva las reservas cuyo identificador no aparece en el fichero de cobros y añade el hotel y un motivo. Los dos procesos escriben primero en `temporal/`. `validar_informe.ktr` y `validar_sin_cobro.ktr` comprueban los resultados provisionales. Finalmente, `cierre_hotel.kjb` publica los dos CSV en `salida/` únicamente después de las validaciones.

## Entradas y tipos

Los tres CSV proceden del paquete personal **A009**, entregado por el profesor para esta práctica. Se conservan sin cambios en `entrada/`; sus huellas SHA-256 coinciden con las registradas en `asignacion.json`.

| Archivo | Separador | Campos y tipos utilizados |
|---|---|---|
| `reservas_pdi.csv` | Coma | `id_reserva` Integer, `id_hotel` Integer, `canal` String, `noches` Integer, `importe` Number con dos decimales |
| `cobros_pdi.csv` | Punto y coma | `id_reserva` Integer, `medio` String, `cobrado` Number con dos decimales |
| `hoteles_pdi.csv` | Punto y coma | `id_hotel` Integer, `hotel` String, `comarca` String, `id_cadena` Integer |

Los importes se expresan en **euros**. El cierre no contiene fechas de reserva, pago o estancia, ni inventario de habitaciones. Por ello, los resultados solo describen la relación entre las tres fuentes recibidas y no permiten demostrar impagos, calcular ocupación o extrapolar el comportamiento a otros periodos.

## Decisiones de diseño

- El informe usa una unión interna entre reservas y cobros por `id_reserva`, porque dirección solicita únicamente reservas con un cobro asociado. Después se incorpora el nombre del hotel mediante `id_hotel`.
- Se suma el campo `cobrado`, no `importe`, porque el encargo pregunta cuánto se ha cobrado. `importe` describe el valor nominal de la reserva y puede no coincidir con el pago registrado.
- Las reservas sin cobro se detectan con una unión externa izquierda desde reservas hacia cobros. Se conserva una reserva cuando la clave de cobro resultante es nula. Así se distingue la ausencia de un registro de cobro de un posible cobro por valor cero.
- Los flujos se ordenan por las claves antes de cada `Merge Join`, como requiere este tipo de paso en PDI.
- Se usa CSV porque es el formato solicitado, se puede revisar sin Spoon y mantiene la entrega interoperable con hojas de cálculo y otros procesos. Se conserva el punto y coma en las salidas para evitar ambigüedad con configuraciones regionales que emplean coma decimal.
- Las salidas provisionales se validan antes de publicarse. La publicación no es atómica: si una copia final falla después de haberse completado la otra, el job termina con error y advierte que `salida/` podría contener una versión parcial.
- Cada ejecución sobrescribe las salidas. Repetir el job con las mismas entradas produce las mismas filas y no acumula duplicados.

## Estructura del repositorio

- `entrada/`: los tres CSV originales del paquete personal.
- `procesos/`: cuatro transformaciones `.ktr` y el job `cierre_hotel.kjb`.
- `temporal/`: resultados provisionales regenerados en cada ejecución; no se versionan.
- `salida/`: los dos informes finales comprobados.
- `evidencias/`: pruebas, registros de avance, tablas de contraste y logs de Kitchen y Pan.

## Ejecución desde una copia recién descargada

### Preparación

1. Descarga o clona el repositorio y entra en su carpeta:

   ```powershell
   git clone https://github.com/ludriaz/practica-pentaho-a009.git
   cd practica-pentaho-a009
   ```

2. Comprueba que existen `entrada/`, `procesos/`, `temporal/`, `salida/` y `evidencias/`. No cambies las rutas internas de los `.ktr` o del `.kjb`; son relativas a la ubicación del proyecto.
3. Utiliza PDI Community 9.4.0.0-343 con Java 8 y una distribución completa de `data-integration`.

### Windows PowerShell

Desde la carpeta `data-integration` de PDI:

```powershell
$env:JAVA_HOME = 'C:\ruta\a\jdk8'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
.\Kitchen.bat /file:"C:\ruta\a\practica-pentaho-a009\procesos\cierre_hotel.kjb" /level:Basic /logfile:"C:\ruta\a\practica-pentaho-a009\evidencias\cierre_kitchen.log"
```

### Linux

Desde la carpeta `data-integration` de PDI:

```bash
export JAVA_HOME=/ruta/a/jdk8
./kitchen.sh -file=/ruta/a/practica-pentaho-a009/procesos/cierre_hotel.kjb -level=Basic -logfile=/ruta/a/practica-pentaho-a009/evidencias/cierre_kitchen.log
```

Kitchen debe terminar sin errores. Los resultados aparecen en [`salida/informe_hotel_canal.csv`](salida/informe_hotel_canal.csv) y [`salida/reservas_sin_cobro.csv`](salida/reservas_sin_cobro.csv). Para probar fallos se debe trabajar sobre una copia aislada y mantener intactos los CSV originales.

## Resultados comprobados

- 20 reservas recibidas: 15 con cobro asociado y 5 sin cobro asociado.
- 13 combinaciones de hotel y canal.
- 15 reservas agrupadas y 3.965,50 euros cobrados.
- Laredo por web: 2 reservas y 496,50 euros.
- IDs sin cobro asociado: 4, 9, 11, 15 y 18; suma de identificadores: 57.
- Conciliación: 15 reservas con cobro + 5 sin cobro = 20 reservas recibidas.

## Comprobaciones y pruebas

La explicación completa de esperado, obtenido y conclusión está en [`evidencias/pruebas_y_comprobacion.md`](evidencias/pruebas_y_comprobacion.md). La comparación independiente por hotel y canal está en [`evidencias/comparacion_resultados.csv`](evidencias/comparacion_resultados.csv).

| Prueba | Evidencia | Resultado |
|---|---|---|
| Primera ejecución | [`kitchen_01_primera_ejecucion.log`](evidencias/kitchen_01_primera_ejecucion.log) | Dos salidas correctas y job finalizado con éxito |
| Repetición | [`kitchen_02_repeticion.log`](evidencias/kitchen_02_repeticion.log) | Mismos resultados, sin filas duplicadas |
| Falta de entrada | [`kitchen_03_falta_entrada.log`](evidencias/kitchen_03_falta_entrada.log) | Job fallido y sin publicación nueva |
| Informe vacío | [`kitchen_04_informe_vacio.log`](evidencias/kitchen_04_informe_vacio.log) | El validador rechaza un CSV con solo cabecera |
| Total incorrecto | [`kitchen_05_total_incorrecto.log`](evidencias/kitchen_05_total_incorrecto.log) | El validador rechaza 3.966,50 euros |
| Recuperación | [`kitchen_06_recuperacion.log`](evidencias/kitchen_06_recuperacion.log) | Se restauran las entradas y se publican resultados correctos |

Las seis pruebas se repitieron el 25 de noviembre con PDI 9.4.0.0-343 y Java 8 Temurin 1.8.0_514. Los logs 01 a 06 se regeneraron sin avisos ambientales de Log4j ni errores de permisos; cada uno identifica la prueba, el comando y el código de salida. Además, se forzó un fallo en la segunda copia dentro de una copia temporal del proyecto: Kitchen terminó con error y ejecutó la advertencia de publicación parcial ([`kitchen_08_publicacion_parcial.log`](evidencias/kitchen_08_publicacion_parcial.log)).

Los avances reconstruidos desde el historial Git están documentados en `evidencias/sesion-01.md` a `evidencias/sesion-04.md`; la revisión actual está en `evidencias/sesion-05.md`.

## Fuentes y ayudas utilizadas

- Enunciado y rúbrica: [Práctica integradora del informe del hotel con Pentaho](https://iesataulfoargentasor.github.io/bda_2026_2027/ut1/tarea-clase/).
- Material de los talleres de Pentaho Data Integration 9.4 proporcionado en el aula.
- Spoon para diseñar y revisar los procesos; Pan y Kitchen para ejecutarlos y guardar evidencias.
- Como apoyo final se consultó OpenAI Codex para comprobar la correspondencia con la rúbrica, revisar la claridad del README y contrastar la ejecución de las pruebas. La autoría, las decisiones de diseño y la defensa del proyecto corresponden a Lucia Ruiz Diaz.

La estructura de los procesos, las uniones, validaciones, resultados y pruebas se han adaptado al paquete personal A009. No se han sustituido las entradas por los CSV comunes de los talleres ni se han modificado los originales.
