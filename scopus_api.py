"""
Scopus API Client - Usando la API oficial de Elsevier
Documentación: https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl

Para usar:
1. Setea tu API key: $Env:SCOPUS_API_KEY = "tu_api_key"
2. Configura scopus_input.json con tus keywords y filtros
3. Ejecuta:
   - Modo sencillo (conteo desde JSON): python scopus_api.py --sencilla
   - Modo extendido (resultados detallados): python scopus_api.py --extendida
   - Sin parámetro: te pregunta qué modo usar
"""

import argparse
import itertools
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict

# Archivo de configuración de entrada
INPUT_FILE = "scopus_input.json"
LOG_DIR = "logs"

# Endpoints de la API de Scopus
BASE_URL = "https://api.elsevier.com/content"
SEARCH_URL = f"{BASE_URL}/search/scopus"
ABSTRACT_URL = f"{BASE_URL}/abstract/scopus_id"

# Variable global para el archivo de log
log_file_handle = None


def init_log_file(mode: str) -> str:
    """Inicializa el archivo de log con timestamp."""
    global log_file_handle
    
    # Crear directorio de logs si no existe
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # Generar nombre con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{LOG_DIR}/scopus_{mode}_{timestamp}.log"
    
    log_file_handle = open(log_filename, "w", encoding="utf-8")
    
    # Escribir cabecera
    write_log(f"=" * 80)
    write_log(f"SCOPUS API LOG - Modo: {mode}")
    write_log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    write_log(f"=" * 80)
    
    return log_filename


def write_log(message: str) -> None:
    """Escribe mensaje tanto a consola como al archivo de log."""
    print(message)
    if log_file_handle:
        log_file_handle.write(message + "\n")
        log_file_handle.flush()


def close_log_file() -> None:
    """Cierra el archivo de log."""
    global log_file_handle
    if log_file_handle:
        log_file_handle.close()
        log_file_handle = None


def log(title: str) -> None:
    msg1 = f"\n{'='*80}"
    msg2 = f"  {title}"
    msg3 = '='*80
    write_log(msg1)
    write_log(msg2)
    write_log(msg3)


def get_api_key() -> str:
    """Obtiene la API key desde variable de entorno."""
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        print("ERROR: No se encontró SCOPUS_API_KEY")
        print("Configúrala con: $Env:SCOPUS_API_KEY = 'tu_api_key'")
        sys.exit(1)
    return api_key


def build_headers(api_key: str) -> Dict[str, str]:
    """Construye los headers necesarios para la API."""
    return {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json",
        "User-Agent": "Python-Scopus-Client/1.0",
    }


def make_request(url: str, headers: Dict[str, str], verbose: bool = True) -> Dict[str, Any]:
    """Realiza un request GET y retorna el JSON parseado."""
    if verbose:
        log("REQUEST")
        print(f"URL: {url}")
        print(f"Headers:")
        for k, v in headers.items():
            if k == "X-ELS-APIKey":
                print(f"  {k}: {v[:8]}...{v[-4:]}")
            else:
                print(f"  {k}: {v}")

    req = urllib.request.Request(url=url, headers=headers, method="GET")
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.time() - start
            
            if verbose:
                log("RESPONSE")
                print(f"Status: {resp.status} {resp.reason}")
                print(f"Elapsed: {elapsed:.2f}s")
                
                print(f"\nHeaders relevantes:")
                for h in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
                    val = resp.headers.get(h)
                    if val:
                        print(f"  {h}: {val}")
            
            data = resp.read().decode("utf-8")
            return json.loads(data)
            
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        if verbose:
            log("ERROR")
        print(f"HTTP Error: {e.code} {e.reason}")
        print(f"Elapsed: {elapsed:.2f}s")
        try:
            error_body = e.read().decode("utf-8")
            print(f"Response: {error_body[:500]}")
        except:
            pass
        return {"error": str(e)}
    except Exception as e:
        print(f"Request failed: {e}")
        return {"error": str(e)}


