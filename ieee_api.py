"""
IEEE Xplore API Client - Usando la API oficial de IEEE
Documentación: https://developer.ieee.org/docs

Para usar:
1. Setea tu API key: $Env:IEEE_API_KEY = "tu_api_key"
2. Configura ieee_input.json con tus keywords y filtros
3. Ejecuta:
   - Modo sencillo (conteo desde JSON): python ieee_api.py --sencilla
   - Modo extendido (resultados detallados): python ieee_api.py --extendida
   - Sin parámetro: te pregunta qué modo usar

Registra tu API key en: https://developer.ieee.org/member/register
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
INPUT_FILE = "ieee_input.json"
LOG_DIR = "logs"

# Endpoint de la API de IEEE Xplore
BASE_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"

# Tipos de contenido válidos (case sensitive)
VALID_CONTENT_TYPES = [
    "Books",
    "Conferences",
    "Courses",
    "Early Access",
    "Journals",
    "Magazines",
    "Standards",
]

# Publishers válidos
VALID_PUBLISHERS = [
    "Alcatel-Lucent", "AGU", "BIAI", "CSEE", "IBM", 
    "IEEE", "IET", "MITP", "Morgan & Claypool", "SMPTE", "TUP", "VDE"
]

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
    log_filename = f"{LOG_DIR}/ieee_{mode}_{timestamp}.log"
    
    log_file_handle = open(log_filename, "w", encoding="utf-8")
    
    # Escribir cabecera
    write_log(f"=" * 80)
    write_log(f"IEEE XPLORE API LOG - Modo: {mode}")
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
    api_key = os.getenv("IEEE_API_KEY")
    if not api_key:
        print("ERROR: No se encontró IEEE_API_KEY")
        print("Configúrala con: $Env:IEEE_API_KEY = 'tu_api_key'")
        print("Obtén tu API key en: https://developer.ieee.org/member/register")
        sys.exit(1)
    return api_key


def make_request(url: str, verbose: bool = True) -> Dict[str, Any]:
    """Realiza un request GET y retorna el JSON parseado."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "Python-IEEE-Client/1.0",
    }
    
    if verbose:
        log("REQUEST")
        # Ocultar API key en la URL para mostrar
        display_url = url
        if "apikey=" in url:
            parts = url.split("apikey=")
            if len(parts) > 1:
                key_part = parts[1].split("&")[0]
                display_url = url.replace(key_part, key_part[:8] + "..." + key_part[-4:] if len(key_part) > 12 else "***")
        print(f"URL: {display_url}")

    req = urllib.request.Request(url=url, headers=headers, method="GET")
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.time() - start
            
            if verbose:
                log("RESPONSE")
                print(f"Status: {resp.status} {resp.reason}")
                print(f"Elapsed: {elapsed:.2f}s")
            
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


def build_query_params(
    query: str,
    api_key: str,
    start_year: int | None = None,
    end_year: int | None = None,
    content_types: list[str] | None = None,
    max_records: int = 25,
    start_record: int = 1,
    sort_field: str | None = None,
    sort_order: str = "desc",
    open_access: bool | None = None,
) -> Dict[str, str]:
    """
    Construye los parámetros de la query para IEEE Xplore.
    
    Args:
        query: Query de búsqueda (usando querytext parameter)
        api_key: API key de IEEE
        start_year: Año de publicación mínimo
        end_year: Año de publicación máximo
        content_types: Lista de tipos de contenido (Journals, Conferences, etc.)
        max_records: Número de resultados (máx 200)
        start_record: Índice de inicio para paginación (1-based)
        sort_field: Campo de ordenamiento (article_number, article_title, publication_title)
        sort_order: asc o desc
        open_access: True para solo open access, None para todos
    
    Returns:
        Dict con los parámetros para la URL
    """
    params = {
        "apikey": api_key,
        "querytext": query,
        "max_records": str(min(max_records, 200)),
        "start_record": str(start_record),
    }
    
    if start_year:
        params["start_year"] = str(start_year)
    
    if end_year:
        params["end_year"] = str(end_year)
    
    # Content types (case sensitive)
    if content_types and len(content_types) > 0:
        # IEEE acepta múltiples content_type en la misma query
        params["content_type"] = content_types[0]  # Solo soporta uno a la vez
    
    if sort_field:
        params["sort_field"] = sort_field
        params["sort_order"] = sort_order
    
    if open_access is not None:
        params["open_access"] = str(open_access).lower()
    
    return params


