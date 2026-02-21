"""
Sistema de logging para el proyecto.
"""

import os
from datetime import datetime
from typing import Optional

from .config import LOG_DIR


class Logger:
    """Manejador de logs con soporte para archivo y consola."""
    
    def __init__(self):
        self._file_handle = None
        self._filename: Optional[str] = None
    
    def init(self, api_name: str, mode: str) -> str:
        """Inicializa el archivo de log con timestamp."""
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._filename = f"{LOG_DIR}/{api_name}_{mode}_{timestamp}.log"
        self._file_handle = open(self._filename, "w", encoding="utf-8")
        
        self.header(f"{api_name.upper()} API LOG - Modo: {mode}")
        self.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.separator()
        
        return self._filename
    
    def write(self, message: str) -> None:
        """Escribe mensaje a consola y archivo."""
        print(message)
        if self._file_handle:
            self._file_handle.write(message + "\n")
            self._file_handle.flush()
    
    def separator(self, char: str = "=", length: int = 80) -> None:
        """Escribe una línea separadora."""
        self.write(char * length)
    
    def header(self, title: str) -> None:
        """Escribe un encabezado destacado."""
        self.write("")
        self.separator()
        self.write(f"  {title}")
        self.separator()
    
    def close(self) -> None:
        """Cierra el archivo de log."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
    
    @property
    def filename(self) -> Optional[str]:
        return self._filename


# Logger global (singleton)
logger = Logger()
