# Instruções Rápidas - Deploy Streamlit Cloud 2025

## Resumo Executivo
Guia rápido para fazer deploy da aplicação Dashboard TopCity no Streamlit Cloud.

## Pré-requisitos
- Conta GitHub ativa
- Conta Streamlit Cloud (share.streamlit.io)
- Todos os arquivos do projeto preparados

## Passos Rápidos

### 1. Preparar Repositório GitHub
```bash
# Criar repositório no GitHub (via interface web)
# Clonar localmente
git clone https://github.com/seu-usuario/nome-repositorio.git

# Copiar arquivos para o repositório
cp -r streamlit_dashboard/* nome-repositorio/

# Commit e push
cd nome-repositorio
git add .
git commit -m "Initial commit: Dashboard TopCity"
git push origin main
```

### 2. Deploy no Streamlit Cloud
1. Acesse https://share.streamlit.io
2. Clique em "New app"
3. Selecione o repositório GitHub
4. Configure:
   - Branch: main
   - Main file path: app.py
   - URL personalizada (opcional)

### 3. Configurar Secrets
1. Na aplicação deployada, clique em "Settings"
2. Vá para "Secrets"
3. Adicione:
```toml
app_password = "sua_senha_aqui"
```

### 4. Verificar Deploy
- Aguarde o build completar (2-5 minutos)
- Teste a aplicação
- Verifique autenticação
- Teste todas as funcionalidades

## Estrutura de Arquivos Necessária
```
projeto/
├── app.py                    # Aplicação principal
├── column_mapping.py         # Mapeamento de colunas
├── requirements.txt          # Dependências
├── README.md                # Documentação
├── .streamlit/
│   ├── config.toml          # Configurações
│   └── secrets.toml         # Secrets (não commitado)
└── .gitignore               # Arquivos ignorados
```

## Troubleshooting Rápido

### Erro de Dependências
- Verifique requirements.txt
- Teste localmente: `pip install -r requirements.txt`

### Erro de Importação
- Verifique se todos os arquivos .py estão no repositório
- Confirme nomes dos arquivos

### Erro de Autenticação
- Verifique se o secret "app_password" está configurado
- Confirme a sintaxe TOML

### Aplicação Não Carrega
- Verifique logs no Streamlit Cloud
- Confirme se app.py está no root do repositório
- Teste localmente: `streamlit run app.py`

## Comandos Úteis
```bash
# Testar localmente
streamlit run app.py

# Verificar sintaxe
python -m py_compile app.py

# Atualizar aplicação
git add .
git commit -m "Update: descrição da mudança"
git push origin main
```

## Links Importantes
- **Streamlit Cloud:** https://share.streamlit.io
- **Documentação:** https://docs.streamlit.io
- **GitHub:** https://github.com

## Suporte
Para problemas detalhados, consulte o arquivo `GUIA_DEPLOY_STREAMLIT_2025.md` que contém instruções completas e troubleshooting avançado.