def build_full_query(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    doc_types: list[str] | None = None,
    subject_areas: list[str] | None = None,
) -> str:
    """Construye la query completa con todos los filtros."""
    full_query = query
    
    if year_from and year_to:
        full_query = f"({query}) AND PUBYEAR > {year_from - 1} AND PUBYEAR < {year_to + 1}"
    elif year_from:
        full_query = f"({query}) AND PUBYEAR > {year_from - 1}"
    elif year_to:
        full_query = f"({query}) AND PUBYEAR < {year_to + 1}"
    
    # Múltiples tipos de documento con OR
    if doc_types and len(doc_types) > 0:
        doc_filter = " OR ".join([f"DOCTYPE({dt.strip()})" for dt in doc_types])
        full_query = f"({full_query}) AND ({doc_filter})"
    
    # Múltiples áreas temáticas con OR
    if subject_areas and len(subject_areas) > 0:
        area_filter = " OR ".join([f"SUBJAREA({sa.strip()})" for sa in subject_areas])
        full_query = f"({full_query}) AND ({area_filter})"
    
    return full_query


def search_scopus(
    query: str,
    api_key: str,
    count: int = 5,
    start: int = 0,
    year_from: int | None = None,
    year_to: int | None = None,
    doc_types: list[str] | None = None,
    subject_areas: list[str] | None = None,
    sort: str = "-citedby-count",
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Busca artículos en Scopus.
    
    Args:
        query: Query de búsqueda (ej: "machine learning AND healthcare")
        api_key: API key de Elsevier
        count: Número de resultados por página (máx 25)
        start: Índice de inicio para paginación (0, 25, 50, ...)
        year_from: Año de publicación mínimo (ej: 2020)
        year_to: Año de publicación máximo (ej: 2024)
        doc_types: Lista de tipos de documento (ar, re, cp, ch, bk)
        subject_areas: Lista de áreas temáticas (COMP, MEDI, ENGI, SOCI)
        sort: Ordenamiento (-citedby-count, -pubyear, +pubyear, -relevancy)
        verbose: Si True, imprime la query construida
    
    Tipos de documento:
        ar = Article
        re = Review
        cp = Conference Paper
        ch = Book Chapter
        bk = Book
        ed = Editorial
        le = Letter
        no = Note
        sh = Short Survey
    
    Áreas temáticas:
        COMP = Computer Science
        MEDI = Medicine
        ENGI = Engineering
        SOCI = Social Sciences
        BUSI = Business
        MATH = Mathematics
        PHYS = Physics
        CHEM = Chemistry
        BIOC = Biochemistry
        ARTS = Arts and Humanities
    
    Límites de la API:
        - Máximo 25 resultados por request (count)
        - Máximo 5000 resultados totales por búsqueda
        - Rate limit: ~2-9 requests/segundo según tipo de key
        - Usar paginación con 'start' para obtener más resultados
    """
    full_query = build_full_query(query, year_from, year_to, doc_types, subject_areas)
    
    if verbose:
        log("QUERY CONSTRUIDA")
        print(f"Query original: {query}")
        print(f"Query final: {full_query}")
    
    params = {
        "query": full_query,
        "count": str(min(count, 25)),  # Máximo 25 por request
        "start": str(start),
        "view": "STANDARD",
        "sort": sort,
    }
    
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
    headers = build_headers(api_key)
    
    return make_request(url, headers, verbose=verbose)


def count_results(
    query: str,
    api_key: str,
    year_from: int | None = None,
    year_to: int | None = None,
    doc_types: list[str] | None = None,
    subject_areas: list[str] | None = None,
) -> int:
    """
    Solo cuenta el total de resultados sin descargar los datos.
    Hace un request con count=1 para obtener opensearch:totalResults.
    """
    full_query = build_full_query(query, year_from, year_to, doc_types, subject_areas)
    
    params = {
        "query": full_query,
        "count": "1",
        "start": "0",
        "view": "STANDARD",
    }
    
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"
    headers = build_headers(api_key)
    
    response = make_request(url, headers, verbose=False)
    
    if "error" in response:
        return -1
    
    search_results = response.get("search-results", {})
    total = int(search_results.get("opensearch:totalResults", 0))
    return total


def search_all_results(
    query: str,
    api_key: str,
    year_from: int | None = None,
    year_to: int | None = None,
    doc_types: list[str] | None = None,
    subject_areas: list[str] | None = None,
    sort: str = "-citedby-count",
    max_results: int = 5000,
) -> list[Dict[str, Any]]:
    """
    Busca TODOS los resultados usando paginación automática.
    
    Args:
        max_results: Límite máximo de resultados a obtener (máx 5000)
    
    Returns:
        Lista con todos los entries encontrados
    """
    all_entries = []
    start = 0
    page_size = 25
    total_results = None
    
    log("BÚSQUEDA CON PAGINACIÓN")
    full_query = build_full_query(query, year_from, year_to, doc_types, subject_areas)
    print(f"Query: {full_query}")
    print(f"Máximo de resultados a obtener: {min(max_results, 5000)}")
    
    while True:
        print(f"\n--- Página {start // page_size + 1} (start={start}) ---")
        
        response = search_scopus(
            query=query,
            api_key=api_key,
            count=page_size,
            start=start,
            year_from=year_from,
            year_to=year_to,
            doc_types=doc_types,
            subject_areas=subject_areas,
            sort=sort,
            verbose=False,
        )
        
        search_results = response.get("search-results", {})
        
        # Obtener total en la primera iteración
        if total_results is None:
            total_results = int(search_results.get("opensearch:totalResults", 0))
            print(f"Total de resultados disponibles: {total_results}")
            if total_results > 5000:
                print(f"NOTA: Solo se pueden obtener hasta 5000 resultados (API limit)")
        
        entries = search_results.get("entry", [])
        
        # Verificar si hay error o no hay más resultados
        if not entries or (len(entries) == 1 and "error" in entries[0]):
            print("No hay más resultados.")
            break
        
        all_entries.extend(entries)
        print(f"Obtenidos: {len(entries)} | Acumulado: {len(all_entries)}")
        
        # Verificar límites
        if len(all_entries) >= min(total_results, max_results, 5000):
            print("\nLímite alcanzado.")
            break
        
        start += page_size
        
        # Pequeña pausa para no saturar la API
        time.sleep(0.3)
    
    log("PAGINACIÓN COMPLETADA")
    print(f"Total de resultados obtenidos: {len(all_entries)}")
    
    return all_entries


def print_search_results(response: Dict[str, Any]) -> None:
    """Imprime los resultados de búsqueda de forma legible."""
    log("RESULTADOS DE BÚSQUEDA")
    
    search_results = response.get("search-results", {})
    total = search_results.get("opensearch:totalResults", "0")
    print(f"Total de resultados: {total}")
    
    entries = search_results.get("entry", [])
    
    if not entries:
        print("No se encontraron resultados.")
        return
    
    print(f"Mostrando {len(entries)} resultados:\n")
    
    for i, entry in enumerate(entries, 1):
        print(f"--- Resultado {i} ---")
        print(f"Título: {entry.get('dc:title', 'N/A')}")
        print(f"Autores: {entry.get('dc:creator', 'N/A')}")
        print(f"Revista: {entry.get('prism:publicationName', 'N/A')}")
        print(f"Fecha: {entry.get('prism:coverDate', 'N/A')}")
        print(f"DOI: {entry.get('prism:doi', 'N/A')}")
        print(f"Citaciones: {entry.get('citedby-count', 'N/A')}")
        
        # Scopus ID para obtener más detalles
        scopus_id = entry.get("dc:identifier", "").replace("SCOPUS_ID:", "")
        if scopus_id:
            print(f"Scopus ID: {scopus_id}")
        print()


def get_filters_input() -> tuple:
    """Solicita los filtros al usuario."""
    print("\n--- Filtros opcionales (Enter para omitir) ---")
    
    year_from_str = input("Año desde (ej: 2020): ").strip()
    year_from = int(year_from_str) if year_from_str.isdigit() else None
    
    year_to_str = input("Año hasta (ej: 2025): ").strip()
    year_to = int(year_to_str) if year_to_str.isdigit() else None
    
    print("\nTipos de documento: ar=Article, re=Review, cp=Conference Paper, ch=Chapter, bk=Book")
    doc_types_str = input("Tipos separados por coma (ej: ar,cp,ch) o Enter para todos: ").strip()
    doc_types = [dt.strip() for dt in doc_types_str.split(",") if dt.strip()] if doc_types_str else None
    
    print("\nÁreas temáticas disponibles:")
    print("  COMP=Computer Science, MEDI=Medicine, ENGI=Engineering, SOCI=Social Sciences")
    print("  BUSI=Business, MATH=Mathematics, PHYS=Physics, CHEM=Chemistry")
    print("  BIOC=Biochemistry, ARTS=Arts and Humanities")
    areas_str = input("Áreas separadas por coma (ej: COMP,MEDI,ENGI) o Enter para todas: ").strip()
    subject_areas = [a.strip().upper() for a in areas_str.split(",") if a.strip()] if areas_str else None
    
    return year_from, year_to, doc_types, subject_areas


def load_input_config() -> Dict[str, Any]:
    """Carga la configuración desde el archivo JSON de entrada."""
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: No se encontró el archivo {INPUT_FILE}")
        print("Creando archivo de ejemplo...")
        example = {
            "keywords": ["ejemplo1", "ejemplo2"],
            "doc_types": [],
            "subject_areas": [],
            "year_from": None,
            "year_to": None
        }
        with open(INPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(example, f, indent=2, ensure_ascii=False)
        print(f"Archivo {INPUT_FILE} creado. Edítalo y vuelve a ejecutar.")
        sys.exit(1)
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return config


def run_simple_mode(api_key: str) -> int:
    """Modo SENCILLO: Lee desde JSON, cuenta por keyword y combinaciones de 3."""
    
    # Inicializar archivo de log
    log_filename = init_log_file("sencilla")
    write_log(f"Archivo de log: {log_filename}")
    
    log("MODO SENCILLO - Solo conteo de publicaciones")
    
    # Cargar configuración desde JSON
    config = load_input_config()
    
    keywords = config.get("keywords", [])
    doc_types = config.get("doc_types", []) or None
    subject_areas = config.get("subject_areas", []) or None
    year_from = config.get("year_from")
    year_to = config.get("year_to")
    
    if not keywords:
        write_log("ERROR: No hay keywords en el archivo scopus_input.json")
        close_log_file()
        return 1
    
    # Convertir listas vacías a None para los filtros
    if doc_types and len(doc_types) == 0:
        doc_types = None
    if subject_areas and len(subject_areas) == 0:
        subject_areas = None
    
    # Mostrar configuración
    log("CONFIGURACIÓN CARGADA")
    write_log(f"Archivo: {INPUT_FILE}")
    write_log(f"Keywords: {len(keywords)}")
    for i, kw in enumerate(keywords, 1):
        write_log(f"  {i}. {kw}")
    write_log(f"\nFiltros:")
    write_log(f"  Años: {year_from or 'Sin límite'} - {year_to or 'Sin límite'}")
    write_log(f"  Tipos de documento: {', '.join(doc_types) if doc_types else 'Todos'}")
    write_log(f"  Áreas temáticas: {', '.join(subject_areas) if subject_areas else 'Todas'}")
    
    # =========================================
    # PARTE 1: Conteo individual por keyword
    # =========================================
    log("RESULTADOS INDIVIDUALES")
    write_log(f"{'Keyword':<50} | {'Publicaciones':>15}")
    write_log("-" * 70)
    
    individual_results = []
    total_individual = 0
    
    for keyword in keywords:
        # Query que se envía a Scopus
        query_sent = f'"{keyword}"'
        
        count = count_results(
            query=query_sent,
            api_key=api_key,
            year_from=year_from,
            year_to=year_to,
            doc_types=doc_types,
            subject_areas=subject_areas,
        )
        
        if count == -1:
            write_log(f"{keyword:<50} | {'ERROR':>15}")
            individual_results.append({"keyword": keyword, "query": query_sent, "count": None, "error": True})
        else:
            write_log(f"{keyword:<50} | {count:>15,}")
            individual_results.append({"keyword": keyword, "query": query_sent, "count": count})
            total_individual += count
        
        time.sleep(0.25)
    
    write_log("-" * 70)
    write_log(f"{'TOTAL INDIVIDUAL (suma)':<50} | {total_individual:>15,}")
    
    # =========================================
    # PARTE 2: Combinaciones de 3 en 3 (ternas)
    # =========================================
    if len(keywords) >= 3:
        log("COMBINACIONES DE 3 KEYWORDS (TERNAS)")
        
        # Generar todas las combinaciones de 3
        combinations = list(itertools.combinations(keywords, 3))
        write_log(f"Total de combinaciones posibles: {len(combinations)}")
        write_log("")
        
        combination_results = []
        total_combinations = 0
        
        for idx, combo in enumerate(combinations, 1):
            # Construir query combinada con AND - ESTO ES LO QUE SE ENVÍA A SCOPUS
            query = f'"{combo[0]}" AND "{combo[1]}" AND "{combo[2]}"'
            
            count = count_results(
                query=query,
                api_key=api_key,
                year_from=year_from,
                year_to=year_to,
                doc_types=doc_types,
                subject_areas=subject_areas,
            )
            
            # Mostrar palabras COMPLETAS
            display_keywords = f"[{combo[0]}] AND [{combo[1]}] AND [{combo[2]}]"
            
            if count == -1:
                write_log(f"\n{idx:3}. ERROR")
                write_log(f"     Keywords: {display_keywords}")
                write_log(f"     Query enviada: {query}")
                combination_results.append({
                    "keywords": list(combo),
                    "query": query,
                    "count": None,
                    "error": True
                })
            else:
                write_log(f"\n{idx:3}. Resultados: {count:,}")
                write_log(f"     Keywords: {display_keywords}")
                write_log(f"     Query enviada: {query}")
                combination_results.append({
                    "keywords": list(combo),
                    "query": query,
                    "count": count
                })
                total_combinations += count
            
            time.sleep(0.25)
        
        log("RESUMEN DE COMBINACIONES")
        write_log(f"Total de combinaciones: {len(combinations)}")
        write_log(f"Suma de resultados: {total_combinations:,}")
        
        # Filtrar combinaciones con resultados > 0
        combos_with_results = [c for c in combination_results if c.get("count", 0) and c["count"] > 0]
        write_log(f"Combinaciones con al menos 1 resultado: {len(combos_with_results)}")
        
        if combos_with_results:
            # Ordenar por count descendente
            combos_with_results.sort(key=lambda x: x["count"], reverse=True)
            
            log("TOP 30 COMBINACIONES CON MÁS RESULTADOS")
            write_log("")
            write_log(f"{'#':<4} | {'Resultados':>12} | {'Keyword 1':<25} | {'Keyword 2':<25} | {'Keyword 3':<25}")
            write_log("-" * 100)
            
            for i, c in enumerate(combos_with_results[:30], 1):
                k1 = c['keywords'][0][:24] if len(c['keywords'][0]) > 24 else c['keywords'][0]
                k2 = c['keywords'][1][:24] if len(c['keywords'][1]) > 24 else c['keywords'][1]
                k3 = c['keywords'][2][:24] if len(c['keywords'][2]) > 24 else c['keywords'][2]
                write_log(f"{i:<4} | {c['count']:>12,} | {k1:<25} | {k2:<25} | {k3:<25}")
            
            write_log("-" * 100)
            write_log("")
            write_log("Detalle de queries enviadas a Scopus:")
            for i, c in enumerate(combos_with_results[:30], 1):
                write_log(f"  {i:2}. {c['query']}")
    else:
        combination_results = []
        total_combinations = 0
        write_log("\nNOTA: Se necesitan al menos 3 keywords para generar combinaciones.")
    
    # =========================================
    # Guardar resultados
    # =========================================
    output_file = "scopus_counts.json"
    output_data = {
        "mode": "sencilla",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_file": INPUT_FILE,
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "doc_types": doc_types,
            "subject_areas": subject_areas,
        },
        "individual_results": {
            "keywords": individual_results,
            "total": total_individual,
        },
        "combination_results": {
            "combination_size": 3,
            "total_combinations": len(combination_results) if keywords and len(keywords) >= 3 else 0,
            "combinations": combination_results,
            "total": total_combinations,
        },
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    log("RESUMEN FINAL")
    write_log(f"Keywords analizados: {len(keywords)}")
    write_log(f"Total individual: {total_individual:,}")
    if len(keywords) >= 3:
        write_log(f"Combinaciones (ternas): {len(combination_results)}")
        write_log(f"Total combinaciones: {total_combinations:,}")
    write_log(f"\nResultados guardados en: {output_file}")
    write_log(f"Log guardado en: {log_filename}")
    
    close_log_file()
    
    return 0


def run_extended_mode(api_key: str) -> int:
    """Modo EXTENDIDO: Búsqueda detallada con resultados completos."""
    log("MODO EXTENDIDO - Resultados detallados")
    
    query = input("\nIngresa tu búsqueda (ej: 'machine learning AND healthcare'): ").strip()
    
    if not query:
        query = "machine learning AND systematic review"
        print(f"Usando query por defecto: {query}")
    
    # Obtener filtros
    year_from, year_to, doc_types, subject_areas = get_filters_input()
    
    # Modo de búsqueda
    print("\n--- Modo de búsqueda ---")
    print("1. Búsqueda simple (hasta 25 resultados)")
    print("2. Obtener TODOS los resultados (con paginación automática, máx 5000)")
    mode = input("Selecciona modo (1 o 2, default 1): ").strip()
    
    if mode == "2":
        # Paginación automática
        max_str = input("Máximo de resultados a obtener (default 100, máx 5000): ").strip()
        max_results = int(max_str) if max_str.isdigit() else 100
        
        all_entries = search_all_results(
            query=query,
            api_key=api_key,
            year_from=year_from,
            year_to=year_to,
            doc_types=doc_types,
            subject_areas=subject_areas,
            max_results=max_results,
        )
        
        # Mostrar resumen
        log("RESUMEN DE RESULTADOS")
        print(f"Total obtenido: {len(all_entries)} artículos")
        
        if all_entries:
            print("\nPrimeros 5 resultados:")
            for i, entry in enumerate(all_entries[:5], 1):
                print(f"  {i}. {entry.get('dc:title', 'N/A')[:80]}...")
        
        # Guardar todos los resultados
        output_file = "scopus_results.json"
        output_data = {
            "query": query,
            "filters": {
                "year_from": year_from,
                "year_to": year_to,
                "doc_types": doc_types,
                "subject_areas": subject_areas,
            },
            "total_results": len(all_entries),
            "entries": all_entries,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nTodos los resultados guardados en: {output_file}")
        
    else:
        # Búsqueda simple
        count_str = input("Número de resultados (máx 25, default 10): ").strip()
        count = int(count_str) if count_str.isdigit() else 10
        
        response = search_scopus(
            query=query,
            api_key=api_key,
            count=count,
            year_from=year_from,
            year_to=year_to,
            doc_types=doc_types,
            subject_areas=subject_areas,
        )
        
        # Mostrar resultados
        print_search_results(response)
        
        # Guardar respuesta
        output_file = "scopus_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        print(f"\nRespuesta guardada en: {output_file}")
    
    return 0


def main() -> int:
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description="Scopus API Client - Busca publicaciones en Scopus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scopus_api.py --sencilla    # Solo conteo de múltiples términos
  python scopus_api.py --extendida   # Resultados detallados
  python scopus_api.py               # Te pregunta qué modo usar
"""
    )
    parser.add_argument(
        "--sencilla", "-s",
        action="store_true",
        help="Modo sencillo: solo cuenta publicaciones para múltiples términos independientes"
    )
    parser.add_argument(
        "--extendida", "-e",
        action="store_true",
        help="Modo extendido: búsqueda detallada con resultados completos"
    )
    
    args = parser.parse_args()
    
    log("SCOPUS API CLIENT")
    
    # Obtener API key
    api_key = get_api_key()
    print(f"API Key configurada: {api_key[:8]}...{api_key[-4:]}")
    
    # Determinar modo
    if args.sencilla:
        return run_simple_mode(api_key)
    elif args.extendida:
        return run_extended_mode(api_key)
    else:
        # Preguntar al usuario
        print("\n--- Selecciona el modo de operación ---")
        print("1. SENCILLA: Solo conteo de publicaciones (múltiples términos independientes)")
        print("2. EXTENDIDA: Búsqueda detallada con resultados completos")
        
        mode = input("\nSelecciona modo (1 o 2): ").strip()
        
        if mode == "1":
            return run_simple_mode(api_key)
        else:
            return run_extended_mode(api_key)


if __name__ == "__main__":
    sys.exit(main())
