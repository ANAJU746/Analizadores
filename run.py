"""
Script para ejecutar la aplicación web del Analizador Léxico
Abre automáticamente el navegador en http://localhost:5000
"""

import webbrowser
import time
import os
from app import app

def open_browser():
    """Abre el navegador después de un pequeño delay"""
    time.sleep(2)  # Esperar a que el servidor esté listo
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 ANALIZADOR LÉXICO INTERACTIVO")
    print("="*70)
    print("\n✓ Iniciando servidor web...")
    print("\n📱 URL: http://localhost:5000")
    print("\n💡 Presiona Ctrl+C para detener el servidor\n")
    
    # Abrir navegador en background
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Iniciar servidor Flask
    app.run(debug=True, use_reloader=False, port=5000)
