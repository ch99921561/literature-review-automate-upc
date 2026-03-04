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
    # Phase 1: Búsqueda y conteo (genera archivo xlsx con TOP 30)
    python main.py --phase1                  # Todas las APIs
    python main.py --phase1 --scopus         # Solo Scopus
    python main.py --phase1 --ieee           # Solo IEEE
    python main.py --phase1 --wos            # Solo Web of Science
    
    # Phase 2: Obtención de abstracts (requiere archivo xlsx de phase1)
    python main.py --phase2 --input outputs/output_consolidado_XXXXXXXX.xlsx

    # Modo extendido interactivo
    python main.py --extendida

Configuración:
    1. Configurar variables de entorno:
       $Env:SCOPUS_API_KEY = "tu_api_key"
       $Env:IEEE_API_KEY = "tu_api_key"
       $Env:WOS_API_KEY = "tu_api_key"
    2. Editar definitions/input.json con keywords y filtros
"""

import argparse
import sys
import os

from src import (
    APIType,
    SearchEngine,
    ScopusAPIClient,
    IEEEAPIClient,
    WOSAPIClient,
    run_extended_mode,
    run_phase2,
)


def main() -> int:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Literature Review Automation - Búsqueda en Scopus, IEEE Xplore y Web of Science",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Phase 1: Búsqueda y conteo (genera xlsx)
  python main.py --phase1              # Todas las APIs
  python main.py --phase1 --scopus     # Solo Scopus
  python main.py --phase1 --wos        # Solo Web of Science
  
  # Phase 2: Obtención de abstracts
  python main.py --phase2 --input outputs/output_consolidado_20260221.xlsx
  
  # Modo extendido
  python main.py --extendida

Configuración:
  1. $Env:SCOPUS_API_KEY = "tu_api_key"
  2. $Env:IEEE_API_KEY = "tu_api_key"
  3. $Env:WOS_API_KEY = "tu_api_key"
  4. Editar definitions/input.json
"""
    )
    parser.add_argument("--phase1", "-p1", action="store_true",
                        help="Phase 1: Búsqueda y conteo de publicaciones (genera xlsx)")
    parser.add_argument("--phase2", "-p2", action="store_true",
                        help="Phase 2: Obtención de abstracts y traducción")
    parser.add_argument("--input", "-i", type=str,
                        help="Archivo xlsx de entrada para Phase 2")
    parser.add_argument("--sencilla", "-s", action="store_true",
                        help="Alias de --phase1 (modo sencillo)")
    parser.add_argument("--extendida", "-e", action="store_true",
                        help="Modo extendido: búsqueda detallada")
    parser.add_argument("--scopus", action="store_true",
                        help="Solo ejecutar Scopus")
    parser.add_argument("--ieee", action="store_true",
                        help="Solo ejecutar IEEE")
    parser.add_argument("--wos", action="store_true",
                        help="Solo ejecutar Web of Science")
    
    args = parser.parse_args()
    
    # Phase 2: Obtención de abstracts
    if args.phase2:
        if not args.input:
            print("ERROR: Se requiere --input con la ruta al archivo xlsx de Phase 1")
            print("Ejemplo: python main.py --phase2 --input outputs/output_consolidado_20260221.xlsx")
            return 1
        
        if not os.path.exists(args.input):
            print(f"ERROR: Archivo no encontrado: {args.input}")
            return 1
        
        return run_phase2(args.input)
    
    # Phase 1 o modo sencillo
    if args.phase1 or args.sencilla:
        return _run_phase1(args)
    
    # Modo extendido
    if args.extendida:
        engine = _create_engine(args)
        if not engine:
            return 1
        return run_extended_mode(engine)
    
    # Modo interactivo
    print("\n--- Selecciona el modo de operación ---")
    print("1. PHASE 1: Búsqueda y conteo (genera xlsx)")
    print("2. PHASE 2: Obtención de abstracts")
    print("3. EXTENDIDA: Búsqueda detallada")
    
    mode = input("\nSelecciona modo (1, 2 o 3): ").strip()
    
    if mode == "1":
        return _run_phase1(args)
    elif mode == "2":
        input_file = input("Ruta al archivo xlsx de Phase 1: ").strip()
        if not os.path.exists(input_file):
            print(f"ERROR: Archivo no encontrado: {input_file}")
            return 1
        return run_phase2(input_file)
    else:
        engine = _create_engine(args)
        if not engine:
            return 1
        return run_extended_mode(engine)


def _create_engine(args) -> SearchEngine:
    """Crea y configura el motor de búsqueda."""
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
        return None
    
    # Cargar configuración
    if not engine.load_config():
        return None
    
    return engine


def _run_phase1(args) -> int:
    """Ejecuta Phase 1: búsqueda y conteo."""
    engine = _create_engine(args)
    if not engine:
        return 1
    
    return _run_simple_for_all(engine)


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
