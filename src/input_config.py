"""
Configuración de entrada desde archivo JSON.
"""

import os
import sys
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
    rate_limits: Dict[str, Dict[str, Optional[int]]]
    thesis_id: Optional[str]
    thesis_description: Optional[str]
    
    @classmethod
    def load(cls, filepath: str = INPUT_FILE,
             thesis_id: Optional[str] = None) -> "InputConfig":
        """Carga la configuración desde archivo JSON."""
        if not os.path.exists(filepath):
            cls._create_example(filepath)
            logger.write(f"Archivo {filepath} creado. Edítalo y vuelve a ejecutar.")
            sys.exit(1)
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extraer configuración común
        selected_thesis_id, thesis_description, keywords = cls._select_thesis(
            data, thesis_id
        )
        year_from = data.get("year_from")
        year_to = data.get("year_to")
        rate_limits = cls._parse_rate_limits(data.get("rate_limits", {}))
        
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
            rate_limits=rate_limits,
            thesis_id=selected_thesis_id,
            thesis_description=thesis_description,
        )

    @staticmethod
    def _select_thesis(data: Dict[str, Any],
                       requested_thesis_id: Optional[str]) -> tuple[Optional[str], Optional[str], List[str]]:
        """Selecciona las keywords de una tesis o mantiene el formato heredado."""
        theses = data.get("tesis")
        if theses is None:
            keywords = data.get("keywords", [])
            if not isinstance(keywords, list):
                raise ValueError("'keywords' debe ser una lista.")
            return None, None, keywords
        if not isinstance(theses, dict):
            raise ValueError("'tesis' debe ser un objeto JSON.")

        thesis_id = requested_thesis_id or data.get("titulo_tesis")
        if not thesis_id:
            raise ValueError(
                "Falta 'titulo_tesis'. Indica una tesis en input.json o usa "
                "--titulo-tesis."
            )
        thesis_id = str(thesis_id)
        thesis = theses.get(thesis_id)
        if not isinstance(thesis, dict):
            available_ids = ", ".join(sorted(theses)) or "ninguna"
            raise ValueError(
                f"La tesis '{thesis_id}' no existe. Tesis disponibles: {available_ids}."
            )

        description = thesis.get("descripcion")
        keywords = thesis.get("keywords")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"La tesis '{thesis_id}' requiere una 'descripcion'.")
        if not isinstance(keywords, list) or not all(
            isinstance(keyword, str) and keyword.strip() for keyword in keywords
        ):
            raise ValueError(
                f"Las 'keywords' de la tesis '{thesis_id}' deben ser una lista de textos."
            )

        return thesis_id, description, keywords

    @staticmethod
    def _parse_rate_limits(raw_limits: Any) -> Dict[str, Dict[str, Optional[int]]]:
        """Valida límites opcionales de solicitudes por API."""
        if not isinstance(raw_limits, dict):
            raise ValueError("'rate_limits' debe ser un objeto JSON.")

        parsed_limits = {}
        for api_name, raw_limit in raw_limits.items():
            if not isinstance(raw_limit, dict):
                raise ValueError(f"El límite de '{api_name}' debe ser un objeto JSON.")

            parsed_limit = {}
            for field in ("calls_per_second", "calls_per_day"):
                value = raw_limit.get(field)
                if value is not None and (not isinstance(value, int) or value <= 0):
                    raise ValueError(
                        f"'{api_name}.{field}' debe ser un entero positivo o null."
                    )
                parsed_limit[field] = value
            parsed_limits[api_name] = parsed_limit

        return parsed_limits
    
    @staticmethod
    def _create_example(filepath: str) -> None:
        """Crea un archivo de ejemplo."""
        # Asegurar que el directorio existe
        dir_path = os.path.dirname(filepath)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        example = {
            "titulo_tesis": "1",
            "tesis": {
                "1": {
                    "descripcion": "Título de tesis 1",
                    "keywords": [
                        "CSIRT",
                        "risk management",
                        "Security Operations Center"
                    ]
                },
                "2": {
                    "descripcion": "Título de tesis 2",
                    "keywords": []
                }
            },
            "year_from": 2020,
            "year_to": 2025,
            "scopus": {
                "doc_types": ["ar", "re", "cp"],
                "subject_areas": ["COMP", "ENGI"]
            },
            "ieee": {
                "content_types": ["Journals", "Conferences"]
            },
            "rate_limits": {
                "ieee": {
                    "calls_per_second": 10,
                    "calls_per_day": 200
                }
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
