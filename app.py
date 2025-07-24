import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
import json

# Tentar importar bibliotecas do Google
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    st.warning("⚠️ Bibliotecas do Google não disponíveis. Usando método público.")

# Assegure-se de que 'column_mapping.py' esteja na mesma pasta
from column_mapping import column_mapping

# Helper function for Brazilian currency formatting (dot for thousands, comma for decimals)
def format_currency_br(value):
    if pd.isna(value) or value is None:
        return "R$ 0,00"
    # Format number with comma as decimal and dot as thousands, then swap them
    s_value = "{:,.2f}".format(value) # e.g., "1,234,567.89" (US locale default)
    # The trick: replace comma (US thousands) with a temp char, dot (US decimal) with comma, then temp char with dot
    s_value = s_value.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s_value}"

# Helper function for Brazilian integer formatting (dot for thousands, no decimals)
def format_integer_br(value):
    if pd.isna(value) or value is None:
        return "0"
    # Ensure value is treated as an integer before formatting
    int_value = int(value)
    s_value = "{:,.0f}".format(int_value) # e.g., "1,000" (US locale default)
    # The trick: replace comma (US thousands) with a temp char, dot (US decimal) with comma, then temp char with dot
    s_value = s_value.replace(",", "X").replace(".", ",").replace("X", ".")
    return s_value

