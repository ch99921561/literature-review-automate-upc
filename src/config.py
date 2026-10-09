"""
Configuración y constantes del sistema.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import os
import re
from typing import Mapping, MutableMapping, Optional


# =============================================================================
# RUTAS Y DIRECTORIOS
# =============================================================================

DEFINITIONS_DIR = "definitions"
OUTPUTS_DIR = "outputs"
LOG_DIR = "outputs/logs"
INPUT_FILE = "definitions/input.json"
CONSOLIDATED_OUTPUT_PREFIX = "output_consolidado"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_FILE = PROJECT_ROOT / ".env"
ENVIRONMENT_VARIABLE = "APP_ENV"
VALID_ENVIRONMENTS = frozenset({"development", "test", "production"})
_ENVIRONMENT_VARIABLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_dotenv(
    dotenv_path: Path = DOTENV_FILE,
    environ: Optional[MutableMapping[str, str]] = None,
) -> bool:
    """Carga variables de un archivo .env sin reemplazar las ya definidas."""
    if environ is None:
        environ = os.environ

    if not dotenv_path.is_file():
        return False

    for line_number, raw_line in enumerate(
        dotenv_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            raise ValueError(
                f"Formato inválido en {dotenv_path.name}, línea {line_number}: "
                "se esperaba NOMBRE=VALOR."
            )

        name, value = line.split("=", maxsplit=1)
        name = name.strip()
        value = value.strip()
        if not _ENVIRONMENT_VARIABLE_PATTERN.fullmatch(name):
            raise ValueError(
                f"Nombre de variable inválido en {dotenv_path.name}, línea {line_number}: "
                f"{name!r}."
            )

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        environ.setdefault(name, value)

    return True


def validate_environment(environ: Optional[Mapping[str, str]] = None) -> str:
    """Valida y retorna el entorno configurado en APP_ENV."""
    if environ is None:
        environ = os.environ

    environment = environ.get(ENVIRONMENT_VARIABLE, "").strip().lower()
    if not environment:
        raise ValueError(
            f"Falta {ENVIRONMENT_VARIABLE}. Defínelo en .env con uno de: "
            f"{', '.join(sorted(VALID_ENVIRONMENTS))}."
        )
    if environment not in VALID_ENVIRONMENTS:
        raise ValueError(
            f"{ENVIRONMENT_VARIABLE}={environment!r} no es válido. "
            f"Valores permitidos: {', '.join(sorted(VALID_ENVIRONMENTS))}."
        )

    return environment


def load_and_validate_environment() -> str:
    """Carga el .env del proyecto y valida el tipo de entorno."""
    load_dotenv()
    return validate_environment()


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
