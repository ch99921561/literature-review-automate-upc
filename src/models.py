"""
Modelos de datos (dataclasses) para el sistema.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


# =============================================================================
# CONFIGURACIÓN DE API (re-export para compatibilidad)
# =============================================================================

class APIType(Enum):
    """Tipos de API soportadas."""
    SCOPUS = "scopus"
    IEEE = "ieee"
    WOS = "wos"


@dataclass
class APIConfig:
    """Configuración específica de una API."""
    api_type: APIType
    base_url: str
    env_var: str
    max_per_request: int
    output_counts_file: str
    output_results_file: str


# =============================================================================
# FILTROS DE BÚSQUEDA
# =============================================================================

@dataclass
class SearchFilters:
    """Filtros de búsqueda comunes."""
    year_from: Optional[int] = None
    year_to: Optional[int] = None


@dataclass
class ScopusFilters(SearchFilters):
    """Filtros específicos de Scopus."""
    doc_types: List[str] = field(default_factory=list)
    subject_areas: List[str] = field(default_factory=list)


@dataclass
class IEEEFilters(SearchFilters):
    """Filtros específicos de IEEE."""
    content_types: List[str] = field(default_factory=list)


@dataclass
class WOSFilters(SearchFilters):
    """Filtros específicos de Web of Science."""
    database: str = "WOS"  # WOS, BIOABS, BCI, BIOSIS, CCC, DIIDW, DRCI, MEDLINE, ZOOREC, WOK
    edition: Optional[str] = None  # WOS+SCI, WOS+SSCI, etc.
    document_types: List[str] = field(default_factory=list)  # Article, Review, etc.
    sort_field: str = "LD+D"  # LD+D=fecha carga, PY+D=año, TC+D=citas, RS+D=relevancia


# =============================================================================
# RESULTADOS DE BÚSQUEDA
# =============================================================================

@dataclass
class SearchResult:
    """Resultado de una búsqueda individual."""
    keyword: str
    query: str
    count: Optional[int]
    error: bool = False


@dataclass
class CombinationResult:
    """Resultado de una combinación de keywords."""
    keywords: List[str]
    query: str
    count: Optional[int]
    error: bool = False
    documents: List[str] = field(default_factory=list)  # Títulos de documentos encontrados