# Configuração da página
st.set_page_config(
    page_title="Dashboard TopCity", 
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para autenticação Google
def get_google_client():
    """Tenta autenticar com Google usando credenciais dos secrets"""
    if not GOOGLE_AUTH_AVAILABLE:
        return None
    
    try:
        # Tentar obter credenciais dos secrets
        google_credentials = st.secrets.get("google_credentials")
        if google_credentials:
            # Parse das credenciais JSON
            creds_dict = json.loads(google_credentials)
            
            # Definir escopos necessários
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            
            # Criar credenciais
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            
            # Criar cliente gspread
            client = gspread.authorize(credentials)
            
            return client
        else:
            return None
    except Exception as e:
        st.warning(f"⚠️ Erro na autenticação Google: {e}")
        return None

senha_correta = st.secrets["app_password"]

# Controle de autenticação na sessão
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Se não estiver autenticado, mostra campo de senha
if not st.session_state.autenticado:
    with st.container():
        st.markdown("### 🔐 Acesso Restrito")
        senha = st.text_input("Digite a senha para acessar o dashboard:", type="password")
        if senha == senha_correta:
            st.session_state.autenticado = True
            st.success("✅ Acesso liberado com sucesso!")
            st.rerun()

        elif senha != "":
            st.error("❌ Senha incorreta. Tente novamente.")
    st.stop() 

# CSS personalizado para visual mais bonito
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #96ca00 0%, #4e9f00 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .metric-title {
        font-size: 1.1em;
        margin-bottom: 0.5rem;
        opacity: 0.8;
    }
    .metric-value {
        font-size: 2.2em;
        font-weight: bold;
    }
    .stMetric { /* Isso pode ser um seletor mais específico dependendo da versão do Streamlit */
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header {
        background: linear-gradient(90deg, #96ca00 0%, #4e9f00  100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    .chart-container {
        padding: 1.5rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
    }

    /* Estilo para os botões do Streamlit (ex: Resetar Filtros) */
    div.stButton > button {
        background-color: #96ca00; /* Cor verde Papello */
        color: white; /* Cor do texto do botão */
        border-radius: 5px; /* Bordas arredondadas */
        border: 1px solid #96ca00; /* Borda da mesma cor */
        padding: 0.5em 1em; /* Espaçamento interno */
    }

    /* Estilo para o botão ao passar o mouse */
    div.stButton > button:hover {
        background-color: #6b8f00; /* Um verde um pouco mais escuro ao passar o mouse */
        color: white;
        border: 1px solid #6b8f00;
    }

    /* NOVO: Estilo para os itens selecionados nos multiselects/selectboxes (para que fiquem pretos) */
    /* Este seletor pode precisar de ajustes dependendo da versão do Streamlit */
    /* Procure por classes como .stMultiSelect div[data-baseweb="tag"] ou similar no inspetor de elementos */
    .stMultiSelect div[data-baseweb="tag"], .stSelectbox div[data-baseweb="tag"] {
        background-color: #000000 !important; /* Cor de fundo preta */
        color: white !important; /* Cor do texto branca para contraste */
    }
    /* Seletor mais específico para o texto dentro dos tags selecionados */
    .stMultiSelect div[data-baseweb="tag"] span, .stSelectbox div[data-baseweb="tag"] span {
        color: white !important;
    }
    /* Seletor para o texto nos dropdowns (opções não selecionadas) - geralmente já é preto, mas para garantir */
    .stMultiSelect div[role="listbox"] div[data-baseweb="popover"] div[role="option"] span,
    .stSelectbox div[role="listbox"] div[data-baseweb="popover"] div[role="option"] span {
        color: black !important;
    }

</style>
""", unsafe_allow_html=True)

# Título Principal do Dashboard
st.markdown("<h1 class='main-header'>Dashboard de Análise de Produtos e Cidades 🏙️</h1>", unsafe_allow_html=True)

# Verificar autenticação Google
google_client = get_google_client()
if google_client:
    st.success("🔐 Dados carregados com segurança via autenticação Google!")
else:
    st.info("📊 Dados carregados via método público.")

@st.cache_data
def load_data():
    """
    Carrega e pré-processa os dados da planilha MENSAL do Google Sheets.
    """
    # PLANILHA MENSAL CORRETA
    sheet_id = st.secrets.get("planilha_mensal_id", '14Y-V3ezwo3LsHWERhSyURCtkQdN3drzv9F5JNRQnXEc')
    tab_name = 'Produtos_Cidades_Completas'
    
    with st.spinner("Carregando dados mensais... Por favor, aguarde."):
        try:
            if google_client:
                # Usar autenticação Google
                sheet = google_client.open_by_key(sheet_id)
                worksheet = sheet.worksheet(tab_name)
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
            else:
                # Fallback para método público
                google_sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
                df = pd.read_csv(google_sheet_url)
        except Exception as e:
            st.error(f"Erro ao carregar dados da planilha mensal: {e}")
            st.stop()

    if df.empty:
        st.warning("A planilha mensal está vazia.")
        st.stop()

    # Converter a coluna 'mes' para datetime
    df['mes'] = pd.to_datetime(df['mes'], format='%Y-%m')

    # Converter colunas numéricas, tratando vírgulas como separadores decimais
    df.loc[:, 'faturamento'] = pd.to_numeric(df['faturamento'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
    df.loc[:, 'faturamento_total_cidade_mes'] = pd.to_numeric(df['faturamento_total_cidade_mes'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
    df.loc[:, 'unidades_fisicas'] = pd.to_numeric(df['unidades_fisicas'], errors='coerce').fillna(0)
    df.loc[:, 'pedidos'] = pd.to_numeric(df['pedidos'], errors='coerce').fillna(0)
    df.loc[:, 'total_pedidos_cidade_mes'] = pd.to_numeric(df['total_pedidos_cidade_mes'], errors='coerce').fillna(0)

    # Renomear colunas usando o mapeamento
    df = df.rename(columns=column_mapping)

    # Calcular colunas derivadas
    df.loc[:, 'Participação Faturamento Cidade Mês (%)'] = np.where(
        df['Faturamento Total da Cidade no Mês'] == 0, 0,
        (df['Faturamento do Produto'] / df['Faturamento Total da Cidade no Mês']) * 100
    )
    df.loc[:, 'Participação Pedidos Cidade Mês (%)'] = np.where(
        df['Total de Pedidos da Cidade no Mês'] == 0, 0,
        (df['Pedidos com Produto'] / df['Total de Pedidos da Cidade no Mês']) * 100
    )
    df.loc[:, 'Ticket Médio do Produto'] = np.where(
        df['Pedidos com Produto'] == 0, 0,
        df['Faturamento do Produto'] / df['Pedidos com Produto']
    )

    return df

@st.cache_data
def load_daily_data():
    """Carrega dados da planilha DIÁRIA"""
    # PLANILHA DIÁRIA CORRETA
    sheet_id = st.secrets.get("planilha_diaria_id", '1cERMKGnnCH0y_C29QNfT__7zeB4bHVHaxdA3fTDcaxs')
    tab_name = 'ResumoDiarioProdutos'

    with st.spinner("Carregando dados diários..."):
        try:
            if google_client:
                # Usar autenticação Google
                sheet = google_client.open_by_key(sheet_id)
                worksheet = sheet.worksheet(tab_name)
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
            else:
                # Fallback para método público
                google_sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
                df = pd.read_csv(google_sheet_url)
        except Exception as e:
            st.error(f"Erro ao carregar dados diários: {e}")
            return pd.DataFrame()

    if df.empty:
        st.warning("A planilha diária está vazia.")
        return pd.DataFrame()

    # Converter data e tratar formatação CORRETAMENTE
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    # CORREÇÃO: tratar vírgula como decimal
    df['faturamento'] = df['faturamento'].astype(str).str.replace(',', '.').astype(float)
    df['quantidade_pedidos'] = pd.to_numeric(df['quantidade_pedidos'], errors='coerce').fillna(0)
    df['total_unidades'] = pd.to_numeric(df['total_unidades'], errors='coerce').fillna(0)

    # Adicionar colunas derivadas
    df['dia_semana'] = df['data'].dt.day_name()
    df['mes'] = df['data'].dt.to_period('M').astype(str)

    return df

# Carregar dados MENSAIS
df = load_data()

# Sidebar com filtros PARA ANÁLISE MENSAL
st.sidebar.header("⚙️ Filtros Globais")

# Botão para resetar filtros
if st.sidebar.button("🔄 Resetar Filtros"):
    # Limpar os filtros da sessão
    for key in ['selected_months', 'selected_estados', 'selected_cidades', 'selected_produtos']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# Filtro de Mês
meses_disponiveis = sorted(df['Mês'].dt.strftime('%Y-%m').unique())
selected_months = st.sidebar.multiselect(
    "📅 Selecione os meses:",
    options=meses_disponiveis,
    default=st.session_state.get('selected_months', []),
    key='selected_months'
)

# Aplicar filtro de mês primeiro
if selected_months:
    df_filtered = df[df['Mês'].dt.strftime('%Y-%m').isin(selected_months)]
else:
    df_filtered = df.copy()

# Filtro de Estado
estados_disponiveis = sorted(df_filtered['Estado'].unique())
selected_estados = st.sidebar.multiselect(
    "🗺️ Selecione os estados:",
    options=estados_disponiveis,
    default=st.session_state.get('selected_estados', []),
    key='selected_estados'
)

# Aplicar filtro de estado
if selected_estados:
    df_filtered = df_filtered[df_filtered['Estado'].isin(selected_estados)]

# Filtro de Cidade
cidades_disponiveis = sorted(df_filtered['Cidade'].unique())
selected_cidades = st.sidebar.multiselect(
    "🏙️ Selecione as cidades:",
    options=cidades_disponiveis,
    default=st.session_state.get('selected_cidades', []),
    key='selected_cidades'
)

# Aplicar filtro de cidade
if selected_cidades:
    df_filtered = df_filtered[df_filtered['Cidade'].isin(selected_cidades)]

# Filtro de Produto
produtos_disponiveis = sorted(df_filtered['Produto'].unique())
selected_produtos = st.sidebar.multiselect(
    "📦 Selecione os produtos:",
    options=produtos_disponiveis,
    default=st.session_state.get('selected_produtos', []),
    key='selected_produtos'
)

# Aplicar filtro de produto
if selected_produtos:
    df_filtered = df_filtered[df_filtered['Produto'].isin(selected_produtos)]

# Verificar se há dados após filtros
if df_filtered.empty:
    st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados. Tente ajustar os filtros.")
    st.stop()

# Indicador de filtros aplicados
filtros_ativos = []
if selected_months: filtros_ativos.append(f"Meses: {len(selected_months)}")
if selected_estados: filtros_ativos.append(f"Estados: {len(selected_estados)}")
if selected_cidades: filtros_ativos.append(f"Cidades: {len(selected_cidades)}")
if selected_produtos: filtros_ativos.append(f"Produtos: {len(selected_produtos)}")

if filtros_ativos:
    st.info(f"🎯 **Filtros ativos:** {' | '.join(filtros_ativos)} | **Registros:** {len(df_filtered):,}")

# Determinar se estamos analisando produtos específicos ou todos
analisando_produtos_especificos = bool(selected_produtos)

# KPIs principais
st.subheader("📊 Principais Indicadores")

if analisando_produtos_especificos:
    # KPIs para produtos selecionados
    total_faturamento = df_filtered['Faturamento do Produto'].sum()
    total_unidades = df_filtered['Unidades Compradas'].sum()
    total_pedidos = df_filtered['Pedidos com Produto'].sum()
    ticket_medio = total_faturamento / total_pedidos if total_pedidos > 0 else 0
    
    # Participação no faturamento total das cidades
    faturamento_total_cidades = df_filtered['Faturamento Total da Cidade no Mês'].sum()
    participacao_faturamento = (total_faturamento / faturamento_total_cidades * 100) if faturamento_total_cidades > 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">💰 Faturamento dos Produtos</div>
            <div class="metric-value">{format_currency_br(total_faturamento)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📦 Total de Pedidos</div>
            <div class="metric-value">{format_integer_br(total_pedidos)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📊 Unidades Compradas</div>
            <div class="metric-value">{format_integer_br(total_unidades)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🎯 Ticket Médio</div>
            <div class="metric-value">{format_currency_br(ticket_medio)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📈 % Partic. Faturamento</div>
            <div class="metric-value">{participacao_faturamento:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

else:
    # KPIs gerais (quando nenhum produto específico está selecionado)
    total_faturamento = df_filtered['Faturamento Total da Cidade no Mês'].sum()
    total_pedidos = df_filtered['Total de Pedidos da Cidade no Mês'].sum()
    ticket_medio_geral = total_faturamento / total_pedidos if total_pedidos > 0 else 0
    cidades_unicas = df_filtered['Cidade'].nunique()
    produtos_unicos = df_filtered['Produto'].nunique()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">💰 Faturamento Total</div>
            <div class="metric-value">{format_currency_br(total_faturamento)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📦 Total de Pedidos</div>
            <div class="metric-value">{format_integer_br(total_pedidos)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🎯 Ticket Médio Geral</div>
            <div class="metric-value">{format_currency_br(ticket_medio_geral)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🏙️ Cidades Atendidas</div>
            <div class="metric-value">{cidades_unicas}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📊 Produtos Únicos</div>
            <div class="metric-value">{produtos_unicos}</div>
        </div>
        """, unsafe_allow_html=True)

        # ESTRUTURA CORRETA: 4 ABAS INTERNAS
tab_produtos, tab_cidades, tab_estados, tab_diario = st.tabs(["📦 Top Produtos", "🏙️ Top Cidades", "🗺️ Top Estados", "📅 Análise Diária"])


with tab_produtos:
    st.subheader("Top Produtos por Métrica")
    metric_produto = st.selectbox(
        "Selecionar Métrica para Top Produtos:",
        options=["Faturamento do Produto", "Unidades Compradas"],
        key='metric_produto_tab'
    )
    n_produtos = st.slider("Número de Produtos no Top N:", min_value=5, max_value=20, value=10, key='n_produtos_tab')

    top_produtos = df_filtrado.groupby('Produto')[metric_produto].sum().astype(float).nlargest(n_produtos).reset_index()
    top_produtos.columns = ['Produto', 'Total']

    fig_top_produtos = px.bar(
        top_produtos,
        x='Total',
        y='Produto',
        orientation='h',
        title=f"Top {n_produtos} Produtos por {metric_produto}",
        labels={'Total': metric_produto, 'Produto': 'Nome do Produto'},
        color='Total',
        color_continuous_scale=px.colors.sequential.Plasma
    )

    if metric_produto == "Faturamento do Produto":
        fig_top_produtos.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
        fig_top_produtos.update_traces(hovertemplate='Produto: %{y}<br>Faturamento: R$ %{x:,.2f}<extra></extra>')
    elif metric_produto == "Unidades Compradas":
        fig_top_produtos.update_xaxes(tickformat=".", tickformatstops=[dict(dtickrange=[None, None], value=".")])
        fig_top_produtos.update_traces(hovertemplate='Produto: %{y}<br>Unidades: %{x:,.0f}<extra></extra>')

    fig_top_produtos.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_top_produtos, use_container_width=True)

    st.subheader("Evolução do Desempenho dos Produtos ao Longo do Tempo")

    all_months_prod_evol = sorted(df['Mês'].dt.to_period('M').unique().to_timestamp().tolist())
    default_prod_evol_month_selection = all_months_prod_evol

    selected_prod_evol_months = st.multiselect(
        "Selecione o(s) Mês(es) para Evolução dos Produtos",
        options=all_months_prod_evol,
        default=default_prod_evol_month_selection,
        format_func=lambda x: x.strftime('%Y-%m'),
        key='prod_evol_month_filter'
    )

    df_filtered_for_prod_evol = df.copy()

    if selected_prod_evol_months:
        df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Mês'].isin(selected_prod_evol_months)]

    if selected_estados:
        df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Estado'].isin(selected_estados)]
    if selected_cidades:
        df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Cidade'].isin(selected_cidades)]

    # 🔁 NÃO filtra por selected_produtos aqui para não limitar a lista do multiselect

    if df_filtered_for_prod_evol.empty:
        st.info("Nenhum dado para mostrar na evolução de produtos com os filtros selecionados.")
    else:
        produtos_para_linha_options = sorted(df_filtered_for_prod_evol['Produto'].unique())

        default_prod_evol_selection_multiselect = [p for p in sorted(top_produtos['Produto'].tolist()[:3]) if p in produtos_para_linha_options]

        produtos_para_linha = st.multiselect(
            "Selecione Produtos para o Gráfico de Linha (máx 5):",
            options=produtos_para_linha_options,
            default=default_prod_evol_selection_multiselect,
            key='produtos_para_linha_filter'
        )

        # ✅ Agora sim aplica o filtro para os produtos selecionados
        if produtos_para_linha:
            df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Produto'].isin(produtos_para_linha)]

            df_produtos_tempo = df_filtered_for_prod_evol.groupby(['Mês', 'Produto']).agg(
                faturamento=('Faturamento do Produto', 'sum'),
                unidades_compradas=('Unidades Compradas', 'sum')
            ).reset_index()
            # Adiciona colunas com média móvel de 3 meses
            df_produtos_tempo['faturamento_mm3'] = df_produtos_tempo.groupby('Produto')['faturamento'].transform(lambda x: x.rolling(3, min_periods=1).mean())
            df_produtos_tempo['unidades_mm3'] = df_produtos_tempo.groupby('Produto')['unidades_compradas'].transform(lambda x: x.rolling(3, min_periods=1).mean())

            fig_prod_tempo_fat = px.line(
                df_produtos_tempo,
                x='Mês',
                y='faturamento',
                color='Produto',
                title='Faturamento dos Produtos Selecionados ao Longo do Tempo',
                labels={'Mês': 'Mês', 'faturamento': 'Faturamento', 'Produto': 'Produto'},
                line_shape='linear'
            )

            for produto in df_produtos_tempo['Produto'].unique():
                df_aux = df_produtos_tempo[df_produtos_tempo['Produto'] == produto]
                fig_prod_tempo_fat.add_scatter(x=df_aux['Mês'], y=df_aux['faturamento_mm3'],
                                   mode='lines', name=f'{produto} (MM3)',
                                   line=dict(dash='dot'))

            fig_prod_tempo_fat.update_xaxes(dtick="M1", tickformat="%Y-%m")
            fig_prod_tempo_fat.update_yaxes(tickprefix="R$ ", tickformat=",.2f") # US locale for numbers, R$ prefix
            fig_prod_tempo_fat.update_traces(hovertemplate='Mês: %{x|%Y-%m}<br>Produto: %{fullData.name}<br>Faturamento: R$ %{y:,.2f}<extra></extra>')
            st.plotly_chart(fig_prod_tempo_fat, use_container_width=True)

            fig_prod_tempo_unid = px.line(
                df_produtos_tempo,
                x='Mês',
                y='unidades_compradas',
                color='Produto',
                title='Unidades Compradas dos Produtos Selecionados ao Longo do Tempo',
                labels={'Mês': 'Mês', 'unidades_compradas': 'Unidades Compradas', 'Produto': 'Produto'},
                line_shape='linear'
            )
            fig_prod_tempo_unid.update_xaxes(dtick="M1", tickformat="%Y-%m")
            fig_prod_tempo_unid.update_yaxes(tickformat="")
            fig_prod_tempo_unid.update_traces(
                hovertemplate='Mês: %{x|%Y-%m}<br>Produto: %{fullData.name}<br>Unidades: %{y:,.0f}<extra></extra>'
)
            st.plotly_chart(fig_prod_tempo_unid, use_container_width=True)
