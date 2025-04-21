import pandas as pd
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import glob
import numpy as np

# Load environment variables from .env file
load_dotenv()

# --- Settings ---

# 1. Get historical data directory from environment variables
historical_data_dir = os.getenv('HISTORICAL_DATA_DIR')

# 2. Get CSV configuration from environment variables
csv_separator = os.getenv('CSV_SEPARATOR', ';')
csv_encoding = os.getenv('CSV_ENCODING', 'latin-1')
csv_decimal = os.getenv('CSV_DECIMAL', ',')

def process_historical_data(company_cnpj):
    """Processa os dados históricos de uma empresa específica"""
    if not company_cnpj:
        print("ERRO: CNPJ da empresa não fornecido")
        return None

    # --- Directory Validation ---
    if not historical_data_dir or not os.path.exists(historical_data_dir):
        print("="*70)
        print("ERRO: Diretório de dados históricos não definido ou inválido.")
        print("Por favor, verifique se a pasta 'data' existe no diretório do projeto.")
        print("="*70)
        return None

    # --- Reading and Processing ---
    print(f"Tentando ler os arquivos do diretório: {historical_data_dir}")
    try:
        all_data = []
        
        # Lista todos os arquivos CSV no diretório, ordenados por ano
        csv_files = sorted(glob.glob(os.path.join(historical_data_dir, "fre_cia_aberta_posicao_acionaria_*.csv")))
        
        if not csv_files:
            print("="*70)
            print("ERRO: Nenhum arquivo CSV encontrado no diretório 'data'.")
            print("Certifique-se de que os arquivos seguem o padrão 'fre_cia_aberta_posicao_acionaria_YYYY.csv'")
            print("="*70)
            return None
        
        for file in csv_files:
            try:
                # Extrai o ano do nome do arquivo
                year = int(os.path.basename(file).split('_')[-1].split('.')[0])
                print(f"Processando dados de {year}...")
                
                # Lê o arquivo CSV
                df = pd.read_csv(
                    file,
                    sep=csv_separator,
                    encoding=csv_encoding,
                    decimal=csv_decimal
                )
                
                # Verifica se as colunas necessárias existem
                required_columns = ['CNPJ_Companhia', 'Acionista', 'Percentual_Total_Acoes_Circulacao']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    print(f"ERRO: Colunas ausentes no arquivo {file}: {missing_columns}")
                    continue
                
                # Filtra pela empresa
                company_data = df[df['CNPJ_Companhia'] == company_cnpj].copy()
                
                if not company_data.empty:
                    # Converte a coluna de percentual para numérico
                    company_data['Percentual_Total_Acoes_Circulacao'] = pd.to_numeric(
                        company_data['Percentual_Total_Acoes_Circulacao'].str.replace(',', '.'), 
                        errors='coerce'
                    )
                    
                    # Filtra linhas onde a participação é 100% ou 0%
                    company_data = company_data[
                        (company_data['Percentual_Total_Acoes_Circulacao'] < 100) & 
                        (company_data['Percentual_Total_Acoes_Circulacao'] > 0)
                    ].copy()
                    
                    if not company_data.empty:
                        print(f"Encontrados {len(company_data)} registros válidos para {company_cnpj} em {year}")
                        # Adiciona o ano aos dados
                        company_data['Ano'] = year
                        all_data.append(company_data)
                    else:
                        print(f"Nenhum registro válido encontrado para {company_cnpj} em {year}")
                else:
                    print(f"Nenhum registro encontrado para {company_cnpj} em {year}")
                    
            except Exception as e:
                print(f"Erro ao processar arquivo {file}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        if not all_data:
            print(f"\nNenhum dado encontrado para o CNPJ {company_cnpj} nos arquivos fornecidos.")
            return None
        
        # Concatena todos os dados
        final_df = pd.concat(all_data, ignore_index=True)
        print(f"Total de registros processados: {len(final_df)}")
        
        # Verifica se há dados válidos
        if final_df['Percentual_Total_Acoes_Circulacao'].isna().all():
            print("ERRO: Todos os valores de participação são nulos")
            return None
            
        return final_df
        
    except Exception as e:
        print(f"\nERRO inesperado durante o processamento: {e}")
        print("Verifique as configurações e a integridade dos arquivos CSV.")
        import traceback
        traceback.print_exc()
        return None

def generate_visualization(df_company, company_name, ticker, output_file='shareholder_evolution.png'):
    """Gera a visualização dos dados históricos"""
    try:
        # --- Selecionar e Renomear Colunas para Exibição ---
        df_display = df_company[[
            'Ano',
            'Acionista',
            'Quantidade_Acao_Ordinaria_Circulacao',
            'Percentual_Acao_Ordinaria_Circulacao',
            'Quantidade_Acao_Preferencial_Circulacao',
            'Percentual_Acao_Preferencial_Circulacao',
            'Quantidade_Total_Acoes_Circulacao',
            'Percentual_Total_Acoes_Circulacao'
        ]].copy()

        rename_map = {
            'Acionista': 'Acionista',
            'Quantidade_Acao_Ordinaria_Circulacao': 'Qtd ON',
            'Percentual_Acao_Ordinaria_Circulacao': '% ON',
            'Quantidade_Acao_Preferencial_Circulacao': 'Qtd PN',
            'Percentual_Acao_Preferencial_Circulacao': '% PN',
            'Quantidade_Total_Acoes_Circulacao': 'Qtd Total',
            'Percentual_Total_Acoes_Circulacao': '% Total'
        }
        df_display.rename(columns=rename_map, inplace=True)

        # --- Convert types for sorting and formatting ---
        numeric_cols = ['Qtd ON', '% ON', 'Qtd PN', '% PN', 'Qtd Total', '% Total']
        for col in numeric_cols:
            df_display[col] = pd.to_numeric(df_display[col], errors='coerce')

        # --- Filter out invalid participation rows ---
        df_display = df_display[(df_display['% Total'] < 100) & (df_display['% Total'] > 0)].copy()

        # --- Sort ---
        df_display.sort_values(by=['Ano', '% Total'], ascending=[True, False], inplace=True)

        # --- Create Visualization ---
        plt.figure(figsize=(15, 8))
        
        # Agrupa dados por acionista
        shareholders = df_display.groupby('Acionista')
        
        # Cores para os diferentes acionistas
        colors = plt.cm.Set3(np.linspace(0, 1, len(shareholders)))
        
        for (shareholder, data), color in zip(shareholders, colors):
            plt.plot(data['Ano'], 
                    pd.to_numeric(data['% Total'].str.rstrip('%').astype(float)),
                    label=shareholder,
                    marker='o',
                    color=color)
        
        # Customize the chart
        plt.title(f'Evolução da Participação Acionária - {company_name} ({ticker})', pad=20)
        plt.xlabel('Ano')
        plt.ylabel('Participação (%)')
        plt.xticks(sorted(df_display['Ano'].unique()))
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Ajusta o layout para acomodar a legenda
        plt.tight_layout()
        
        # Save the chart
        plt.savefig(output_file, bbox_inches='tight', dpi=300)
        print(f"\nGráfico salvo como '{output_file}'")
        
        return df_display
        
    except Exception as e:
        print(f"\nERRO ao gerar visualização: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # Este bloco não será mais executado diretamente
    print("Este módulo deve ser importado e usado por app.py")