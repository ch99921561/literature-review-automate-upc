# Literature Review Automation Tool

Herramienta unificada para automatizar búsquedas en bases de datos académicas:
- **Scopus** (API de Elsevier)
- **IEEE Xplore** (API de IEEE)
- **Web of Science** (API Starter de Clarivate)

## Arquitectura

El proyecto utiliza un diseño orientado a objetos con las siguientes clases principales:

```
BaseAPIClient (ABC)          # Clase base abstracta
├── ScopusAPIClient          # Cliente específico Scopus
├── IEEEAPIClient            # Cliente específico IEEE
└── WOSAPIClient             # Cliente específico Web of Science

SearchEngine                 # Coordina las búsquedas
InputConfig                  # Configuración unificada
Logger                       # Manejo de logs
HTTPClient                   # Cliente HTTP genérico
```

## Requisitos

- Python 3.10+
- API Key de Elsevier (https://dev.elsevier.com/)
- API Key de IEEE (https://developer.ieee.org/member/register)
- API Key de Web of Science (https://developer.clarivate.com/apis/wos-starter)

## Configuración

### 1. Configurar variables de entorno

```powershell
# PowerShell
$Env:SCOPUS_API_KEY = "tu_api_key_scopus"
$Env:IEEE_API_KEY = "tu_api_key_ieee"
$Env:WOS_API_KEY = "tu_api_key_wos"
```

```bash
# Bash/Linux
export SCOPUS_API_KEY="tu_api_key_scopus"
export IEEE_API_KEY="tu_api_key_ieee"
export WOS_API_KEY="tu_api_key_wos"
```

### 2. Editar archivo de configuración

El archivo `input.json` contiene la configuración unificada:

```json
{
  "keywords": [
    "CSIRT",
    "risk management",
    "Security Operations Center"
  ],
  "year_from": 2020,
  "year_to": 2025,
  "scopus": {
    "doc_types": ["ar", "re", "cp"],
    "subject_areas": ["COMP", "ENGI"]
  },
  "ieee": {
    "content_types": ["Journals", "Conferences"]
  },
  "wos": {
    "database": "WOS",
    "edition": null,
    "document_types": ["Article", "Review"]
  }
}
```

## Uso

### Modo Sencillo (conteo)

```powershell
# Ejecutar todas las APIs
python main.py --sencilla

# Solo Scopus
python main.py --sencilla --scopus

# Solo IEEE
python main.py --sencilla --ieee

# Solo Web of Science
python main.py --sencilla --wos
```

**Funcionalidades:**
1. Conteo individual por keyword
2. Combinaciones de 3 keywords (ternas)
3. TOP 30 combinaciones con más resultados
4. Log con timestamp

### Modo Extendido (resultados detallados)

```powershell
python main.py --extendida
```

**Funcionalidades:**
1. Búsqueda simple o con paginación
2. Resultados completos con metadatos
3. Exportación a JSON

### Modo Interactivo

```powershell
python main.py
```

## Estructura del Proyecto

```
literature-review-automate-upc/
├── main.py                 # Script principal unificado
├── input.json              # Configuración de entrada unificada
├── scopus_counts.json      # Salida modo sencillo Scopus
├── scopus_results.json     # Salida modo extendido Scopus
├── ieee_counts.json        # Salida modo sencillo IEEE
├── ieee_results.json       # Salida modo extendido IEEE
├── wos_counts.json         # Salida modo sencillo WOS
├── wos_results.json        # Salida modo extendido WOS
├── README.md               # Este archivo
├── docs/
│   ├── sequence_diagram.txt      # Diagrama Scopus
│   └── ieee_sequence_diagram.txt # Diagrama IEEE
└── logs/
    ├── scopus_sencilla_*.log     # Logs Scopus
    ├── ieee_sencilla_*.log       # Logs IEEE
    └── wos_sencilla_*.log        # Logs WOS
```

## Archivo de Entrada (input.json)

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `keywords` | Lista de términos a buscar | `["CSIRT", "SOC"]` |
| `year_from` | Año mínimo (null = sin límite) | `2020` |
| `year_to` | Año máximo (null = sin límite) | `2025` |
| `scopus.doc_types` | Tipos de documento Scopus | `["ar", "cp"]` |
| `scopus.subject_areas` | Áreas temáticas Scopus | `["COMP"]` |
| `ieee.content_types` | Tipos de contenido IEEE | `["Journals"]` |
| `wos.database` | Base de datos WOS | `"WOS"` |
| `wos.edition` | Edición WOS (null = todas) | `"WOS+SCI"` |
| `wos.document_types` | Tipos de documento WOS | `["Article"]` |

### Tipos de documento Scopus

| Código | Tipo |
|--------|------|
| `ar` | Article |
| `re` | Review |
| `cp` | Conference Paper |
| `ch` | Book Chapter |
| `bk` | Book |

### Áreas temáticas Scopus

| Código | Área |
|--------|------|
| `COMP` | Computer Science |
| `MEDI` | Medicine |
| `ENGI` | Engineering |
| `SOCI` | Social Sciences |
| `BUSI` | Business |

### Tipos de contenido IEEE (case sensitive)

| Tipo |
|------|
| `Books` |
| `Conferences` |
| `Courses` |
| `Early Access` |
| `Journals` |
| `Magazines` |
| `Standards` |

### Bases de datos Web of Science

| Código | Nombre |
|--------|--------|
| `WOS` | Web of Science Core Collection |
| `BIOABS` | Biological Abstracts |
| `BCI` | BIOSIS Citation Index |
| `BIOSIS` | BIOSIS Previews |
| `CCC` | Current Contents Connect |
| `DIIDW` | Derwent Innovations Index |
| `DRCI` | Data Citation Index |
| `MEDLINE` | MEDLINE |
| `ZOOREC` | Zoological Records |
| `PPRN` | Preprint Citation Index |
| `WOK` | All databases |

### Tipos de documento Web of Science

| Tipo |
|------|
| `Article` |
| `Review` |
| `Proceedings Paper` |
| `Editorial Material` |
| `Book Chapter` |
| `Letter` |
| `Meeting Abstract` |

## Límites de las APIs

| API | Max por request | Rate limit |
|-----|-----------------|------------|
| Scopus | 25 | ~2-9 req/seg |
| IEEE | 200 | Según suscripción |
| WOS Starter | 50 | 50-20,000 req/día (según plan) |

### Planes Web of Science Starter API

| Plan | Límite diario | Times Cited |
|------|---------------|-------------|
| Free Trial | 50 req/día | No |
| Institutional Member | 5,000 req/día | Sí |
| Institutional Integration | 20,000 req/día | Sí |

## Diagrama de Secuencia

Los archivos en `docs/` contienen diagramas de secuencia para visualizar en https://sequencediagram.org/

```
┌─────────┐     ┌────────────┐     ┌─────────────┐     ┌────────────┐
│ Usuario │     │  main.py   │     │  APIs       │     │ Archivos   │
└────┬────┘     └─────┬──────┘     └──────┬──────┘     └─────┬──────┘
     │                │                    │                  │
     │ --sencilla     │                    │                  │
     │───────────────>│                    │                  │
     │                │                    │                  │
     │                │ Leer input.json    │                  │
     │                │───────────────────────────────────────>│
     │                │                    │                  │
     │                │ Por cada API       │                  │
     │                │───────────────────>│                  │
     │                │  (Scopus/IEEE/WOS) │                  │
     │                │<───────────────────│                  │
     │                │                    │                  │
     │                │ Guardar resultados │                  │
     │                │───────────────────────────────────────>│
     │                │                    │                  │
     │   Resumen      │                    │                  │
     │<───────────────│                    │                  │
```

## Documentación de APIs

### Scopus
- [Scopus Search API](https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl)
- [Search Tips](https://dev.elsevier.com/sc_search_tips.html)

### IEEE Xplore
- [IEEE API Documentation](https://developer.ieee.org/docs)
- [Search Parameters](https://developer.ieee.org/docs/read/Metadata_API_details)
- [Boolean Operators](https://developer.ieee.org/docs/read/metadata_api_details/Leveraging_Boolean_Logic)

### Web of Science Starter
- [WOS Starter API](https://developer.clarivate.com/apis/wos-starter)
- [API Swagger](https://api.clarivate.com/swagger-ui/?url=https://developer.clarivate.com/apis/wos-starter/swagger)
- [Advanced Search Query Builder](https://webofscience.help.clarivate.com/en-us/Content/advanced-search.html)
- [WOS Release Notes](https://clarivate.com/academia-government/release-notes/wos-apis/)

#### Field Tags soportados por WOS Starter API

| Tag | Descripción |
|-----|-------------|
| `TS` | Topic Search (título, abstract, keywords) |
| `TI` | Título del documento |
| `AU` | Autor |
| `AI` | Author Identifier |
| `PY` | Año de publicación |
| `DT` | Document Type |
| `DO` | DOI |
| `IS` | ISSN o ISBN |
| `SO` | Source title |
| `UT` | Accession Number |
| `OG` | Organization |

## Archivos Legacy

Los siguientes archivos son versiones anteriores (no unificadas):
- `scopus_api.py` - Cliente Scopus independiente
- `ieee_api.py` - Cliente IEEE independiente
- `scopus_input.json` - Input anterior Scopus
- `ieee_input.json` - Input anterior IEEE

Se recomienda usar `main.py` con `input.json` para nuevas ejecuciones.
