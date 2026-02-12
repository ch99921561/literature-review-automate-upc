"""
Literature Review Automation Tool
=================================
Cliente unificado para búsqueda en múltiples APIs académicas:
- Scopus (Elsevier)
- IEEE Xplore

Uso:
    python main.py --sencilla              # Ejecutar ambas APIs en modo conteo
    python main.py --sencilla --scopus     # Solo Scopus
    python main.py --sencilla --ieee       # Solo IEEE
    python main.py --extendida             # Modo extendido interactivo

Configuración:
    1. Configurar variables de entorno:
       $Env:SCOPUS_API_KEY = "tu_api_key"
       $Env:IEEE_API_KEY = "tu_api_key"
    2. Editar input.json con keywords y filtros
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# CONFIGURACIÓN Y CONSTANTES
# =============================================================================

INPUT_FILE = "input.json"
LOG_DIR = "logs"


class APIType(Enum):
    """Tipos de API soportadas."""
    SCOPUS = "scopus"
    IEEE = "ieee"


@dataclass
class APIConfig:
    """Configuración específica de una API."""
    api_type: APIType
    base_url: str
    env_var: str
    max_per_request: int
    output_counts_file: str
    output_results_file: str


# Configuraciones de cada API
API_CONFIGS = {
    APIType.SCOPUS: APIConfig(
        api_type=APIType.SCOPUS,
        base_url="https://api.elsevier.com/content/search/scopus",
        env_var="SCOPUS_API_KEY",
        max_per_request=25,
        output_counts_file="scopus_counts.json",
        output_results_file="scopus_results.json",
    ),
    APIType.IEEE: APIConfig(
        api_type=APIType.IEEE,
        base_url="https://ieeexploreapi.ieee.org/api/v1/search/articles",
        env_var="IEEE_API_KEY",
        max_per_request=200,
        output_counts_file="ieee_counts.json",
        output_results_file="ieee_results.json",
    ),
}


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
class SearchResult:
    """Resultado de una búsqueda."""
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


# =============================================================================
# LOGGER
# =============================================================================

class Logger:
    """Manejador de logs con soporte para archivo y consola."""
    
    def __init__(self):
        self._file_handle = None
        self._filename: Optional[str] = None
    
    def init(self, api_name: str, mode: str) -> str:
        """Inicializa el archivo de log con timestamp."""
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._filename = f"{LOG_DIR}/{api_name}_{mode}_{timestamp}.log"
        self._file_handle = open(self._filename, "w", encoding="utf-8")
        
        self.header(f"{api_name.upper()} API LOG - Modo: {mode}")
        self.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.separator()
        
        return self._filename
    
    def write(self, message: str) -> None:
        """Escribe mensaje a consola y archivo."""
        print(message)
        if self._file_handle:
            self._file_handle.write(message + "\n")
            self._file_handle.flush()
    
    def separator(self, char: str = "=", length: int = 80) -> None:
        """Escribe una línea separadora."""
        self.write(char * length)
    
    def header(self, title: str) -> None:
        """Escribe un encabezado destacado."""
        self.write("")
        self.separator()
        self.write(f"  {title}")
        self.separator()
    
    def close(self) -> None:
        """Cierra el archivo de log."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
    
    @property
    def filename(self) -> Optional[str]:
        return self._filename


# Logger global
logger = Logger()


# =============================================================================
# HTTP CLIENT
# =============================================================================

