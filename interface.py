import sys
import os
import serial.tools.list_ports
import requests
import subprocess
import shutil
import webbrowser 
from urllib.parse import quote 
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QFrame, QHBoxLayout, QVBoxLayout, 
                             QHeaderView, QTableWidgetItem, QFileDialog, 
                             QAbstractItemView, QCompleter, QWidget)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QThread, QLocale

# Fluent Widgets Imports
from qfluentwidgets import (
    FluentWindow, SubtitleLabel, PrimaryPushButton, PushButton,
    TableWidget, LineEdit, ComboBox, DoubleSpinBox, SpinBox, DatePicker,
    FluentIcon as FIF, NavigationItemPosition, CardWidget, InfoBar, 
    InfoBarPosition, StrongBodyLabel, setTheme, Theme, CalendarPicker,
    BodyLabel, SwitchButton, ScrollArea
)

# Nossos módulos
from banco import BancoDados
from impressora import ImpressoraTermica
from gerador_pdf import GeradorPDF
from gerenciador_config import ConfigManager

# --- FUNÇÃO AUXILIAR ---
def abrir_arquivo_automaticamente(caminho_arquivo):
    try:
        if sys.platform == 'win32': os.startfile(caminho_arquivo)
        elif sys.platform == 'darwin': subprocess.call(['open', caminho_arquivo])
        else: subprocess.call(['xdg-open', caminho_arquivo])
    except: pass

