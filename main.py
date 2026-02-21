#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Literature Review Automation Tool
=================================
Cliente unificado para búsqueda en múltiples APIs académicas:
- Scopus (Elsevier)
- IEEE Xplore
- Web of Science Starter (Clarivate)

Uso:
    python main.py --sencilla              # Ejecutar todas las APIs en modo conteo
    python main.py --sencilla --scopus     # Solo Scopus
    python main.py --sencilla --ieee       # Solo IEEE
    python main.py --sencilla --wos        # Solo Web of Science
    python main.py --extendida             # Modo extendido interactivo

Configuración:
    1. Configurar variables de entorno:
       $Env:SCOPUS_API_KEY = "tu_api_key"
       $Env:IEEE_API_KEY = "tu_api_key"
       $Env:WOS_API_KEY = "tu_api_key"
    2. Editar definitions/input.json con keywords y filtros
"""

import argparse
import sys

from src import (
    APIType,
    SearchEngine,
    ScopusAPIClient,
    IEEEAPIClient,
    WOSAPIClient,
    run_extended_mode,
)


def main() -> int:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Literature Review Automation - Búsqueda en Scopus, IEEE Xplore y Web of Science",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py --sencilla              # Todas las APIs en modo conteo
  python main.py --sencilla --scopus     # Solo Scopus
  python main.py --sencilla --ieee       # Solo IEEE
  python main.py --sencilla --wos        # Solo Web of Science
  python main.py --extendida             # Modo extendido interactivo

Configuración:
  1. $Env:SCOPUS_API_KEY = "tu_api_key"
  2. $Env:IEEE_API_KEY = "tu_api_key"
  3. $Env:WOS_API_KEY = "tu_api_key"
  4. Editar definitions/input.json
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
    parser.add_argument("--wos", action="store_true",
                        help="Solo ejecutar Web of Science")
    
    args = parser.parse_args()
    
    # Determinar qué APIs ejecutar
    any_specific = args.scopus or args.ieee or args.wos
    run_scopus = args.scopus or not any_specific
    run_ieee = args.ieee or not any_specific
    run_wos = args.wos or not any_specific
    
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
    
    if run_wos:
        print("\n[Web of Science]")
        wos_client = WOSAPIClient()
        engine.register_client(APIType.WOS, wos_client)
    
    if not engine.clients:
        print("\nERROR: No se pudo autenticar ninguna API")
        return 1
    
    # Cargar configuración
    if not engine.load_config():
        return 1
    
    # Determinar modo
    if args.sencilla:
        return _run_simple_for_all(engine)
    
    elif args.extendida:
        return run_extended_mode(engine)
    
    else:
        # Modo interactivo
        print("\n--- Selecciona el modo de operación ---")
        print("1. SENCILLA: Solo conteo de publicaciones")
        print("2. EXTENDIDA: Búsqueda detallada")
        
        mode = input("\nSelecciona modo (1 o 2): ").strip()
        
        if mode == "1":
            return _run_simple_for_all(engine)
        else:
            return run_extended_mode(engine)


def _run_simple_for_all(engine: SearchEngine) -> int:
    """Ejecuta modo sencillo para todas las APIs registradas."""
    result = 0
    all_combination_results = {}
    
    for api_type in engine.clients.keys():
        ret, combinations = engine.run_simple_mode(api_type)
        if ret != 0:
            result = ret
        else:
            all_combination_results[api_type] = combinations
    
    # Generar archivo consolidado con TOP 30
    if all_combination_results:
        engine.save_consolidated_top30(all_combination_results)
    
    return result


if __name__ == "__main__":
    sys.exit(main())
