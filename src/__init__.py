"""
Literature Review Automation Tool - Source Package
===================================================
Módulos para búsqueda automatizada en APIs académicas.
"""

from .config import APIType, API_CONFIGS, DEFINITIONS_DIR, OUTPUTS_DIR, LOG_DIR
from .models import (
    SearchFilters, ScopusFilters, IEEEFilters, WOSFilters,
    SearchResult, CombinationResult, APIConfig
)
from .logger import Logger, logger
from .http_client import HTTPClient
from .base_client import BaseAPIClient
from .scopus_client import ScopusAPIClient
from .ieee_client import IEEEAPIClient
from .wos_client import WOSAPIClient
from .input_config import InputConfig
from .search_engine import SearchEngine, run_extended_mode

__all__ = [
    # Config
    'APIType', 'API_CONFIGS', 'DEFINITIONS_DIR', 'OUTPUTS_DIR', 'LOG_DIR',
    # Models
    'SearchFilters', 'ScopusFilters', 'IEEEFilters', 'WOSFilters',
    'SearchResult', 'CombinationResult', 'APIConfig',
    # Logger
    'Logger', 'logger',
    # Clients
    'HTTPClient', 'BaseAPIClient', 
    'ScopusAPIClient', 'IEEEAPIClient', 'WOSAPIClient',
    # Config & Engine
    'InputConfig', 'SearchEngine', 'run_extended_mode',
]
