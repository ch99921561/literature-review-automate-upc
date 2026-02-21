"""
Configuración y constantes del sistema.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# RUTAS Y DIRECTORIOS
# =============================================================================

DEFINITIONS_DIR = "definitions"
OUTPUTS_DIR = "outputs"
LOG_DIR = "outputs/logs"
INPUT_FILE = "definitions/input.json"
CONSOLIDATED_OUTPUT_PREFIX = "output_consolidado"


# =============================================================================
# TIPOS DE API
# =============================================================================

class APIType(Enum):
    """Tipos de API soportadas."""
    SCOPUS = "scopus"
    IEEE = "ieee"
    WOS = "wos"


# =============================================================================
# CONFIGURACIÓN DE APIs
# =============================================================================

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
        output_counts_file=f"{OUTPUTS_DIR}/scopus_counts.json",
        output_results_file=f"{OUTPUTS_DIR}/scopus_results.json",
    ),
    APIType.IEEE: APIConfig(
        api_type=APIType.IEEE,
        base_url="https://ieeexploreapi.ieee.org/api/v1/search/articles",
        env_var="IEEE_API_KEY",
        max_per_request=200,
        output_counts_file=f"{OUTPUTS_DIR}/ieee_counts.json",
        output_results_file=f"{OUTPUTS_DIR}/ieee_results.json",
    ),
    APIType.WOS: APIConfig(
        api_type=APIType.WOS,
        base_url="https://wos-api.clarivate.com/api/wos/",
        env_var="WOS_API_KEY",
        max_per_request=100,
        output_counts_file=f"{OUTPUTS_DIR}/wos_counts.json",
        output_results_file=f"{OUTPUTS_DIR}/wos_results.json",
    ),
}
