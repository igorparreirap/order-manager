import csv
import json

def importar_csv_para_json():
    produtos = {}
    
    # Tenta ler com encoding latin1 (comum em arquivos do Excel/Windows)
    try:
        arquivo = open('relacao_produtos.csv', 'r', encoding='latin1')
    except:
        arquivo = open('relacao_produtos.csv', 'r', encoding='utf-8')

    with arquivo as f:
        reader = csv.DictReader(f, delimiter=';')
        
        for row in reader:
            codigo = row['codigo'].strip()
            # Limpa o nome removendo espaços extras e caracteres estranhos
            nome = row['nome'].strip().replace('Â', '')
            
            # Pega o preço da coluna 'preco'
            try:
                # Garante que decimal seja ponto
                preco_str = row['preco'].replace(',', '.')
                preco = float(preco_str)
            except (ValueError, KeyError):
                preco = 0.0
                
            produtos[codigo] = {
                "nome": nome,
                "preco": preco
            }
            
    # Sobrescreve o produtos.json com os novos dados
    with open('produtos.json', 'w', encoding='utf-8') as f:
        json.dump(produtos, f, indent=4, ensure_ascii=False)
        
    print(f"Prontinho! {len(produtos)} produtos foram importados para o produtos.json.")

if __name__ == "__main__":
    importar_csv_para_json()