def search_ieee(
    query: str,
    api_key: str,
    max_records: int = 25,
    start_record: int = 1,
    start_year: int | None = None,
    end_year: int | None = None,
    content_types: list[str] | None = None,
    sort_field: str | None = None,
    sort_order: str = "desc",
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Busca artículos en IEEE Xplore.
    
    Args:
        query: Query de búsqueda (ej: "machine learning AND healthcare")
        api_key: API key de IEEE
        max_records: Número de resultados por página (máx 200)
        start_record: Índice de inicio para paginación (1-based)
        start_year: Año de publicación mínimo
        end_year: Año de publicación máximo
        content_types: Lista de tipos de contenido
        sort_field: Campo de ordenamiento
        sort_order: asc o desc
        verbose: Si True, imprime detalles del request
    
    Content Types (case sensitive):
        - Books
        - Conferences
        - Courses
        - Early Access
        - Journals
        - Magazines
        - Standards
    
    Límites de la API:
        - Máximo 200 resultados por request
        - Rate limit según tipo de suscripción
        - Usar paginación con start_record para más resultados
    """
    params = build_query_params(
        query=query,
        api_key=api_key,
        start_year=start_year,
        end_year=end_year,
        content_types=content_types,
        max_records=max_records,
        start_record=start_record,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    
    if verbose:
        log("QUERY CONSTRUIDA")
        print(f"Query: {query}")
        if start_year or end_year:
            print(f"Años: {start_year or 'Sin límite'} - {end_year or 'Sin límite'}")
        if content_types:
            print(f"Content Types: {', '.join(content_types)}")
    
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    
    return make_request(url, verbose=verbose)


def count_results(
    query: str,
    api_key: str,
    start_year: int | None = None,
    end_year: int | None = None,
    content_types: list[str] | None = None,
) -> int:
    """
    Solo cuenta el total de resultados sin descargar todos los datos.
    Hace un request con max_records=1 para obtener total_records.
    """
    params = build_query_params(
        query=query,
        api_key=api_key,
        start_year=start_year,
        end_year=end_year,
        content_types=content_types,
        max_records=1,
        start_record=1,
    )
    
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    
    response = make_request(url, verbose=False)
    
    if "error" in response:
        return -1
    
    total = int(response.get("total_records", 0))
    return total


def search_all_results(
    query: str,
    api_key: str,
    start_year: int | None = None,
    end_year: int | None = None,
    content_types: list[str] | None = None,
    sort_field: str | None = None,
    sort_order: str = "desc",
    max_results: int = 1000,
) -> list[Dict[str, Any]]:
    """
    Busca TODOS los resultados usando paginación automática.
    
    Args:
        max_results: Límite máximo de resultados a obtener
    
    Returns:
        Lista con todos los articles encontrados
    """
    all_articles = []
    start_record = 1
    page_size = 200  # Máximo permitido por IEEE
    total_results = None
    
    log("BÚSQUEDA CON PAGINACIÓN")
    print(f"Query: {query}")
    print(f"Máximo de resultados a obtener: {max_results}")
    
    while True:
        print(f"\n--- Página {(start_record - 1) // page_size + 1} (start_record={start_record}) ---")
        
        response = search_ieee(
            query=query,
            api_key=api_key,
            max_records=page_size,
            start_record=start_record,
            start_year=start_year,
            end_year=end_year,
            content_types=content_types,
            sort_field=sort_field,
            sort_order=sort_order,
            verbose=False,
        )
        
        # Verificar error
        if "error" in response:
            print(f"Error en la búsqueda: {response['error']}")
            break
        
        # Obtener total en la primera iteración
        if total_results is None:
            total_results = int(response.get("total_records", 0))
            print(f"Total de resultados disponibles: {total_results}")
        
        articles = response.get("articles", [])
        
        # Verificar si no hay más resultados
        if not articles:
            print("No hay más resultados.")
            break
        
        all_articles.extend(articles)
        print(f"Obtenidos: {len(articles)} | Acumulado: {len(all_articles)}")
        
        # Verificar límites
        if len(all_articles) >= min(total_results, max_results):
            print("\nLímite alcanzado.")
            break
        
        start_record += page_size
        
        # Pequeña pausa para no saturar la API
        time.sleep(0.5)
    
    log("PAGINACIÓN COMPLETADA")
    print(f"Total de resultados obtenidos: {len(all_articles)}")
    
    return all_articles


def print_search_results(response: Dict[str, Any]) -> None:
    """Imprime los resultados de búsqueda de forma legible."""
    log("RESULTADOS DE BÚSQUEDA")
    
    total = response.get("total_records", 0)
    print(f"Total de resultados: {total}")
    
    articles = response.get("articles", [])
    
    if not articles:
        print("No se encontraron resultados.")
        return
    
    print(f"Mostrando {len(articles)} resultados:\n")
    
    for i, article in enumerate(articles, 1):
        print(f"--- Resultado {i} ---")
        print(f"Título: {article.get('title', 'N/A')}")
        
        # Autores
        authors = article.get('authors', {}).get('authors', [])
        if authors:
            author_names = [a.get('full_name', 'N/A') for a in authors[:3]]
            author_str = ', '.join(author_names)
            if len(authors) > 3:
                author_str += f" (+{len(authors) - 3} más)"
            print(f"Autores: {author_str}")
        
        print(f"Publicación: {article.get('publication_title', 'N/A')}")
        print(f"Año: {article.get('publication_year', 'N/A')}")
        print(f"DOI: {article.get('doi', 'N/A')}")
        print(f"Tipo: {article.get('content_type', 'N/A')}")
        print(f"Article Number: {article.get('article_number', 'N/A')}")
        
        # Abstract (truncado)
        abstract = article.get('abstract', '')
        if abstract:
            print(f"Abstract: {abstract[:200]}...")
        print()


def get_filters_input() -> tuple:
    """Solicita los filtros al usuario."""
    print("\n--- Filtros opcionales (Enter para omitir) ---")
    
    year_from_str = input("Año desde (ej: 2020): ").strip()
    start_year = int(year_from_str) if year_from_str.isdigit() else None
    
    year_to_str = input("Año hasta (ej: 2025): ").strip()
    end_year = int(year_to_str) if year_to_str.isdigit() else None
    
    print("\nTipos de contenido (case sensitive):")
    print("  Books, Conferences, Courses, Early Access, Journals, Magazines, Standards")
    content_type_str = input("Tipo de contenido (uno solo) o Enter para todos: ").strip()
    content_types = [content_type_str] if content_type_str else None
    
    return start_year, end_year, content_types


def load_input_config() -> Dict[str, Any]:
    """Carga la configuración desde el archivo JSON de entrada."""
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: No se encontró el archivo {INPUT_FILE}")
        print("Creando archivo de ejemplo...")
        example = {
            "keywords": ["ejemplo1", "ejemplo2"],
            "content_types": [],
            "start_year": None,
            "end_year": None
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
    content_types = config.get("content_types", []) or None
    start_year = config.get("start_year")
    end_year = config.get("end_year")
    
    if not keywords:
        write_log("ERROR: No hay keywords en el archivo ieee_input.json")
        close_log_file()
        return 1
    
    # Convertir listas vacías a None para los filtros
    if content_types and len(content_types) == 0:
        content_types = None
    
    # Mostrar configuración
    log("CONFIGURACIÓN CARGADA")
    write_log(f"Archivo: {INPUT_FILE}")
    write_log(f"Keywords: {len(keywords)}")
    for i, kw in enumerate(keywords, 1):
        write_log(f"  {i}. {kw}")
    write_log(f"\nFiltros:")
    write_log(f"  Años: {start_year or 'Sin límite'} - {end_year or 'Sin límite'}")
    write_log(f"  Tipos de contenido: {', '.join(content_types) if content_types else 'Todos'}")
    
    # =========================================
    # PARTE 1: Conteo individual por keyword
    # =========================================
    log("RESULTADOS INDIVIDUALES")
    write_log(f"{'Keyword':<50} | {'Publicaciones':>15}")
    write_log("-" * 70)
    
    individual_results = []
    total_individual = 0
    
    for keyword in keywords:
        # Query que se envía a IEEE - usando comillas para frase exacta
        query_sent = f'"{keyword}"'
        
        count = count_results(
            query=query_sent,
            api_key=api_key,
            start_year=start_year,
            end_year=end_year,
            content_types=content_types,
        )
        
        if count == -1:
            write_log(f"{keyword:<50} | {'ERROR':>15}")
            individual_results.append({"keyword": keyword, "query": query_sent, "count": None, "error": True})
        else:
            write_log(f"{keyword:<50} | {count:>15,}")
            individual_results.append({"keyword": keyword, "query": query_sent, "count": count})
            total_individual += count
        
        time.sleep(0.3)  # Rate limiting
    
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
            # Construir query combinada con AND - IEEE usa AND como operador booleano
            query = f'"{combo[0]}" AND "{combo[1]}" AND "{combo[2]}"'
            
            count = count_results(
                query=query,
                api_key=api_key,
                start_year=start_year,
                end_year=end_year,
                content_types=content_types,
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
            
            time.sleep(0.3)  # Rate limiting
        
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
            write_log("Detalle de queries enviadas a IEEE Xplore:")
            for i, c in enumerate(combos_with_results[:30], 1):
                write_log(f"  {i:2}. {c['query']}")
    else:
        combination_results = []
        total_combinations = 0
        write_log("\nNOTA: Se necesitan al menos 3 keywords para generar combinaciones.")
    
    # =========================================
    # Guardar resultados
    # =========================================
    output_file = "ieee_counts.json"
    output_data = {
        "mode": "sencilla",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_file": INPUT_FILE,
        "filters": {
            "start_year": start_year,
            "end_year": end_year,
            "content_types": content_types,
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
    start_year, end_year, content_types = get_filters_input()
    
    # Modo de búsqueda
    print("\n--- Modo de búsqueda ---")
    print("1. Búsqueda simple (hasta 200 resultados)")
    print("2. Obtener TODOS los resultados (con paginación automática)")
    mode = input("Selecciona modo (1 o 2, default 1): ").strip()
    
    if mode == "2":
        # Paginación automática
        max_str = input("Máximo de resultados a obtener (default 200): ").strip()
        max_results = int(max_str) if max_str.isdigit() else 200
        
        all_articles = search_all_results(
            query=query,
            api_key=api_key,
            start_year=start_year,
            end_year=end_year,
            content_types=content_types,
            max_results=max_results,
        )
        
        # Mostrar resumen
        log("RESUMEN DE RESULTADOS")
        print(f"Total obtenido: {len(all_articles)} artículos")
        
        if all_articles:
            print("\nPrimeros 5 resultados:")
            for i, article in enumerate(all_articles[:5], 1):
                print(f"  {i}. {article.get('title', 'N/A')[:80]}...")
        
        # Guardar todos los resultados
        output_file = "ieee_results.json"
        output_data = {
            "query": query,
            "filters": {
                "start_year": start_year,
                "end_year": end_year,
                "content_types": content_types,
            },
            "total_results": len(all_articles),
            "articles": all_articles,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nTodos los resultados guardados en: {output_file}")
        
    else:
        # Búsqueda simple
        count_str = input("Número de resultados (máx 200, default 25): ").strip()
        max_records = int(count_str) if count_str.isdigit() else 25
        
        response = search_ieee(
            query=query,
            api_key=api_key,
            max_records=max_records,
            start_year=start_year,
            end_year=end_year,
            content_types=content_types,
        )
        
        # Mostrar resultados
        print_search_results(response)
        
        # Guardar respuesta
        output_file = "ieee_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        print(f"\nRespuesta guardada en: {output_file}")
    
    return 0


def main() -> int:
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description="IEEE Xplore API Client - Busca publicaciones en IEEE Xplore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python ieee_api.py --sencilla    # Solo conteo de múltiples términos
  python ieee_api.py --extendida   # Resultados detallados
  python ieee_api.py               # Te pregunta qué modo usar

Configuración:
  1. Obtén tu API key en: https://developer.ieee.org/member/register
  2. Configura la variable de entorno: $Env:IEEE_API_KEY = "tu_api_key"
  3. Edita ieee_input.json con tus keywords y filtros
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
    
    log("IEEE XPLORE API CLIENT")
    
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