#INSIGTHS 
            st.subheader("🔍 Insights Automáticos: Variação Mês a Mês dos Produtos")

        if len(selected_prod_evol_months) >= 2 and not df_produtos_tempo.empty:
            df_insights = df_produtos_tempo.copy()
            df_insights['Mês'] = df_insights['Mês'].dt.to_period('M')
            df_insights = df_insights.sort_values(['Produto', 'Mês'])

            df_insights['unidades_pct_change'] = df_insights.groupby('Produto')['unidades_compradas'].pct_change()
            df_insights['faturamento_pct_change'] = df_insights.groupby('Produto')['faturamento'].pct_change()

            ult_mes = df_insights['Mês'].max()
            penult_mes = sorted(df_insights['Mês'].unique())[-2]

            ult_var = df_insights[df_insights['Mês'] == ult_mes]

            for _, row in ult_var.iterrows():
                produto = row['Produto']
                unid_pct = row['unidades_pct_change']
                fat_pct = row['faturamento_pct_change']

                if not pd.isna(unid_pct) and abs(unid_pct) > 0.05:
                    simbolo = "🟢⬆️" if unid_pct > 0 else "🔴⬇️"
                    st.markdown(f"{simbolo} **{produto}** teve variação de **{unid_pct*100:.1f}%** em *unidades* de {penult_mes} para {ult_mes}.")

                if not pd.isna(fat_pct) and abs(fat_pct) > 0.05:
                    simbolo = "🟢⬆️" if fat_pct > 0 else "🔴⬇️"
                    st.markdown(f"{simbolo} **{produto}** teve variação de **{fat_pct*100:.1f}%** em *faturamento* de {penult_mes} para {ult_mes}.")
        else:
            st.info("Selecione ao menos dois meses para gerar os insights automáticos.")


