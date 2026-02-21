"""
Configuración de entrada desde archivo JSON.
"""

import os
import sys
import json
from dataclasses import dataclass
from typing import List, Optional

from .config import INPUT_FILE, DEFINITIONS_DIR
from .models import ScopusFilters, IEEEFilters, WOSFilters
from .logger import logger


@dataclass
class InputConfig:
    """Configuración de entrada unificada."""
    keywords: List[str]
    year_from: Optional[int]
    year_to: Optional[int]
    scopus: ScopusFilters
    ieee: IEEEFilters
    wos: WOSFilters
    
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
        
        # Configuración específica de WOS
        wos_data = data.get("wos", {})
        wos_filters = WOSFilters(
            year_from=year_from,
            year_to=year_to,
            database=wos_data.get("database", "WOS"),
            edition=wos_data.get("edition"),
            document_types=wos_data.get("document_types", []),
            sort_field=wos_data.get("sort_field", "LD+D"),
        )
        
        return cls(
            keywords=keywords,
            year_from=year_from,
            year_to=year_to,
            scopus=scopus_filters,
            ieee=ieee_filters,
            wos=wos_filters,
        )
    
    @staticmethod
    def _create_example(filepath: str) -> None:
        """Crea un archivo de ejemplo."""
        # Asegurar que el directorio existe
        dir_path = os.path.dirname(filepath)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
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
            },
            "wos": {
                "database": "WOS",
                "edition": None,
                "document_types": ["Article", "Review"],
                "sort_field": "LD+D"
            }
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(example, f, indent=2, ensure_ascii=False)
        logger.write(f"ERROR: No se encontró {filepath}")
        logger.write("Creando archivo de ejemplo...")
