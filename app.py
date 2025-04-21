from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
from datetime import datetime
import glob
from posicao_acionaria import process_historical_data
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configuração do diretório de dados
DATA_DIR = "data"

def get_available_companies():
    """Retorna lista de empresas disponíveis nos arquivos CSV"""
    companies = []
    csv_files = glob.glob(os.path.join(DATA_DIR, "fre_cia_aberta_posicao_acionaria_*.csv"))
    
    for file in csv_files:
        try:
            df = pd.read_csv(
                file,
                sep=os.getenv('CSV_SEPARATOR', ';'),
                encoding=os.getenv('CSV_ENCODING', 'latin-1'),
                decimal=os.getenv('CSV_DECIMAL', ',')
            )
            if 'CNPJ_Companhia' in df.columns and 'Nome_Companhia' in df.columns:
                # Obtém as combinações únicas de CNPJ e Nome
                unique_companies = df[['CNPJ_Companhia', 'Nome_Companhia']].drop_duplicates()
                # Converte para lista de dicionários
                companies.extend(unique_companies.to_dict('records'))
        except Exception as e:
            print(f"Erro ao ler arquivo {file}: {str(e)}")
    
    # Remove duplicatas mantendo a primeira ocorrência
    seen = set()
    unique_companies = []
    for company in companies:
        key = (company['CNPJ_Companhia'], company['Nome_Companhia'])
        if key not in seen:
            seen.add(key)
            unique_companies.append({
                'cnpj': company['CNPJ_Companhia'],
                'nome': company['Nome_Companhia']
            })
    
    # Ordena por nome da empresa
    return sorted(unique_companies, key=lambda x: x['nome'])

@app.route('/')
def index():
    companies = get_available_companies()
    return render_template('index.html', companies=companies)

@app.route('/api/company/data')
def get_company_data():
    cnpjs = request.args.getlist('cnpj')
    if not cnpjs:
        return jsonify({"error": "Nenhum CNPJ fornecido"}), 400
    
    all_data = []
    for cnpj in cnpjs:
        print(f"Processando dados para CNPJ: {cnpj}")
        try:
            data = process_historical_data(cnpj)
            if data is not None:
                # Adiciona o CNPJ aos dados para identificação
                data['CNPJ'] = cnpj
                all_data.append(data)
        except Exception as e:
            print(f"Erro ao processar dados para CNPJ {cnpj}: {str(e)}")
            continue
    
    if not all_data:
        return jsonify({"error": "Nenhum dado encontrado para as empresas selecionadas"}), 404
    
    # Concatena todos os dados
    final_data = pd.concat(all_data, ignore_index=True)
    
    # Processa os dados para o formato necessário
    processed_data = []
    
    # Agrupa por CNPJ, ano e acionista
    grouped = final_data.groupby(['CNPJ', 'Ano', 'Acionista'])
    
    for (cnpj, year, shareholder), group in grouped:
        try:
            percentual = float(group['Percentual_Total_Acoes_Circulacao'].iloc[0])
            processed_data.append({
                'cnpj': cnpj,
                'ano': int(year),
                'acionista': shareholder,
                'percentual_total': percentual
            })
        except Exception as e:
            print(f"Erro ao processar dados do acionista {shareholder} no ano {year}: {str(e)}")
            continue
    
    return jsonify(processed_data)

if __name__ == '__main__':
    app.run(debug=True) 