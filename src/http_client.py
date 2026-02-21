"""
Cliente HTTP genérico para requests a las APIs.
"""

import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from .logger import logger


class HTTPClient:
    """Cliente HTTP genérico."""
    
    @staticmethod
    def get(url: str, headers: Optional[Dict[str, str]] = None, 
            verbose: bool = True, mask_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Realiza un request GET y retorna el JSON parseado.
        
        Args:
            url: URL del request
            headers: Headers opcionales
            verbose: Si True, imprime detalles
            mask_key: Clave a enmascarar en la URL para logs
        """
        default_headers = {
            "Accept": "application/json",
            "User-Agent": "Python-LitReview-Client/2.0",
        }
        if headers:
            default_headers.update(headers)
        
        if verbose:
            display_url = url
            if mask_key and mask_key in url:
                # Enmascarar API key en logs
                parts = url.split(mask_key + "=")
                if len(parts) > 1:
                    key_part = parts[1].split("&")[0]
                    if len(key_part) > 12:
                        masked = key_part[:8] + "..." + key_part[-4:]
                        display_url = url.replace(key_part, masked)
            logger.header("REQUEST")
            logger.write(f"URL: {display_url}")
        
        req = urllib.request.Request(url=url, headers=default_headers, method="GET")
        
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                elapsed = time.time() - start
                
                if verbose:
                    logger.header("RESPONSE")
                    logger.write(f"Status: {resp.status} {resp.reason}")
                    logger.write(f"Elapsed: {elapsed:.2f}s")
                
                data = resp.read().decode("utf-8")
                return json.loads(data)
                
        except urllib.error.HTTPError as e:
            elapsed = time.time() - start
            if verbose:
                logger.header("ERROR HTTP")
            logger.write(f"HTTP Error: {e.code} {e.reason}")
            logger.write(f"Elapsed: {elapsed:.2f}s")
            
            # Capturar headers de error para diagnóstico
            try:
                error_headers = dict(e.headers)
                logger.write("")
                logger.write("=== DIAGNÓSTICO DE ERROR ===")
                
                # Headers específicos de error (IEEE/Mashery)
                if "X-Error-Detail-Header" in error_headers:
                    logger.write(f"Error Detail: {error_headers['X-Error-Detail-Header']}")
                if "X-Mashery-Error-Code" in error_headers:
                    logger.write(f"Error Code: {error_headers['X-Mashery-Error-Code']}")
                
                # Headers específicos de Scopus/Elsevier
                if "X-ELS-Status" in error_headers:
                    logger.write(f"Elsevier Status: {error_headers['X-ELS-Status']}")
                
                # Headers específicos de WOS/Clarivate
                if "X-RateLimit-Remaining" in error_headers:
                    logger.write(f"Rate Limit Remaining: {error_headers['X-RateLimit-Remaining']}")
                
                # Mostrar todos los headers relevantes
                logger.write("")
                logger.write("Headers de respuesta:")
                for key, value in error_headers.items():
                    if key.lower().startswith(('x-', 'www-', 'retry')):
                        logger.write(f"  {key}: {value}")
                
            except Exception:
                pass
            
            # Capturar body del error
            try:
                error_body = e.read().decode("utf-8")
                logger.write("")
                logger.write(f"Response Body: {error_body[:500]}")
                
                # Mensajes de ayuda según el error
                if e.code == 403:
                    logger.write("")
                    logger.write("=== POSIBLES SOLUCIONES ===")
                    if "Developer Inactive" in error_body or "DEVELOPER_INACTIVE" in str(e.headers):
                        logger.write("• Tu cuenta de desarrollador está INACTIVA")
                        logger.write("• Revisa tu email para activar la cuenta")
                        logger.write("• Verifica el estado en el portal de desarrollador")
                    else:
                        logger.write("• Verifica que tu API key sea válida")
                        logger.write("• Confirma que tu suscripción esté activa")
                        logger.write("• Revisa los límites de tu plan")
                elif e.code == 401:
                    logger.write("")
                    logger.write("=== POSIBLES SOLUCIONES ===")
                    logger.write("• API key inválida o no proporcionada")
                    logger.write("• Verifica la variable de entorno")
                elif e.code == 429:
                    logger.write("")
                    logger.write("=== POSIBLES SOLUCIONES ===")
                    logger.write("• Has excedido el límite de requests")
                    logger.write("• Espera unos minutos antes de reintentar")
                    
            except Exception:
                pass
            
            logger.write("=" * 40)
            return {"error": str(e)}
        except Exception as e:
            logger.write(f"Request failed: {e}")
            return {"error": str(e)}
