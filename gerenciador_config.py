import json
import os

class ConfigManager:
    def __init__(self):
        self.arquivo = "config.json"
        self.config = {
            "tema": "Claro",
            "porta_impressora": "",
            "vias_impressao": 1,
            "abrir_pdf_auto": True,
            "empresa_nome": "Minha Empresa",
            "empresa_rodape": "Obrigado pela preferencia!"
        }
        self.carregar()

    def carregar(self):
        if os.path.exists(self.arquivo):
            try:
                with open(self.arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.config.update(dados) # Atualiza mantendo chaves novas se houver
            except: pass

    def salvar(self):
        try:
            with open(self.arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar config: {e}")

    def get(self, chave):
        return self.config.get(chave)

    def set(self, chave, valor):
        self.config[chave] = valor
        self.salvar()