with tab_cidades:
    st.subheader("Top Cidades por Métrica")
    metric_cidade = st.selectbox(
        "Selecionar Métrica para Top Cidades:",
        options=["Faturamento Total da Cidade no Mês", "Unidades Compradas", "Pedidos com Produto"],
        key='metric_cidade_tab'
    )
    n_cidades = st.slider("Número de Cidades no Top N:", min_value=5, max_value=20, value=10, key='n_cidades_tab')

    if selected_produtos:
        if metric_cidade == "Faturamento Total da Cidade no Mês":
            top_cidades = df_filtrado.groupby('Cidade')['Faturamento do Produto'].sum().astype(float).nlargest(n_cidades).reset_index()
        elif metric_cidade == "Unidades Compradas":
            top_cidades = df_filtrado.groupby('Cidade')['Unidades Compradas'].sum().astype(float).nlargest(n_cidades).reset_index()
        else:
            top_cidades = df_filtrado.groupby('Cidade')['Pedidos com Produto'].sum().astype(float).nlargest(n_cidades).reset_index()
    else:
        if metric_cidade == "Faturamento Total da Cidade no Mês":
            top_cidades_agg = df_filtrado.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().reset_index()
            top_cidades = top_cidades_agg.groupby('Cidade')['Faturamento Total da Cidade no Mês'].sum().astype(float).nlargest(n_cidades).reset_index()
        elif metric_cidade == "Unidades Compradas":
            top_cidades = df_filtrado.groupby('Cidade')['Unidades Compradas'].sum().astype(float).nlargest(n_cidades).reset_index()
        else:
            top_cidades = df_filtrado.groupby('Cidade')['Pedidos com Produto'].sum().astype(float).nlargest(n_cidades).reset_index()

    top_cidades.columns = ['Cidade', 'Total']
    fig_top_cidades = px.bar(
        top_cidades,
        x='Total',
        y='Cidade',
        orientation='h',
        title=f"Top {n_cidades} Cidades por {metric_cidade}",
        labels={'Total': metric_cidade, 'Cidade': 'Nome da Cidade'},
        color='Total',
        color_continuous_scale=px.colors.sequential.Viridis
    )

    if metric_cidade == "Faturamento Total da Cidade no Mês":
        fig_top_cidades.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
        fig_top_cidades.update_traces(hovertemplate='Cidade: %{y}<br>Faturamento: R$ %{x:,.2f}<extra></extra>')
    elif metric_cidade == "Unidades Compradas":
        fig_top_cidades.update_xaxes(tickformat=",d")
        fig_top_cidades.update_traces(hovertemplate='Cidade: %{y}<br>Unidades: %{x:,.0f}<extra></extra>')
    elif metric_cidade == "Pedidos com Produto":
        fig_top_cidades.update_xaxes(tickformat=",d")
        fig_top_cidades.update_traces(hovertemplate='Cidade: %{y}<br>Pedidos: %{x:,.0f}<extra></extra>')

    fig_top_cidades.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_top_cidades, use_container_width=True)

