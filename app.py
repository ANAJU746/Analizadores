"""
Aplicación Web Interactiva del Analizador Léxico y Sintáctico
Flask + HTML/CSS/JavaScript
"""

import os
import struct
import tempfile
import graphviz
from fpdf import FPDF
from flask import Flask, render_template, request, jsonify, send_file
from lexical_analyzer import LexicalAnalyzer, TokenType
from syntax_analyzer import SyntaxAnalyzer

app = Flask(__name__)
analyzer = LexicalAnalyzer()
syntax_analyzer = SyntaxAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        code = data.get('code', '')
        
        statistics = {
            'total_tokens': 0, 'keywords': 0, 'identifiers': 0,
            'operators': 0, 'delimiters': 0, 'literals': 0, 
            'errors': 0, 'syntax_errors': 0
        }
        
        if not code.strip():
            return jsonify({
                'tokens': [], 
                'errors': [], 
                'syntax_errors': [],
                'structures': [],
                'syntax_valid': True,
                'statistics': statistics, 
                'success': True
            })
        
        # 1. ANÁLISIS LÉXICO
        tokens = analyzer.analyze(code)
        tokens_data = []
        
        keywords_types = [
            TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STRING_TYPE, 
            TokenType.VOID, TokenType.IF, TokenType.ELSE, TokenType.WHILE, 
            TokenType.FOR, TokenType.RETURN, TokenType.TRUE, TokenType.FALSE,
            TokenType.SWITCH, TokenType.PRINT, TokenType.READ_INT, TokenType.READ_FLOAT
        ]
        
        operators_types = [
            TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY, TokenType.DIVIDE,
            TokenType.MODULO, TokenType.ASSIGN, TokenType.EQUAL, TokenType.NOT_EQUAL,
            TokenType.LESS_THAN, TokenType.LESS_EQUAL, TokenType.GREATER_THAN,
            TokenType.GREATER_EQUAL, TokenType.LOGICAL_AND, TokenType.LOGICAL_OR,
            TokenType.LOGICAL_NOT
        ]
        
        delimiters_types = [
            TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACE, TokenType.RBRACE,
            TokenType.LBRACKET, TokenType.RBRACKET, TokenType.SEMICOLON,
            TokenType.COMMA, TokenType.DOT, TokenType.COLON
        ]
        
        literals_types = [TokenType.INTEGER, TokenType.REAL, TokenType.STRING]

        for token in tokens:
            category = 'other'
            if token.type in keywords_types:
                category = 'keyword'
                statistics['keywords'] += 1
            elif token.type == TokenType.IDENTIFIER:
                category = 'identifier'
                statistics['identifiers'] += 1
            elif token.type in operators_types:
                category = 'operator'
                statistics['operators'] += 1
            elif token.type in delimiters_types:
                category = 'delimiter'
                statistics['delimiters'] += 1
            elif token.type in literals_types:
                category = 'literal'
                statistics['literals'] += 1
            
            statistics['total_tokens'] += 1
            tokens_data.append({
                'type': token.type.value,
                'value': token.value,
                'line': token.line,
                'column': token.column,
                'category': category
            })
        
        # 2. ANÁLISIS SINTÁCTICO
        syntax_result = syntax_analyzer.parse(tokens)
        
        all_errors = []
        for error in analyzer.error_report.errors:
            statistics['errors'] += 1
            all_errors.append({
                'type': 'Léxico',
                'message': f"[Error Léxico] {error['message']}",
                'line': error['line'],
                'column': error['column'],
                'char': error['char']
            })
            
        for s_error in syntax_result['errors']:
            statistics['errors'] += 1
            statistics['syntax_errors'] += 1
            all_errors.append({
                'type': 'Sintáctico',
                'message': f"[Error Sintáctico] {s_error['message']}",
                'line': s_error['line'],
                'column': s_error['column'],
                'char': s_error['char']
            })

        all_errors.sort(key=lambda e: (e['line'], e['column']))
        
        return jsonify({
            'tokens': tokens_data,
            'errors': all_errors,
            'syntax_errors': syntax_result['errors'],
            'structures': syntax_result['structures'],
            'syntax_valid': syntax_result['valid'] and len(analyzer.error_report.errors) == 0,
            'statistics': statistics,
            'success': True
        })
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 400


