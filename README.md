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

Cuenta publicaciones para múltiples términos de búsqueda independientes.

```powershell
python scopus_api.py --sencilla
# o
python scopus_api.py -s
```

**Ejemplo de entrada:**
```
Términos de búsqueda: machine learning, deep learning, neural networks
```

Cada término se busca de forma independiente y muestra el conteo total. Los resultados se guardan en `scopus_counts.json`.

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

- `scopus_counts.json` - Resultados del modo sencillo (conteos)
- `scopus_results.json` - Resultados del modo extendido (datos completos)

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
├── scopus_api.py        # Script principal
├── scopus_counts.json   # Salida modo sencillo
├── scopus_results.json  # Salida modo extendido
└── README.md            # Este archivo
```

## Documentación adicional

- [Scopus Search API](https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl)
- [Scopus Search Tips](https://dev.elsevier.com/sc_search_tips.html)
- [API Key Registration](https://dev.elsevier.com/)