with tab_estados:
    st.subheader("Top Estados por Métrica")
    metric_estado = st.selectbox(
        "Selecionar Métrica para Top Estados:",
        options=["Faturamento Total da Cidade no Mês", "Unidades Compradas", "Pedidos com Produto"],
        key='metric_estado_tab'
    )
    n_estados = st.slider("Número de Estados no Top N:", min_value=5, max_value=20, value=10, key='n_estados_tab')

    if selected_produtos:
        if metric_estado == "Faturamento Total da Cidade no Mês":
            top_estados = df_filtrado.groupby('Estado')['Faturamento do Produto'].sum().astype(float).nlargest(n_estados).reset_index()
        elif metric_estado == "Unidades Compradas":
            top_estados = df_filtrado.groupby('Estado')['Unidades Compradas'].sum().astype(float).nlargest(n_estados).reset_index()
        else:
            top_estados = df_filtrado.groupby('Estado')['Pedidos com Produto'].sum().astype(float).nlargest(n_estados).reset_index()
    else:
        if metric_estado == "Faturamento Total da Cidade no Mês":
            top_estados_agg = df_filtrado.groupby(['Mês', 'Estado'])['Faturamento Total da Cidade no Mês'].sum().reset_index()
            top_estados = top_estados_agg.groupby('Estado')['Faturamento Total da Cidade no Mês'].sum().astype(float).nlargest(n_estados).reset_index()
        elif metric_estado == "Unidades Compradas":
            top_estados = df_filtrado.groupby('Estado')['Unidades Compradas'].sum().astype(float).nlargest(n_estados).reset_index()
        else:
            top_estados = df_filtrado.groupby('Estado')['Pedidos com Produto'].sum().astype(float).nlargest(n_estados).reset_index()

    top_estados.columns = ['Estado', 'Total']
    fig_top_estados = px.bar(
        top_estados,
        x='Total',
        y='Estado',
        orientation='h',
        title=f"Top {n_estados} Estados por {metric_estado}",
        labels={'Total': metric_estado, 'Estado': 'Nome do Estado'},
        color='Total',
        color_continuous_scale=px.colors.sequential.Cividis
    )

    if metric_estado == "Faturamento Total da Cidade no Mês":
        fig_top_estados.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
        fig_top_estados.update_traces(hovertemplate='Estado: %{y}<br>Faturamento: R$ %{x:,.2f}<extra></extra>')
    elif metric_estado == "Unidades Compradas":
        fig_top_estados.update_xaxes(tickformat=",d")
        fig_top_estados.update_traces(hovertemplate='Estado: %{y}<br>Unidades: %{x:,.0f}<extra></extra>')
    elif metric_estado == "Pedidos com Produto":
        fig_top_estados.update_xaxes(tickformat=",d")
        fig_top_estados.update_traces(hovertemplate='Estado: %{y}<br>Pedidos: %{x:,.0f}<extra></extra>')

    fig_top_estados.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_top_estados, use_container_width=True)

st.markdown("---")

# --- Comparativos de Período ---
st.header("🔄 Comparativos de Período")

# Use um container para agrupar as métricas de comparação e garantir o layout
with st.container():
    if selected_months:
        # Cria as colunas dentro do container
        col_comp1, col_comp2 = st.columns(2)

        # Base para comparativos: df original (não filtrado), depois aplica os filtros
        df_base_comp = df.copy()
        if selected_cidades:
            df_base_comp = df_base_comp[df_base_comp['Cidade'].isin(selected_cidades)]
        if selected_estados:
            df_base_comp = df_base_comp[df_base_comp['Estado'].isin(selected_estados)]

        # Condição para faturamento e pedidos: se houver produto selecionado, usa métricas de produto
        if selected_produtos:
            st.info("Comparativos calculados usando 'Faturamento do Produto' e 'Pedidos com Produto' (produto(s) selecionado(s)).")

            df_current_period_for_comp = df_base_comp[(df_base_comp['Mês'] >= min(selected_months)) & (df_base_comp['Mês'] <= max(selected_months)) & \
                                                     df_base_comp['Produto'].isin(selected_produtos)]
            df_previous_month = df_base_comp[(df_base_comp['Mês'] >= (min(selected_months) - pd.DateOffset(months=1))) & (df_base_comp['Mês'] <= (min(selected_months) - pd.DateOffset(days=1))) & \
                                             df_base_comp['Produto'].isin(selected_produtos)]
            df_three_months_ago = df_base_comp[(df_base_comp['Mês'] >= (min(selected_months) - pd.DateOffset(months=3))) & (df_base_comp['Mês'] <= (min(selected_months) - pd.DateOffset(days=1))) & \
                                             df_base_comp['Produto'].isin(selected_produtos)]

            current_faturamento_base_comp = df_current_period_for_comp['Faturamento do Produto'].sum()
            current_pedidos_base_comp = df_current_period_for_comp['Pedidos com Produto'].sum()

            previous_faturamento_base_comp = df_previous_month['Faturamento do Produto'].sum()
            previous_pedidos_base_comp = df_previous_month['Pedidos com Produto'].sum()

            three_months_faturamento_base_comp = df_three_months_ago['Faturamento do Produto'].sum()
            three_months_pedidos_base_comp = df_three_months_ago['Pedidos com Produto'].sum()

        else: # Se nenhum produto for selecionado, usa faturamento total da cidade
            st.info("Comparativos calculados usando 'Faturamento Total da Cidade no Mês' e 'Total de Pedidos da Cidade no Mês'.")

            df_current_period_for_comp = df_base_comp[(df_base_comp['Mês'] >= min(selected_months)) & (df_base_comp['Mês'] <= max(selected_months))]
            df_previous_month = df_base_comp[(df_base_comp['Mês'] >= (min(selected_months) - pd.DateOffset(months=1))) & (df_base_comp['Mês'] <= (min(selected_months) - pd.DateOffset(days=1)))]
            df_three_months_ago = df_base_comp[(df_base_comp['Mês'] >= (min(selected_months) - pd.DateOffset(months=3))) & (df_base_comp['Mês'] <= (min(selected_months) - pd.DateOffset(days=1)))]

            # Agregações para o período (faturamento total da cidade)
            current_faturamento_base_comp = df_current_period_for_comp.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum()
            current_pedidos_base_comp = df_current_period_for_comp.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum()

            previous_faturamento_base_comp = df_previous_month.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum()
            previous_pedidos_base_comp = df_previous_month.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum()

            three_months_faturamento_base_comp = df_three_months_ago.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum()
            three_months_pedidos_base_comp = df_three_months_ago.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum()

        # Calcular variações (lógica idêntica, apenas os valores de base mudam)
        fat_diff_prev = current_faturamento_base_comp - previous_faturamento_base_comp
        fat_perc_prev = (fat_diff_prev / previous_faturamento_base_comp * 100) if previous_faturamento_base_comp > 0 else 0

        ped_diff_prev = current_pedidos_base_comp - previous_pedidos_base_comp
        ped_perc_prev = (ped_diff_prev / previous_pedidos_base_comp * 100) if previous_pedidos_base_comp > 0 else 0

        num_unique_months_3m = len(df_three_months_ago['Mês'].dt.to_period('M').unique())
        avg_3m_faturamento = (three_months_faturamento_base_comp / num_unique_months_3m) if num_unique_months_3m > 0 else 0
        avg_3m_pedidos = (three_months_pedidos_base_comp / num_unique_months_3m) if num_unique_months_3m > 0 else 0

        fat_diff_3m = current_faturamento_base_comp - avg_3m_faturamento
        fat_perc_3m = (fat_diff_3m / avg_3m_faturamento * 100) if avg_3m_faturamento > 0 else 0

        ped_diff_3m = current_pedidos_base_comp - avg_3m_pedidos
        ped_perc_3m = (ped_diff_3m / avg_3m_pedidos * 100) if avg_3m_pedidos > 0 else 0

        with col_comp1:
            st.subheader("Período Selecionado vs. Período Anterior")
            st.metric(label="Faturamento", value=format_currency_br(current_faturamento_base_comp), delta=f"{format_currency_br(fat_diff_prev)} ({fat_perc_prev:,.2f}%)")
            st.metric(label="Total Pedidos", value=format_integer_br(current_pedidos_base_comp), delta=f"{format_integer_br(ped_diff_prev)} ({ped_perc_prev:,.2f}%)")

        with col_comp2:
            st.subheader("Período Selecionado vs. Média Últimos 3 Meses")
            st.metric(label="Faturamento", value=format_currency_br(current_faturamento_base_comp), delta=f"{format_currency_br(fat_diff_3m)} ({fat_perc_3m:,.2f}%)")
            st.metric(label="Total Pedidos", value=format_integer_br(current_pedidos_base_comp), delta=f"{format_integer_br(ped_diff_3m)} ({ped_perc_3m:,.2f}%)")

    else:
        st.info("Selecione pelo menos um mês nos filtros globais para ver os comparativos de período.")

