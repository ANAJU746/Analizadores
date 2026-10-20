from typing import List, Optional
from lexical_analyzer import Token, TokenType

class SyntaxAnalyzer:
    def __init__(self):
        self.tokens: List[Token] = []
        self.pos: int = 0
        self.errors: List[dict] = []
        self.structures: List[dict] = []

    def current_token(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def previous_token(self) -> Optional[Token]:
        if self.pos > 0:
            return self.tokens[self.pos - 1]
        return None

    def advance(self) -> Optional[Token]:
        token = self.current_token()
        self.pos += 1
        return token

    def match(self, *expected_types: TokenType) -> Optional[Token]:
        token = self.current_token()
        if token and token.type in expected_types:
            return self.advance()
        return None

    def expect(self, expected_type: TokenType, error_msg: str) -> Optional[Token]:
        token = self.current_token()
        if token and token.type == expected_type:
            return self.advance()
        
        prev = self.previous_token()
        
        if expected_type in [TokenType.SEMICOLON, TokenType.RPAREN] and prev and (
            not token or token.line > prev.line or token.type in [TokenType.LBRACE, TokenType.RBRACE]
        ):
            line = prev.line
            col = prev.column
            full_msg = f"{error_msg} (después de '{prev.value}')"
            self.add_error(full_msg, line, col, prev.value)
        elif token:
            full_msg = f"{error_msg} (se encontró '{token.value}')"
            self.add_error(full_msg, token.line, token.column, token.value)
        else:
            last_line = prev.line if prev else 1
            last_col = prev.column if prev else 1
            last_val = prev.value if prev else ""
            full_msg = f"{error_msg} (al final del código)"
            self.add_error(full_msg, last_line, last_col, last_val)
            
        return None

    def add_error(self, message: str, line: int, column: int, token_val: str = ""):
        self.errors.append({
            'type': 'Sintáctico',
            'message': message,
            'line': line,
            'column': column,
            'char': token_val if token_val else message
        })

    def parse(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors = []
        self.structures = []
        ast_statements = []

        while self.current_token() is not None:
            start_pos = self.pos
            node = self.parse_statement()
            if node:
                ast_statements.append(node)
            # Seguro anti-bucle infinito: garantiza que el cursor siempre avance
            if self.pos == start_pos and self.current_token() is not None:
                self.advance()

        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'structures': self.structures,
            'ast': {
                'kind': 'root',
                'label': 'statement\nsequence',
                'children': ast_statements
            }
        }

    # ================= REGLAS GRAMATICALES =================

    def parse_statement(self) -> Optional[dict]:
        token = self.current_token()
        if not token:
            return None

        if token.type in [TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STRING_TYPE, TokenType.VOID]:
            return self.parse_declaration()
        elif token.type == TokenType.IF:
            return self.parse_if()
        elif token.type == TokenType.ELSE:
            self.add_error("Estructura 'else' inesperada sin un 'if' previo", token.line, token.column, token.value)
            self.advance()
            if self.current_token() and self.current_token().type == TokenType.LBRACE:
                self.parse_block()
            return None
        elif token.type == TokenType.WHILE:
            return self.parse_while()
        elif token.type == TokenType.FOR:
            return self.parse_for()
        elif token.type == TokenType.SWITCH:
            return self.parse_switch()
        elif token.type == TokenType.PRINT:
            return self.parse_print()
        elif token.type == TokenType.RETURN:
            return self.parse_return()
        elif token.type == TokenType.IDENTIFIER:
            return self.parse_assignment_or_call()
        elif token.type == TokenType.LBRACE:
            return self.parse_block()
        elif token.type == TokenType.RBRACE:
            self.add_error(
                "Llave de cierre '}' inesperada (sin bloque '{' abierto)",
                token.line,
                token.column,
                token.value
            )
            self.advance()
            return None
        else:
            first_bad = token
            bad_sequence = token.value
            self.advance()

            valid_starters = [
                TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STRING_TYPE,
                TokenType.VOID, TokenType.IF, TokenType.ELSE, TokenType.WHILE, TokenType.FOR,
                TokenType.SWITCH, TokenType.PRINT, TokenType.RETURN, TokenType.IDENTIFIER,
                TokenType.LBRACE, TokenType.RBRACE
            ]
            while (
                self.current_token()
                and self.current_token().line == first_bad.line
                and self.current_token().type not in valid_starters
            ):
                bad_sequence += self.current_token().value
                self.advance()

            self.add_error(
                f"Secuencia o token inesperado '{bad_sequence}' al inicio de instrucción",
                first_bad.line,
                first_bad.column,
                bad_sequence
            )
            return None

    def parse_declaration(self) -> Optional[dict]:
        type_token = self.advance()
        id_token = self.expect(TokenType.IDENTIFIER, f"Falta nombre de identificador después de '{type_token.value}'")
        
        if not id_token:
            return None

        # Caso 1: Declaración de Función
        if self.match(TokenType.LPAREN):
            params_list = []
            if self.current_token() and self.current_token().type != TokenType.RPAREN:
                while True:
                    p_type = self.match(TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STRING_TYPE)
                    if not p_type:
                        t = self.current_token()
                        if t:
                            self.add_error(f"Se esperaba tipo de dato en parámetro (se encontró '{t.value}')", t.line, t.column, t.value)
                        break
                    p_id = self.expect(TokenType.IDENTIFIER, "Falta nombre del parámetro")
                    if p_id:
                        params_list.append(f"{p_type.value} {p_id.value}")
                    if not self.match(TokenType.COMMA):
                        break
            
            self.expect(TokenType.RPAREN, "Falta ')' al cerrar parámetros de función")
            self.structures.append({'line': type_token.line, 'type': 'Declaración de Función', 'detail': f"{type_token.value} {id_token.value}()"})
            body_node = self.parse_block()
            children = []
            if body_node:
                body_node['edge_label'] = 'body'
                children.append(body_node)
            return {
                'kind': 'control',
                'label': f"function\n{type_token.value} {id_token.value}()",
                'children': children
            }

        # Caso 2: Declaración de Variable
        val_node = None
        if self.match(TokenType.ASSIGN):
            val_node = self.parse_expression()
        
        if self.expect(TokenType.SEMICOLON, "Falta punto y coma ';' al final de la declaración"):
            self.structures.append({'line': type_token.line, 'type': 'Declaración de Variable', 'detail': f"{type_token.value} {id_token.value}"})

        children = [{'kind': 'var', 'label': f"variable\nname: {id_token.value}", 'children': []}]
        if val_node:
            children.append(val_node)
        return {
            'kind': 'decl',
            'label': f"declare ({type_token.value})",
            'children': children
        }

    def parse_assignment_or_call(self, require_semicolon=True) -> Optional[dict]:
        id_token = self.advance()
        
        # Caso 1: Asignación (id = expr;)
        if self.match(TokenType.ASSIGN):
            val_node = self.parse_expression()
            if require_semicolon:
                if self.expect(TokenType.SEMICOLON, f"Falta punto y coma ';' después de asignar a '{id_token.value}'"):
                    self.structures.append({'line': id_token.line, 'type': 'Asignación', 'detail': f"Variable '{id_token.value}'"})
            children = [{'kind': 'var', 'label': f"variable\nname: {id_token.value}", 'children': []}]
            if val_node:
                children.append(val_node)
            return {
                'kind': 'assign',
                'label': 'assign\nop: =',
                'children': children
            }
        
        # Caso 2: Llamada a función (id(args);)
        elif self.match(TokenType.LPAREN):
            args_nodes = []
            if self.current_token() and self.current_token().type != TokenType.RPAREN:
                first_arg = self.parse_expression()
                if first_arg:
                    args_nodes.append(first_arg)
                while self.match(TokenType.COMMA):
                    next_arg = self.parse_expression()
                    if next_arg:
                        args_nodes.append(next_arg)
            self.expect(TokenType.RPAREN, f"Falta ')' en llamada a función '{id_token.value}'")
            if require_semicolon:
                if self.expect(TokenType.SEMICOLON, f"Falta ';' después de llamar a '{id_token.value}()'"):
                    self.structures.append({'line': id_token.line, 'type': 'Llamada a Función', 'detail': f"{id_token.value}()"})
            return {
                'kind': 'io',
                'label': f"call\n{id_token.value}()",
                'children': args_nodes
            }
        else:
            self.add_error(
                f"Instrucción incompleta: identificador '{id_token.value}' suelto (se esperaba '=' o '()')", 
                id_token.line, id_token.column, id_token.value
            )
            return None

    def parse_if(self) -> dict:
        if_token = self.advance()
        self.expect(TokenType.LPAREN, "Falta '(' después de 'if'")
        
        if self.current_token() and self.current_token().type == TokenType.RPAREN:
            self.add_error("La condición del 'if' no puede estar vacía", if_token.line, if_token.column, "()")
            cond_node = {'kind': 'error', 'label': 'condición vacía', 'children': []}
        else:
            cond_node = self.parse_expression()
            
        self.expect(TokenType.RPAREN, "Falta ')' después de la condición del 'if'")
        
        self.structures.append({'line': if_token.line, 'type': 'Condicional IF', 'detail': 'Estructura if'})
        if_body = self.parse_block()

        children = []
        if cond_node:
            cond_node['edge_label'] = 'condition'
            children.append(cond_node)
        if if_body:
            if_body['edge_label'] = 'if-body'
            children.append(if_body)

        if self.match(TokenType.ELSE):
            self.structures.append({'line': self.previous_token().line, 'type': 'Bloque ELSE', 'detail': 'Alternativa else'})
            if self.current_token() and self.current_token().type == TokenType.IF:
                else_node = self.parse_if()
            else:
                else_node = self.parse_block()
            if else_node:
                else_node['edge_label'] = 'else-body'
                children.append(else_node)

        return {
            'kind': 'control',
            'label': 'branch\n(if)',
            'children': children
        }

    def parse_while(self) -> dict:
        w_token = self.advance()
        self.expect(TokenType.LPAREN, "Falta '(' después de 'while'")
        
        if self.current_token() and self.current_token().type == TokenType.RPAREN:
            self.add_error("La condición del 'while' no puede estar vacía", w_token.line, w_token.column, "()")
            cond_node = {'kind': 'error', 'label': 'condición vacía', 'children': []}
        else:
            cond_node = self.parse_expression()
            
        self.expect(TokenType.RPAREN, "Falta ')' después de la condición del 'while'")
        self.structures.append({'line': w_token.line, 'type': 'Ciclo WHILE', 'detail': 'Bucle while'})
        body_node = self.parse_block()

        children = []
        if cond_node:
            cond_node['edge_label'] = 'condition'
            children.append(cond_node)
        if body_node:
            body_node['edge_label'] = 'body'
            children.append(body_node)

        return {
            'kind': 'control',
            'label': 'while',
            'children': children
        }

    def parse_for(self) -> dict:
        f_token = self.advance()
        self.expect(TokenType.LPAREN, "Falta '(' después de 'for'")
        
        init_node = None
        if self.current_token() and self.current_token().type in [TokenType.INT, TokenType.FLOAT]:
            init_node = self.parse_declaration()
        elif self.current_token() and self.current_token().type == TokenType.IDENTIFIER:
            init_node = self.parse_assignment_or_call(require_semicolon=True)
        else:
            self.expect(TokenType.SEMICOLON, "Falta ';' en inicialización del 'for'")

        cond_node = self.parse_expression()
        self.expect(TokenType.SEMICOLON, "Falta ';' después de condición del 'for'")

        inc_node = None
        if self.current_token() and self.current_token().type == TokenType.IDENTIFIER:
            inc_node = self.parse_assignment_or_call(require_semicolon=False)

        self.expect(TokenType.RPAREN, "Falta ')' al cerrar encabezado del 'for'")
        self.structures.append({'line': f_token.line, 'type': 'Ciclo FOR', 'detail': 'Bucle for'})
        body_node = self.parse_block()

        children = []
        if init_node:
            init_node['edge_label'] = 'init'
            children.append(init_node)
        if cond_node:
            cond_node['edge_label'] = 'condition'
            children.append(cond_node)
        if inc_node:
            inc_node['edge_label'] = 'step'
            children.append(inc_node)
        if body_node:
            body_node['edge_label'] = 'body'
            children.append(body_node)

        return {
            'kind': 'control',
            'label': 'for',
            'children': children
        }

    def parse_switch(self) -> dict:
        s_token = self.advance()
        self.expect(TokenType.LPAREN, "Falta '(' después de 'switch'")
        expr_node = self.parse_expression()
        self.expect(TokenType.RPAREN, "Falta ')' después de la expresión del 'switch'")
        self.structures.append({'line': s_token.line, 'type': 'Selección SWITCH', 'detail': 'Estructura switch'})
        body_node = self.parse_block()
        children = []
        if expr_node:
            expr_node['edge_label'] = 'value'
            children.append(expr_node)
        if body_node:
            body_node['edge_label'] = 'cases'
            children.append(body_node)
        return {
            'kind': 'control',
            'label': 'switch',
            'children': children
        }

    def parse_print(self) -> dict:
        p_token = self.advance()
        self.expect(TokenType.LPAREN, "Falta '(' después de 'print'")
        val_node = None
        if self.current_token() and self.current_token().type != TokenType.RPAREN:
            val_node = self.parse_expression()
        else:
            self.add_error("La función 'print()' requiere un valor dentro del paréntesis", p_token.line, p_token.column, p_token.value)
        self.expect(TokenType.RPAREN, "Falta ')' al cerrar 'print'")
        if self.expect(TokenType.SEMICOLON, "Falta ';' al final de 'print()'"):
            self.structures.append({'line': p_token.line, 'type': 'Impresión (I/O)', 'detail': 'print()'})
        return {
            'kind': 'io',
            'label': 'print',
            'children': [val_node] if val_node else []
        }

    def parse_return(self) -> dict:
        r_token = self.advance()
        val_node = None
        if self.current_token() and self.current_token().type not in [TokenType.SEMICOLON, TokenType.RBRACE]:
            val_node = self.parse_expression()
        if self.expect(TokenType.SEMICOLON, "Falta ';' después de 'return'"):
            self.structures.append({'line': r_token.line, 'type': 'Retorno', 'detail': 'return'})
        return {
            'kind': 'control',
            'label': 'return',
            'children': [val_node] if val_node else []
        }

    def parse_block(self) -> Optional[dict]:
        stmts = []
        if self.expect(TokenType.LBRACE, "Falta '{' para abrir el bloque de código"):
            while self.current_token() and self.current_token().type != TokenType.RBRACE:
                start_pos = self.pos
                s = self.parse_statement()
                if s:
                    stmts.append(s)
                if self.pos == start_pos and self.current_token() and self.current_token().type != TokenType.RBRACE:
                    self.advance()
            self.expect(TokenType.RBRACE, "Falta '}' para cerrar el bloque de código")
        else:
            if self.current_token():
                s = self.parse_statement()
                if s:
                    stmts.append(s)

        if len(stmts) == 1:
            return stmts[0]
        return {
            'kind': 'block',
            'label': 'statement\nsequence',
            'children': stmts
        }

    # ================= EXPRESIONES =================

    def parse_expression(self) -> Optional[dict]:
        return self.parse_logical()

    def parse_logical(self) -> Optional[dict]:
        left = self.parse_comparison()
        while self.match(TokenType.LOGICAL_AND, TokenType.LOGICAL_OR):
            op = self.previous_token().value
            right = self.parse_comparison()
            left = {
                'kind': 'op',
                'label': f"logical op\nop: {op}",
                'children': [c for c in [left, right] if c]
            }
        return left

    def parse_comparison(self) -> Optional[dict]:
        left = self.parse_additive()
        while self.match(TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.LESS_THAN, 
                         TokenType.LESS_EQUAL, TokenType.GREATER_THAN, TokenType.GREATER_EQUAL):
            op = self.previous_token().value
            right = self.parse_additive()
            left = {
                'kind': 'op',
                'label': f"compare\nop: {op}",
                'children': [c for c in [left, right] if c]
            }
        return left

    def parse_additive(self) -> Optional[dict]:
        left = self.parse_multiplicative()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.previous_token().value
            right = self.parse_multiplicative()
            left = {
                'kind': 'op',
                'label': f"bin op\nop: {op}",
                'children': [c for c in [left, right] if c]
            }
        return left

    def parse_multiplicative(self) -> Optional[dict]:
        left = self.parse_primary()
        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op = self.previous_token().value
            right = self.parse_primary()
            left = {
                'kind': 'op',
                'label': f"bin op\nop: {op}",
                'children': [c for c in [left, right] if c]
            }
        return left

    def parse_primary(self) -> Optional[dict]:
        token = self.current_token()
        if not token:
            prev = self.previous_token()
            line = prev.line if prev else 1
            col = prev.column if prev else 1
            self.add_error("Expresión incompleta al final del código", line, col)
            return None

        
        if self.match(TokenType.LOGICAL_NOT, TokenType.MINUS):
            op = self.previous_token().value
            operand = self.parse_primary()
            return {
                'kind': 'op',
                'label': f"unary op\nop: {op}",
                'children': [operand] if operand else []
            }

        
        if self.match(TokenType.LPAREN):
            if self.current_token() and self.current_token().type == TokenType.RPAREN:
                self.add_error("Paréntesis vacíos '()' dentro de la expresión", token.line, token.column, "()")
                self.advance()
                return None
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN, "Falta ')' para cerrar la expresión")
            return expr

       
        if self.match(TokenType.READ_INT, TokenType.READ_FLOAT):
            fn_tok = self.previous_token()
            self.expect(TokenType.LPAREN, f"Falta '(' después de '{fn_tok.value}'")
            self.expect(TokenType.RPAREN, f"Falta ')' después de '{fn_tok.value}'")
            return {'kind': 'io', 'label': f"input\n{fn_tok.value}()", 'children': []}

      
        if self.match(TokenType.INTEGER, TokenType.REAL, TokenType.STRING, TokenType.TRUE, TokenType.FALSE):
            lit_tok = self.previous_token()
            return {'kind': 'const', 'label': f"constant\nvalue: {lit_tok.value}", 'children': []}

        
        if self.match(TokenType.IDENTIFIER):
            id_tok = self.previous_token()
            if self.match(TokenType.LPAREN):
                args = []
                if self.current_token() and self.current_token().type != TokenType.RPAREN:
                    a = self.parse_expression()
                    if a:
                        args.append(a)
                    while self.match(TokenType.COMMA):
                        a = self.parse_expression()
                        if a:
                            args.append(a)
                self.expect(TokenType.RPAREN, f"Falta ')' en llamada a '{id_tok.value}'")
                return {'kind': 'io', 'label': f"call\n{id_tok.value}()", 'children': args}
            return {'kind': 'var', 'label': f"variable\nname: {id_tok.value}", 'children': []}

        
        self.add_error(
            f"Se esperaba un valor o expresión válida antes de '{token.value}'",
            token.line,
            token.column,
            token.value
        )
        if token.type not in [TokenType.SEMICOLON, TokenType.LBRACE, TokenType.RBRACE, TokenType.RPAREN]:
            self.advance()
        return None