# --- Thread Busca CEP ---
class BuscaCepThread(QThread):
    resultado_pronto = pyqtSignal(dict)
    erro_ocorreu = pyqtSignal(str)
    def __init__(self, cep):
        super().__init__()
        self.cep = cep
    def run(self):
        try:
            response = requests.get(f"https://viacep.com.br/ws/{self.cep}/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "erro" not in data: self.resultado_pronto.emit(data)
                else: self.erro_ocorreu.emit("CEP não encontrado.")
            else: self.erro_ocorreu.emit("Erro no servidor.")
        except Exception as e: self.erro_ocorreu.emit(f"Erro: {str(e)}")


# --- PÁGINA DE CONFIGURAÇÕES ---
class ConfiguracoesPage(ScrollArea):
    sinal_tema_mudou = pyqtSignal(str) # Sinal para avisar a janela principal

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("configuracoesPage")
        self.cfg = ConfigManager()
        
        self.scrollWidget = QWidget()
        self.scrollWidget.setObjectName("scrollWidget") # Nome para CSS
        self.layout = QVBoxLayout(self.scrollWidget)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)
        
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        self.layout.addWidget(SubtitleLabel("Configurações do Sistema", self))
        
        self.create_aparencia_group()
        self.create_impressao_group()
        self.create_empresa_group()
        self.create_dados_group()
        self.layout.addStretch()

    def create_aparencia_group(self):
        card = CardWidget(self)
        l = QVBoxLayout(card)
        l.addWidget(StrongBodyLabel("Aparência"))
        
        self.combo_tema = ComboBox()
        self.combo_tema.addItems(["Claro", "Escuro"])
        tema_salvo = self.cfg.get("tema")
        self.combo_tema.setCurrentText(tema_salvo if tema_salvo else "Claro")
        self.combo_tema.currentTextChanged.connect(self.mudar_tema)
        
        l.addWidget(BodyLabel("Tema do Sistema:"))
        l.addWidget(self.combo_tema)
        self.layout.addWidget(card)

    def create_impressao_group(self):
        card = CardWidget(self)
        l = QVBoxLayout(card)
        l.addWidget(StrongBodyLabel("Impressão"))
        
        self.combo_portas = ComboBox()
        portas = serial.tools.list_ports.comports()
        self.combo_portas.addItem("Selecione...")
        for p in portas: self.combo_portas.addItem(p.device)
        
        porta_salva = self.cfg.get("porta_impressora")
        if porta_salva: self.combo_portas.setCurrentText(porta_salva)
        self.combo_portas.currentTextChanged.connect(lambda t: self.cfg.set("porta_impressora", t))

        self.switch_pdf = SwitchButton()
        self.switch_pdf.setOnText("Sim")
        self.switch_pdf.setOffText("Não")
        self.switch_pdf.setChecked(self.cfg.get("abrir_pdf_auto"))
        self.switch_pdf.checkedChanged.connect(lambda c: self.cfg.set("abrir_pdf_auto", c))

        l.addWidget(BodyLabel("Impressora Padrão:"))
        l.addWidget(self.combo_portas)
        l.addSpacing(10)
        
        row_pdf = QHBoxLayout()
        row_pdf.addWidget(BodyLabel("Abrir PDF automaticamente após salvar?"))
        row_pdf.addWidget(self.switch_pdf)
        row_pdf.addStretch()
        l.addLayout(row_pdf)
        self.layout.addWidget(card)

    def create_empresa_group(self):
        card = CardWidget(self)
        l = QVBoxLayout(card)
        l.addWidget(StrongBodyLabel("Dados da Empresa (Cupom)"))
        
        self.input_empresa = LineEdit()
        self.input_empresa.setText(self.cfg.get("empresa_nome"))
        self.input_empresa.setPlaceholderText("Nome no cabeçalho")
        self.input_empresa.editingFinished.connect(lambda: self.cfg.set("empresa_nome", self.input_empresa.text()))
        
        self.input_rodape = LineEdit()
        self.input_rodape.setText(self.cfg.get("empresa_rodape"))
        self.input_rodape.setPlaceholderText("Mensagem de rodapé")
        self.input_rodape.editingFinished.connect(lambda: self.cfg.set("empresa_rodape", self.input_rodape.text()))
        
        l.addWidget(BodyLabel("Nome da Empresa:"))
        l.addWidget(self.input_empresa)
        l.addWidget(BodyLabel("Rodapé do Cupom:"))
        l.addWidget(self.input_rodape)
        self.layout.addWidget(card)

    def create_dados_group(self):
        card = CardWidget(self)
        l = QVBoxLayout(card)
        l.addWidget(StrongBodyLabel("Segurança de Dados"))
        
        btn_backup = PushButton(FIF.SAVE, "Fazer Backup dos Dados")
        btn_backup.clicked.connect(self.fazer_backup)
        l.addWidget(BodyLabel("Salvar cópia de segurança:"))
        l.addWidget(btn_backup)
        self.layout.addWidget(card)

    def mudar_tema(self, text):
        self.cfg.set("tema", text)
        self.sinal_tema_mudou.emit(text) # Avisa a MainWindow para repintar

    def fazer_backup(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Backup")
        if pasta:
            try:
                data_hoje = datetime.now().strftime("%Y-%m-%d")
                destino = os.path.join(pasta, f"Backup_Pedidos_{data_hoje}")
                os.makedirs(destino, exist_ok=True)
                for f in ["produtos.json", "clientes.json", "pedidos.json", "config.json"]:
                    if os.path.exists(f): shutil.copy2(f, destino)
                InfoBar.success(title='Sucesso', content=f"Backup salvo em: {destino}", parent=self)
            except Exception as e:
                InfoBar.error(title='Erro', content=f"Falha no backup: {e}", parent=self)


# --- PÁGINA NOVO PEDIDO ---
class PedidoPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("pedidoPage")
        self.banco = BancoDados()
        self.cfg = ConfigManager()
        self.id_edicao = None 
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)

        self.lbl_titulo = SubtitleLabel("Emissão de Novo Pedido", self)
        self.layout.addWidget(self.lbl_titulo)
        
        self.create_form_section()
        self.create_table_section()
        self.create_footer_section()

    def create_form_section(self):
        row = QHBoxLayout()
        row.setSpacing(20)
        
        # Esquerda
        left_card = CardWidget(self)
        left_layout = QVBoxLayout(left_card)
        self.cliente_input = LineEdit()
        self.cliente_input.setPlaceholderText("Nome do Cliente (Busca)")
        self.cliente_input.setClearButtonEnabled(True)
        self.atualizar_completer_clientes()
        self.cliente_input.editingFinished.connect(self.preencher_cliente_se_existir)
        
        self.data_input = CalendarPicker(self)
        self.data_input.setDateFormat("dd/MM/yyyy")
        self.data_input.setDate(QDate.currentDate())
        
        self.pagamento_input = ComboBox()
        self.pagamento_input.addItems(["Na entrega", "PIX", "Cartão", "Dinheiro"])
        self.contato_nome = LineEdit()
        self.contato_nome.setPlaceholderText("Responsável")
        self.contato_telefone = LineEdit()
        self.contato_telefone.setPlaceholderText("Celular")
        self.contato_telefone.setInputMask("(00) 00000-0000;_")
        
        btn_salvar_cli = PushButton(FIF.SAVE, "Salvar Cliente")
        btn_salvar_cli.clicked.connect(self.salvar_cliente_atual)
        
        left_layout.addWidget(StrongBodyLabel("Cliente"))
        left_layout.addWidget(self.cliente_input)
        r2 = QHBoxLayout()
        r2.addWidget(self.data_input)
        r2.addWidget(self.pagamento_input)
        left_layout.addLayout(r2)
        left_layout.addWidget(self.contato_nome)
        left_layout.addWidget(self.contato_telefone)
        left_layout.addWidget(btn_salvar_cli)
        row.addWidget(left_card, 1)

        # Direita
        right_card = CardWidget(self)
        right_layout = QVBoxLayout(right_card)
        self.cep_input = LineEdit()
        self.cep_input.setPlaceholderText("CEP")
        self.cep_input.setInputMask("00000-000;_")
        self.cep_input.editingFinished.connect(self.iniciar_busca_cep)
        self.rua_input = LineEdit()
        self.rua_input.setPlaceholderText("Rua")
        r_num = QHBoxLayout()
        self.numero_input = LineEdit()
        self.numero_input.setPlaceholderText("Nº")
        self.bairro_input = LineEdit()
        self.bairro_input.setPlaceholderText("Bairro")
        r_num.addWidget(self.numero_input, 1)
        r_num.addWidget(self.bairro_input, 2)
        r_city = QHBoxLayout()
        self.cidade_input = LineEdit()
        self.uf_input = LineEdit()
        self.uf_input.setFixedWidth(60)
        r_city.addWidget(self.cidade_input)
        r_city.addWidget(self.uf_input)

        right_layout.addWidget(StrongBodyLabel("Endereço"))
        right_layout.addWidget(self.cep_input)
        right_layout.addWidget(self.rua_input)
        right_layout.addLayout(r_num)
        right_layout.addLayout(r_city)
        row.addWidget(right_card, 1)
        self.layout.addLayout(row)

    def create_table_section(self):
        container = CardWidget(self)
        vbox = QVBoxLayout(container)
        hbox = QHBoxLayout()
        self.btn_add = PushButton(FIF.ADD, "Adicionar Produto")
        self.btn_add.clicked.connect(self.add_row)
        self.btn_del = PushButton(FIF.DELETE, "Remover")
        self.btn_del.clicked.connect(self.remove_row)
        hbox.addWidget(self.btn_add)
        hbox.addWidget(self.btn_del)
        hbox.addStretch()
        vbox.addLayout(hbox)

        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Cód", "Produto", "Qtd", "Unitário", "Total"])
        self.table.verticalHeader().hide()
        self.table.setBorderRadius(8)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        vbox.addWidget(self.table)
        self.layout.addWidget(container)

    def create_footer_section(self):
        footer = QHBoxLayout()
        self.combo_portas = ComboBox()
        self.atualizar_portas()
        
        porta_salva = self.cfg.get("porta_impressora")
        if porta_salva: self.combo_portas.setCurrentText(porta_salva)

        self.lbl_total = SubtitleLabel("Total: R$ 0,00")
        self.lbl_total.setStyleSheet("color: #0078D4;") 
        
        # Botões
        self.btn_cancel = PushButton(FIF.CANCEL, "Cancelar")
        self.btn_cancel.clicked.connect(self.acao_cancelar)
        self.btn_save_sys = PushButton(FIF.SAVE, "Salvar (Sistema)")
        self.btn_save_sys.clicked.connect(self.acao_salvar_sistema)
        self.btn_whatsapp = PushButton(FIF.CHAT, "Zap")
        self.btn_whatsapp.clicked.connect(self.enviar_whatsapp)
        self.btn_save_pdf = PushButton(FIF.SAVE, "PDF") # Ícone corrigido
        self.btn_save_pdf.clicked.connect(self.acao_salvar_pdf)
        self.btn_print = PrimaryPushButton(FIF.PRINT, "Imprimir")
        self.btn_print.clicked.connect(self.acao_imprimir)

        footer.addWidget(StrongBodyLabel("Impressora:"))
        footer.addWidget(self.combo_portas)
        footer.addStretch()
        footer.addWidget(self.lbl_total)
        footer.addSpacing(10)
        
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_save_sys)
        footer.addSpacing(10)
        footer.addWidget(self.btn_whatsapp)
        footer.addWidget(self.btn_save_pdf)
        footer.addWidget(self.btn_print)
        
        self.layout.addLayout(footer)

    def acao_cancelar(self):
        self.limpar_formulario()
        InfoBar.info(title='Cancelado', content="Operação cancelada. Formulário limpo.", parent=self)

    def acao_salvar_sistema(self):
        dados = self.coletar_dados()
        if not dados: return
        self.banco.salvar_novo_pedido(dados)
        self.limpar_formulario()
        InfoBar.success(title='Salvo', content="Pedido salvo no sistema com sucesso!", parent=self)

    def enviar_whatsapp(self):
        dados = self.coletar_dados()
        if not dados: return
        
        msg = f"*PEDIDO - {dados['cliente']}*\n"
        msg += f"Data: {dados['data']}\n\n"
        msg += "*ITENS:*\n"
        for item in dados['itens']:
            msg += f"- {item['qtd']}x {item['nome']} (R$ {item['total']:.2f})\n"
        msg += f"\n*TOTAL: R$ {dados['total_geral']:.2f}*\n"
        msg += f"Pagamento: {dados['pagamento']}"
        
        fone = "".join(filter(str.isdigit, dados['telefone']))
        if not fone: return InfoBar.warning(title='Atenção', content="Cliente sem telefone.", parent=self)
        if len(fone) <= 11: fone = "55" + fone
            
        link = f"https://web.whatsapp.com/send?phone={fone}&text={quote(msg)}"
        webbrowser.open(link)
        InfoBar.success(title='WhatsApp', content="Abrindo navegador...", parent=self)

    def acao_salvar_pdf(self):
        dados = self.coletar_dados()
        if not dados: return
        path_dl = os.path.join(os.path.expanduser("~"), "Downloads")
        nome_sugerido = os.path.join(path_dl, f"Pedido_{dados['cliente']}.pdf")
        nome, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", nome_sugerido, "PDF (*.pdf)")
        if nome:
            if GeradorPDF().gerar_pdf(dados, nome):
                InfoBar.success(title='Sucesso', content="PDF gerado!", parent=self)
                self.banco.salvar_novo_pedido(dados)
                self.limpar_formulario()
                if self.cfg.get("abrir_pdf_auto"): abrir_arquivo_automaticamente(nome)

    def acao_imprimir(self):
        dados = self.coletar_dados()
        if not dados: return
        porta = self.combo_portas.text()
        if "Sem impressora" in porta: return InfoBar.error(title='Erro', content="Impressora inválida.", parent=self)
        imp = ImpressoraTermica(porta)
        ok, msg = imp.imprimir_pedido(dados)
        if ok:
            InfoBar.success(title='Impresso', content="Pedido enviado.", parent=self)
            self.banco.salvar_novo_pedido(dados)
            self.limpar_formulario()
        else:
            InfoBar.error(title='Falha', content=msg, parent=self)

    def carregar_pedido_para_edicao(self, pedido):
        self.limpar_formulario(reset_id=False)
        self.id_edicao = pedido['id']
        self.lbl_titulo.setText(f"Editando Pedido #{pedido['id']}")
        self.lbl_titulo.setStyleSheet("color: #E65100;") 
        self.cliente_input.setText(pedido['cliente'])
        try:
            d = datetime.strptime(pedido['data'], "%d/%m/%Y")
            self.data_input.setDate(d)
        except: pass
        self.pagamento_input.setText(pedido['pagamento'])
        self.pagamento_input.setCurrentText(pedido['pagamento'])
        self.contato_nome.setText(pedido.get('contato', ''))
        tel = ''.join(filter(str.isdigit, pedido.get('telefone', '')))
        self.contato_telefone.setText(tel)
        end = pedido.get('endereco', {})
        self.cep_input.setText(end.get('cep', ''))
        self.rua_input.setText(end.get('rua', ''))
        self.numero_input.setText(end.get('numero', ''))
        self.bairro_input.setText(end.get('bairro', ''))
        self.cidade_input.setText(end.get('cidade', ''))
        self.uf_input.setText(end.get('uf', ''))
        self.table.setRowCount(0)
        for item in pedido['itens']: self.add_row_com_dados(item)
        self.atualizar_total_geral()
        InfoBar.info(title='Edição', content="Pedido carregado para edição.", parent=self)

    def add_row_com_dados(self, dados_item):
        self.add_row()
        row = self.table.rowCount() - 1
        w_cod = self.table.cellWidget(row, 0); w_cod.setText(dados_item['codigo'])
        w_nome = self.table.cellWidget(row, 1); w_nome.setText(dados_item['nome'])
        w_qtd = self.table.cellWidget(row, 2); w_qtd.setValue(int(dados_item['qtd']))
        self.table.item(row, 3).setText(f"{dados_item['unit']:.2f}")
        self.table.item(row, 4).setText(f"{dados_item['total']:.2f}")

    def atualizar_completer_clientes(self):
        lista = list(self.banco.clientes.keys())
        self.comp = QCompleter(lista)
        self.comp.setFilterMode(Qt.MatchContains)
        self.comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.cliente_input.setCompleter(self.comp)

    def salvar_cliente_atual(self):
        nome = self.cliente_input.text().strip()
        if not nome: return InfoBar.warning(title='Aviso', content="Nome vazio", parent=self)
        dados = {
            "nome": nome, "contato": self.contato_nome.text(), "telefone": self.contato_telefone.text(),
            "cep": self.cep_input.text(), "rua": self.rua_input.text(), "numero": self.numero_input.text(),
            "bairro": self.bairro_input.text(), "cidade": self.cidade_input.text(), "uf": self.uf_input.text()
        }
        self.banco.salvar_cliente(dados)
        self.atualizar_completer_clientes()
        InfoBar.success(title='Sucesso', content="Cliente salvo!", parent=self)

    def preencher_cliente_se_existir(self):
        c = self.banco.get_cliente(self.cliente_input.text().strip())
        if c:
            self.contato_nome.setText(c.get('contato', ''))
            tel = ''.join(filter(str.isdigit, c.get('telefone', '')))
            self.contato_telefone.setText(tel)
            self.cep_input.setText(c.get('cep', ''))
            self.rua_input.setText(c.get('rua', ''))
            self.numero_input.setText(c.get('numero', ''))
            self.bairro_input.setText(c.get('bairro', ''))
            self.cidade_input.setText(c.get('cidade', ''))
            self.uf_input.setText(c.get('uf', ''))
            InfoBar.info(title='Info', content="Cliente encontrado.", parent=self)

    def add_row(self):
        self.banco.carregar_dados() 
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        le_cod = LineEdit(); le_cod.setPlaceholderText("Cód")
        comp_cod = QCompleter(list(self.banco.produtos.keys()))
        comp_cod.setFilterMode(Qt.MatchStartsWith)
        le_cod.setCompleter(comp_cod)
        le_cod.editingFinished.connect(lambda: self.buscar_por_codigo(le_cod))
        self.table.setCellWidget(row, 0, le_cod)
        
        le_nome = LineEdit(); le_nome.setPlaceholderText("Produto...")
        comp_nome = QCompleter([p['nome'] for p in self.banco.produtos.values()])
        comp_nome.setFilterMode(Qt.MatchContains)
        le_nome.setCompleter(comp_nome)
        le_nome.editingFinished.connect(lambda: self.buscar_por_nome(le_nome))
        self.table.setCellWidget(row, 1, le_nome)
        
        sb_qtd = SpinBox(); sb_qtd.setRange(1, 9999)
        sb_qtd.valueChanged.connect(lambda: self.calcular_linha(row))
        self.table.setCellWidget(row, 2, sb_qtd)
        
        item_unit = QTableWidgetItem("0.00")
        item_unit.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item_unit.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 3, item_unit)
        
        item_total = QTableWidgetItem("0.00")
        item_total.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 4, item_total)
        le_cod.setFocus()

    def buscar_por_codigo(self, w):
        cod = w.text().strip()
        if not cod: return
        try: row = self.table.indexAt(w.pos()).row()
        except: return
        p = self.banco.get_produto(cod)
        if p:
            self.table.cellWidget(row, 1).setText(p['nome'])
            self.table.item(row, 3).setText(f"{p['preco']:.2f}")
            self.calcular_linha(row)

    def buscar_por_nome(self, w):
        nome = w.text().strip()
        if not nome: return
        try: row = self.table.indexAt(w.pos()).row()
        except: return
        for c, d in self.banco.produtos.items():
            if d['nome'].upper() == nome.upper():
                self.table.cellWidget(row, 0).setText(c)
                self.table.item(row, 3).setText(f"{d['preco']:.2f}")
                self.calcular_linha(row)
                break

    def calcular_linha(self, row):
        try:
            w_qtd = self.table.cellWidget(row, 2)
            text_unit = self.table.item(row, 3).text().replace(",", ".")
            unit_val = float(text_unit) if text_unit else 0.0
            if w_qtd:
                qtd = w_qtd.value()
                total = qtd * unit_val
                self.table.item(row, 4).setText(f"{total:.2f}")
                self.atualizar_total_geral()
        except: pass

    def remove_row(self):
        if self.table.currentRow() >= 0:
            self.table.removeRow(self.table.currentRow())
            self.atualizar_total_geral()

    def atualizar_total_geral(self):
        total = 0.0
        for r in range(self.table.rowCount()):
            try: total += float(self.table.item(r, 4).text())
            except: pass
        self.lbl_total.setText(f"Total: R$ {total:,.2f}")

    def atualizar_portas(self):
        self.combo_portas.clear()
        portas = serial.tools.list_ports.comports()
        if portas: 
            for p in portas: self.combo_portas.addItem(p.device)
        else: self.combo_portas.addItem("Sem impressora")

    def coletar_dados(self):
        if not self.cliente_input.text():
            InfoBar.warning(title='Atenção', content="Cliente vazio.", parent=self)
            return None
        dados = {
            "cliente": self.cliente_input.text(), "data": self.data_input.date.toString("dd/MM/yyyy"),
            "telefone": self.contato_telefone.text(), "contato": self.contato_nome.text(),
            "endereco": {
                "rua": self.rua_input.text(), "numero": self.numero_input.text(),
                "bairro": self.bairro_input.text(), "cidade": self.cidade_input.text(),
                "uf": self.uf_input.text(), "cep": self.cep_input.text()
            },
            "itens": [], "pagamento": self.pagamento_input.text(), "total_geral": 0.0
        }
        
        if self.id_edicao:
            dados['id'] = self.id_edicao

        for r in range(self.table.rowCount()):
            w_nome = self.table.cellWidget(r, 1)
            nome = w_nome.text() if w_nome else ""
            if not nome: continue
            qtd = self.table.cellWidget(r, 2).value()
            unit = float(self.table.item(r, 3).text())
            total = qtd * unit
            dados["total_geral"] += total
            dados["itens"].append({
                "codigo": self.table.cellWidget(r, 0).text(), "nome": nome,
                "qtd": qtd, "unit": unit, "total": total
            })
        if not dados["itens"]:
             InfoBar.warning(title='Atenção', content="Adicione produtos.", parent=self)
             return None
        return dados

    def limpar_formulario(self, reset_id=True):
        if reset_id:
            self.id_edicao = None
            self.lbl_titulo.setText("Emissão de Novo Pedido")
            self.lbl_titulo.setStyleSheet("") 
            
        self.cliente_input.clear()
        self.rua_input.clear()
        self.numero_input.clear()
        self.bairro_input.clear()
        self.cidade_input.clear()
        self.uf_input.clear()
        self.cep_input.clear()
        self.contato_nome.clear()
        self.contato_telefone.clear()
        self.table.setRowCount(0)
        self.atualizar_total_geral()

    def iniciar_busca_cep(self):
        cep = self.cep_input.text().replace("-", "").strip()
        if len(cep) == 8:
            self.thread = BuscaCepThread(cep)
            self.thread.resultado_pronto.connect(self.preencher_endereco)
            self.thread.start()
    
    def preencher_endereco(self, data):
        self.rua_input.setText(data.get("logradouro", ""))
        self.bairro_input.setText(data.get("bairro", ""))
        self.cidade_input.setText(data.get("localidade", ""))
        self.uf_input.setText(data.get("uf", ""))


