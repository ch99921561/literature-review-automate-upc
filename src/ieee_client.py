"""
Cliente para la API de IEEE Xplore.
"""

import urllib.parse
from typing import Any, Dict, List, Optional

from .config import API_CONFIGS, APIType
from .models import SearchFilters, IEEEFilters
from .base_client import BaseAPIClient


class IEEEAPIClient(BaseAPIClient):
    """Cliente para la API de IEEE Xplore."""
    
    # Tipos de contenido válidos (case sensitive)
    CONTENT_TYPES = [
        "Books",
        "Conferences", 
        "Courses",
        "Early Access",
        "Journals",
        "Magazines",
        "Standards",
    ]
    
    def __init__(self):
        super().__init__(API_CONFIGS[APIType.IEEE])
    
    def build_query_url(self, query: str, filters: SearchFilters,
                        max_records: int = 1, start: int = 1) -> str:
        """Construye la URL de búsqueda para IEEE."""
        params = {
            "apikey": self.api_key,
            "querytext": query,
            "max_records": str(min(max_records, self.config.max_per_request)),
            "start_record": str(start if start > 0 else 1),
        }
        
        # Filtros de años
        if filters.year_from:
            params["start_year"] = str(filters.year_from)
        if filters.year_to:
            params["end_year"] = str(filters.year_to)
        
        # Filtros específicos de IEEE
        if isinstance(filters, IEEEFilters) and filters.content_types:
            params["content_type"] = filters.content_types[0]  # IEEE solo acepta uno
        
        return f"{self.config.base_url}?{urllib.parse.urlencode(params)}"
    
    def parse_total_results(self, response: Dict[str, Any]) -> int:
        """Extrae el total de resultados de la respuesta de IEEE."""
        return int(response.get("total_records", 0))
    
    def parse_entries(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrae las entradas de la respuesta de IEEE."""
        return response.get("articles", [])
    
    def extract_document_titles(self, entries: List[Dict[str, Any]]) -> List[str]:
        """Extrae los títulos de los documentos de IEEE."""
        titles = []
        for entry in entries:
            title = entry.get('title', '')
            if title:
                titles.append(title)
        return titles
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """IEEE usa API key en URL, no necesita headers especiales."""
        return None
    
    def _get_mask_key(self) -> Optional[str]:
        """IEEE usa apikey en URL, enmascarar en logs."""
        return "apikey"
