from escpos.printer import Serial
import textwrap
import os

class ImpressoraTermica:
    def __init__(self, porta_serial, baudrate=9600):
        self.porta = porta_serial
        self.baudrate = baudrate
        self.colunas = 48 

    def imprimir_pedido(self, dados):
        try:
            printer = Serial(devfile=self.porta, 
                           baudrate=self.baudrate, 
                           bytesize=8, 
                           parity='N', 
                           stopbits=1, 
                           timeout=1.00, 
                           dsrdtr=True)

            # --- LOGO ---
            printer.set(align='center')
            
            logo_path = "logo.png"
            if os.path.exists(logo_path):
                try:
                    # Imprime a imagem centralizada
                    # obs: Se a impressora demorar ou travar na imagem,
                    # pode ser necessário reduzir o tamanho do arquivo png original.
                    printer.image(logo_path)
                    printer.text("\n") # Espaço após logo
                except Exception as e:
                    # Se falhar a imagem, segue a vida sem travar o pedido
                    print(f"Erro ao imprimir logo térmico: {e}")

            # --- TÍTULO ---
            printer.text("PEDIDO DE VENDAS\n")
            printer.text("------------------------------------------------\n")
            
            # --- DADOS DO CLIENTE ---
            printer.set(align='left')
            printer.text(f"CLIENTE: {dados['cliente']}\n")
            printer.text(f"DATA:    {dados['data']}\n")
            
            if dados.get('contato'):
                printer.text(f"CONTATO: {dados['contato']}\n")
            
            printer.text(f"TEL:     {dados['telefone']}\n")
            
            # Endereço
            end = dados['endereco']
            endereco_str = f"{end['rua']}, {end['numero']} - {end['bairro']}"
            
            for linha in textwrap.wrap(endereco_str, width=self.colunas):
                printer.text(linha + "\n")
            
            printer.text(f"{end['cidade']}/{end['uf']} - CEP: {end['cep']}\n")
            printer.text("\n")

            # --- ITENS ---
            printer.set(align='center')
            printer.text("ITENS DO PEDIDO\n")
            printer.set(align='left')
            printer.text("-" * self.colunas + "\n")

            for item in dados['itens']:
                nome_completo = f"{item['codigo']} - {item['nome']}"
                
                for linha in textwrap.wrap(nome_completo, width=self.colunas):
                    printer.text(linha + "\n")
                
                txt_qtd = f"{item['qtd']}"
                txt_unit = f"R$ {item['unit']:.2f}"
                txt_total = f"R$ {item['total']:.2f}"
                
                linha_val = f"Qtd: {txt_qtd} x {txt_unit} = {txt_total}"
                
                espacos = self.colunas - len(linha_val)
                if espacos > 0:
                    printer.text(" " * espacos + linha_val + "\n")
                else:
                    printer.text(linha_val + "\n")
                
                printer.text("-" * self.colunas + "\n")

            # --- TOTAIS ---
            printer.text("\n")
            printer.set(align='right', text_type='B')
            printer.text(f"TOTAL GERAL: R$ {dados['total_geral']:.2f}\n")
            printer.set(align='left', text_type='NORMAL')
            
            printer.text("\n")
            printer.text(f"Forma de Pagamento: {dados['pagamento']}\n")
            
            # --- RODAPÉ ---
            printer.text("\n\n")
            printer.set(align='center')
            printer.text("Obrigado pela preferencia!\n\n\n")

            printer.cut()
            
            return True, "Impressão enviada com sucesso!"

        except Exception as e:
            return False, f"Erro na impressora: {str(e)}"