# Configuración de tesis

Las palabras clave se definen por tesis en `definitions/input.json`. La clave
`titulo_tesis` indica la selección predeterminada y cada entrada de `tesis`
contiene una descripción informativa y su lista de keywords.

```json
{
  "titulo_tesis": "1",
  "tesis": {
    "1": {
      "descripcion": "Título de tesis 1",
      "keywords": ["keyword 1", "keyword 2", "keyword 3"]
    },
    "2": {
      "descripcion": "Título de tesis 2",
      "keywords": ["keyword A", "keyword B", "keyword C"]
    }
  }
}
```

Ejecuta la tesis predeterminada:

```powershell
python main.py --sencilla
```

Sobrescribe la selección al ejecutar:

```powershell
python main.py --sencilla --titulo-tesis 2
```

Los campos de nivel superior como `year_from`, `year_to`, `scopus`, `ieee`,
`wos` y `rate_limits` son transversales: no se duplican dentro de cada tesis y
se aplican a la tesis seleccionada.

## Optimización de combinaciones

Antes de consultar ternas, el programa obtiene el conteo individual de cada
keyword. Una terna se consulta únicamente si sus tres keywords tienen al menos
un resultado individual. Se omite toda terna que incluya una keyword con cero
resultados.

Por ejemplo, si `A` y `B` tienen resultados y `C` tiene 0, se omite
`A AND B AND C`, porque una consulta con `AND` no puede devolver documentos.
El log muestra el número de combinaciones posibles, omitidas y consultadas.

Las ternas no se repiten por orden: `A AND B AND C` se consulta una sola vez,
y no se vuelven a consultar las permutaciones `B AND C AND A`, `C AND A AND B`
ni ninguna otra. Si una keyword se repite en `input.json`, se considera una
única keyword para generar combinaciones.

El reporte consolidado incluye la hoja `Keywords_Sin_Combinacion`. Para cada
API, muestra las keywords que no participaron en una terna ejecutada, sus
resultados individuales y el motivo. Esta hoja ayuda a decidir qué keywords
ajustar antes de la siguiente iteración.

Si una cuota de API detiene la ejecución, el reporte también incluye
`Ternas_No_Ejecutadas`. Esta hoja y el log muestran cada terna pendiente con
los conteos individuales de sus tres keywords. Así se distingue una keyword
que debe ajustarse de una combinación válida que no llegó a consultarse.

La hoja `Ternas_Sin_Resultados` muestra un caso diferente: las tres keywords
tenían resultados individuales positivos y la terna se consultó, pero su
consulta `AND` devolvió 0. Esta información también aparece en el log y en el
resumen impreso al finalizar la ejecución.