st.markdown("---")

# --- Tabela Detalhada ---
st.header("📋 Dados Detalhados")

# Colunas que o usuário quer ver na tabela (agora com nomes amigáveis)
columns_to_display = [
    'Mês', 'Cidade', 'Estado', 'Produto', 'Unidades Compradas',
    'Pedidos com Produto', 'Faturamento do Produto', 'Participação Faturamento Cidade Mês (%)',
    'Participação Pedidos Cidade Mês (%)', 'Ticket Médio do Produto'
]

# Opção de ordenação
sort_column_options = {
    'Mês': 'Mês',
    'Cidade': 'Cidade',
    'Estado': 'Estado',
    'Produto': 'Produto',
    'Unidades Compradas': 'Unidades Compradas',
    'Pedidos com Produto': 'Pedidos com Produto',
    'Faturamento do Produto': 'Faturamento do Produto',
    'Ticket Médio do Produto': 'Ticket Médio do Produto',
    'Participação Faturamento Cidade Mês (%)': 'Participação Faturamento Cidade Mês (%)',
    'Participação Pedidos Cidade Mês (%)': 'Participação Pedidos Cidade Mês (%)'
}
sort_column_display = st.selectbox(
    "Ordenar Tabela Por:",
    options=list(sort_column_options.keys()),
    index=list(sort_column_options.keys()).index('Faturamento do Produto'),
    key='sort_column_table'
)
sort_column_actual = sort_column_options[sort_column_display] # Obtém o nome da coluna real para ordenação

sort_order = st.radio("Ordem:", options=["Decrescente", "Crescente"], index=0, key='sort_order_table')
ascending = True if sort_order == "Crescente" else False

# Ordenar o DataFrame filtrado ANTES de formatar para exibição
df_sorted = df_filtrado.sort_values(by=sort_column_actual, ascending=ascending)

# Agora, selecione as colunas para exibição e formate
df_exibir_formatted = df_sorted[columns_to_display].copy()
df_exibir_formatted['Mês'] = df_exibir_formatted['Mês'].dt.strftime('%Y-%m')
df_exibir_formatted['Faturamento do Produto'] = df_exibir_formatted['Faturamento do Produto'].apply(format_currency_br)
df_exibir_formatted['Participação Faturamento Cidade Mês (%)'] = df_exibir_formatted['Participação Faturamento Cidade Mês (%)'].apply(lambda x: f"{x:,.2f}%")
df_exibir_formatted['Participação Pedidos Cidade Mês (%)'] = df_exibir_formatted['Participação Pedidos Cidade Mês (%)'].apply(lambda x: f"{x:,.2f}%")
df_exibir_formatted['Ticket Médio do Produto'] = df_exibir_formatted['Ticket Médio do Produto'].apply(format_currency_br)
df_exibir_formatted['Unidades Compradas'] = df_exibir_formatted['Unidades Compradas'].apply(format_integer_br)
df_exibir_formatted['Pedidos com Produto'] = df_exibir_formatted['Pedidos com Produto'].apply(format_integer_br)

st.dataframe(
    df_exibir_formatted,
    use_container_width=True,
    hide_index=True
)

# Download dos dados
st.header("📥 Export de Dados")

col1, col2 = st.columns(2)

with col1:
    if not df_filtrado.empty:
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Dados Filtrados CSV",
            data=csv,
            file_name=f"dados_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

