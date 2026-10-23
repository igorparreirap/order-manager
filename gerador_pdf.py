from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
import os

class GeradorPDF:
    def gerar_pdf(self, dados, nome_arquivo):
        c = canvas.Canvas(nome_arquivo, pagesize=A4)
        width, height = A4
        
        # Margens iniciais
        y = height - 15 * mm 
        left = 20 * mm
        
        # --- LOGO ---
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            try:
                # Carrega a imagem para pegar as dimensões originais e manter proporção
                img = ImageReader(logo_path)
                img_w, img_h = img.getSize()
                aspect = img_h / float(img_w)
                
                # Define largura desejada no PDF (ex: 60mm)
                display_width = 60 * mm
                display_height = display_width * aspect
                
                # Centraliza a imagem: (Largura da Pág - Largura Img) / 2
                x_centered = (width - display_width) / 2
                
                # Desenha a imagem (x, y, width, height)
                # Subtrai a altura da imagem do Y atual
                y -= display_height
                c.drawImage(logo_path, x_centered, y, width=display_width, height=display_height, mask='auto')
                
                # Dá um espaço extra abaixo do logo
                y -= 10 * mm
            except Exception as e:
                print(f"Erro ao carregar logo no PDF: {e}")
        else:
            # Se não tiver logo, só desce um pouco para o título
            y -= 10 * mm

        # --- CABEÇALHO DE TEXTO ---
        c.setFont("Helvetica-Bold", 16)
        # Centraliza o título também
        c.drawCentredString(width / 2, y, "PEDIDO DE VENDAS")
        y -= 15 * mm
        
        # Dados do Cliente
        c.setFont("Helvetica", 12)
        c.drawString(left, y, f"Data: {dados['data']}")
        y -= 6 * mm
        c.drawString(left, y, f"Cliente: {dados['cliente']}")
        y -= 6 * mm
        c.drawString(left, y, f"Contato: {dados['telefone']} - {dados['contato'] if 'contato' in dados else ''}")
        y -= 6 * mm
        
        end = dados['endereco']
        endereco_str = f"{end['rua']}, {end['numero']} - {end['bairro']} - {end['cidade']}/{end['uf']}"
        c.drawString(left, y, endereco_str)
        y -= 15 * mm
        
        # --- TABELA HEADER ---
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "CÓD")
        c.drawString(left + 25*mm, y, "PRODUTO")
        c.drawString(left + 110*mm, y, "QTD")
        c.drawString(left + 130*mm, y, "UNIT (R$)")
        c.drawString(left + 160*mm, y, "TOTAL (R$)")
        y -= 2 * mm
        c.line(left, y, width - left, y)
        y -= 5 * mm
        
        # --- ITENS ---
        c.setFont("Helvetica", 10)
        for item in dados['itens']:
            if y < 30 * mm: # Nova página se acabar espaço
                c.showPage()
                y = height - 20 * mm
                c.setFont("Helvetica", 10)
            
            c.drawString(left, y, str(item['codigo']))
            # Corta nome se for muito longo
            nome = item['nome'][:45] 
            c.drawString(left + 25*mm, y, nome)
            c.drawString(left + 110*mm, y, str(item['qtd']))
            c.drawString(left + 130*mm, y, f"{item['unit']:.2f}")
            c.drawString(left + 160*mm, y, f"{item['total']:.2f}")
            y -= 5 * mm

        c.line(left, y, width - left, y)
        y -= 8 * mm
        
        # --- TOTAIS ---
        c.setFont("Helvetica-Bold", 12)
        c.drawString(left + 130*mm, y, "TOTAL:")
        c.drawString(left + 160*mm, y, f"R$ {dados['total_geral']:.2f}")
        y -= 8 * mm
        
        c.setFont("Helvetica", 10)
        c.drawString(left, y, f"Forma de Pagamento: {dados['pagamento']}")
        
        # Rodapé
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(left, 15*mm, "Gerado pelo Sistema de Pedidos")
        
        c.save()
        return True