@app.route('/api/download_ast', methods=['POST'])
def download_ast():
    try:
        data = request.json
        code = data.get('code', '')
        
        tokens = analyzer.analyze(code)
        syntax_result = syntax_analyzer.parse(tokens)
        ast_root = syntax_result.get('ast')
        

        if ast_root and len(ast_root.get('children', [])) > 5:
            decls = [c for c in ast_root['children'] if c.get('kind') == 'decl']
            main_stmts = [c for c in ast_root['children'] if c.get('kind') not in ['decl', 'io']]
            io_stmts = [c for c in ast_root['children'] if c.get('kind') == 'io']
            
            balanced_children = []
            if decls:
                balanced_children.append({'kind': 'block', 'label': 'declarations\nblock', 'edge_label': 'init', 'children': decls})
            balanced_children.extend(main_stmts)
            if io_stmts:
                balanced_children.append({'kind': 'block', 'label': 'output\nsequence', 'edge_label': 'output', 'children': io_stmts})
            ast_root = {'kind': 'root', 'label': 'statement\nsequence', 'children': balanced_children}

        
        dot = graphviz.Digraph(comment='AST', format='png')
        dot.attr(rankdir='TB', dpi='250', nodesep='0.28', ranksep='0.48', splines='line')
        dot.attr('node', shape='box', style='filled', fontname='Times-Roman', fontsize='11', margin='0.14,0.08', color='#334155', penwidth='1.0')
        dot.attr('edge', fontname='Times-Roman', fontsize='10', penwidth='1.3', color='#0f172a', arrowhead='none')

        palette = {
            'root':    ('#cce5ff', '#000000'), # Azul cielo (statement sequence)
            'block':   ('#cce5ff', '#000000'), # Azul cielo (bloques)
            'control': ('#cce5ff', '#000000'), # Azul cielo (while, branch/if, for, return)
            'assign':  ('#cce5ff', '#000000'), # Azul cielo (assign)
            'decl':    ('#e0f2fe', '#000000'), # Azul claro (declaraciones)
            'op':      ('#cce5ff', '#000000'), # Azul cielo (compare, bin op, logical op)
            'var':     ('#99ff99', '#000000'), # Verde (variable)
            'const':   ('#fff9c4', '#000000'), # Amarillo crema (constant)
            'io':      ('#f3e8ff', '#000000'), # Lavanda suave (print / read_int / read_float)
            'error':   ('#fecaca', '#7f1d1d')  # Rojo claro (error)
        }

        counter = [0]
        def add_ast_nodes(node, parent_id=None):
            if not node:
                return
            my_id = f"n_{counter[0]}"
            counter[0] += 1
            
            kind = node.get('kind', 'control')
            fill_col, font_col = palette.get(kind, ('#cce5ff', '#000000'))
            label = str(node.get('label', ''))
            
            dot.node(my_id, label, fillcolor=fill_col, fontcolor=font_col)
            
            if parent_id is not None:
                edge_lbl = node.get('edge_label', '')
                if edge_lbl:
                    dot.edge(parent_id, my_id, label=f" {edge_lbl} ")
                else:
                    dot.edge(parent_id, my_id)
                    
            for child in node.get('children', []):
                add_ast_nodes(child, my_id)

        add_ast_nodes(ast_root)

       
        base_path = os.path.join(tempfile.gettempdir(), 'ast_tree_render')
        img_path = dot.render(base_path, view=False, cleanup=True)

        
        with open(img_path, 'rb') as f:
            f.seek(16)
            img_w, img_h = struct.unpack('>II', f.read(8))

        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(88, 28, 135)
        pdf.cell(0, 8, txt="ÁRBOL SINTÁCTICO ABSTRACTO (AST)", ln=True, align='C')

       
        max_w, max_h = 277.0, 175.0
        ratio = min(max_w / float(img_w), max_h / float(img_h))
        final_w = img_w * ratio
        final_h = img_h * ratio

       
        x_pos = (297.0 - final_w) / 2.0
        y_pos = 20.0 + (max_h - final_h) / 2.0

        pdf.image(img_path, x=x_pos, y=y_pos, w=final_w, h=final_h)

        pdf_path = os.path.join(tempfile.gettempdir(), 'Arbol_Sintactico_ITVH.pdf')
        pdf.output(pdf_path)

        return send_file(pdf_path, as_attachment=True, download_name='Arbol_Sintactico_ITVH.pdf')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n🚀 Iniciando Analizador Léxico y Sintáctico Web...")
    print("🌐 Abre http://localhost:5000 en tu navegador")
    app.run(debug=True, port=5000)