class HTTPClient:
    """Cliente HTTP genérico."""
    
    @staticmethod
    def get(url: str, headers: Optional[Dict[str, str]] = None, 
            verbose: bool = True, mask_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Realiza un request GET y retorna el JSON parseado.
        
        Args:
            url: URL del request
            headers: Headers opcionales
            verbose: Si True, imprime detalles
            mask_key: Clave a enmascarar en la URL para logs
        """
        default_headers = {
            "Accept": "application/json",
            "User-Agent": "Python-LitReview-Client/2.0",
        }
        if headers:
            default_headers.update(headers)
        
        if verbose:
            display_url = url
            if mask_key and mask_key in url:
                # Enmascarar API key en logs
                parts = url.split(mask_key + "=")
                if len(parts) > 1:
                    key_part = parts[1].split("&")[0]
                    if len(key_part) > 12:
                        masked = key_part[:8] + "..." + key_part[-4:]
                        display_url = url.replace(key_part, masked)
            logger.header("REQUEST")
            logger.write(f"URL: {display_url}")
        
        req = urllib.request.Request(url=url, headers=default_headers, method="GET")
        
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                elapsed = time.time() - start
                
                if verbose:
                    logger.header("RESPONSE")
                    logger.write(f"Status: {resp.status} {resp.reason}")
                    logger.write(f"Elapsed: {elapsed:.2f}s")
                
                data = resp.read().decode("utf-8")
                return json.loads(data)
                
        except urllib.error.HTTPError as e:
            elapsed = time.time() - start
            if verbose:
                logger.header("ERROR")
            logger.write(f"HTTP Error: {e.code} {e.reason}")
            logger.write(f"Elapsed: {elapsed:.2f}s")
            try:
                error_body = e.read().decode("utf-8")
                logger.write(f"Response: {error_body[:500]}")
            except:
                pass
            return {"error": str(e)}
        except Exception as e:
            logger.write(f"Request failed: {e}")
            return {"error": str(e)}


# =============================================================================
# BASE API CLIENT (Abstract)
# =============================================================================

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
        all_entries = []
        start = 0 if self.config.api_type == APIType.SCOPUS else 1
        page_size = self.config.max_per_request
        total_results = None
        
        logger.header("BÚSQUEDA CON PAGINACIÓN")
        logger.write(f"Query: {query}")
        logger.write(f"Máximo de resultados: {max_results}")
        
        while True:
            page_num = (start // page_size + 1) if self.config.api_type == APIType.SCOPUS else ((start - 1) // page_size + 1)
            logger.write(f"\n--- Página {page_num} ---")
            
            response = self.search(query, filters, page_size, start, verbose=False)
            
            if "error" in response:
                logger.write(f"Error: {response['error']}")
                break
            
            if total_results is None:
                total_results = self.parse_total_results(response)
                logger.write(f"Total disponible: {total_results}")
            
            entries = self.parse_entries(response)
            if not entries:
                logger.write("No hay más resultados.")
                break
            
            all_entries.extend(entries)
            logger.write(f"Obtenidos: {len(entries)} | Acumulado: {len(all_entries)}")
            
            if len(all_entries) >= min(total_results, max_results):
                logger.write("\nLímite alcanzado.")
                break
            
            start += page_size
            time.sleep(0.3)
        
        logger.header("PAGINACIÓN COMPLETADA")
        logger.write(f"Total obtenido: {len(all_entries)}")
        
        return all_entries
    
    @abstractmethod
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Retorna headers específicos de la API."""
        pass
    
    @abstractmethod
    def _get_mask_key(self) -> Optional[str]:
        """Retorna la clave a enmascarar en logs."""
        pass
    
    def get_api_name(self) -> str:
        """Retorna el nombre de la API."""
        return self.config.api_type.value


# =============================================================================
# SCOPUS API CLIENT
# =============================================================================

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
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """Retorna headers específicos de Scopus."""
        return {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json",
        }
    
    def _get_mask_key(self) -> Optional[str]:
        """Scopus usa header para API key, no necesita enmascarar en URL."""
        return None


# =============================================================================
# IEEE API CLIENT
# =============================================================================

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
    
    def _get_headers(self) -> Optional[Dict[str, str]]:
        """IEEE usa API key en URL, no necesita headers especiales."""
        return None
    
    def _get_mask_key(self) -> Optional[str]:
        """IEEE usa apikey en URL, enmascarar en logs."""
        return "apikey"


# =============================================================================
# INPUT CONFIGURATION
# =============================================================================

@dataclass
class InputConfig:
    """Configuración de entrada unificada."""
    keywords: List[str]
    year_from: Optional[int]
    year_to: Optional[int]
    scopus: ScopusFilters
    ieee: IEEEFilters
    
    @classmethod
    def load(cls, filepath: str = INPUT_FILE) -> "InputConfig":
        """Carga la configuración desde archivo JSON."""
        if not os.path.exists(filepath):
            cls._create_example(filepath)
            logger.write(f"Archivo {filepath} creado. Edítalo y vuelve a ejecutar.")
            sys.exit(1)
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extraer configuración común
        keywords = data.get("keywords", [])
        year_from = data.get("year_from")
        year_to = data.get("year_to")
        
        # Configuración específica de Scopus
        scopus_data = data.get("scopus", {})
        scopus_filters = ScopusFilters(
            year_from=year_from,
            year_to=year_to,
            doc_types=scopus_data.get("doc_types", []),
            subject_areas=scopus_data.get("subject_areas", []),
        )
        
        # Configuración específica de IEEE
        ieee_data = data.get("ieee", {})
        ieee_filters = IEEEFilters(
            year_from=year_from,
            year_to=year_to,
            content_types=ieee_data.get("content_types", []),
        )
        
        return cls(
            keywords=keywords,
            year_from=year_from,
            year_to=year_to,
            scopus=scopus_filters,
            ieee=ieee_filters,
        )
    
    @staticmethod
    def _create_example(filepath: str) -> None:
        """Crea un archivo de ejemplo."""
        example = {
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
            }
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(example, f, indent=2, ensure_ascii=False)
        logger.write(f"ERROR: No se encontró {filepath}")
        logger.write("Creando archivo de ejemplo...")


# =============================================================================
# SEARCH ENGINE
# =============================================================================

class SearchEngine:
    """Motor de búsqueda que coordina las APIs."""
    
    def __init__(self):
        self.clients: Dict[APIType, BaseAPIClient] = {}
        self.config: Optional[InputConfig] = None
    
    def register_client(self, api_type: APIType, client: BaseAPIClient) -> bool:
        """Registra y autentica un cliente de API."""
        if client.authenticate():
            self.clients[api_type] = client
            return True
        return False
    
    def load_config(self) -> bool:
        """Carga la configuración de entrada."""
        try:
            self.config = InputConfig.load()
            return True
        except Exception as e:
            logger.write(f"Error cargando configuración: {e}")
            return False
    
    def run_simple_mode(self, api_type: APIType) -> int:
        """Ejecuta el modo sencillo para una API específica."""
        if api_type not in self.clients:
            logger.write(f"ERROR: Cliente {api_type.value} no registrado")
            return 1
        
        client = self.clients[api_type]
        api_name = client.get_api_name()
        
        # Inicializar log
        log_filename = logger.init(api_name, "sencilla")
        logger.write(f"Archivo de log: {log_filename}")
        
        logger.header(f"MODO SENCILLO - {api_name.upper()}")
        
        # Obtener filtros según el tipo de API
        filters = self._get_filters_for_api(api_type)
        
        # Mostrar configuración
        self._print_config(api_type, filters)
        
        # Ejecutar búsquedas
        individual_results = self._search_individual(client, filters)
        combination_results = self._search_combinations(client, filters)
        
        # Guardar resultados
        self._save_results(api_type, individual_results, combination_results)
        
        logger.close()
        return 0
    
    def _get_filters_for_api(self, api_type: APIType) -> SearchFilters:
        """Obtiene los filtros específicos para una API."""
        if api_type == APIType.SCOPUS:
            return self.config.scopus
        elif api_type == APIType.IEEE:
            return self.config.ieee
        return SearchFilters(year_from=self.config.year_from, year_to=self.config.year_to)
    
    def _print_config(self, api_type: APIType, filters: SearchFilters) -> None:
        """Imprime la configuración cargada."""
        logger.header("CONFIGURACIÓN CARGADA")
        logger.write(f"Archivo: {INPUT_FILE}")
        logger.write(f"Keywords: {len(self.config.keywords)}")
        for i, kw in enumerate(self.config.keywords, 1):
            logger.write(f"  {i}. {kw}")
        
        logger.write(f"\nFiltros:")
        logger.write(f"  Años: {filters.year_from or 'Sin límite'} - {filters.year_to or 'Sin límite'}")
        
        if isinstance(filters, ScopusFilters):
            logger.write(f"  Tipos de documento: {', '.join(filters.doc_types) if filters.doc_types else 'Todos'}")
            logger.write(f"  Áreas temáticas: {', '.join(filters.subject_areas) if filters.subject_areas else 'Todas'}")
        elif isinstance(filters, IEEEFilters):
            logger.write(f"  Tipos de contenido: {', '.join(filters.content_types) if filters.content_types else 'Todos'}")
    
    def _search_individual(self, client: BaseAPIClient, 
                           filters: SearchFilters) -> List[SearchResult]:
        """Realiza búsqueda individual por keyword."""
        logger.header("RESULTADOS INDIVIDUALES")
        logger.write(f"{'Keyword':<50} | {'Publicaciones':>15}")
        logger.write("-" * 70)
        
        results = []
        total = 0
        
        for keyword in self.config.keywords:
            query = f'"{keyword}"'
            count = client.count_results(query, filters)
            
            if count == -1:
                logger.write(f"{keyword:<50} | {'ERROR':>15}")
                results.append(SearchResult(keyword=keyword, query=query, count=None, error=True))
            else:
                logger.write(f"{keyword:<50} | {count:>15,}")
                results.append(SearchResult(keyword=keyword, query=query, count=count))
                total += count
            
            time.sleep(0.25)
        
        logger.write("-" * 70)
        logger.write(f"{'TOTAL INDIVIDUAL (suma)':<50} | {total:>15,}")
        
        return results
    
    def _search_combinations(self, client: BaseAPIClient,
                              filters: SearchFilters) -> List[CombinationResult]:
        """Realiza búsqueda por combinaciones de 3 keywords."""
        keywords = self.config.keywords
        
        if len(keywords) < 3:
            logger.write("\nNOTA: Se necesitan al menos 3 keywords para generar combinaciones.")
            return []
        
        logger.header("COMBINACIONES DE 3 KEYWORDS (TERNAS)")
        
        combinations = list(itertools.combinations(keywords, 3))
        logger.write(f"Total de combinaciones posibles: {len(combinations)}")
        logger.write("")
        
        results = []
        total = 0
        
        for idx, combo in enumerate(combinations, 1):
            query = f'"{combo[0]}" AND "{combo[1]}" AND "{combo[2]}"'
            count = client.count_results(query, filters)
            
            display_keywords = f"[{combo[0]}] AND [{combo[1]}] AND [{combo[2]}]"
            
            if count == -1:
                logger.write(f"\n{idx:3}. ERROR")
                logger.write(f"     Keywords: {display_keywords}")
                logger.write(f"     Query enviada: {query}")
                results.append(CombinationResult(keywords=list(combo), query=query, count=None, error=True))
            else:
                logger.write(f"\n{idx:3}. Resultados: {count:,}")
                logger.write(f"     Keywords: {display_keywords}")
                logger.write(f"     Query enviada: {query}")
                results.append(CombinationResult(keywords=list(combo), query=query, count=count))
                total += count
            
            time.sleep(0.25)
        
        # Mostrar resumen y TOP 30
        self._print_combination_summary(results, total)
        
        return results
    
    def _print_combination_summary(self, results: List[CombinationResult], total: int) -> None:
        """Imprime el resumen de combinaciones."""
        logger.header("RESUMEN DE COMBINACIONES")
        logger.write(f"Total de combinaciones: {len(results)}")
        logger.write(f"Suma de resultados: {total:,}")
        
        # Filtrar combinaciones con resultados > 0
        with_results = [r for r in results if r.count and r.count > 0]
        logger.write(f"Combinaciones con al menos 1 resultado: {len(with_results)}")
        
        if with_results:
            with_results.sort(key=lambda x: x.count or 0, reverse=True)
            
            logger.header("TOP 30 COMBINACIONES CON MÁS RESULTADOS")
            logger.write("")
            logger.write(f"{'#':<4} | {'Resultados':>12} | {'Keyword 1':<25} | {'Keyword 2':<25} | {'Keyword 3':<25}")
            logger.write("-" * 100)
            
            for i, r in enumerate(with_results[:30], 1):
                k1 = r.keywords[0][:24] if len(r.keywords[0]) > 24 else r.keywords[0]
                k2 = r.keywords[1][:24] if len(r.keywords[1]) > 24 else r.keywords[1]
                k3 = r.keywords[2][:24] if len(r.keywords[2]) > 24 else r.keywords[2]
                logger.write(f"{i:<4} | {r.count:>12,} | {k1:<25} | {k2:<25} | {k3:<25}")
            
            logger.write("-" * 100)
            logger.write("")
            logger.write("Detalle de queries enviadas:")
            for i, r in enumerate(with_results[:30], 1):
                logger.write(f"  {i:2}. {r.query}")
    
    def _save_results(self, api_type: APIType, 
                      individual: List[SearchResult],
                      combinations: List[CombinationResult]) -> None:
        """Guarda los resultados en archivo JSON."""
        config = API_CONFIGS[api_type]
        filters = self._get_filters_for_api(api_type)
        
        # Calcular totales
        total_individual = sum(r.count or 0 for r in individual)
        total_combinations = sum(r.count or 0 for r in combinations)
        
        output_data = {
            "api": api_type.value,
            "mode": "sencilla",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input_file": INPUT_FILE,
            "filters": {
                "year_from": filters.year_from,
                "year_to": filters.year_to,
            },
            "individual_results": {
                "keywords": [
                    {"keyword": r.keyword, "query": r.query, "count": r.count, "error": r.error}
                    for r in individual
                ],
                "total": total_individual,
            },
            "combination_results": {
                "combination_size": 3,
                "total_combinations": len(combinations),
                "combinations": [
                    {"keywords": r.keywords, "query": r.query, "count": r.count, "error": r.error}
                    for r in combinations
                ],
                "total": total_combinations,
            },
        }
        
        # Agregar filtros específicos
        if isinstance(filters, ScopusFilters):
            output_data["filters"]["doc_types"] = filters.doc_types
            output_data["filters"]["subject_areas"] = filters.subject_areas
        elif isinstance(filters, IEEEFilters):
            output_data["filters"]["content_types"] = filters.content_types
        
        with open(config.output_counts_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.header("RESUMEN FINAL")
        logger.write(f"Keywords analizados: {len(self.config.keywords)}")
        logger.write(f"Total individual: {total_individual:,}")
        if combinations:
            logger.write(f"Combinaciones (ternas): {len(combinations)}")
            logger.write(f"Total combinaciones: {total_combinations:,}")
        logger.write(f"\nResultados guardados en: {config.output_counts_file}")
        logger.write(f"Log guardado en: {logger.filename}")


# =============================================================================
# EXTENDED MODE
# =============================================================================

def run_extended_mode(engine: SearchEngine) -> int:
    """Ejecuta el modo extendido interactivo."""
    print("\n--- Selecciona la API ---")
    print("1. Scopus")
    print("2. IEEE Xplore")
    
    api_choice = input("\nSelecciona API (1 o 2): ").strip()
    
    if api_choice == "1":
        api_type = APIType.SCOPUS
    elif api_choice == "2":
        api_type = APIType.IEEE
    else:
        print("Opción no válida")
        return 1
    
    if api_type not in engine.clients:
        print(f"ERROR: Cliente {api_type.value} no disponible")
        return 1
    
    client = engine.clients[api_type]
    config = API_CONFIGS[api_type]
    
    logger.header(f"MODO EXTENDIDO - {api_type.value.upper()}")
    
    query = input("\nIngresa tu búsqueda (ej: 'machine learning AND healthcare'): ").strip()
    if not query:
        query = "machine learning AND systematic review"
        print(f"Usando query por defecto: {query}")
    
    # Filtros básicos
    print("\n--- Filtros opcionales (Enter para omitir) ---")
    year_from_str = input("Año desde (ej: 2020): ").strip()
    year_from = int(year_from_str) if year_from_str.isdigit() else None
    
    year_to_str = input("Año hasta (ej: 2025): ").strip()
    year_to = int(year_to_str) if year_to_str.isdigit() else None
    
    # Crear filtros según API
    if api_type == APIType.SCOPUS:
        filters = ScopusFilters(year_from=year_from, year_to=year_to)
    else:
        filters = IEEEFilters(year_from=year_from, year_to=year_to)
    
    # Modo de búsqueda
    print("\n--- Modo de búsqueda ---")
    print(f"1. Búsqueda simple (hasta {config.max_per_request} resultados)")
    print("2. Obtener TODOS los resultados (con paginación)")
    mode = input("Selecciona modo (1 o 2, default 1): ").strip()
    
    if mode == "2":
        max_str = input("Máximo de resultados (default 200): ").strip()
        max_results = int(max_str) if max_str.isdigit() else 200
        
        all_entries = client.search_all(query, filters, max_results)
        
        logger.header("RESUMEN DE RESULTADOS")
        print(f"Total obtenido: {len(all_entries)} artículos")
        
        if all_entries:
            print("\nPrimeros 5 resultados:")
            for i, entry in enumerate(all_entries[:5], 1):
                title = entry.get('dc:title') or entry.get('title', 'N/A')
                print(f"  {i}. {title[:80]}...")
        
        output_data = {
            "api": api_type.value,
            "query": query,
            "filters": {"year_from": year_from, "year_to": year_to},
            "total_results": len(all_entries),
            "entries": all_entries,
        }
        
        with open(config.output_results_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nResultados guardados en: {config.output_results_file}")
    else:
        count_str = input(f"Número de resultados (máx {config.max_per_request}, default 25): ").strip()
        max_records = int(count_str) if count_str.isdigit() else 25
        
        response = client.search(query, filters, max_records, verbose=True)
        
        # Mostrar resultados
        total = client.parse_total_results(response)
        entries = client.parse_entries(response)
        
        logger.header("RESULTADOS DE BÚSQUEDA")
        print(f"Total de resultados: {total}")
        print(f"Mostrando: {len(entries)}\n")
        
        for i, entry in enumerate(entries, 1):
            title = entry.get('dc:title') or entry.get('title', 'N/A')
            print(f"--- Resultado {i} ---")
            print(f"Título: {title}")
            print()
        
        with open(config.output_results_file, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        print(f"\nRespuesta guardada en: {config.output_results_file}")
    
    return 0


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Literature Review Automation - Búsqueda en Scopus e IEEE Xplore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py --sencilla              # Ambas APIs en modo conteo
  python main.py --sencilla --scopus     # Solo Scopus
  python main.py --sencilla --ieee       # Solo IEEE
  python main.py --extendida             # Modo extendido interactivo

Configuración:
  1. $Env:SCOPUS_API_KEY = "tu_api_key"
  2. $Env:IEEE_API_KEY = "tu_api_key"
  3. Editar input.json
"""
    )
    parser.add_argument("--sencilla", "-s", action="store_true",
                        help="Modo sencillo: conteo de publicaciones")
    parser.add_argument("--extendida", "-e", action="store_true",
                        help="Modo extendido: búsqueda detallada")
    parser.add_argument("--scopus", action="store_true",
                        help="Solo ejecutar Scopus")
    parser.add_argument("--ieee", action="store_true",
                        help="Solo ejecutar IEEE")
    
    args = parser.parse_args()
    
    # Determinar qué APIs ejecutar
    run_scopus = args.scopus or (not args.scopus and not args.ieee)
    run_ieee = args.ieee or (not args.scopus and not args.ieee)
    
    # Crear motor de búsqueda
    engine = SearchEngine()
    
    # Registrar clientes
    print("\n" + "=" * 80)
    print("  LITERATURE REVIEW AUTOMATION TOOL")
    print("=" * 80)
    
    if run_scopus:
        print("\n[Scopus]")
        scopus_client = ScopusAPIClient()
        engine.register_client(APIType.SCOPUS, scopus_client)
    
    if run_ieee:
        print("\n[IEEE Xplore]")
        ieee_client = IEEEAPIClient()
        engine.register_client(APIType.IEEE, ieee_client)
    
    if not engine.clients:
        print("\nERROR: No se pudo autenticar ninguna API")
        return 1
    
    # Cargar configuración
    if not engine.load_config():
        return 1
    
    # Determinar modo
    if args.sencilla:
        result = 0
        for api_type in engine.clients.keys():
            ret = engine.run_simple_mode(api_type)
            if ret != 0:
                result = ret
        return result
    
    elif args.extendida:
        return run_extended_mode(engine)
    
    else:
        # Modo interactivo
        print("\n--- Selecciona el modo de operación ---")
        print("1. SENCILLA: Solo conteo de publicaciones")
        print("2. EXTENDIDA: Búsqueda detallada")
        
        mode = input("\nSelecciona modo (1 o 2): ").strip()
        
        if mode == "1":
            result = 0
            for api_type in engine.clients.keys():
                ret = engine.run_simple_mode(api_type)
                if ret != 0:
                    result = ret
            return result
        else:
            return run_extended_mode(engine)


if __name__ == "__main__":
    sys.exit(main())
