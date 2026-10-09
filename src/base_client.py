"""
Clase base abstracta para clientes de API.
"""

import os
import time
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
    def extract_documents(self, entries: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extrae título y año de publicación. Implementar en subclases."""
        pass
    
    def get_documents(self, query: str, filters: SearchFilters,
                      max_docs: int = 200) -> List[Dict[str, str]]:
        """
        Obtiene títulos y años de publicación para una query con paginación.
        
        Args:
            query: Query de búsqueda
            filters: Filtros de búsqueda
            max_docs: Máximo de documentos a recuperar
        
        Returns:
            Lista de documentos con título y año de publicación
        """
        all_documents = []
        page_size = self.config.max_per_request
        start = 0 if self.config.api_type.value == "scopus" else 1
        total_results = None
        
        while len(all_documents) < max_docs:
            url = self.build_query_url(query, filters, max_records=page_size, start=start)
            response = self.http.get(url, headers=self._get_headers(), verbose=False,
                                     mask_key=self._get_mask_key())
            
            if "error" in response:
                break
            
            if total_results is None:
                total_results = self.parse_total_results(response)
            
            entries = self.parse_entries(response)
            if not entries:
                break
            
            documents = self.extract_documents(entries)
            all_documents.extend(documents)
            
            start += page_size
            if start > (total_results or 0):
                break
            
            # Pequeña pausa entre páginas
            time.sleep(0.15)
        
        return all_documents[:max_docs]
    
    def get_api_name(self) -> str:
        """Retorna el nombre de la API."""
        return self.config.api_type.value

    @staticmethod
    def get_download_url(entry: Dict[str, Any]) -> str:
        """Extrae una URL explícita de PDF o texto completo desde metadatos."""
        for field in ("pdf_url", "full_text_url", "fulltext_url", "download_url"):
            value = entry.get(field)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value

        links = entry.get("links") or entry.get("link") or []
        if isinstance(links, dict):
            links = [links]
        if not isinstance(links, list):
            return ""

        for link in links:
            if not isinstance(link, dict):
                continue
            relation = str(
                link.get("@ref")
                or link.get("ref")
                or link.get("type")
                or link.get("rel")
                or ""
            ).lower()
            if "pdf" not in relation and "full" not in relation:
                continue
            value = link.get("@href") or link.get("href") or link.get("url")
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value

        return ""
