from typing import List, Optional
from lexical_analyzer import Token, TokenType

class SyntaxAnalyzer:
    def __init__(self):
        self.tokens: List[Token] = []
        self.pos: int = 0
        self.errors: List[dict] = []
        self.structures: List[dict] = []
        self.symbol_table: dict = {}
        self.loop_or_switch_depth: int = 0
        self.function_depth: int = 0

    def current_token(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek_token(self, offset: int = 1) -> Optional[Token]:
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
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
        
        if expected_type in [TokenType.SEMICOLON, TokenType.RPAREN, TokenType.COLON] and prev and (
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

    def expect_rparen_and_sync(self, error_msg: str):
        """Espera ')' y, si quedaron tokens sobrantes en la misma línea, sincroniza hasta ')' para no afectar al '{'."""
        if self.match(TokenType.RPAREN):
            return
        self.expect(TokenType.RPAREN, error_msg)
        prev = self.previous_token()
        ref_line = prev.line if prev else (self.current_token().line if self.current_token() else 1)
        while self.current_token() and self.current_token().line == ref_line:
            if self.current_token().type == TokenType.RPAREN:
                self.advance()
                break
            if self.current_token().type in [TokenType.LBRACE, TokenType.RBRACE, TokenType.SEMICOLON]:
                break
            self.advance()

    def add_error(self, message: str, line: int, column: int, token_val: str = ""):
        self.errors.append({
            'type': 'Sintáctico',
            'message': message,
            'line': line,
            'column': column,
            'char': token_val if token_val else message
        })

    def check_type_compatibility(self, var_type: TokenType, var_name: str, expr_node: Optional[dict], line: int, col: int):
        """Valida incompatibilidades de tipos en declaraciones y asignaciones."""
        if not expr_node or not var_type:
            return
        val_type = expr_node.get('value_type')
        if not val_type:
            return

        if var_type == TokenType.INT and val_type != 'int':
            self.add_error(
                f"Incompatibilidad de tipos: no se puede asignar un valor de tipo '{val_type}' a la variable '{var_name}' de tipo 'int'",
                line, col, var_name
            )
        elif var_type == TokenType.FLOAT and val_type not in ('float', 'int'):
            self.add_error(
                f"Incompatibilidad de tipos: no se puede asignar un valor de tipo '{val_type}' a la variable '{var_name}' de tipo 'float'",
                line, col, var_name
            )
        elif var_type == TokenType.STRING_TYPE and val_type != 'string':
            self.add_error(
                f"Incompatibilidad de tipos: no se puede asignar un valor de tipo '{val_type}' a la variable '{var_name}' de tipo 'string'",
                line, col, var_name
            )
        elif var_type == TokenType.BOOL and val_type != 'bool':
            self.add_error(
                f"Incompatibilidad de tipos: no se puede asignar un valor de tipo '{val_type}' a la variable '{var_name}' de tipo 'bool'",
                line, col, var_name
            )

    def parse(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors = []
        self.structures = []
        self.symbol_table = {}
        self.loop_or_switch_depth = 0
        self.function_depth = 0
        ast_statements = []

        while self.current_token() is not None:
            start_pos = self.pos
            node = self.parse_statement()
            if node:
                ast_statements.append(node)
            # Seguro anti-bucle infinito
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
            if self.current_token() and self.current_token().type == TokenType.LPAREN:
                self.advance()
                self.parse_expression()
                self.expect_rparen_and_sync("Falta ')'")
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
        elif token.type in [TokenType.READ_INT, TokenType.READ_FLOAT]:
            fn_tok = self.advance()
            self.add_error(
                f"La función de lectura '{fn_tok.value}()' debe asignarse a una variable (ej. x = {fn_tok.value}();)",
                fn_tok.line, fn_tok.column, fn_tok.value
            )
            if self.match(TokenType.LPAREN):
                self.expect_rparen_and_sync(f"Falta ')' en '{fn_tok.value}'")
            self.match(TokenType.SEMICOLON)
            return None
        elif token.type == TokenType.IDENTIFIER:
            if token.value == 'break':
                b_tok = self.advance()
                if self.loop_or_switch_depth == 0:
                    self.add_error(
                        "La instrucción 'break' solo puede usarse dentro de un ciclo ('while', 'for') o 'switch'",
                        b_tok.line, b_tok.column, b_tok.value
                    )
                self.expect(TokenType.SEMICOLON, "Falta ';' después de 'break'")
                return {'kind': 'control', 'label': 'break', 'children': []}
            elif token.value in ('case', 'default'):
                self.add_error(f"Etiqueta '{token.value}' fuera de una estructura 'switch'", token.line, token.column, token.value)
                self.advance()
                if token.value == 'case' and self.current_token() and self.current_token().type != TokenType.COLON:
                    self.advance()
                self.match(TokenType.COLON)
                return None
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

            stmt_starters = [
                TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STRING_TYPE,
                TokenType.VOID, TokenType.IF, TokenType.ELSE, TokenType.WHILE, TokenType.FOR,
                TokenType.SWITCH, TokenType.PRINT, TokenType.RETURN,
                TokenType.LBRACE, TokenType.RBRACE
            ]
            while (
                self.current_token()
                and self.current_token().line == first_bad.line
                and self.current_token().type not in stmt_starters
            ):
                tok_cur = self.current_token()
                bad_sequence += tok_cur.value
                self.advance()
                if tok_cur.type == TokenType.SEMICOLON:
                    break

            self.add_error(
                f"Secuencia o token inesperado '{bad_sequence}' al inicio de instrucción",
                first_bad.line,
                first_bad.column,
                first_bad.value
            )
            return None

    def parse_declaration(self) -> Optional[dict]:
        type_token = self.advance()
        id_token = self.expect(TokenType.IDENTIFIER, f"Falta nombre de identificador después de '{type_token.value}'")
        
        if not id_token:
            if self.current_token() and self.current_token().line == type_token.line and self.current_token().type not in [TokenType.SEMICOLON, TokenType.LBRACE, TokenType.RBRACE]:
                self.advance()
                if self.match(TokenType.ASSIGN):
                    self.parse_expression()
                self.match(TokenType.SEMICOLON)
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
                            self.add_error(f"Se esperaba tipo de dato válido en parámetro (se encontró '{t.value}')", t.line, t.column, t.value)
                        break
                    p_id = self.expect(TokenType.IDENTIFIER, "Falta nombre del parámetro")
                    if p_id:
                        self.symbol_table[p_id.value] = p_type.type
                        params_list.append(f"{p_type.value} {p_id.value}")
                    if not self.match(TokenType.COMMA):
                        break
            
            self.expect_rparen_and_sync("Falta ')' al cerrar parámetros de función")
            self.structures.append({'line': type_token.line, 'type': 'Declaración de Función', 'detail': f"{type_token.value} {id_token.value}()"})
            self.function_depth += 1
            body_node = self.parse_block()
            self.function_depth -= 1
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
        if type_token.type == TokenType.VOID:
            self.add_error(
                f"El tipo 'void' solo es válido para declarar funciones, no variables ('{id_token.value}')",
                type_token.line, type_token.column, type_token.value
            )

        if id_token.value in self.symbol_table:
            self.add_error(
                f"Redeclaración de variable: '{id_token.value}' ya fue declarada previamente",
                id_token.line, id_token.column, id_token.value
            )
        else:
            self.symbol_table[id_token.value] = type_token.type

        val_node = None
        if self.match(TokenType.ASSIGN):
            val_node = self.parse_expression()
            self.check_type_compatibility(type_token.type, id_token.value, val_node, id_token.line, id_token.column)
        
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
        
       
        if (
            self.current_token() and self.peek_token()
            and self.current_token().type in [TokenType.PLUS, TokenType.MINUS]
            and self.peek_token().type == self.current_token().type
            and self.current_token().line == id_token.line
        ):
            op_tok = self.advance()
            self.advance()
            op_str = "++" if op_tok.type == TokenType.PLUS else "--"
            if require_semicolon:
                if self.expect(TokenType.SEMICOLON, f"Falta punto y coma ';' después de '{id_token.value}{op_str}'"):
                    self.structures.append({'line': id_token.line, 'type': 'Asignación', 'detail': f"Incremento '{id_token.value}{op_str}'"})
            return {
                'kind': 'assign',
                'label': f"step\nop: {op_str}",
                'children': [{'kind': 'var', 'label': f"variable\nname: {id_token.value}", 'children': []}]
            }

   
        if (
            self.current_token() and self.peek_token()
            and self.current_token().type in [TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY, TokenType.DIVIDE]
            and self.peek_token().type == TokenType.ASSIGN
            and self.current_token().line == id_token.line
        ):
            op_tok = self.advance()
            self.advance()
            val_node = self.parse_expression()
            if require_semicolon:
                if self.expect(TokenType.SEMICOLON, f"Falta punto y coma ';' después de asignar a '{id_token.value}'"):
                    self.structures.append({'line': id_token.line, 'type': 'Asignación', 'detail': f"Variable '{id_token.value}'"})
            return {
                'kind': 'assign',
                'label': f"assign\nop: {op_tok.value}=",
                'children': [c for c in [{'kind': 'var', 'label': f"variable\nname: {id_token.value}", 'children': []}, val_node] if c]
            }

        
        if self.match(TokenType.ASSIGN):
            val_node = self.parse_expression()
            if id_token.value in self.symbol_table:
                self.check_type_compatibility(self.symbol_table[id_token.value], id_token.value, val_node, id_token.line, id_token.column)

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
            self.expect_rparen_and_sync(f"Falta ')' en llamada a función '{id_token.value}'")
            if require_semicolon:
                if self.expect(TokenType.SEMICOLON, f"Falta ';' después de llamar a '{id_token.value}()'"):
                    self.structures.append({'line': id_token.line, 'type': 'Llamada a Función', 'detail': f"{id_token.value}()"})
            return {
                'kind': 'io',
                'label': f"call\n{id_token.value}()",
                'children': args_nodes
            }
        else:
            if self.current_token() and self.current_token().type in [
                TokenType.LESS_THAN, TokenType.GREATER_THAN, TokenType.LESS_EQUAL,
                TokenType.GREATER_EQUAL, TokenType.EQUAL, TokenType.NOT_EQUAL
            ]:
                op_bad = self.advance()
                self.add_error(
                    f"Se esperaba una asignación '=' o llamada '()' para '{id_token.value}', no un operador relacional '{op_bad.value}'",
                    op_bad.line, op_bad.column, op_bad.value
                )
                self.parse_expression()
                if require_semicolon:
                    self.match(TokenType.SEMICOLON)
                return None

            self.add_error(
                f"Instrucción incompleta: identificador '{id_token.value}' suelto (se esperaba '=' o '()')", 
                id_token.line, id_token.column, id_token.value
            )
            if require_semicolon and self.current_token() and self.current_token().type == TokenType.SEMICOLON:
                self.advance()
            return None

    def parse_condition(self, construct_name: str, line: int, col: int) -> Optional[dict]:
        """Valida que la condición en if, while y for sea una expresión booleana/relacional válida."""
        if self.current_token() and self.current_token().type in [TokenType.RPAREN, TokenType.SEMICOLON]:
            self.add_error(f"La condición del '{construct_name}' no puede estar vacía", line, col, "()")
            return {'kind': 'error', 'label': 'condición vacía', 'children': []}

        if self.current_token() and self.current_token().type in [TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STRING_TYPE, TokenType.VOID]:
            bad_tok = self.advance()
            self.add_error(
                f"No se permite declarar variables ('{bad_tok.value}') dentro de la condición de '{construct_name}'",
                bad_tok.line, bad_tok.column, bad_tok.value
            )

        cond_node = self.parse_expression()

        if self.current_token() and self.current_token().type == TokenType.ASSIGN:
            eq_tok = self.advance()
            if self.current_token() and self.current_token().type in [TokenType.LESS_THAN, TokenType.GREATER_THAN]:
                op2 = self.advance()
                good_op = "<=" if op2.type == TokenType.LESS_THAN else ">="
                self.add_error(
                    f"Operador relacional mal escrito '={op2.value}' en '{construct_name}' (¿quisiste usar '{good_op}'?)",
                    eq_tok.line, eq_tok.column, f"={op2.value}"
                )
            else:
                self.add_error(
                    f"No se permite asignación '=' dentro de la condición de '{construct_name}' (¿quisiste usar '=='?)",
                    eq_tok.line, eq_tok.column, eq_tok.value
                )
            self.parse_expression()
            return cond_node

        if cond_node and cond_node.get('value_type') in ('int', 'float', 'string'):
            self.add_error(
                f"Condición inválida en '{construct_name}': se esperaba una comparación o expresión lógica, no un valor de tipo '{cond_node.get('value_type')}'",
                line, col, construct_name
            )

        return cond_node

    def parse_if(self) -> dict:
        if_token = self.advance()
        self.expect(TokenType.LPAREN, "Falta '(' después de 'if'")
        
        cond_node = self.parse_condition('if', if_token.line, if_token.column)
            
        self.expect_rparen_and_sync("Falta ')' después de la condición del 'if'")
        
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
            else_tok = self.previous_token()
            self.structures.append({'line': else_tok.line, 'type': 'Bloque ELSE', 'detail': 'Alternativa else'})
            if self.current_token() and self.current_token().type == TokenType.IF:
                else_node = self.parse_if()
            elif self.current_token() and self.current_token().type == TokenType.LPAREN:
                lp_tok = self.current_token()
                self.add_error(
                    "No se permite poner una condición directamente después de 'else' (¿quisiste escribir 'else if (...)'?)",
                    lp_tok.line, lp_tok.column, "else ("
                )
                self.advance()
                self.parse_expression()
                self.expect_rparen_and_sync("Falta ')'")
                else_node = self.parse_block()
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
        
        cond_node = self.parse_condition('while', w_token.line, w_token.column)
            
        self.expect_rparen_and_sync("Falta ')' después de la condición del 'while'")
        self.structures.append({'line': w_token.line, 'type': 'Ciclo WHILE', 'detail': 'Bucle while'})
        
        self.loop_or_switch_depth += 1
        body_node = self.parse_block()
        self.loop_or_switch_depth -= 1

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
        
        if self.current_token() and self.current_token().type == TokenType.RPAREN:
            self.add_error("El encabezado del ciclo 'for' no puede estar vacío (requiere inicialización; condición; incremento)", f_token.line, f_token.column, "for ()")
            self.advance()
            self.loop_or_switch_depth += 1
            body_node = self.parse_block()
            self.loop_or_switch_depth -= 1
            return {'kind': 'control', 'label': 'for', 'children': [body_node] if body_node else []}

        lookahead_idx = self.pos
        has_semicolon_in_header = False
        paren_depth = 0
        while lookahead_idx < len(self.tokens):
            t_look = self.tokens[lookahead_idx]
            if t_look.type == TokenType.LPAREN:
                paren_depth += 1
            elif t_look.type == TokenType.RPAREN:
                if paren_depth == 0:
                    break
                paren_depth -= 1
            elif t_look.type == TokenType.SEMICOLON and paren_depth == 0:
                has_semicolon_in_header = True
                break
            elif t_look.type == TokenType.LBRACE and paren_depth == 0:
                break
            lookahead_idx += 1

        if not has_semicolon_in_header:
            self.add_error(
                "Estructura 'for' inválida: se requieren 3 secciones separadas por ';' (inicialización; condición; incremento)",
                f_token.line, f_token.column, "for"
            )
            while self.current_token() and self.current_token().type not in [TokenType.RPAREN, TokenType.LBRACE]:
                self.advance()
            self.match(TokenType.RPAREN)
            self.loop_or_switch_depth += 1
            body_node = self.parse_block()
            self.loop_or_switch_depth -= 1
            return {'kind': 'control', 'label': 'for', 'children': [body_node] if body_node else []}

        init_node = None
        if self.current_token() and self.current_token().type in [TokenType.INT, TokenType.FLOAT]:
            init_node = self.parse_declaration()
        elif self.current_token() and self.current_token().type == TokenType.IDENTIFIER:
            init_node = self.parse_assignment_or_call(require_semicolon=True)
        else:
            self.expect(TokenType.SEMICOLON, "Falta ';' en inicialización del 'for'")

        cond_node = self.parse_condition('for', f_token.line, f_token.column)
        self.expect(TokenType.SEMICOLON, "Falta ';' después de condición del 'for'")

        inc_node = None
        if self.current_token() and self.current_token().type == TokenType.IDENTIFIER:
            inc_node = self.parse_assignment_or_call(require_semicolon=False)
        elif self.current_token() and self.current_token().type == TokenType.RPAREN:
            self.add_error("Falta expresión de incremento/actualización en el tercer bloque del 'for'", f_token.line, f_token.column, "for")

        self.expect_rparen_and_sync("Falta ')' al cerrar encabezado del 'for'")
        self.structures.append({'line': f_token.line, 'type': 'Ciclo FOR', 'detail': 'Bucle for'})
        
        self.loop_or_switch_depth += 1
        body_node = self.parse_block()
        self.loop_or_switch_depth -= 1

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
        
        if self.current_token() and self.current_token().type == TokenType.RPAREN:
            self.add_error("El selector del 'switch' no puede estar vacío", s_token.line, s_token.column, "()")
            expr_node = {'kind': 'error', 'label': 'selector vacío', 'children': []}
        else:
            expr_node = self.parse_additive()
            bad_cond_op = self.match(
                TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.LESS_THAN,
                TokenType.LESS_EQUAL, TokenType.GREATER_THAN, TokenType.GREATER_EQUAL,
                TokenType.LOGICAL_AND, TokenType.LOGICAL_OR, TokenType.ASSIGN
            )
            if bad_cond_op:
                self.add_error(
                    f"El 'switch' evalúa una variable o valor selector, no una condición u operación '{bad_cond_op.value}'",
                    bad_cond_op.line,
                    bad_cond_op.column,
                    bad_cond_op.value
                )
                self.parse_expression()

        self.expect_rparen_and_sync("Falta ')' después de la expresión del 'switch'")
        
        cases_nodes = []
        has_valid_cases = False
        self.loop_or_switch_depth += 1

        if self.expect(TokenType.LBRACE, "Falta '{' para abrir el bloque de 'switch'"):
            if self.current_token() and self.current_token().type == TokenType.RBRACE:
                self.add_error("El bloque 'switch' no puede estar vacío (requiere al menos un 'case' o 'default')", s_token.line, s_token.column, "switch")

            reported_missing_case = False
            while self.current_token() and self.current_token().type != TokenType.RBRACE:
                tok = self.current_token()

                if tok.type == TokenType.IDENTIFIER and tok.value in ('case', 'default'):
                    has_valid_cases = True
                    label_tok = self.advance()

                    if label_tok.value == 'case':
                        val_tok = self.match(TokenType.INTEGER, TokenType.REAL, TokenType.STRING, TokenType.IDENTIFIER)
                        if not val_tok:
                            cur = self.current_token()
                            self.add_error(
                                "Se esperaba un valor constante después de 'case'",
                                cur.line if cur else label_tok.line,
                                cur.column if cur else label_tok.column,
                                cur.value if cur else "case"
                            )
                        self.expect(TokenType.COLON, "Falta ':' después del valor del 'case'")
                        case_label = f"case {val_tok.value}:" if val_tok else "case ?:"
                    else:
                        self.expect(TokenType.COLON, "Falta ':' después de 'default'")
                        case_label = "default:"

                    case_stmts = []
                    while (
                        self.current_token()
                        and self.current_token().type != TokenType.RBRACE
                        and not (self.current_token().type == TokenType.IDENTIFIER and self.current_token().value in ('case', 'default'))
                    ):
                        start_pos = self.pos
                        stmt = self.parse_statement()
                        if stmt:
                            case_stmts.append(stmt)
                        if self.pos == start_pos and self.current_token() is not None:
                            self.advance()

                    cases_nodes.append({
                        'kind': 'block',
                        'label': case_label,
                        'edge_label': 'case',
                        'children': case_stmts
                    })
                else:
                    if not reported_missing_case:
                        self.add_error(
                            f"Estructura 'switch' inválida: se esperaba 'case <valor>:' o 'default:' antes de '{tok.value}'",
                            tok.line,
                            tok.column,
                            tok.value
                        )
                        reported_missing_case = True
                    start_pos = self.pos
                    stmt = self.parse_statement()
                    if stmt:
                        cases_nodes.append(stmt)
                    if self.pos == start_pos and self.current_token() is not None:
                        self.advance()

            self.expect(TokenType.RBRACE, "Falta '}' para cerrar el bloque de 'switch'")

        self.loop_or_switch_depth -= 1

        if has_valid_cases:
            self.structures.append({'line': s_token.line, 'type': 'Selección SWITCH', 'detail': 'Estructura switch'})

        children = []
        if expr_node:
            expr_node['edge_label'] = 'selector'
            children.append(expr_node)
        children.extend(cases_nodes)

        return {
            'kind': 'control',
            'label': 'switch',
            'children': children
        }

    def parse_print(self) -> dict:
        p_token = self.advance()
        self.expect(TokenType.LPAREN, "Falta '(' después de 'print'")
        val_node = None
        if self.current_token() and self.current_token().type not in [TokenType.RPAREN, TokenType.SEMICOLON]:
            val_node = self.parse_expression()
        else:
            self.add_error("La función 'print()' requiere un valor dentro del paréntesis", p_token.line, p_token.column, p_token.value)
        self.expect_rparen_and_sync("Falta ')' al cerrar 'print'")
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
        if self.current_token() and self.current_token().type == TokenType.SEMICOLON:
            bad_semi = self.advance()
            self.add_error(
                "Punto y coma ';' inesperado antes del bloque de código '{'",
                bad_semi.line, bad_semi.column, ";"
            )
            if not (self.current_token() and self.current_token().type == TokenType.LBRACE):
                return None

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
        node = self.parse_logical()
        while (
            self.current_token()
            and self.previous_token()
            and self.current_token().line == self.previous_token().line
            and self.current_token().type in [
                TokenType.IDENTIFIER, TokenType.INTEGER, TokenType.REAL,
                TokenType.STRING, TokenType.TRUE, TokenType.FALSE, TokenType.LPAREN
            ]
        ):
            bad_tok = self.current_token()
            self.add_error(
                f"Falta un operador antes de '{bad_tok.value}'",
                bad_tok.line, bad_tok.column, bad_tok.value
            )
            right = self.parse_logical()
            node = {
                'kind': 'error',
                'label': 'missing op',
                'children': [c for c in [node, right] if c]
            }
        return node

    def parse_logical(self) -> Optional[dict]:
        left = self.parse_comparison()
        while self.match(TokenType.LOGICAL_AND, TokenType.LOGICAL_OR):
            op = self.previous_token().value
            right = self.parse_comparison()
            left = {
                'kind': 'op',
                'label': f"logical op\nop: {op}",
                'value_type': 'bool',
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
                'value_type': 'bool',
                'children': [c for c in [left, right] if c]
            }
        return left

    def parse_additive(self) -> Optional[dict]:
        left = self.parse_multiplicative()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.previous_token().value
            right = self.parse_multiplicative()
            vtype = 'float' if (left and left.get('value_type') == 'float') or (right and right.get('value_type') == 'float') else (left.get('value_type') if left else None)
            left = {
                'kind': 'op',
                'label': f"bin op\nop: {op}",
                'value_type': vtype,
                'children': [c for c in [left, right] if c]
            }
        return left

    def parse_multiplicative(self) -> Optional[dict]:
        left = self.parse_primary()
        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op = self.previous_token().value
            right = self.parse_primary()
            vtype = 'float' if (left and left.get('value_type') == 'float') or (right and right.get('value_type') == 'float') else (left.get('value_type') if left else None)
            left = {
                'kind': 'op',
                'label': f"bin op\nop: {op}",
                'value_type': vtype,
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
                'value_type': 'bool' if op == '!' else (operand.get('value_type') if operand else None),
                'children': [operand] if operand else []
            }

        if self.match(TokenType.LPAREN):
            if self.current_token() and self.current_token().type == TokenType.RPAREN:
                self.add_error("Paréntesis vacíos '()' dentro de la expresión", token.line, token.column, "()")
                self.advance()
                return None
            expr = self.parse_expression()
            self.expect_rparen_and_sync("Falta ')' para cerrar la expresión")
            return expr

        if self.match(TokenType.READ_INT, TokenType.READ_FLOAT):
            fn_tok = self.previous_token()
            ret_type = 'int' if fn_tok.type == TokenType.READ_INT else 'float'
            if self.expect(TokenType.LPAREN, f"Falta '(' después de '{fn_tok.value}'"):
                if self.current_token() and self.current_token().type != TokenType.RPAREN:
                    bad_arg = self.current_token()
                    self.add_error(
                        f"La función '{fn_tok.value}()' no recibe parámetros (se encontró '{bad_arg.value}')",
                        bad_arg.line, bad_arg.column, bad_arg.value
                    )
                    while self.current_token() and self.current_token().line == fn_tok.line and self.current_token().type not in [TokenType.RPAREN, TokenType.SEMICOLON]:
                        self.advance()
                self.expect_rparen_and_sync(f"Falta ')' después de '{fn_tok.value}'")
            return {'kind': 'io', 'label': f"input\n{fn_tok.value}()", 'value_type': ret_type, 'children': []}

        if self.match(TokenType.INTEGER):
            lit_tok = self.previous_token()
            return {'kind': 'const', 'label': f"constant\nvalue: {lit_tok.value}", 'value_type': 'int', 'children': []}

        if self.match(TokenType.REAL):
            lit_tok = self.previous_token()
            return {'kind': 'const', 'label': f"constant\nvalue: {lit_tok.value}", 'value_type': 'float', 'children': []}

        if self.match(TokenType.STRING):
            lit_tok = self.previous_token()
            return {'kind': 'const', 'label': f"constant\nvalue: {lit_tok.value}", 'value_type': 'string', 'children': []}

        if self.match(TokenType.TRUE, TokenType.FALSE):
            lit_tok = self.previous_token()
            return {'kind': 'const', 'label': f"constant\nvalue: {lit_tok.value}", 'value_type': 'bool', 'children': []}

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
                self.expect_rparen_and_sync(f"Falta ')' en llamada a '{id_tok.value}'")
                return {'kind': 'io', 'label': f"call\n{id_tok.value}()", 'children': args}
            
            mapped_type = None
            if id_tok.value in self.symbol_table:
                t_enum = self.symbol_table[id_tok.value]
                mapped_type = {
                    TokenType.INT: 'int', TokenType.FLOAT: 'float',
                    TokenType.BOOL: 'bool', TokenType.STRING_TYPE: 'string'
                }.get(t_enum)
            return {'kind': 'var', 'label': f"variable\nname: {id_tok.value}", 'value_type': mapped_type, 'children': []}

        self.add_error(
            f"Se esperaba un valor o expresión válida antes de '{token.value}'",
            token.line,
            token.column,
            token.value
        )
        if token.type not in [TokenType.SEMICOLON, TokenType.LBRACE, TokenType.RBRACE, TokenType.RPAREN]:
            self.advance()
        return None