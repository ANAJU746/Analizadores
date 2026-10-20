# Analizador Léxico en Python
import re
from enum import Enum
from dataclasses import dataclass
from typing import List


class LexicalError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        if self.line > 0 and self.column > 0:
            return f"Error léxico en línea {self.line}, columna {self.column}: {self.message}"
        return f"Error léxico: {self.message}"

@dataclass
class ErrorReport:
    errors: List[dict]
    
    def add_error(self, message: str, line: int, column: int, char: str):
        self.errors.append({
            'message': message,
            'line': line,
            'column': column,
            'char': char
        })


class TokenType(Enum):
    # Palabras reservadas
    SWITCH = "SWITCH"
    INT = "INT"
    FLOAT = "FLOAT"
    BOOL = "BOOL"
    VOID = "VOID"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    FOR = "FOR"
    RETURN = "RETURN"
    TRUE = "TRUE"
    FALSE = "FALSE"
    STRING_TYPE = "STRING_TYPE" # Para la palabra reservada 'string'

    # NUEVAS PALABRAS RESERVADAS PARA I/O
    PRINT = "PRINT"
    READ_INT = "READ_INT"
    READ_FLOAT = "READ_FLOAT"
    
    # Identificadores y literales
    IDENTIFIER = "IDENTIFIER"
    INTEGER = "INTEGER"
    REAL = "REAL"
    STRING = "STRING"
    
    # Operadores
    PLUS = "PLUS"
    MINUS = "MINUS"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    MODULO = "MODULO"
    ASSIGN = "ASSIGN"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_EQUAL = "LESS_EQUAL"
    GREATER_THAN = "GREATER_THAN"
    GREATER_EQUAL = "GREATER_EQUAL"
    LOGICAL_AND = "LOGICAL_AND"
    LOGICAL_OR = "LOGICAL_OR"
    LOGICAL_NOT = "LOGICAL_NOT"
    
    # Delimitadores
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    SEMICOLON = "SEMICOLON"
    COMMA = "COMMA"
    DOT = "DOT"
    COLON = "COLON"
    
    # Ignorados
    NEWLINE = "NEWLINE"
    WHITESPACE = "WHITESPACE"
    COMMENT = "COMMENT"
    UNKNOWN = "UNKNOWN"


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int


class LexicalAnalyzer:
    def __init__(self):
        self.error_report = ErrorReport([])
        
        self.keywords = {
            'int': TokenType.INT,
            'float': TokenType.FLOAT,
            'bool': TokenType.BOOL,
            'string': TokenType.STRING_TYPE,
            'void': TokenType.VOID,
            'if': TokenType.IF,
            'else': TokenType.ELSE,
            'while': TokenType.WHILE,
            'for': TokenType.FOR,
            'return': TokenType.RETURN,
            'true': TokenType.TRUE,
            'false': TokenType.FALSE,
            'switch': TokenType.SWITCH,  

            # NUEVAS REGLAS APLICADAS
            'print': TokenType.PRINT,
            'read_int': TokenType.READ_INT,
            'read_float': TokenType.READ_FLOAT
        }
        
        self.patterns = [
            # 1. Comentarios 
            (r'//.*', TokenType.COMMENT),
            (r'/\*[\s\S]*?\*/', TokenType.COMMENT),
            
            # 2. Literales
            (r'"([^"\\]|\\.)*"', TokenType.STRING),
            (r'\d+\.\d+', TokenType.REAL),
            (r'\d+', TokenType.INTEGER),
            
            # 3. Operadores Dobles
            (r'==', TokenType.EQUAL),
            (r'!=', TokenType.NOT_EQUAL),
            (r'<=', TokenType.LESS_EQUAL),
            (r'>=', TokenType.GREATER_EQUAL),
            (r'&&', TokenType.LOGICAL_AND),
            (r'\|\|', TokenType.LOGICAL_OR),
            
            # 4. Operadores Simples
            (r'\+', TokenType.PLUS),
            (r'-', TokenType.MINUS),
            (r'\*', TokenType.MULTIPLY),
            (r'/', TokenType.DIVIDE),
            (r'%', TokenType.MODULO),
            (r'=', TokenType.ASSIGN),
            (r'<', TokenType.LESS_THAN),
            (r'>', TokenType.GREATER_THAN),
            (r'!', TokenType.LOGICAL_NOT),
            
            # 5. Delimitadores
            (r'\(', TokenType.LPAREN),
            (r'\)', TokenType.RPAREN),
            (r'\{', TokenType.LBRACE),
            (r'\}', TokenType.RBRACE),
            (r'\[', TokenType.LBRACKET),
            (r'\]', TokenType.RBRACKET),
            (r';', TokenType.SEMICOLON),
            (r',', TokenType.COMMA),
            (r'\.', TokenType.DOT),
            (r':', TokenType.COLON),
            
            # 6. Identificadores
            (r'[a-zA-Z_]\w*', TokenType.IDENTIFIER),
            
            # 7. Espacios (Se ignoran)
            (r'[ \t]+', TokenType.WHITESPACE),
            (r'\n', TokenType.NEWLINE)
        ]
        
        self.compiled_patterns = [(re.compile(p), t) for p, t in self.patterns]
    
    def analyze(self, input_text: str) -> List[Token]:
        tokens = []
        self.error_report = ErrorReport([])
        line = 1
        column = 1
        pos = 0
        
        while pos < len(input_text):
            match_found = False
            
            for pattern, token_type in self.compiled_patterns:
                match = pattern.match(input_text, pos)
                
                if match:
                    value = match.group(0)
                    
                    
                    if token_type not in [TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.COMMENT]:
                        if token_type == TokenType.IDENTIFIER and value in self.keywords:
                            token_type = self.keywords[value]
                        
                        tokens.append(Token(type=token_type, value=value, line=line, column=column))
                    
                    
                    if token_type == TokenType.COMMENT and '\n' in value:
                        newlines = value.count('\n')
                        line += newlines
                        
                        last_newline_idx = value.rfind('\n')
                        column = len(value) - last_newline_idx
                    elif token_type == TokenType.NEWLINE:
                        line += 1
                        column = 1
                    else:
                        column += len(value)
                    
                    pos = match.end()
                    match_found = True
                    break
            
            if not match_found:
                char = input_text[pos]
                self.error_report.add_error(f"Símbolo no válido '{char}'", line, column, char)
                pos += 1
                column += 1
                
        
        return tokens