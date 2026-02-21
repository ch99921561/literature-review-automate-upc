"""
Clase base abstracta para clientes de API.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .config import APIConfig
from .models import SearchFilters
from .logger import logger
from .http_client import HTTPClient


class BaseAPIClient(ABC):
    """Clase base abstracta para clientes de API."""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.api_key: Optional[str] = None
        self.http = HTTPClient()
    
    def authenticate(self) -> bool:
        """Obtiene la API key desde variable de entorno."""
        self.api_key = os.getenv(self.config.env_var)
        if not self.api_key:
            logger.write(f"ERROR: No se encontró {self.config.env_var}")
            logger.write(f"Configúrala con: $Env:{self.config.env_var} = 'tu_api_key'")
            return False
        logger.write(f"API Key configurada: {self.api_key[:8]}...{self.api_key[-4:]}")
        return True
    
    @abstractmethod
    def build_query_url(self, query: str, filters: SearchFilters, 
                        max_records: int = 1, start: int = 0) -> str:
        """Construye la URL de búsqueda. Implementar en subclases."""
        pass
    
    @abstractmethod
    def parse_total_results(self, response: Dict[str, Any]) -> int:
        """Extrae el total de resultados de la respuesta. Implementar en subclases."""
        pass
    
    @abstractmethod
    def parse_entries(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrae las entradas de la respuesta. Implementar en subclases."""
        pass
    
    def count_results(self, query: str, filters: SearchFilters) -> int:
        """Cuenta el total de resultados sin descargar datos."""
        url = self.build_query_url(query, filters, max_records=1, start=0)
        response = self.http.get(url, headers=self._get_headers(), verbose=False,
                                  mask_key=self._get_mask_key())
        
        if "error" in response:
            return -1
        
        return self.parse_total_results(response)
    
    def search(self, query: str, filters: SearchFilters, 
               max_records: int = 25, start: int = 0, verbose: bool = True) -> Dict[str, Any]:
        """Realiza una búsqueda."""
        url = self.build_query_url(query, filters, max_records, start)
        return self.http.get(url, headers=self._get_headers(), verbose=verbose,
                             mask_key=self._get_mask_key())
    
    def search_all(self, query: str, filters: SearchFilters, 
                   max_results: int = 1000) -> List[Dict[str, Any]]:
        """Busca todos los resultados con paginación automática."""
        from .config import APIType
        
        all_entries = []
        start = 0 if self.config.api_type == APIType.SCOPUS else 1
        page_size = self.config.max_per_request
        total_results = None
        
        logger.header("BÚSQUEDA CON PAGINACIÓN")
        logger.write(f"Query: {query}")
        logger.write(f"Máximo de resultados: {max_results}")
        
        while len(all_entries) < max_results:
            response = self.search(query, filters, max_records=page_size, 
                                   start=start, verbose=False)
            
            if "error" in response:
                logger.write(f"Error en página {start}: {response['error']}")
                break
            
            if total_results is None:
                total_results = self.parse_total_results(response)
                logger.write(f"Total disponible: {total_results:,}")
            
            entries = self.parse_entries(response)
            if not entries:
                break
            
            all_entries.extend(entries)
            logger.write(f"  Página {start//page_size + 1}: {len(entries)} registros (acumulado: {len(all_entries)})")
            
            start += page_size
            if start >= total_results:
                break
        
        logger.write(f"\nTotal recuperado: {len(all_entries)}")
        return all_entries[:max_results]
    
    @abstractmethod
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Retorna headers específicos para la API. Implementar en subclases."""
        pass
    
    @abstractmethod
    def _get_mask_key(self) -> Optional[str]:
        """Retorna la clave a enmascarar en logs. Implementar en subclases."""
        pass
    
    @abstractmethod
    def extract_document_titles(self, entries: List[Dict[str, Any]]) -> List[str]:
        """Extrae los títulos de los documentos. Implementar en subclases."""
        pass
    
    def get_document_titles(self, query: str, filters: SearchFilters, max_docs: int = 200) -> List[str]:
        """
        Obtiene los títulos de documentos para una query.
        
        Args:
            query: Query de búsqueda
            filters: Filtros de búsqueda
            max_docs: Máximo de documentos a recuperar
        
        Returns:
            Lista de títulos de documentos
        """
        url = self.build_query_url(query, filters, 
                                   max_records=min(max_docs, self.config.max_per_request), start=1)
        response = self.http.get(url, headers=self._get_headers(), verbose=False,
                                 mask_key=self._get_mask_key())
        
        if "error" in response:
            return []
        
        entries = self.parse_entries(response)
        return self.extract_document_titles(entries)
    
    def get_api_name(self) -> str:
        """Retorna el nombre de la API."""
        return self.config.api_type.value
