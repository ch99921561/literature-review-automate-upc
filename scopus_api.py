"""
Scopus API Client - Usando la API oficial de Elsevier
Documentación: https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl

Para usar:
1. Setea tu API key: $Env:SCOPUS_API_KEY = "tu_api_key"
2. Ejecuta:
   - Modo sencillo (solo conteo): python scopus_api.py --sencilla
   - Modo extendido (resultados detallados): python scopus_api.py --extendida
   - Sin parámetro: te pregunta qué modo usar
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict

# Endpoints de la API de Scopus
BASE_URL = "https://api.elsevier.com/content"
SEARCH_URL = f"{BASE_URL}/search/scopus"
ABSTRACT_URL = f"{BASE_URL}/abstract/scopus_id"


def log(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


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


def run_simple_mode(api_key: str) -> int:
    """Modo SENCILLO: Solo cuenta publicaciones para múltiples términos independientes."""
    log("MODO SENCILLO - Solo conteo de publicaciones")
    
    print("\nIngresa los términos de búsqueda separados por coma.")
    print("Cada término se buscará de forma INDEPENDIENTE.")
    print("Ejemplo: machine learning, deep learning, neural networks")
    
    terms_input = input("\nTérminos de búsqueda: ").strip()
    
    if not terms_input:
        print("ERROR: Debes ingresar al menos un término.")
        return 1
    
    # Separar términos por coma
    terms = [t.strip() for t in terms_input.split(",") if t.strip()]
    
    print(f"\nSe buscarán {len(terms)} términos independientes.")
    
    # Obtener filtros
    year_from, year_to, doc_types, subject_areas = get_filters_input()
    
    # Mostrar filtros aplicados
    log("FILTROS APLICADOS")
    print(f"Años: {year_from or 'Sin límite'} - {year_to or 'Sin límite'}")
    print(f"Tipos de documento: {', '.join(doc_types) if doc_types else 'Todos'}")
    print(f"Áreas temáticas: {', '.join(subject_areas) if subject_areas else 'Todas'}")
    
    # Buscar cada término
    log("RESULTADOS DE CONTEO")
    print(f"{'Término':<50} | {'Publicaciones':>15}")
    print("-" * 70)
    
    results = []
    total_all = 0
    
    for term in terms:
        count = count_results(
            query=term,
            api_key=api_key,
            year_from=year_from,
            year_to=year_to,
            doc_types=doc_types,
            subject_areas=subject_areas,
        )
        
        if count == -1:
            print(f"{term:<50} | {'ERROR':>15}")
            results.append({"term": term, "count": None, "error": True})
        else:
            print(f"{term:<50} | {count:>15,}")
            results.append({"term": term, "count": count})
            total_all += count
        
        # Pequeña pausa entre requests
        time.sleep(0.2)
    
    print("-" * 70)
    print(f"{'TOTAL (suma)':<50} | {total_all:>15,}")
    
    # Guardar resultados
    output_file = "scopus_counts.json"
    output_data = {
        "mode": "sencilla",
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "doc_types": doc_types,
            "subject_areas": subject_areas,
        },
        "terms": results,
        "total_sum": total_all,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"\nResultados guardados en: {output_file}")
    
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