with col2:
    if not df_filtrado.empty:
        # Resumo executivo (agregado pelos filtros aplicados)
        resumo = df_filtrado.groupby(['Mês', 'Cidade', 'Estado']).agg(
            faturamento_total_produtos_selecionados=('Faturamento do Produto', 'sum'),
            unidades_compradas_total_produtos_selecionadas=('Unidades Compradas', 'sum'),
            pedidos_com_produto_selecionado=('Pedidos com Produto', 'sum'),
            total_pedidos_cidade_mes_unique=('Total de Pedidos da Cidade no Mês', 'first'),
            faturamento_total_cidade_mes_unique=('Faturamento Total da Cidade no Mês', 'first')
        ).reset_index()

        # CRITICAL FIX: Ensure columns exist in 'resumo' after aggregation, especially for empty/NaN groups
        expected_agg_cols = ['faturamento_total_produtos_selecionados', 'unidades_compradas_total_produtos_selecionadas', 'pedidos_com_produto_selecionado',
                             'total_pedidos_cidade_mes_unique', 'faturamento_total_cidade_mes_unique']
        for col in expected_agg_cols:
            if col not in resumo.columns:
                resumo[col] = 0.0 # Add missing column with default value if not created by agg

        # Recalcula participações e ticket médio para o resumo
        resumo['Participação Faturamento Cidade Mês (%)'] = np.where(
            resumo['faturamento_total_cidade_mes_unique'] == 0,
            0,
            (resumo['faturamento_total_produtos_selecionados'] / resumo['faturamento_total_cidade_mes_unique']) * 100
        )
        resumo['Participação Pedidos Cidade Mês (%)'] = np.where(
            resumo['total_pedidos_cidade_mes_unique'] == 0,
            0,
            (resumo['pedidos_com_produto_selecionado'] / resumo['total_pedidos_cidade_mes_unique']) * 100
        )
        resumo['Ticket Médio Geral Cidade'] = np.where(
            resumo['pedidos_com_produto_selecionado'] == 0,
            0,
            resumo['faturamento_total_produtos_selecionados'] / resumo['pedidos_com_produto_selecionado']
        )

        # Selecionar e renomear colunas para o CSV de resumo
        resumo_final_cols = [
            'Mês', 'Cidade', 'Estado',
            'faturamento_total_produtos_selecionados',
            'unidades_compradas_total_produtos_selecionadas',
            'pedidos_com_produto_selecionado',
            'total_pedidos_cidade_mes_unique',
            'faturamento_total_cidade_mes_unique',
            'Participação Faturamento Cidade Mês (%)',
            'Participação Pedidos Cidade Mês (%)',
            'Ticket Médio Geral Cidade'
        ]
        resumo_final = resumo[resumo_final_cols].rename(columns={
            'faturamento_total_produtos_selecionados': 'Faturamento Total Produtos Selecionados',
            'unidades_compradas_total_produtos_selecionadas': 'Unidades Compradas Produtos Selecionados',
            'pedidos_com_produto_selecionado': 'Pedidos com Produtos Selecionados',
            'total_pedidos_cidade_mes_unique': 'Total de Pedidos da Cidade no Mês',
            'faturamento_total_cidade_mes_unique': 'Faturamento Total da Cidade no Mês'
        })

        # Formata colunas para o CSV de resumo
        resumo_final['Mês'] = resumo_final['Mês'].dt.strftime('%Y-%m')
        resumo_final['Faturamento Total Produtos Selecionados'] = resumo_final['Faturamento Total Produtos Selecionados'].apply(format_currency_br)
        resumo_final['Unidades Compradas Produtos Selecionados'] = resumo_final['Unidades Compradas Produtos Selecionados'].apply(format_integer_br) # APLICAR AQUI
        resumo_final['Pedidos com Produtos Selecionados'] = resumo_final['Pedidos com Produtos Selecionados'].apply(format_integer_br) # APLICAR AQUI
        resumo_final['Total de Pedidos da Cidade no Mês'] = resumo_final['Total de Pedidos da Cidade no Mês'].apply(format_integer_br) # APLICAR AQUI
        resumo_final['Faturamento Total da Cidade no Mês'] = resumo_final['Faturamento Total da Cidade no Mês'].apply(format_currency_br)
        resumo_final['Participação Faturamento Cidade Mês (%)'] = resumo_final['Participação Faturamento Cidade Mês (%)'].apply(lambda x: f"{x:,.2f}%")
        resumo_final['Participação Pedidos Cidade Mês (%)'] = resumo_final['Participação Pedidos Cidade Mês (%)'].apply(lambda x: f"{x:,.2f}%")
        resumo_final['Ticket Médio Geral Cidade'] = resumo_final['Ticket Médio Geral Cidade'].apply(format_currency_br)

        csv_resumo = resumo_final.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Download Resumo Executivo CSV",
            data=csv_resumo,
            file_name=f"resumo_executivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

with tab_diario:
    # NOVA ABA DIÁRIA - SEPARADA E INDEPENDENTE
    st.header("📅 Análise Diária")
    
    # Carregar dados diários
    df_daily = load_daily_data()
    
    if df_daily.empty:
        st.error("Não foi possível carregar os dados diários.")
    else:
        # Filtros para análise diária
        st.subheader("🎛️ Filtros")
        
        col_filtro1, col_filtro2 = st.columns(2)
        
        with col_filtro1:
            # Data padrão: mês corrente
            hoje = datetime.now()
            primeiro_dia_mes = hoje.replace(day=1)
            
            data_inicio = st.date_input(
                "📅 Data Início:",
                value=primeiro_dia_mes,
                min_value=df_daily['data'].min(),
                max_value=df_daily['data'].max()
            )
            
            data_fim = st.date_input(
                "📅 Data Fim:",
                value=hoje,
                min_value=df_daily['data'].min(),
                max_value=df_daily['data'].max()
            )
        
        with col_filtro2:
            # Filtro de produtos baseado no período selecionado
            df_periodo = df_daily[
                (df_daily['data'] >= pd.to_datetime(data_inicio)) & 
                (df_daily['data'] <= pd.to_datetime(data_fim))
            ]
            
            produtos_disponiveis = sorted(df_periodo['nome_universal'].unique()) if not df_periodo.empty else []
            produtos_selecionados = st.multiselect(
                "🎯 Produtos:",
                options=produtos_disponiveis,
                default=[]
            )
        
        # Aplicar filtros
        df_daily_filtrado = df_daily[
            (df_daily['data'] >= pd.to_datetime(data_inicio)) & 
            (df_daily['data'] <= pd.to_datetime(data_fim))
        ].copy()
        
        if produtos_selecionados:
            df_daily_filtrado = df_daily_filtrado[df_daily_filtrado['nome_universal'].isin(produtos_selecionados)]
        
        if df_daily_filtrado.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            # Indicador do período
            st.info(f"📊 **Período**: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')} | **Registros**: {len(df_daily_filtrado):,}")
            
            # KPIs Principais
            st.subheader("📊 KPIs Principais")
            
            total_faturamento_diario = df_daily_filtrado['faturamento'].sum()
            total_pedidos_diario = df_daily_filtrado['quantidade_pedidos'].sum()
            total_unidades_diario = df_daily_filtrado['total_unidades'].sum()
            ticket_medio_diario = total_faturamento_diario / total_pedidos_diario if total_pedidos_diario > 0 else 0
            produtos_unicos = df_daily_filtrado['nome_universal'].nunique()
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">💰 Faturamento Total</div>
                    <div class="metric-value">{format_currency_br(total_faturamento_diario)}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">📦 Total Pedidos</div>
                    <div class="metric-value">{format_integer_br(total_pedidos_diario)}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">📊 Unidades Vendidas</div>
                    <div class="metric-value">{format_integer_br(total_unidades_diario)}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🎯 Ticket Médio</div>
                    <div class="metric-value">{format_currency_br(ticket_medio_diario)}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col5:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🏷️ Produtos Únicos</div>
                    <div class="metric-value">{produtos_unicos}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Gráficos
            st.subheader("📈 Análises Visuais")
            
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                # Tendência diária
                df_tendencia = df_daily_filtrado.groupby('data').agg({
                    'faturamento': 'sum',
                    'quantidade_pedidos': 'sum'
                }).reset_index().sort_values('data')
                
                fig_tendencia = px.line(
                    df_tendencia,
                    x='data',
                    y='faturamento',
                    title='Tendência de Faturamento Diário',
                    labels={'faturamento': 'Faturamento (R$)', 'data': 'Data'}
                )
                fig_tendencia.update_layout(height=400)
                st.plotly_chart(fig_tendencia, use_container_width=True)
            
            with col_graf2:
                # Top 10 produtos
                top_produtos_diario = df_daily_filtrado.groupby('nome_universal')['faturamento'].sum().nlargest(10).reset_index()
                
                fig_top_produtos = px.bar(
                    top_produtos_diario,
                    x='faturamento',
                    y='nome_universal',
                    orientation='h',
                    title='Top 10 Produtos por Faturamento',
                    labels={'faturamento': 'Faturamento (R$)', 'nome_universal': 'Produto'}
                )
                fig_top_produtos.update_layout(
                    height=400,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig_top_produtos, use_container_width=True)
            
            # Análise de sazonalidade
            st.subheader("📅 Análise de Sazonalidade")
            
            vendas_dia_semana = df_daily_filtrado.groupby('dia_semana').agg({
                'faturamento': 'sum',
                'quantidade_pedidos': 'sum'
            }).reset_index()
            
            # Ordenar dias da semana
            dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            vendas_dia_semana['dia_ordem'] = vendas_dia_semana['dia_semana'].map({dia: i for i, dia in enumerate(dias_ordem)})
            vendas_dia_semana = vendas_dia_semana.sort_values('dia_ordem')
            
            fig_sazonalidade = px.bar(
                vendas_dia_semana,
                x='dia_semana',
                y='faturamento',
                title='Faturamento por Dia da Semana',
                labels={'dia_semana': 'Dia da Semana', 'faturamento': 'Faturamento'}
            )
            fig_sazonalidade.update_layout(height=400)
            st.plotly_chart(fig_sazonalidade, use_container_width=True)
            
            # Insights automáticos baseados no mensal5.py
            st.subheader("💡 Insights Automáticos")
            
            if not df_daily_filtrado.empty:
                # Produto destaque
                produto_destaque = df_daily_filtrado.groupby('nome_universal')['faturamento'].sum().idxmax()
                faturamento_destaque = df_daily_filtrado.groupby('nome_universal')['faturamento'].sum().max()
                participacao_destaque = (faturamento_destaque / total_faturamento_diario) * 100
                
                st.success(f"🏆 **Produto Destaque**: {produto_destaque} representa {participacao_destaque:.1f}% do faturamento total")
                
                # Melhor dia da semana
                if not vendas_dia_semana.empty:
                    melhor_dia = vendas_dia_semana.loc[vendas_dia_semana['faturamento'].idxmax(), 'dia_semana']
                    pior_dia = vendas_dia_semana.loc[vendas_dia_semana['faturamento'].idxmin(), 'dia_semana']
                    
                    st.info(f"📅 **Sazonalidade**: Melhor dia da semana é {melhor_dia}, pior é {pior_dia}")
                
                # Análise de concentração (Pareto)
                produtos_pareto = df_daily_filtrado.groupby('nome_universal')['faturamento'].sum().sort_values(ascending=False)
                produtos_pareto_pct = (produtos_pareto.cumsum() / produtos_pareto.sum()) * 100
                produtos_80_pct = len(produtos_pareto_pct[produtos_pareto_pct <= 80])
                
                st.warning(f"⚠️ **Concentração**: {produtos_80_pct} produtos ({(produtos_80_pct/len(produtos_pareto)*100):.1f}%) representam 80% do faturamento")
            
            # Tabela detalhada
            st.subheader("📋 Dados Detalhados")
            
            df_display_diario = df_daily_filtrado.copy()
            df_display_diario['data'] = df_display_diario['data'].dt.strftime('%d/%m/%Y')
            df_display_diario['faturamento'] = df_display_diario['faturamento'].apply(format_currency_br)
            df_display_diario['quantidade_pedidos'] = df_display_diario['quantidade_pedidos'].apply(format_integer_br)
            df_display_diario['total_unidades'] = df_display_diario['total_unidades'].apply(format_integer_br)
            
            colunas_exibicao_diario = ['data', 'sku', 'nome_universal', 'quantidade_pedidos', 'total_unidades', 'faturamento']
            
            st.dataframe(
                df_display_diario[colunas_exibicao_diario],
                use_container_width=True,
                hide_index=True
            )
            
            # Export de dados diários
            st.subheader("📥 Export de Dados")
            
            csv_diario = df_daily_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Dados Diários CSV",
                data=csv_diario,
                file_name=f"dados_diarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

