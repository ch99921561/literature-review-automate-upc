# -*- coding: utf-8 -*-
"""
search_engine.py - Motor de búsqueda para Literature Review
"""

import os
import itertools
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json

from .config import (
    APIType, API_CONFIGS, OUTPUTS_DIR, CONSOLIDATED_OUTPUT_PREFIX
)
from .models import (
    SearchFilters, ScopusFilters, IEEEFilters, WOSFilters,
    SearchResult, CombinationResult
)
from .logger import logger
from .base_client import BaseAPIClient
from .input_config import InputConfig


class SearchEngine:
    """Motor de búsqueda que coordina múltiples clientes de APIs."""
    
    def __init__(self):
        self.clients: Dict[APIType, BaseAPIClient] = {}
        self.config: Optional[InputConfig] = None
    
    def register_client(self, api_type: APIType, client: BaseAPIClient) -> bool:
        """Registra un cliente de API si está autenticado correctamente."""
        if client.authenticate():
            self.clients[api_type] = client
            print(f"  ✓ {client.get_api_name()} autenticado correctamente")
            return True
        else:
            print(f"  ✗ {client.get_api_name()} no autenticado (API_KEY no configurada)")
            return False
    
    def load_config(self) -> bool:
        """Carga la configuración desde el archivo de entrada."""
        self.config = InputConfig.load()
        return self.config is not None
    
    def run_simple_mode(self, api_type: APIType) -> Tuple[int, List[CombinationResult]]:
        """
        Ejecuta el modo sencillo (conteo de publicaciones).
        
        Returns:
            Tupla (código_retorno, lista_combinaciones)
        """
        if api_type not in self.clients:
            logger.write(f"ERROR: Cliente {api_type.value} no registrado")
            return (1, [])
        
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
        return (0, combination_results)
    
    def _get_filters_for_api(self, api_type: APIType) -> SearchFilters:
        """Obtiene los filtros específicos para una API."""
        if api_type == APIType.SCOPUS:
            return self.config.scopus
        elif api_type == APIType.IEEE:
            return self.config.ieee
        elif api_type == APIType.WOS:
            return self.config.wos
        return SearchFilters(year_from=self.config.year_from, year_to=self.config.year_to)
    
    def _print_config(self, api_type: APIType, filters: SearchFilters) -> None:
        """Imprime la configuración cargada."""
        logger.header("CONFIGURACIÓN CARGADA")
        logger.write(f"Archivo: definitions/input.json")
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
        elif isinstance(filters, WOSFilters):
            logger.write(f"  Base de datos: {filters.database}")
            logger.write(f"  Edición: {filters.edition or 'Todas'}")
            logger.write(f"  Tipos de documento: {', '.join(filters.document_types) if filters.document_types else 'Todos'}")
    
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
        self._print_combination_summary(results, total, client, filters)
        
        return results
    
    def _print_combination_summary(self, results: List[CombinationResult], total: int,
                                   client: BaseAPIClient = None, 
                                   filters: SearchFilters = None) -> None:
        """Imprime el resumen de combinaciones."""
        logger.header("RESUMEN DE COMBINACIONES")
        logger.write(f"Total de combinaciones: {len(results)}")
        logger.write(f"Suma de resultados: {total:,}")
        
        # Filtrar combinaciones con resultados > 0
        with_results = [r for r in results if r.count and r.count > 0]
        logger.write(f"Combinaciones con al menos 1 resultado: {len(with_results)}")
        
        if with_results:
            with_results.sort(key=lambda x: x.count or 0, reverse=True)
            
            # Obtener documentos para el TOP 30 si tenemos cliente y filtros
            top_30 = with_results[:30]
            if client and filters:
                logger.write("")
                logger.write("Obteniendo títulos de documentos para el TOP 30...")
                for idx, r in enumerate(top_30, 1):
                    titles = client.get_document_titles(r.query, filters, max_docs=200)
                    r.documents = titles
                    logger.write(f"  Llave {idx}: {len(titles)} documentos obtenidos")
                    time.sleep(0.25)
            
            logger.header("TOP 30 COMBINACIONES CON MÁS RESULTADOS")
            logger.write("")
            logger.write(f"{'Llave':<6} | {'Resultados':>12} | {'Keyword 1':<25} | {'Keyword 2':<25} | {'Keyword 3':<25}")
            logger.write("-" * 102)
            
            for i, r in enumerate(top_30, 1):
                k1 = r.keywords[0][:24] if len(r.keywords[0]) > 24 else r.keywords[0]
                k2 = r.keywords[1][:24] if len(r.keywords[1]) > 24 else r.keywords[1]
                k3 = r.keywords[2][:24] if len(r.keywords[2]) > 24 else r.keywords[2]
                logger.write(f"{i:<6} | {r.count:>12,} | {k1:<25} | {k2:<25} | {k3:<25}")
            
            logger.write("-" * 102)
            logger.write("")
            logger.write("Detalle de queries enviadas:")
            for i, r in enumerate(top_30, 1):
                logger.write(f"  {i:2}. {r.query}")
            
            # Tabla: DOCUMENTOS POR LLAVE
            if any(r.documents for r in top_30):
                logger.header("DOCUMENTOS ENCONTRADOS POR LLAVE (TOP 30)")
                logger.write("")
                for i, r in enumerate(top_30, 1):
                    logger.write(f"{'='*80}")
                    logger.write(f"LLAVE {i} - {len(r.documents)} documento(s)")
                    logger.write(f"Keywords: {' AND '.join(r.keywords)}")
                    logger.write(f"{'='*80}")
                    if r.documents:
                        for doc_idx, title in enumerate(r.documents, 1):
                            display_title = title[:120] + "..." if len(title) > 120 else title
                            logger.write(f"  {doc_idx:3}. {display_title}")
                    else:
                        logger.write("  (Sin documentos recuperados)")
                    logger.write("")
    
    def _build_documents_by_key(self, combinations: List[CombinationResult]) -> List[Dict[str, Any]]:
        """Construye la tabla de documentos por llave (TOP 30)."""
        with_results = [r for r in combinations if r.count and r.count > 0]
        with_results.sort(key=lambda x: x.count or 0, reverse=True)
        
        documents_table = []
        for i, r in enumerate(with_results[:30], 1):
            documents_table.append({
                "llave": i,
                "keywords": r.keywords,
                "query": r.query,
                "count": r.count,
                "documentos": r.documents
            })
        
        return documents_table
    
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
            "input_file": "definitions/input.json",
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
                    {"keywords": r.keywords, "query": r.query, "count": r.count, "error": r.error, "documents": r.documents}
                    for r in combinations
                ],
                "total": total_combinations,
            },
            "documents_by_key": self._build_documents_by_key(combinations),
        }
        
        # Agregar filtros específicos
        if isinstance(filters, ScopusFilters):
            output_data["filters"]["doc_types"] = filters.doc_types
            output_data["filters"]["subject_areas"] = filters.subject_areas
        elif isinstance(filters, IEEEFilters):
            output_data["filters"]["content_types"] = filters.content_types
        
        # Guardar en carpeta outputs (la ruta ya incluye OUTPUTS_DIR)
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
    
    def save_consolidated_top30(self, all_results: Dict[APIType, List[CombinationResult]]) -> str:
        """
        Guarda un archivo consolidado con el TOP 30 en formato tabla de texto.
        
        Args:
            all_results: Diccionario {APIType: List[CombinationResult]} con resultados por API
        
        Returns:
            Nombre del archivo generado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(OUTPUTS_DIR, f"{CONSOLIDATED_OUTPUT_PREFIX}_{timestamp}.txt")
        
        # Determinar qué APIs fueron ejecutadas
        apis_executed = list(all_results.keys())
        apis_names = [api.value for api in apis_executed]
        
        lines = []
        lines.append("=" * 100)
        lines.append("  TOP 30 COMBINACIONES CON MÁS RESULTADOS - REPORTE CONSOLIDADO")
        lines.append("=" * 100)
        lines.append("")
        lines.append(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Archivo de entrada: definitions/input.json")
        lines.append(f"APIs ejecutadas: {', '.join(apis_names)}")
        lines.append(f"Keywords: {len(self.config.keywords)}")
        lines.append(f"Rango de años: {self.config.year_from or 'Sin límite'} - {self.config.year_to or 'Sin límite'}")
        lines.append("")
        
        # TOP 30 por cada API
        for api_type, combinations in all_results.items():
            api_name = api_type.value.upper()
            
            # Filtrar combinaciones con resultados > 0 y ordenar
            with_results = [r for r in combinations if r.count and r.count > 0]
            with_results.sort(key=lambda x: x.count or 0, reverse=True)
            
            lines.append("=" * 100)
            lines.append(f"  [{api_name}] TOP 30 COMBINACIONES")
            lines.append("=" * 100)
            lines.append("")
            lines.append(f"Total de combinaciones con resultados: {len(with_results)}")
            lines.append("")
            
            if with_results:
                # Encabezado de tabla
                lines.append(f"{'Rank':<6} | {'Resultados':>12} | {'Keyword 1':<28} | {'Keyword 2':<28} | {'Keyword 3':<28}")
                lines.append("-" * 110)
                
                # Datos TOP 30
                for i, r in enumerate(with_results[:30], 1):
                    k1 = r.keywords[0][:27] if len(r.keywords[0]) > 27 else r.keywords[0]
                    k2 = r.keywords[1][:27] if len(r.keywords[1]) > 27 else r.keywords[1]
                    k3 = r.keywords[2][:27] if len(r.keywords[2]) > 27 else r.keywords[2]
                    lines.append(f"{i:<6} | {r.count:>12,} | {k1:<28} | {k2:<28} | {k3:<28}")
                
                lines.append("-" * 110)
                lines.append("")
                
                # Queries enviadas
                lines.append("Queries enviadas:")
                for i, r in enumerate(with_results[:30], 1):
                    lines.append(f"  {i:2}. {r.query}")
                lines.append("")
                
                # Documentos por llave
                if any(r.documents for r in with_results[:30]):
                    lines.append("")
                    lines.append(f"{'='*100}")
                    lines.append(f"  [{api_name}] DOCUMENTOS POR LLAVE (TOP 30)")
                    lines.append(f"{'='*100}")
                    
                    for i, r in enumerate(with_results[:30], 1):
                        lines.append("")
                        lines.append(f"--- LLAVE {i} ({r.count:,} resultados) ---")
                        lines.append(f"Keywords: {' AND '.join(r.keywords)}")
                        if r.documents:
                            for doc_idx, title in enumerate(r.documents, 1):
                                display_title = title[:115] + "..." if len(title) > 115 else title
                                lines.append(f"  {doc_idx:3}. {display_title}")
                        else:
                            lines.append("  (Sin documentos recuperados)")
            else:
                lines.append("  (Sin combinaciones con resultados)")
            
            lines.append("")
        
        # Si hay múltiples APIs, agregar TOP 30 global
        if len(apis_executed) > 1:
            lines.append("=" * 100)
            lines.append("  TOP 30 GLOBAL (TODAS LAS APIs)")
            lines.append("=" * 100)
            lines.append("")
            
            # Combinar todos los resultados
            all_combinations = []
            for api_type, combinations in all_results.items():
                for r in combinations:
                    if r.count and r.count > 0:
                        all_combinations.append({
                            "api": api_type.value,
                            "keywords": r.keywords,
                            "count": r.count,
                            "query": r.query
                        })
            
            all_combinations.sort(key=lambda x: x["count"], reverse=True)
            
            lines.append(f"{'Rank':<6} | {'API':<8} | {'Resultados':>12} | {'Keyword 1':<25} | {'Keyword 2':<25} | {'Keyword 3':<25}")
            lines.append("-" * 115)
            
            for i, combo in enumerate(all_combinations[:30], 1):
                k1 = combo["keywords"][0][:24] if len(combo["keywords"][0]) > 24 else combo["keywords"][0]
                k2 = combo["keywords"][1][:24] if len(combo["keywords"][1]) > 24 else combo["keywords"][1]
                k3 = combo["keywords"][2][:24] if len(combo["keywords"][2]) > 24 else combo["keywords"][2]
                lines.append(f"{i:<6} | {combo['api']:<8} | {combo['count']:>12,} | {k1:<25} | {k2:<25} | {k3:<25}")
            
            lines.append("-" * 115)
            lines.append("")
        
        lines.append("=" * 100)
        lines.append("  FIN DEL REPORTE")
        lines.append("=" * 100)
        
        # Guardar archivo
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"\n{'='*80}")
        print(f"  ARCHIVO CONSOLIDADO GENERADO")
        print(f"{'='*80}")
        print(f"Archivo: {filename}")
        print(f"APIs incluidas: {', '.join(apis_names)}")
        
        # Mostrar resumen
        for api_type, combinations in all_results.items():
            with_results = [r for r in combinations if r.count and r.count > 0]
            with_results.sort(key=lambda x: x.count or 0, reverse=True)
            
            if with_results:
                print(f"\n[{api_type.value.upper()}] TOP 5 (de {len(with_results)} con resultados):")
                for i, r in enumerate(with_results[:5], 1):
                    keywords_str = " AND ".join(r.keywords)
                    print(f"  {i:2}. {r.count:,} resultados - {keywords_str}")
            else:
                print(f"\n[{api_type.value.upper()}] Sin combinaciones con resultados")
        
        return filename


def run_extended_mode(engine: SearchEngine) -> int:
    """Ejecuta el modo extendido interactivo."""
    print("\n--- Selecciona la API ---")
    print("1. Scopus")
    print("2. IEEE Xplore")
    print("3. Web of Science")
    
    api_choice = input("\nSelecciona API (1, 2 o 3): ").strip()
    
    if api_choice == "1":
        api_type = APIType.SCOPUS
    elif api_choice == "2":
        api_type = APIType.IEEE
    elif api_choice == "3":
        api_type = APIType.WOS
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
    elif api_type == APIType.IEEE:
        filters = IEEEFilters(year_from=year_from, year_to=year_to)
    elif api_type == APIType.WOS:
        filters = WOSFilters(year_from=year_from, year_to=year_to)
    else:
        filters = SearchFilters(year_from=year_from, year_to=year_to)
    
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
