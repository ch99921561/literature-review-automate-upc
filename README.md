# Scopus API Client

Cliente Python para buscar publicaciones académicas usando la API oficial de Elsevier/Scopus.

## Requisitos

- Python 3.10+
- API Key de Elsevier (obtener en https://dev.elsevier.com/)

## Configuración

1. Obtén tu API Key en https://dev.elsevier.com/
2. Configura la variable de entorno:

```powershell
# PowerShell
$Env:SCOPUS_API_KEY = "tu_api_key_aqui"
```

```bash
# Bash/Linux
export SCOPUS_API_KEY="tu_api_key_aqui"
```

## Uso

### Modo Sencillo (solo conteo)

Cuenta publicaciones usando la configuración del archivo `scopus_input.json`.

```powershell
python scopus_api.py --sencilla
# o
python scopus_api.py -s
```

**Configuración en `scopus_input.json`:**
```json
{
  "keywords": [
    "CSIRT",
    "SOC",
    "Security Operations Center",
    "cybersecurity act"
  ],
  "doc_types": ["ar", "cp"],
  "subject_areas": ["COMP", "ENGI"],
  "year_from": 2020,
  "year_to": 2025
}
```

El modo sencillo:
1. **Conteo individual**: Cuenta publicaciones por cada keyword
2. **Combinaciones de 3**: Genera todas las combinaciones posibles de 3 keywords (ternas) y cuenta las publicaciones que coinciden con los 3 términos
3. **Top 30**: Muestra las 30 combinaciones con más resultados en formato tabla
4. **Log con timestamp**: Guarda todo el output en `logs/scopus_sencilla_YYYYMMDD_HHMMSS.log`

Los resultados se guardan en `scopus_counts.json`.

### Modo Extendido (resultados detallados)

Búsqueda detallada con información completa de cada publicación.

```powershell
python scopus_api.py --extendida
# o
python scopus_api.py -e
```

Opciones dentro del modo extendido:
- **Búsqueda simple**: hasta 25 resultados
- **Paginación automática**: hasta 5000 resultados

Los resultados se guardan en `scopus_results.json`.

### Modo interactivo

```powershell
python scopus_api.py
```

Te preguntará qué modo deseas usar.

## Filtros disponibles

| Filtro | Descripción | Ejemplo |
|--------|-------------|---------|
| Año desde | Año mínimo de publicación | 2020 |
| Año hasta | Año máximo de publicación | 2025 |
| Tipos de documento | Filtrar por tipo | ar,cp,ch |
| Áreas temáticas | Filtrar por área | COMP,MEDI |

### Tipos de documento

| Código | Tipo |
|--------|------|
| `ar` | Article |
| `re` | Review |
| `cp` | Conference Paper |
| `ch` | Book Chapter |
| `bk` | Book |
| `ed` | Editorial |
| `le` | Letter |
| `no` | Note |
| `sh` | Short Survey |

### Áreas temáticas

| Código | Área |
|--------|------|
| `COMP` | Computer Science |
| `MEDI` | Medicine |
| `ENGI` | Engineering |
| `SOCI` | Social Sciences |
| `BUSI` | Business |
| `MATH` | Mathematics |
| `PHYS` | Physics |
| `CHEM` | Chemistry |
| `BIOC` | Biochemistry |
| `ARTS` | Arts and Humanities |

## Archivos de salida

- `scopus_counts.json` - Resultados del modo sencillo (conteos individuales y combinaciones)
- `scopus_results.json` - Resultados del modo extendido (datos completos)
- `logs/scopus_*.log` - Archivos de log con timestamp de cada ejecución

## Límites de la API

| Límite | Valor |
|--------|-------|
| Resultados por request | 25 máximo |
| Total por búsqueda | 5000 máximo |
| Rate limit | ~2-9 req/seg |

## Ejemplos de búsqueda

### Búsqueda combinada (modo extendido)
```
machine learning AND healthcare
"systematic review" AND automation
TITLE(artificial intelligence) AND PUBYEAR > 2020
```

### Términos independientes (modo sencillo)
```
machine learning, deep learning, artificial intelligence, neural networks
```

## Estructura del proyecto

```
literature-review-automate-upc/
├── scopus_api.py           # Script principal
├── scopus_input.json       # Configuración de entrada (keywords, filtros)
├── scopus_counts.json      # Salida modo sencillo (conteos individuales y combinaciones)
├── scopus_results.json     # Salida modo extendido
├── README.md               # Este archivo
├── docs/
│   └── sequence_diagram.txt  # Diagrama de secuencia (sequencediagram.org)
└── logs/
    └── scopus_sencilla_YYYYMMDD_HHMMSS.log  # Logs con timestamp
```

## Diagrama de Secuencia

El archivo `docs/sequence_diagram.txt` contiene el diagrama de secuencia del modo sencillo.
Para visualizarlo, copia el contenido en: https://sequencediagram.org/

```
┌─────────┐     ┌────────────┐     ┌─────────────┐     ┌────────────┐
│ Usuario │     │ Script     │     │ Scopus API  │     │ Archivos   │
└────┬────┘     └─────┬──────┘     └──────┬──────┘     └─────┬──────┘
     │                │                    │                  │
     │ --sencilla     │                    │                  │
     │───────────────>│                    │                  │
     │                │                    │                  │
     │                │ Leer config        │                  │
     │                │───────────────────────────────────────>│
     │                │                    │                  │
     │                │ Por cada keyword   │                  │
     │                │───────────────────>│                  │
     │                │    totalResults    │                  │
     │                │<───────────────────│                  │
     │                │                    │                  │
     │                │ Por cada terna     │                  │
     │                │───────────────────>│                  │
     │                │    totalResults    │                  │
     │                │<───────────────────│                  │
     │                │                    │                  │
     │                │ Guardar resultados │                  │
     │                │───────────────────────────────────────>│
     │                │                    │                  │
     │   Resumen      │                    │                  │
     │<───────────────│                    │                  │
     │                │                    │                  │
```

## Archivo de entrada (scopus_input.json)

```json
{
  "keywords": [
    "CSIRT",
    "SOC",
    "Security Operations Center",
    "cybersecurity act",
    "risk-based prioritization",
    "SOC service catalog",
    "privacy act",
    "incident cost",
    "SOC operating model",
    "breach notification act",
    "economic impact"
  ],
  "doc_types": [],
  "subject_areas": [],
  "year_from": null,
  "year_to": null
}
```

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `keywords` | Lista de términos a buscar | `["SOC", "CSIRT"]` |
| `doc_types` | Tipos de documento (vacío = todos) | `["ar", "cp"]` |
| `subject_areas` | Áreas temáticas (vacío = todas) | `["COMP", "ENGI"]` |
| `year_from` | Año mínimo (null = sin límite) | `2020` |
| `year_to` | Año máximo (null = sin límite) | `2025` |

## Documentación adicional

- [Scopus Search API](https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl)
- [Scopus Search Tips](https://dev.elsevier.com/sc_search_tips.html)
- [API Key Registration](https://dev.elsevier.com/)
