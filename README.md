# Analizador Léxico y Sintáctico

## Descripción del Proyecto
Este proyecto es un **Analizador Léxico y Sintáctico** diseñado para procesar y validar código fuente.

El sistema implementa las dos primeras fases fundamentales de un compilador:
1. **Análisis Léxico (*Scanner*)**: Escanea el código fuente carácter por carácter mediante expresiones regulares, agrupando lexemas válidos en una secuencia de *tokens* clasificados (palabras reservadas, identificadores, literales, operadores y delimitadores) y detectando símbolos que no pertenecen al alfabeto del lenguaje.
2. **Análisis Sintáctico (*Parser*)**: Evalúa la secuencia de *tokens* utilizando un analizador por **Descenso Recursivo** con recuperación de errores a nivel de frase (*Phrase-Level Recovery*). Verifica que las instrucciones cumplan con las reglas gramaticales del lenguaje (declaraciones, asignaciones, estructuras condicionales `if/else`, ciclos `while` y `for`, funciones, sentencias `print`/`return` y jerarquía de expresiones).


---

## Estructura del Proyecto
El proyecto está organizado de la siguiente manera:

```text
Analizador Lexico/
├── app.py                  # Servidor Flask y API REST que conecta el análisis léxico y sintáctico
├── lexical_analyzer.py     # Implementación del analizador léxico (Expresiones Regulares y Tokens)
├── syntax_analyzer.py      # Implementación del analizador sintáctico (Gramática y Parser)
├── run.py                  # Script de arranque rápido que inicia el servidor y abre el navegador
├── requirements.txt        # Dependencias del proyecto (Flask, Werkzeug)
├── Ejemplos/               # Archivos de prueba en texto plano (.txt)
│   ├── Ejemplo1.txt
│   ├── Ejemplo2.txt
│   └── Ejemplo3.txt
├── static/                 # Recursos estáticos locales (CSS, JS de CodeMirror, fuentes e imágenes)
│   ├── css/
│   ├── fonts/
│   ├── js/
│   ├── fondo1.png
│   └── logotecnm.png
└── templates/
    └── index.html          # Interfaz web interactiva (UI/UX en tonos negro y morado)

### Archivos principales

1. **`lexical_analyzer.py`**: Contiene la lógica del analizador léxico. Este archivo define las reglas para identificar tokens y procesa el texto de entrada.
2. **`app.py`**: Configura la aplicación web utilizando Flask. Define las rutas y conecta la lógica del analizador léxico con la interfaz de usuario.
3. **`run.py`**: Es el punto de entrada del proyecto. Ejecuta la aplicación web.
4. **`templates/index.html`**: Proporciona la interfaz de usuario para interactuar con el analizador léxico.
5. **`requirements.txt`**: Lista las dependencias necesarias para ejecutar el proyecto.

## Instalación y Ejecución

Sigue estos pasos para instalar y ejecutar el proyecto:

### Prerrequisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Instalación
1. Clona este repositorio o descarga los archivos.
2. Abre una terminal y navega al directorio del proyecto.
3. Instala las dependencias ejecutando:
   ```bash
   pip install -r requirements.txt
   ```

### Ejecución
1. Ejecuta el archivo `run.py` para iniciar la aplicación:
   ```bash
   python run.py
   ```
2. Abre un navegador web y ve a `http://127.0.0.1:5000` para acceder a la interfaz.

## Funcionamiento del Analizador Léxico

El analizador léxico funciona de la siguiente manera:

1. **Entrada de texto**: El usuario ingresa una cadena de texto a través de la interfaz web.
2. **Procesamiento**: El texto se envía al servidor, donde `lexical_analyzer.py` procesa la entrada y genera una lista de tokens.
3. **Salida**: Los tokens generados se devuelven al cliente y se muestran en la interfaz web.

### Conexión entre los archivos
- `index.html` proporciona la interfaz para que el usuario ingrese texto.
- `app.py` recibe las solicitudes del cliente, utiliza `lexical_analyzer.py` para procesar el texto y devuelve los resultados.
- `run.py` inicia el servidor Flask definido en `app.py`.

## Contribuciones
Las contribuciones son bienvenidas. Si encuentras un problema o tienes una mejora, abre un issue o envía un pull request.

## Licencia
Este proyecto está bajo la licencia MIT. Puedes usarlo, modificarlo y distribuirlo libremente.

---

¡Gracias por usar el Analizador Léxico! Si tienes preguntas o necesitas ayuda, no dudes en contactarme.