"""
Cliente para la API de Web of Science (Clarivate).
"""

import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import API_CONFIGS, APIType
from .models import SearchFilters, WOSFilters
from .base_client import BaseAPIClient


class WOSAPIClient(BaseAPIClient):
    """
    Cliente para la API de Web of Science (Clarivate).
    
    Documentación Swagger: https://api.clarivate.com/swagger-ui/?url=https://developer.clarivate.com/apis/wos/swagger
    
    La API proporciona acceso a metadatos y búsqueda de documentos en Web of Science.
    Requiere autenticación via X-ApiKey header.
    
    Planes disponibles:
    - Free Trial: 50 req/día (sin times cited)
    - Institutional Member: 5,000 req/día
    - Institutional Integration: 20,000 req/día
    """
    
    # Bases de datos disponibles
    DATABASES = {
        "WOS": "Web of Science Core Collection",
        "BIOABS": "Biological Abstracts",
        "BCI": "BIOSIS Citation Index",
        "BIOSIS": "BIOSIS Previews",
        "CCC": "Current Contents Connect",
        "DIIDW": "Derwent Innovations Index",
        "DRCI": "Data Citation Index",
        "MEDLINE": "MEDLINE",
        "ZOOREC": "Zoological Records",
        "PPRN": "Preprint Citation Index",
        "WOK": "All databases",
    }
    
    # Tipos de documento comunes
    DOCUMENT_TYPES = [
        "Article",
        "Review",
        "Proceedings Paper",
        "Editorial Material",
        "Book Chapter",
        "Letter",
        "Meeting Abstract",
        "Book Review",
        "Correction",
        "News Item",
    ]
    
    # Ediciones WOS Core Collection
    WOS_EDITIONS = [
        "SCI",    # Science Citation Index Expanded
        "SSCI",   # Social Sciences Citation Index
        "AHCI",   # Arts & Humanities Citation Index
        "ESCI",   # Emerging Sources Citation Index
        "CPCI-S", # Conference Proceedings Citation Index - Science
        "CPCI-SSH", # Conference Proceedings Citation Index - Social Science & Humanities
    ]
    
    def __init__(self):
        super().__init__(API_CONFIGS[APIType.WOS])
    
    def build_query_url(self, query: str, filters: SearchFilters,
                        max_records: int = 10, start: int = 1) -> str:
        """
        Construye la URL de búsqueda para WOS API (Search endpoint).
        
        La API usa parámetros:
        - databaseId: Base de datos (WOS, WOK, etc.)
        - usrQuery: Query en formato WOS (TS=topic, TI=title, AU=author, etc.)
        - publishTimeSpan: Rango de fechas (formato: YYYY-MM-DD+YYYY-MM-DD)
        - count: Número de registros a retornar (máximo 100)
        - firstRecord: Índice del primer registro (1-based)
        - sortField: Ordenamiento (LD+D=fecha carga desc, PY+D=año desc, TC+D=citas desc, RS+D=relevancia desc)
        """
        # Construir query SIN filtros de año (se usan en publishTimeSpan)
        full_query = self._build_full_query(query, filters, include_years=False)
        
        # Calcular firstRecord (1-indexed)
        first_record = max(1, start)
        
        params = {
            "usrQuery": full_query,
            "count": str(min(max_records, self.config.max_per_request)),
            "firstRecord": str(first_record),
        }
        
        # Ordenamiento configurable
        if isinstance(filters, WOSFilters):
            params["sortField"] = filters.sort_field
        else:
            params["sortField"] = "LD+D"  # Default: fecha de carga descendente
        
        # Base de datos
        if isinstance(filters, WOSFilters):
            params["databaseId"] = filters.database
            if filters.edition:
                params["edition"] = filters.edition
        else:
            params["databaseId"] = "WOS"
        
        # Rango de fechas usando publishTimeSpan
        if filters.year_from or filters.year_to:
            year_from = filters.year_from or 1900
            year_to = filters.year_to or datetime.now().year
            # Formato: YYYY-MM-DD+YYYY-MM-DD
            params["publishTimeSpan"] = f"{year_from}-01-01+{year_to}-12-31"
        
        return f"{self.config.base_url}?{urllib.parse.urlencode(params)}"
    
    def _build_full_query(self, query: str, filters: SearchFilters, include_years: bool = False) -> str:
        """
        Construye la query completa para WOS.
        
        WOS usa field tags específicos:
        - TS: Topic Search (título, abstract, keywords)
        - TI: Título
        - AU: Autor
        - PY: Publication Year
        - DT: Document Type
        - DO: DOI
        
        Args:
            query: Término de búsqueda
            filters: Filtros de búsqueda
            include_years: Si True, incluye años en la query (para compatibilidad)
                          Si False, los años se manejan via publishTimeSpan
        """
        # Si la query ya tiene formato WOS (contiene '=' como TS=, TI=, etc.), usarla directamente
        if '=' in query and not query.startswith('"'):
            full_query = query
        # Si la query contiene operadores booleanos AND/OR, cada término debe tener su TS=
        elif ' AND ' in query or ' OR ' in query:
            # Dividir por AND/OR y envolver cada término en TS=(...)
            # Ejemplo: '"CSIRT" AND "risk management"' -> 'TS=(CSIRT) AND TS=(risk management)'
            parts = re.split(r'\s+(AND|OR)\s+', query)
            result_parts = []
            for part in parts:
                if part in ('AND', 'OR'):
                    result_parts.append(part)
                else:
                    # Limpiar comillas externas del término
                    term = part.strip().strip('"')
                    # Envolver en TS=(...) - WoS buscará en título, abstract y keywords
                    result_parts.append(f'TS=({term})')
            full_query = ' '.join(result_parts)
        else:
            # Búsqueda simple: envolver en TS (Topic Search)
            full_query = f"TS=({query})"
        
        # Agregar filtro de años usando PY solo si se solicita explícitamente
        if include_years:
            if filters.year_from and filters.year_to:
                if filters.year_from == filters.year_to:
                    full_query = f"{full_query} AND PY={filters.year_from}"
                else:
                    full_query = f"{full_query} AND PY={filters.year_from}-{filters.year_to}"
            elif filters.year_from:
                full_query = f"{full_query} AND PY>={filters.year_from}"
            elif filters.year_to:
                full_query = f"{full_query} AND PY<={filters.year_to}"
        
        # Filtrar por tipo de documento si se especifica
        if isinstance(filters, WOSFilters) and filters.document_types:
            dt_filter = " OR ".join([f'DT=("{dt}")' for dt in filters.document_types])
            full_query = f"{full_query} AND ({dt_filter})"
        
        return full_query
    
    def parse_total_results(self, response: Dict[str, Any]) -> int:
        """
        Extrae el total de resultados de la respuesta de WOS API.
        
        La respuesta tiene la estructura:
        {
            "QueryResult": {
                "RecordsFound": 123,
                "RecordsSearched": 123,
                "QueryID": "..."
            },
            "Data": {
                "Records": {...}
            }
        }
        """
        # Estructura de WoS API (Search endpoint)
        query_result = response.get("QueryResult", {})
        records_found = query_result.get("RecordsFound", 0)
        if records_found:
            return int(records_found)
        
        # Fallback: estructura de WoS Starter API
        metadata = response.get("metadata", {})
        return int(metadata.get("total", 0))
    
    def parse_entries(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrae las entradas de la respuesta de WOS API.
        
        La respuesta tiene la estructura:
        {
            "Data": {
                "Records": {
                    "records": {
                        "REC": [...]
                    }
                }
            }
        }
        """
        # Estructura de WoS API (Search endpoint) - datos en "Data"
        data = response.get("Data", {})
        records = data.get("Records", {})
        
        if records:
            # Los records pueden estar en diferentes formatos
            if isinstance(records, dict):
                records_data = records.get("records", {})
                if isinstance(records_data, dict):
                    return records_data.get("REC", [])
                return records_data if isinstance(records_data, list) else []
            return records if isinstance(records, list) else []
        
        # Fallback: estructura de WoS Starter API
        return response.get("hits", [])
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """WOS usa X-ApiKey header para autenticación."""
        return {
            "X-ApiKey": self.api_key,
            "Accept": "application/json",
        }
    
    def _get_mask_key(self) -> Optional[str]:
        """WOS usa header para API key, no necesita enmascarar en URL."""
        return None
    
    def extract_document_titles(self, entries: List[Dict[str, Any]]) -> List[str]:
        """
        Extrae los títulos de los documentos de WOS.
        
        La estructura de WoS API tiene títulos en:
        {
            "static_data": {
                "summary": {
                    "titles": {
                        "title": [{"type": "item", "content": "Title text"}]
                    }
                }
            }
        }
        """
        titles = []
        for entry in entries:
            title = None
            
            # WoS API: Estructura anidada en static_data
            static_data = entry.get('static_data', {})
            if static_data:
                summary = static_data.get('summary', {})
                titles_data = summary.get('titles', {})
                title_list = titles_data.get('title', [])
                
                # Buscar el título de tipo "item" (título principal)
                if isinstance(title_list, list):
                    for t in title_list:
                        if isinstance(t, dict) and t.get('type') == 'item':
                            title = t.get('content', '')
                            break
                elif isinstance(title_list, dict):
                    title = title_list.get('content', '')
            
            # Fallback: WOS Starter API usa el campo 'title' directamente
            if not title:
                title = entry.get('title', '')
            
            if title:
                titles.append(title)
        return titles
    
    def get_document_by_uid(self, uid: str) -> Dict[str, Any]:
        """
        Obtiene un documento específico por su UID (Accession Number).
        
        Args:
            uid: Web of Science Unique Identifier (ej: WOS:000267144200002)
        
        Returns:
            Documento con metadatos completos
        """
        # Usar el endpoint de documentos individuales
        url = f"https://wos-api.clarivate.com/api/wos/id/{uid}"
        return self.http.get(url, headers=self._get_headers(), verbose=True)
