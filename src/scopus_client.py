"""
Cliente para la API de Scopus (Elsevier).
"""

import urllib.parse
from typing import Any, Dict, List, Optional

from .config import API_CONFIGS, APIType
from .models import SearchFilters, ScopusFilters
from .base_client import BaseAPIClient


class ScopusAPIClient(BaseAPIClient):
    """Cliente para la API de Scopus (Elsevier)."""
    
    # Tipos de documento válidos
    DOC_TYPES = {
        "ar": "Article",
        "re": "Review", 
        "cp": "Conference Paper",
        "ch": "Book Chapter",
        "bk": "Book",
        "ed": "Editorial",
        "le": "Letter",
        "no": "Note",
        "sh": "Short Survey",
    }
    
    # Áreas temáticas válidas
    SUBJECT_AREAS = {
        "COMP": "Computer Science",
        "MEDI": "Medicine",
        "ENGI": "Engineering",
        "SOCI": "Social Sciences",
        "BUSI": "Business",
        "MATH": "Mathematics",
        "PHYS": "Physics",
        "CHEM": "Chemistry",
        "BIOC": "Biochemistry",
        "ARTS": "Arts and Humanities",
    }
    
    def __init__(self):
        super().__init__(API_CONFIGS[APIType.SCOPUS])
    
    def build_query_url(self, query: str, filters: SearchFilters,
                        max_records: int = 1, start: int = 0) -> str:
        """Construye la URL de búsqueda para Scopus."""
        full_query = self._build_full_query(query, filters)
        
        params = {
            "query": full_query,
            "count": str(min(max_records, self.config.max_per_request)),
            "start": str(start),
            "view": "STANDARD",
            "sort": "-citedby-count",
        }
        
        return f"{self.config.base_url}?{urllib.parse.urlencode(params)}"
    
    def _build_full_query(self, query: str, filters: SearchFilters) -> str:
        """Construye la query completa con filtros para Scopus."""
        full_query = query
        
        # Filtro de años
        if filters.year_from and filters.year_to:
            full_query = f"({query}) AND PUBYEAR > {filters.year_from - 1} AND PUBYEAR < {filters.year_to + 1}"
        elif filters.year_from:
            full_query = f"({query}) AND PUBYEAR > {filters.year_from - 1}"
        elif filters.year_to:
            full_query = f"({query}) AND PUBYEAR < {filters.year_to + 1}"
        
        # Filtros específicos de Scopus
        if isinstance(filters, ScopusFilters):
            # Tipos de documento
            if filters.doc_types:
                doc_filter = " OR ".join([f"DOCTYPE({dt})" for dt in filters.doc_types])
                full_query = f"({full_query}) AND ({doc_filter})"
            
            # Áreas temáticas
            if filters.subject_areas:
                area_filter = " OR ".join([f"SUBJAREA({sa})" for sa in filters.subject_areas])
                full_query = f"({full_query}) AND ({area_filter})"
        
        return full_query
    
    def parse_total_results(self, response: Dict[str, Any]) -> int:
        """Extrae el total de resultados de la respuesta de Scopus."""
        search_results = response.get("search-results", {})
        return int(search_results.get("opensearch:totalResults", 0))
    
    def parse_entries(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrae las entradas de la respuesta de Scopus."""
        search_results = response.get("search-results", {})
        entries = search_results.get("entry", [])
        # Verificar si hay error en las entries
        if entries and len(entries) == 1 and "error" in entries[0]:
            return []
        return entries
    
    def extract_document_titles(self, entries: List[Dict[str, Any]]) -> List[str]:
        """Extrae los títulos de los documentos de Scopus."""
        titles = []
        for entry in entries:
            title = entry.get('dc:title', '')
            if title:
                titles.append(title)
        return titles
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Retorna headers específicos de Scopus."""
        return {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json",
        }
    
    def _get_mask_key(self) -> Optional[str]:
        """Scopus usa header para API key, no necesita enmascarar en URL."""
        return None