# Tabela detalhada GERAL (ANÁLISE MENSAL)
st.subheader("📋 Dados Detalhados")

# Preparar dados para exibição
df_display = df_filtered.copy()
df_display['Mês'] = df_display['Mês'].dt.strftime('%m/%Y')
df_display['Faturamento do Produto'] = df_display['Faturamento do Produto'].apply(format_currency_br)
df_display['Faturamento Total da Cidade no Mês'] = df_display['Faturamento Total da Cidade no Mês'].apply(format_currency_br)
df_display['Ticket Médio do Produto'] = df_display['Ticket Médio do Produto'].apply(format_currency_br)
df_display['Unidades Compradas'] = df_display['Unidades Compradas'].apply(format_integer_br)
df_display['Pedidos com Produto'] = df_display['Pedidos com Produto'].apply(format_integer_br)
df_display['Total de Pedidos da Cidade no Mês'] = df_display['Total de Pedidos da Cidade no Mês'].apply(format_integer_br)
df_display['Participação Faturamento Cidade Mês (%)'] = df_display['Participação Faturamento Cidade Mês (%)'].apply(lambda x: f"{x:.2f}%")
df_display['Participação Pedidos Cidade Mês (%)'] = df_display['Participação Pedidos Cidade Mês (%)'].apply(lambda x: f"{x:.2f}%")

# Selecionar colunas para exibição
colunas_exibicao = [
    'Mês', 'Estado', 'Cidade', 'Produto', 
    'Faturamento do Produto', 'Unidades Compradas', 'Pedidos com Produto',
    'Ticket Médio do Produto', 'Participação Faturamento Cidade Mês (%)'
]

st.dataframe(
    df_display[colunas_exibicao], 
    use_container_width=True,
    hide_index=True
)

# Opção de download GERAL
st.subheader("📥 Download dos Dados")

col1, col2 = st.columns(2)

with col1:
    # Download dados filtrados
    csv_filtrado = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📊 Download Dados Filtrados (CSV)",
        data=csv_filtrado,
        file_name=f"dados_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

with col2:
    # Download resumo executivo
    if analisando_produtos_especificos:
        resumo_data = {
            'Produto': selected_produtos,
            'Faturamento Total': [format_currency_br(df_filtered[df_filtered['Produto'] == produto]['Faturamento do Produto'].sum()) for produto in selected_produtos],
            'Pedidos Total': [format_integer_br(df_filtered[df_filtered['Produto'] == produto]['Pedidos com Produto'].sum()) for produto in selected_produtos],
            'Unidades Total': [format_integer_br(df_filtered[df_filtered['Produto'] == produto]['Unidades Compradas'].sum()) for produto in selected_produtos]
        }
        resumo_df = pd.DataFrame(resumo_data)
        csv_resumo = resumo_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📋 Download Resumo Executivo (CSV)",
            data=csv_resumo,
            file_name=f"resumo_executivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )