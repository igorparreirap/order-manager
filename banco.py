import json
import os
from datetime import datetime

class BancoDados:
    def __init__(self):
        self.arquivo_produtos = "produtos.json"
        self.arquivo_pedidos = "pedidos.json"
        self.arquivo_clientes = "clientes.json"
        
        self.produtos = {}
        self.pedidos = []
        self.clientes = {}

        self.ddd_por_uf = {
            'AC': '68', 'AL': '82', 'AP': '96', 'AM': '92', 'BA': '71', 
            'CE': '85', 'DF': '61', 'ES': '27', 'GO': '62', 'MA': '98',
            'MT': '65', 'MS': '67', 'MG': '31', 'PA': '91', 'PB': '83',
            'PR': '41', 'PE': '81', 'PI': '86', 'RJ': '21', 'RN': '84',
            'RS': '51', 'RO': '69', 'RR': '95', 'SC': '47', 'SP': '11',
            'SE': '79', 'TO': '63'
        }
        self.carregar_dados()

    def carregar_dados(self):
        # Carrega Produtos
        if os.path.exists(self.arquivo_produtos):
            try:
                with open(self.arquivo_produtos, 'r', encoding='utf-8') as f:
                    self.produtos = json.load(f)
            except: self.produtos = {}
        
        # Carrega Pedidos
        if os.path.exists(self.arquivo_pedidos):
            try:
                with open(self.arquivo_pedidos, 'r', encoding='utf-8') as f:
                    self.pedidos = json.load(f)
            except: self.pedidos = []

        # Carrega Clientes
        if os.path.exists(self.arquivo_clientes):
            try:
                with open(self.arquivo_clientes, 'r', encoding='utf-8') as f:
                    self.clientes = json.load(f)
            except: self.clientes = {}

    # --- PEDIDOS (NOVA LÓGICA DE EDIÇÃO) ---
    def salvar_novo_pedido(self, dados_pedido):
        # Se não tiver ID (é novo), cria um baseado no timestamp
        if not dados_pedido.get('id'):
            dados_pedido['id'] = int(datetime.now().timestamp())
            self.pedidos.append(dados_pedido)
        else:
            # Se já tem ID, é uma edição. Vamos atualizar na lista.
            self.atualizar_pedido_existente(dados_pedido)
            
        self.salvar_arquivo_pedidos()

    def atualizar_pedido_existente(self, dados_atualizados):
        for i, p in enumerate(self.pedidos):
            if p['id'] == dados_atualizados['id']:
                self.pedidos[i] = dados_atualizados
                break

    def salvar_arquivo_pedidos(self):
        try:
            with open(self.arquivo_pedidos, 'w', encoding='utf-8') as f:
                json.dump(self.pedidos, f, indent=4, ensure_ascii=False)
        except: pass

    # --- CLIENTES ---
    def salvar_cliente(self, dados_cliente):
        nome = dados_cliente['nome'].strip().upper()
        self.clientes[nome] = dados_cliente
        self.salvar_arquivo_clientes()

    def salvar_arquivo_clientes(self):
        try:
            with open(self.arquivo_clientes, 'w', encoding='utf-8') as f:
                json.dump(self.clientes, f, indent=4, ensure_ascii=False)
        except: pass

    def get_cliente(self, nome):
        return self.clientes.get(nome.strip().upper(), None)

    # --- PRODUTOS ---
    def salvar_produto(self, codigo, nome, preco):
        self.produtos[str(codigo)] = {
            "nome": nome.upper(),
            "preco": float(preco)
        }
        self.salvar_arquivo_produtos()

    def remover_produto(self, codigo):
        if str(codigo) in self.produtos:
            del self.produtos[str(codigo)]
            self.salvar_arquivo_produtos()

    def gerar_proximo_codigo(self):
        maior = 0
        for cod in self.produtos.keys():
            if cod.isdigit():
                if int(cod) > maior:
                    maior = int(cod)
        return str(maior + 1)

    def salvar_arquivo_produtos(self):
        try:
            with open(self.arquivo_produtos, 'w', encoding='utf-8') as f:
                json.dump(self.produtos, f, indent=4, ensure_ascii=False)
        except: pass

    # --- UTIL ---
    def get_produto(self, codigo):
        if codigo in self.produtos:
            return self.produtos[codigo].copy()
        return None

    def get_ddd(self, uf):
        return self.ddd_por_uf.get(uf.upper(), "")

    def filtrar_pedidos(self, texto="", data_inicio=None, data_fim=None):
        resultados = []
        texto = texto.lower().strip()
        for p in self.pedidos:
            try: data_ped = datetime.strptime(p['data'], "%d/%m/%Y").date()
            except: continue

            if data_inicio and data_ped < data_inicio: continue
            if data_fim and data_ped > data_fim: continue

            match = False
            if not texto: match = True
            elif texto in p['cliente'].lower(): match = True
            else:
                for item in p['itens']:
                    if texto in item['nome'].lower() or texto in item['codigo'].lower():
                        match = True
                        break
            if match: resultados.append(p)
        return sorted(resultados, key=lambda x: x['id'], reverse=True)