# --- PÁGINAS RESTANTES (PRODUTOS / HISTÓRICO) ---
class ProdutosPage(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("produtosPage")
        self.banco = BancoDados()
        self.codigo_original = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(20)
        self.layout.addWidget(SubtitleLabel("Gerenciar Produtos", self))
        
        card = CardWidget(self); l = QVBoxLayout(card); row = QHBoxLayout()
        self.ci = LineEdit(); self.ci.setPlaceholderText("Cód. (Auto)")
        self.ni = LineEdit(); self.ni.setPlaceholderText("Nome")
        self.pi = DoubleSpinBox(); self.pi.setRange(0, 99999.99)
        row.addWidget(self.ci); row.addWidget(self.ni); row.addWidget(self.pi)
        btn = PrimaryPushButton(FIF.SAVE, "Salvar"); btn.clicked.connect(self.salvar)
        btn_clr = PushButton(FIF.REMOVE, "Limpar"); btn_clr.clicked.connect(self.limpar)
        l.addLayout(row); row_btns = QHBoxLayout(); row_btns.addStretch(); row_btns.addWidget(btn_clr); row_btns.addWidget(btn); l.addLayout(row_btns); self.layout.addWidget(card)
        
        self.si = LineEdit(); self.si.setPlaceholderText("Buscar..."); self.si.textChanged.connect(self.load)
        self.layout.addWidget(self.si)
        self.tb = TableWidget(self); self.tb.setColumnCount(3); self.tb.setHorizontalHeaderLabels(["Cód", "Nome", "Preço"])
        self.tb.verticalHeader().hide(); self.tb.cellClicked.connect(self.click)
        self.tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.layout.addWidget(self.tb); self.load()

    def load(self):
        t = self.si.text().lower(); self.banco.carregar_dados()
        res = []
        for c,d in self.banco.produtos.items():
            if t in c.lower() or t in d['nome'].lower(): res.append((c,d))
        try: res.sort(key=lambda x: int(x[0]) if x[0].isdigit() else x[0])
        except: pass
        self.tb.setRowCount(len(res))
        for i, (c,d) in enumerate(res):
            self.tb.setItem(i,0,QTableWidgetItem(c)); self.tb.setItem(i,1,QTableWidgetItem(d['nome'])); self.tb.setItem(i,2,QTableWidgetItem(f"{d['preco']:.2f}"))

    def click(self, r, c):
        self.ci.setText(self.tb.item(r,0).text()); self.ni.setText(self.tb.item(r,1).text())
        self.pi.setValue(float(self.tb.item(r,2).text().replace("R$ ","")))
        self.codigo_original = self.ci.text()

    def salvar(self):
        c, n, p = self.ci.text().strip(), self.ni.text().strip(), self.pi.value()
        if not n: return
        if not c: c = self.banco.gerar_proximo_codigo()
        if self.codigo_original and self.codigo_original != c: self.banco.remover_produto(self.codigo_original)
        self.banco.salvar_produto(c, n, p); self.load(); self.limpar()
        InfoBar.success(title='Salvo', content="Produto salvo", parent=self)

    def limpar(self):
        self.ci.clear(); self.ni.clear(); self.pi.setValue(0); self.codigo_original=None; self.tb.clearSelection()

class HistoricoPage(QFrame):
    sinal_editar_pedido = pyqtSignal(dict) 

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("historicoPage") 
        self.banco = BancoDados()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30,30,30,30)
        self.layout.addWidget(SubtitleLabel("Histórico", self))
        
        card = CardWidget(self); l = QHBoxLayout(card)
        self.si = LineEdit(); self.si.setPlaceholderText("Buscar..."); self.si.returnPressed.connect(self.load)
        b = PrimaryPushButton(FIF.SEARCH, "Filtrar"); b.clicked.connect(self.load)
        bp = PushButton(FIF.SAVE, "PDF"); bp.clicked.connect(self.pdf)
        bedit = PushButton(FIF.EDIT, "Editar"); bedit.clicked.connect(self.editar_selecionado)
        l.addWidget(self.si); l.addWidget(b); l.addStretch(); l.addWidget(bedit); l.addWidget(bp); self.layout.addWidget(card)
        
        self.tb = TableWidget(self); self.tb.setColumnCount(5); self.tb.setHorizontalHeaderLabels(["ID", "Data", "Cliente", "Total", "Pgto"])
        self.tb.verticalHeader().hide(); self.tb.setSelectionBehavior(TableWidget.SelectRows); self.tb.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tb.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.layout.addWidget(self.tb); self.load()

    def load(self):
        t = self.si.text(); self.banco.carregar_dados()
        res = self.banco.filtrar_pedidos(t)
        self.tb.setRowCount(len(res))
        for i, p in enumerate(res):
            self.tb.setItem(i,0,QTableWidgetItem(str(p['id']))); self.tb.setItem(i,1,QTableWidgetItem(p['data']))
            self.tb.setItem(i,2,QTableWidgetItem(p['cliente'])); self.tb.setItem(i,3,QTableWidgetItem(f"{p['total_geral']:.2f}"))
            self.tb.setItem(i,4,QTableWidgetItem(p['pagamento'])); self.tb.item(i,0).setData(Qt.UserRole, p)

    def pdf(self):
        r = self.tb.currentRow()
        if r >= 0:
            p = self.tb.item(r,0).data(Qt.UserRole)
            path_dl = os.path.join(os.path.expanduser("~"), "Downloads")
            n, _ = QFileDialog.getSaveFileName(self, "PDF", os.path.join(path_dl, f"Pedido_{p['cliente']}.pdf"), "PDF (*.pdf)")
            if n: GeradorPDF().gerar_pdf(p, n); abrir_arquivo_automaticamente(n)

    def editar_selecionado(self):
        r = self.tb.currentRow()
        if r >= 0:
            pedido = self.tb.item(r, 0).data(Qt.UserRole)
            self.sinal_editar_pedido.emit(pedido)
        else:
            InfoBar.warning(title='Atenção', content="Selecione um pedido para editar.", parent=self)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Pedidos")
        self.resize(1150, 750)
        self.cfg = ConfigManager()
        
        # Inicia tema
        t = self.cfg.get("tema")
        if t == "Escuro": 
            setTheme(Theme.DARK)
            self.aplicar_estilo("Escuro")
        elif t == "Claro": 
            setTheme(Theme.LIGHT)
            self.aplicar_estilo("Claro")
        
        self.pedido = PedidoPage(self)
        self.produtos = ProdutosPage(self)
        self.historico = HistoricoPage(self)
        self.config = ConfiguracoesPage(self)
        
        # Conexões
        self.historico.sinal_editar_pedido.connect(self.iniciar_edicao_pedido)
        self.config.sinal_tema_mudou.connect(self.aplicar_estilo_tema)
        
        self.initNavigation()

    def initNavigation(self):
        self.addSubInterface(self.pedido, FIF.SHOPPING_CART, "Novo Pedido")
        self.addSubInterface(self.produtos, FIF.TAG, "Produtos")
        self.addSubInterface(self.historico, FIF.HISTORY, "Histórico")
        self.addSubInterface(self.config, FIF.SETTING, "Configurações", position=NavigationItemPosition.BOTTOM)

    def iniciar_edicao_pedido(self, pedido):
        self.stackedWidget.setCurrentIndex(0)
        self.pedido.carregar_pedido_para_edicao(pedido)

    def aplicar_estilo_tema(self, tema):
        if tema == "Escuro": 
            setTheme(Theme.DARK)
            self.aplicar_estilo("Escuro")
        else: 
            setTheme(Theme.LIGHT)
            self.aplicar_estilo("Claro")

    def aplicar_estilo(self, tema):
        # Corrige o problema de "letra branca no fundo branco" no tema escuro
        if tema == "Escuro":
            self.setStyleSheet("""
                QFrame#pedidoPage, QFrame#produtosPage, QFrame#historicoPage, QWidget#scrollWidget {
                    background-color: #202020; 
                }
                QLabel, BodyLabel, StrongBodyLabel, SubtitleLabel {
                    color: white;
                }
                QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
                    background-color: #333333;
                    color: white;
                    border: 1px solid #454545;
                }
                QTableWidget {
                    background-color: #2b2b2b;
                    color: white;
                    gridline-color: #454545;
                }
                QHeaderView::section {
                    background-color: #333333;
                    color: white;
                }
            """)
        else:
            self.setStyleSheet("") # Remove estilo forçado para voltar ao padrão claro

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Portuguese, QLocale.Brazil)) 
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())