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

## Instalación

### 1. Crear y activar el entorno virtual

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

`Set-ExecutionPolicy` solo aplica a la consola actual y permite activar el
entorno cuando PowerShell bloquea scripts. La carpeta `.venv` está excluida del
repositorio.

### 2. Instalar dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Para comprobar la instalación:

```powershell
python -m unittest discover -s tests -v
```

## Configuración

### 1. Configurar el archivo `.env`

El archivo `.env` contiene secretos locales y está ignorado por Git. Copia la
plantilla versionada `.env.example` y completa los valores:

```powershell
Copy-Item .env.example .env
```

El valor de `APP_ENV` es obligatorio y solo puede ser `development`, `test` o
`production`. La aplicación carga y valida este archivo antes de ejecutar
cualquier modo.

```dotenv
APP_ENV=development
SCOPUS_API_KEY=tu_api_key_scopus
IEEE_API_KEY=tu_api_key_ieee
WOS_API_KEY=tu_api_key_wos
```

Las variables de entorno ya definidas en el sistema tienen prioridad sobre las
del archivo `.env`.

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

# Ejecutar las keywords de la tesis 2
python main.py --sencilla --titulo-tesis 2
```

**Funcionalidades:**
1. Conteo individual por keyword
2. Combinaciones de 3 keywords (ternas); se consultan únicamente si las tres
   keywords tuvieron resultados individuales
3. TOP 30 combinaciones con más resultados
4. Log con timestamp
5. Hojas `SCOPUS_Documentos`, `IEEE_Documentos` y `WOS_Documentos` con
   título, año de publicación y posible URL de descarga cuando la API la
   proporciona explícitamente
6. Hoja `Keywords_Sin_Combinacion` con keywords no usadas en ternas, su conteo
   individual y un motivo para orientar el ajuste de `input.json`
7. Hoja `Ternas_No_Ejecutadas` con las ternas de keywords que tenían conteos
   individuales positivos, pero no se consultaron por alcanzar una cuota de API
8. Hoja `Ternas_Sin_Resultados` con ternas ejecutadas cuyos tres conteos
   individuales eran positivos, pero devolvieron 0 al aplicar `AND`

Las hojas `*_Documentos` recuperan todos los registros que la API devuelve
para cada terna del TOP 30, hasta el límite operativo de 200 documentos por
terna.

La columna `Posible URL de descarga` solo se completa con enlaces explícitos
de PDF o texto completo incluidos en los metadatos. No se incluyen páginas de
metadatos, enlaces de pago ni URLs inferidas.

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
| `titulo_tesis` | ID de tesis predeterminado | `"1"` |
| `tesis.<id>.descripcion` | Nombre informativo de la tesis | `"Automatización de..."` |
| `tesis.<id>.keywords` | Keywords asociadas a una tesis | `["CSIRT", "SOC"]` |
| `year_from` | Año mínimo (null = sin límite) | `2020` |
| `year_to` | Año máximo (null = sin límite) | `2025` |
| `scopus.doc_types` | Tipos de documento Scopus | `["ar", "cp"]` |
| `scopus.subject_areas` | Áreas temáticas Scopus | `["COMP"]` |
| `ieee.content_types` | Tipos de contenido IEEE | `["Journals"]` |
| `rate_limits.<api>.calls_per_second` | Máximo de solicitudes por segundo (`null` = sin límite) | `10` |
| `rate_limits.<api>.calls_per_day` | Máximo de solicitudes por ejecución (`null` = sin límite) | `200` |
| `wos.database` | Base de datos WOS | `"WOS"` |
| `wos.edition` | Edición WOS (null = todas) | `"WOS+SCI"` |
| `wos.document_types` | Tipos de documento WOS | `["Article"]` |

### Selección de tesis

Las keywords se agrupan por tesis en `tesis`. `titulo_tesis` define cuál se
usa por defecto y la opción `--titulo-tesis ID` permite escoger otra al
ejecutar el programa. Los filtros transversales (`year_from`, `year_to`,
`scopus`, `ieee`, `wos` y `rate_limits`) se aplican sin cambios a todas las
tesis.

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

Ejemplos:

```powershell
# Usa titulo_tesis definido en input.json
python main.py --sencilla

# Sobrescribe la selección y usa la tesis 2
python main.py --sencilla --titulo-tesis 2
```

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

### Cuotas de API

Las cuotas se configuran opcionalmente en `rate_limits` de
`definitions/input.json`. Si una API no figura, o un valor se define como
`null`, no se aplica ese límite. La configuración actual limita únicamente IEEE
a 10 solicitudes por segundo y 200 solicitudes por ejecución:

```json
"rate_limits": {
  "ieee": {
    "calls_per_second": 10,
    "calls_per_day": 200
  }
}
```

El límite diario se controla dentro de cada ejecución para impedir que el
programa supere por sí solo la cuota. Las solicitudes previas hechas con la
misma clave también cuentan en el límite real de IEEE.

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
