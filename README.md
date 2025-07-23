# Dashboard TopCity - Streamlit

Este é um dashboard interativo desenvolvido em Streamlit para análise de produtos e cidades.

## Funcionalidades

- Dashboard interativo com métricas de faturamento e pedidos
- Filtros por mês, estado, cidade e produto
- Gráficos de análise de desempenho
- Comparativos de período
- Export de dados em CSV
- Sistema de autenticação por senha

## Estrutura do Projeto

```
streamlit_dashboard/
├── app.py                    # Aplicação principal
├── column_mapping.py         # Mapeamento de colunas
├── requirements.txt          # Dependências Python
├── README.md                # Documentação
├── .streamlit/
│   ├── config.toml          # Configurações do Streamlit
│   └── secrets.toml         # Configurações secretas
└── .gitignore               # Arquivos ignorados pelo Git
```

## Como executar localmente

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Execute a aplicação:
```bash
streamlit run app.py
```

## Deploy no Streamlit Cloud

1. Faça upload dos arquivos para um repositório GitHub
2. Conecte o repositório no Streamlit Cloud
3. Configure os secrets através da interface web
4. Faça o deploy

## Configurações Necessárias

- Configure a senha no arquivo secrets.toml ou através do Streamlit Cloud
- Verifique se a planilha do Google Sheets está pública para leitura

