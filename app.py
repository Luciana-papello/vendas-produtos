import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
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
    .main-header {
        background: linear-gradient(90deg, #96ca00 0%, #4e9f00  100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    div.stButton > button {
        background-color: #96ca00;
        color: white;
        border-radius: 5px;
        border: 1px solid #96ca00;
        padding: 0.5em 1em;
    }
    div.stButton > button:hover {
        background-color: #6b8f00;
        color: white;
        border: 1px solid #6b8f00;
    }
</style>
""", unsafe_allow_html=True)

# Título Principal do Dashboard
st.markdown("<h1 class='main-header'>Dashboard de Análise de Produtos e Cidades 🏙️</h1>", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """
    Carrega e pré-processa os dados da planilha do Google Sheets.
    """
    sheet_id = '14Y-V3ezwo3LsHWERhSyURCtkQdN3drzv9F5JNRQnXEc'
    tab_name = 'Produtos_Cidades_Completas'
    google_sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"

    with st.spinner("Carregando dados... Por favor, aguarde."):
        try:
            df = pd.read_csv(google_sheet_url)
        except Exception as e:
            st.error(f"Erro ao carregar dados da planilha do Google Sheets: {e}")
            st.warning("Por favor, verifique se o ID da planilha e o nome da aba estão corretos e se a planilha está compartilhada como 'Qualquer pessoa com o link'.")
            st.stop()

    if df.empty:
        st.warning("A planilha do Google Sheets está vazia ou não contém dados. Verifique a planilha ou os filtros iniciais.")
        st.stop()

    # Convert 'mes' to datetime objects
    df['mes'] = pd.to_datetime(df['mes'], format='%Y-%m')

    # Conversão robusta de colunas numéricas:
    df.loc[:, 'faturamento'] = pd.to_numeric(df['faturamento'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
    df.loc[:, 'faturamento_total_cidade_mes'] = pd.to_numeric(df['faturamento_total_cidade_mes'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

    df.loc[:, 'unidades_fisicas'] = pd.to_numeric(df['unidades_fisicas'], errors='coerce').fillna(0)
    df.loc[:, 'pedidos'] = pd.to_numeric(df['pedidos'], errors='coerce').fillna(0)
    df.loc[:, 'total_pedidos_cidade_mes'] = pd.to_numeric(df['total_pedidos_cidade_mes'], errors='coerce').fillna(0)

    # Renomear colunas para nomes amigáveis usando o mapping importado
    df = df.rename(columns=column_mapping)

    # Calcular Métricas Derivadas usando os nomes de coluna já renomeados
    df.loc[:, 'Participação Faturamento Cidade Mês (%)'] = np.where(
        df['Faturamento Total da Cidade no Mês'] == 0,
        0,
        (df['Faturamento do Produto'] / df['Faturamento Total da Cidade no Mês']) * 100
    )

    df.loc[:, 'Participação Pedidos Cidade Mês (%)'] = np.where(
        df['Total de Pedidos da Cidade no Mês'] == 0,
        0,
        (df['Pedidos com Produto'] / df['Total de Pedidos da Cidade no Mês']) * 100
    )

    df.loc[:, 'Ticket Médio do Produto'] = np.where(
        df['Pedidos com Produto'] == 0,
        0,
        df['Faturamento do Produto'] / df['Pedidos com Produto']
    )
    return df

@st.cache_data
def load_daily_data():
    """
    Carrega dados da planilha diária (separada da mensal)
    """
    sheet_id = '1cERMKGnnCH0y_C29QNfT__7zeB4bHVHaxdA3fTDcaxs'
    tab_name = 'ResumoDiarioProdutos'
    google_sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"

    with st.spinner("Carregando dados diários... Por favor, aguarde."):
        try:
            df = pd.read_csv(google_sheet_url)
        except Exception as e:
            st.error(f"Erro ao carregar dados diários: {e}")
            return pd.DataFrame()

    if df.empty:
        st.warning("A planilha diária está vazia.")
        return pd.DataFrame()

    # Converter data
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    
    # CORREÇÃO CRÍTICA: Tratar vírgula como decimal
    df['faturamento'] = df['faturamento'].astype(str).str.replace(',', '.').astype(float)
    
    # Converter outras colunas numéricas
    df['quantidade_pedidos'] = pd.to_numeric(df['quantidade_pedidos'], errors='coerce').fillna(0)
    df['total_unidades'] = pd.to_numeric(df['total_unidades'], errors='coerce').fillna(0)

    return df

# Criar abas
tab_mensal, tab_diaria = st.tabs(["📊 Análise Mensal", "📅 Análise Diária"])

with tab_mensal:
    # TODO O CÓDIGO ORIGINAL DA ANÁLISE MENSAL AQUI (sem alterações)
    df = load_data()

    # --- Sidebar para Filtros ---
    st.sidebar.header("⚙️ Filtros Globais")

    # Botão de Resetar Filtros
    if st.sidebar.button("🔄 Resetar Filtros"):
        st.session_state['selected_months'] = []
        st.session_state['selected_estados'] = []
        st.session_state['selected_cidades'] = []
        st.session_state['selected_produtos'] = []
        st.experimental_rerun()

    # Recupera valores padrão ou do session_state
    min_date = df['Mês'].min()
    max_date = df['Mês'].max()

    available_months = sorted(df['Mês'].dt.to_period('M').unique().to_timestamp().tolist())

    # Usa session_state para manter o estado dos filtros após o reset
    if 'selected_months' not in st.session_state:
        st.session_state['selected_months'] = available_months
    if 'selected_estados' not in st.session_state:
        st.session_state['selected_estados'] = sorted(df['Estado'].unique())
    if 'selected_cidades' not in st.session_state:
        st.session_state['selected_cidades'] = sorted(df['Cidade'].unique())
    if 'selected_produtos' not in st.session_state:
        st.session_state['selected_produtos'] = []

    selected_months = st.sidebar.multiselect(
        "Selecione o(s) Mês(es)",
        options=available_months,
        default=st.session_state['selected_months'],
        format_func=lambda x: x.strftime('%Y-%m'),
        key='month_filter'
    )

    # Filtro de Estado
    all_estados = sorted(df['Estado'].unique())
    selected_estados = st.sidebar.multiselect(
        "Selecione o(s) Estado(s)",
        options=all_estados,
        default=st.session_state['selected_estados'],
        key='estado_filter'
    )

    # Filtro de Cidade (dependente do estado)
    if selected_estados:
        available_cidades = sorted(df[df['Estado'].isin(selected_estados)]['Cidade'].unique())
    else:
        available_cidades = sorted(df['Cidade'].unique())

    default_cidades_validas = [c for c in st.session_state['selected_cidades'] if c in available_cidades]
    selected_cidades = st.sidebar.multiselect(
        "Selecione a(s) Cidade(s)",
        options=available_cidades,
        default=default_cidades_validas,
        key='cidade_filter'
    )

    # Filtro de Produto
    all_produtos = sorted(df['Produto'].unique())
    selected_produtos = st.sidebar.multiselect(
        "Selecione o(s) Produto(s)",
        options=all_produtos,
        default=st.session_state['selected_produtos'],
        key='produto_filter'
    )

    # --- Aplica os Filtros Globais ---
    df_filtrado = df.copy()

    if selected_months:
        df_filtrado = df_filtrado[df_filtrado['Mês'].isin(selected_months)]

    if selected_estados:
        df_filtrado = df_filtrado[df_filtrado['Estado'].isin(selected_estados)]

    if selected_cidades:
        df_filtrado = df_filtrado[df_filtrado['Cidade'].isin(selected_cidades)]

    if selected_produtos:
        df_filtrado = df_filtrado[df_filtrado['Produto'].isin(selected_produtos)]

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados. Tente ajustar os filtros.")
        st.stop()

    # --- KPIs no Topo ---
    st.header("📊 Principais Indicadores")

    # AJUSTADO: Lógica condicional para KPIs de Faturamento Total e Total Pedidos
    if selected_produtos:
        total_faturamento = df_filtrado['Faturamento do Produto'].sum()
        total_pedidos_kpi = df_filtrado['Pedidos com Produto'].sum()
    else:
        df_kpi_base = df_filtrado.groupby(['Mês', 'Cidade']).agg(
            total_pedidos_cidade_mes=('Total de Pedidos da Cidade no Mês', 'first'),
            faturamento_total_cidade_mes=('Faturamento Total da Cidade no Mês', 'first')
        ).reset_index()
        total_faturamento = df_kpi_base['faturamento_total_cidade_mes'].sum()
        total_pedidos_kpi = df_kpi_base['total_pedidos_cidade_mes'].sum()

    total_unidades_fisicas = df_filtrado['Unidades Compradas'].sum()
    ticket_medio_geral = total_faturamento / total_pedidos_kpi if total_pedidos_kpi > 0 else 0
    media_participacao_faturamento = df_filtrado['Participação Faturamento Cidade Mês (%)'].mean()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Faturamento Total</div>
            <div class="metric-value">{format_currency_br(total_faturamento)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Pedidos</div>
            <div class="metric-value">{format_integer_br(total_pedidos_kpi)}</div> </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Unidades Compradas</div>
            <div class="metric-value">{format_integer_br(total_unidades_fisicas)}</div> </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Ticket Médio Geral</div>
            <div class="metric-value">{format_currency_br(ticket_medio_geral)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">% Partic. Faturamento Prod. (Méd.)</div>
            <div class="metric-value">{media_participacao_faturamento:,.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.header("📋 Dados Detalhados")

    # Colunas que o usuário quer ver na tabela
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
    sort_column_actual = sort_column_options[sort_column_display]

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

with tab_diaria:
    st.header("📅 Análise Diária de Produtos")
    
    # Carregar dados diários
    df_daily = load_daily_data()
    
    if df_daily.empty:
        st.error("Não foi possível carregar os dados diários.")
        st.stop()
    
    # Filtros para análise diária
    st.subheader("🎛️ Filtros")
    
    # Data padrão: mês corrente
    hoje = datetime.now()
    primeiro_dia_mes = hoje.replace(day=1)
    
    col_data1, col_data2 = st.columns(2)
    with col_data1:
        data_inicio = st.date_input(
            "Data Início:",
            value=primeiro_dia_mes,
            min_value=df_daily['data'].min(),
            max_value=df_daily['data'].max(),
            key='data_inicio_diaria'
        )
    
    with col_data2:
        data_fim = st.date_input(
            "Data Fim:",
            value=hoje,
            min_value=df_daily['data'].min(),
            max_value=df_daily['data'].max(),
            key='data_fim_diaria'
        )
    
    # Aplicar filtro de data
    df_daily_filtrado = df_daily[
        (df_daily['data'] >= pd.to_datetime(data_inicio)) & 
        (df_daily['data'] <= pd.to_datetime(data_fim))
    ].copy()
    
    if df_daily_filtrado.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        st.stop()
    
    # Filtro de produtos baseado no período selecionado
    produtos_disponiveis = sorted(df_daily_filtrado['nome_universal'].unique())
    produtos_selecionados = st.multiselect(
        "Selecione Produtos (opcional):",
        options=produtos_disponiveis,
        default=[],
        key='produtos_diarios'
    )
    
    # Aplicar filtro de produtos se selecionado
    if produtos_selecionados:
        df_daily_filtrado = df_daily_filtrado[df_daily_filtrado['nome_universal'].isin(produtos_selecionados)]
    
    # Indicador do período analisado
    st.info(f"📊 Analisando período de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')} - {len(df_daily_filtrado)} registros encontrados")
    
    # KPIs principais
    st.subheader("📊 Principais Indicadores")
    
    total_faturamento_diario = df_daily_filtrado['faturamento'].sum()
    total_pedidos_diario = df_daily_filtrado['quantidade_pedidos'].sum()
    total_unidades_diario = df_daily_filtrado['total_unidades'].sum()
    ticket_medio_diario = total_faturamento_diario / total_pedidos_diario if total_pedidos_diario > 0 else 0
    produtos_unicos = df_daily_filtrado['nome_universal'].nunique()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Faturamento Total</div>
            <div class="metric-value">{format_currency_br(total_faturamento_diario)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Pedidos</div>
            <div class="metric-value">{format_integer_br(total_pedidos_diario)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Unidades Vendidas</div>
            <div class="metric-value">{format_integer_br(total_unidades_diario)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Ticket Médio</div>
            <div class="metric-value">{format_currency_br(ticket_medio_diario)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Produtos Únicos</div>
            <div class="metric-value">{produtos_unicos}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Gráficos de tendência
    st.subheader("📈 Tendências Diárias")
    
    # Agregar por data
    df_tendencia = df_daily_filtrado.groupby('data').agg({
        'faturamento': 'sum',
        'quantidade_pedidos': 'sum',
        'total_unidades': 'sum'
    }).reset_index()
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        fig_fat = px.line(
            df_tendencia,
            x='data',
            y='faturamento',
            title='Faturamento Diário',
            labels={'data': 'Data', 'faturamento': 'Faturamento'}
        )
        fig_fat.update_traces(line_color='#96ca00')
        st.plotly_chart(fig_fat, use_container_width=True)
    
    with col_graf2:
        fig_ped = px.bar(
            df_tendencia,
            x='data',
            y='quantidade_pedidos',
            title='Pedidos Diários',
            labels={'data': 'Data', 'quantidade_pedidos': 'Quantidade de Pedidos'}
        )
        fig_ped.update_traces(marker_color='#4e9f00')
        st.plotly_chart(fig_ped, use_container_width=True)
    
    # Top 10 produtos
    st.subheader("🏆 Top 10 Produtos")
    
    top_produtos_diario = df_daily_filtrado.groupby('nome_universal').agg({
        'faturamento': 'sum',
        'total_unidades': 'sum',
        'quantidade_pedidos': 'sum'
    }).reset_index()
    
    top_produtos_diario = top_produtos_diario.nlargest(10, 'faturamento')
    
    fig_top = px.bar(
        top_produtos_diario,
        x='faturamento',
        y='nome_universal',
        orientation='h',
        title='Top 10 Produtos por Faturamento',
        labels={'faturamento': 'Faturamento', 'nome_universal': 'Produto'}
    )
    fig_top.update_traces(marker_color='#96ca00')
    fig_top.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_top, use_container_width=True)
    
    # Tabela detalhada
    st.subheader("📋 Dados Detalhados")
    
    df_exibir_diario = df_daily_filtrado.copy()
    df_exibir_diario['data'] = df_exibir_diario['data'].dt.strftime('%d/%m/%Y')
    df_exibir_diario['faturamento'] = df_exibir_diario['faturamento'].apply(format_currency_br)
    df_exibir_diario['total_unidades'] = df_exibir_diario['total_unidades'].apply(format_integer_br)
    df_exibir_diario['quantidade_pedidos'] = df_exibir_diario['quantidade_pedidos'].apply(format_integer_br)
    
    # Renomear colunas para exibição
    df_exibir_diario = df_exibir_diario.rename(columns={
        'data': 'Data',
        'sku': 'SKU',
        'nome_universal': 'Produto',
        'quantidade_pedidos': 'Qtd Pedidos',
        'total_unidades': 'Total Unidades',
        'faturamento': 'Faturamento'
    })
    
    st.dataframe(
        df_exibir_diario[['Data', 'SKU', 'Produto', 'Qtd Pedidos', 'Total Unidades', 'Faturamento']],
        use_container_width=True,
        hide_index=True
    )
    
    # Export CSV
    st.subheader("📥 Export de Dados")
    
    if not df_daily_filtrado.empty:
        csv_diario = df_daily_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Dados Diários CSV",
            data=csv_diario,
            file_name=f"dados_diarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )