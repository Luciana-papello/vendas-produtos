import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import collections
import itertools

#======================================================================
# CONFIGURAÇÃO DA PÁGINA E AUTENTICAÇÃO
#======================================================================
st.set_page_config(
    page_title="Dashboard de Análises Papello",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
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


# Controle de autenticação
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("### 🔐 Acesso Restrito")
    senha = st.text_input("Digite a senha para acessar o dashboard:", type="password")
    if senha == st.secrets["app_password"]:
        st.session_state.autenticado = True
        st.success("✅ Acesso liberado com sucesso!")
        st.rerun()
    elif senha != "":
        st.error("❌ Senha incorreta. Tente novamente.")
    st.stop()

#======================================================================
# FUNÇÕES AUXILIARES DE FORMATAÇÃO E DADOS
#======================================================================
def format_currency_br(value):
    if pd.isna(value) or value is None: return "R$ 0,00"
    s_value = "{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s_value}"

def format_integer_br(value):
    if pd.isna(value) or value is None: return "0"
    return "{:,.0f}".format(int(value)).replace(",", ".")

#======================================================================
# CARREGAMENTO DE DADOS (CACHEADO)
#======================================================================

# Função para autorizar e conectar ao Google Sheets
@st.cache_resource(ttl=600)
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google_credentials"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope )
    client = gspread.authorize(creds)
    return client

# Função para carregar uma aba específica de uma planilha
def load_sheet_data(sheet_id, tab_name):
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(tab_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erro ao carregar dados da aba '{tab_name}': {e}")
        return pd.DataFrame()

# Carregador de dados para a ANÁLISE DIÁRIA
@st.cache_data(ttl=600)
def load_daily_analysis_data():
    sheet_id = st.secrets["planilha_diaria_id"]
    with st.spinner("Carregando dados da análise diária..."):
        df_pedidos = load_sheet_data(sheet_id, 'Pedidos')
        df_produtos = load_sheet_data(sheet_id, 'Produtos')

    if df_pedidos.empty or df_produtos.empty:
        st.warning("Dados de pedidos ou produtos da análise diária estão vazios.")
        return pd.DataFrame(), pd.DataFrame()

    # --- Pré-processamento dos dados diários ---
    df_pedidos['created_at_dt'] = pd.to_datetime(df_pedidos['created_at_dt'], errors='coerce')
    numeric_cols_pedidos = ['valor_total', 'customer_id']
    for col in numeric_cols_pedidos:
        df_pedidos[col] = pd.to_numeric(df_pedidos[col], errors='coerce').fillna(0)

    numeric_cols_produtos = ['quantidade', 'price', 'total_item']
    for col in numeric_cols_produtos:
        df_produtos[col] = pd.to_numeric(df_produtos[col], errors='coerce').fillna(0)

    # Merge para ter uma base única de análise
    df_analysis = pd.merge(
        df_produtos,
        df_pedidos[['id', 'created_at_dt', 'valor_total', 'nome', 'cidade', 'estado', 'cliente_unico_id']],
        left_on='order_id',
        right_on='id',
        how='inner'
    )
    df_analysis.rename(columns={'nome_produto': 'Produto', 'cidade': 'Cidade', 'estado': 'Estado', 'nome': 'Cliente'}, inplace=True)
    return df_analysis

# Carregador de dados para a ANÁLISE DE CIDADES (código original)
@st.cache_data(ttl=600)
def load_city_analysis_data():
    sheet_id = st.secrets["planilha_mensal_id"]
    tab_name = 'Produtos_Cidades_Completas'
    with st.spinner("Carregando dados da análise de cidades..."):
        df = load_sheet_data(sheet_id, tab_name)

    if df.empty:
        st.warning("A planilha de análise de cidades está vazia.")
        return pd.DataFrame()

    # --- Pré-processamento (do seu código original) ---
    df['mes'] = pd.to_datetime(df['mes'], format='%Y-%m')
    df['faturamento'] = pd.to_numeric(df['faturamento'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
    df['faturamento_total_cidade_mes'] = pd.to_numeric(df['faturamento_total_cidade_mes'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
    df['unidades_fisicas'] = pd.to_numeric(df['unidades_fisicas'], errors='coerce').fillna(0)
    df['pedidos'] = pd.to_numeric(df['pedidos'], errors='coerce').fillna(0)
    df['total_pedidos_cidade_mes'] = pd.to_numeric(df['total_pedidos_cidade_mes'], errors='coerce').fillna(0)

    column_mapping = {
        'mes': 'Mês', 'cidade': 'Cidade', 'estado': 'Estado', 'nome_universal': 'Produto',
        'unidades_fisicas': 'Unidades Compradas', 'pedidos': 'Pedidos com Produto',
        'faturamento': 'Faturamento do Produto', 'total_pedidos_cidade_mes': 'Total de Pedidos da Cidade no Mês',
        'faturamento_total_cidade_mes': 'Faturamento Total da Cidade no Mês'
    }
    df = df.rename(columns=column_mapping)

    df['Participação Faturamento Cidade Mês (%)'] = np.where(df['Faturamento Total da Cidade no Mês'] == 0, 0, (df['Faturamento do Produto'] / df['Faturamento Total da Cidade no Mês']) * 100)
    df['Participação Pedidos Cidade Mês (%)'] = np.where(df['Total de Pedidos da Cidade no Mês'] == 0, 0, (df['Pedidos com Produto'] / df['Total de Pedidos da Cidade no Mês']) * 100)
    df['Ticket Médio do Produto'] = np.where(df['Pedidos com Produto'] == 0, 0, df['Faturamento do Produto'] / df['Pedidos com Produto'])
    return df

#======================================================================
# ESTRUTURA DE ABAS DO DASHBOARD
#======================================================================
st.title("📊 Dashboard de Análises Gerenciais")

tab_diaria, tab_produtos_cidade, tab_cidades, tab_estados = st.tabs([
    "Análise Diária", "Top Produtos por Cidade", "Top Cidades", "Top Estados"
])


#======================================================================
# ABA 1: ANÁLISE DIÁRIA
#======================================================================
with tab_diaria:
    st.header("Análise de Vendas Diária 📅")
    df_daily = load_daily_analysis_data()

    if df_daily.empty:
        st.warning("Não foi possível carregar os dados para a análise diária.")
    else:
        # --- SIDEBAR DE FILTROS PARA ANÁLISE DIÁRIA ---
        st.sidebar.header("⚙️ Filtros - Análise Diária")
        
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        date_selection = st.sidebar.date_input(
            "Selecione o Período",
            value=(start_of_month, today),
            min_value=df_daily['created_at_dt'].min().date(),
            max_value=df_daily['created_at_dt'].max().date()
        )
        
        if len(date_selection) == 2:
            start_date, end_date = date_selection

            all_produtos = sorted(df_daily['Produto'].unique())
            selected_produtos = st.sidebar.multiselect("Produtos", all_produtos, default=[], key="daily_prod_filter")

            all_estados = sorted(df_daily['Estado'].unique())
            selected_estados = st.sidebar.multiselect("Estados", all_estados, default=[], key="daily_estado_filter")

            if selected_estados:
                cidades_options = sorted(df_daily[df_daily['Estado'].isin(selected_estados)]['Cidade'].unique())
            else:
                cidades_options = sorted(df_daily['Cidade'].unique())
            selected_cidades = st.sidebar.multiselect("Cidades", cidades_options, default=[], key="daily_cidade_filter")

            # --- APLICAÇÃO DOS FILTROS ---
            df_filtrado_daily = df_daily[
                (df_daily['created_at_dt'].dt.date >= start_date) &
                (df_daily['created_at_dt'].dt.date <= end_date)
            ]
            if selected_produtos:
                df_filtrado_daily = df_filtrado_daily[df_filtrado_daily['Produto'].isin(selected_produtos)]
            if selected_estados:
                df_filtrado_daily = df_filtrado_daily[df_filtrado_daily['Estado'].isin(selected_estados)]
            if selected_cidades:
                df_filtrado_daily = df_filtrado_daily[df_filtrado_daily['Cidade'].isin(selected_cidades)]

            if df_filtrado_daily.empty:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
            else:
                # --- KPIs ---
                st.subheader("Principais Indicadores do Período")
                total_faturamento = df_filtrado_daily['total_item'].sum()
                total_pedidos = df_filtrado_daily['order_id'].nunique()
                ticket_medio = total_faturamento / total_pedidos if total_pedidos > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Faturamento Total</div><div class="metric-value">{format_currency_br(total_faturamento)}</div></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Total de Pedidos</div><div class="metric-value">{format_integer_br(total_pedidos)}</div></div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="metric-card"><div class="metric-title">Ticket Médio</div><div class="metric-value">{format_currency_br(ticket_medio)}</div></div>', unsafe_allow_html=True)

                st.markdown("---")
                
                # --- COMPARATIVOS DE PERÍODO ---
                st.subheader("🔄 Comparativos de Período")
                
                period_duration = (end_date - start_date).days + 1
                
                prev_start_date = start_date - timedelta(days=period_duration)
                prev_end_date = start_date - timedelta(days=1)
                df_previous_period = df_daily[(df_daily['created_at_dt'].dt.date >= prev_start_date) & (df_daily['created_at_dt'].dt.date <= prev_end_date)]
                if selected_produtos: df_previous_period = df_previous_period[df_previous_period['Produto'].isin(selected_produtos)]
                if selected_estados: df_previous_period = df_previous_period[df_previous_period['Estado'].isin(selected_estados)]
                if selected_cidades: df_previous_period = df_previous_period[df_previous_period['Cidade'].isin(selected_cidades)]

                prev_faturamento = df_previous_period['total_item'].sum()
                prev_pedidos = df_previous_period['order_id'].nunique()

                three_months_ago_start = start_date - timedelta(days=90)
                df_3_months = df_daily[(df_daily['created_at_dt'].dt.date >= three_months_ago_start) & (df_daily['created_at_dt'].dt.date < start_date)]
                if selected_produtos: df_3_months = df_3_months[df_3_months['Produto'].isin(selected_produtos)]
                if selected_estados: df_3_months = df_3_months[df_3_months['Estado'].isin(selected_estados)]
                if selected_cidades: df_3_months = df_3_months[df_3_months['Cidade'].isin(selected_cidades)]

                avg_3m_faturamento = (df_3_months['total_item'].sum() / 3) if not df_3_months.empty else 0
                avg_3m_pedidos = (df_3_months['order_id'].nunique() / 3) if not df_3_months.empty else 0

                col_comp1, col_comp2 = st.columns(2)
                with col_comp1:
                    st.subheader("Vs. Período Anterior")
                    st.metric(label="Faturamento", value=format_currency_br(total_faturamento), delta=f"{format_currency_br(total_faturamento - prev_faturamento)}")
                    st.metric(label="Total Pedidos", value=format_integer_br(total_pedidos), delta=f"{format_integer_br(total_pedidos - prev_pedidos)}")
                with col_comp2:
                    st.subheader("Vs. Média Mensal (últimos 90 dias)")
                    st.metric(label="Faturamento", value=format_currency_br(total_faturamento), delta=f"{format_currency_br(total_faturamento - avg_3m_faturamento)}")
                    st.metric(label="Total Pedidos", value=format_integer_br(total_pedidos), delta=f"{format_integer_br(total_pedidos - avg_3m_pedidos)}")

                st.markdown("---")

                # --- VISUALIZAÇÕES GRÁFICAS ---
                st.subheader("Visualizações Gráficas")
                
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    df_filtrado_daily['dia_semana'] = df_filtrado_daily['created_at_dt'].dt.day_name()
                    vendas_dia = df_filtrado_daily.groupby('dia_semana')['total_item'].sum().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).fillna(0)
                    vendas_dia.index = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
                    fig = px.bar(vendas_dia, x=vendas_dia.index, y='total_item', title='Faturamento por Dia da Semana', labels={'total_item': 'Faturamento', 'index': 'Dia da Semana'})
                    st.plotly_chart(fig, use_container_width=True)
                with col_g2:
                    df_filtrado_daily['hora_dia'] = df_filtrado_daily['created_at_dt'].dt.hour
                    vendas_hora = df_filtrado_daily.groupby('hora_dia')['total_item'].sum().reset_index()
                    fig = px.bar(vendas_hora, x='hora_dia', y='total_item', title='Faturamento por Hora do Dia', labels={'total_item': 'Faturamento', 'hora_dia': 'Hora'})
                    st.plotly_chart(fig, use_container_width=True)

                col_g3, col_g4 = st.columns(2)
                with col_g3:
                    top_produtos = df_filtrado_daily.groupby('Produto')['total_item'].sum().nlargest(10).sort_values()
                    fig = px.bar(top_produtos, y=top_produtos.index, x='total_item', orientation='h', title='Top 10 Produtos por Faturamento', labels={'total_item': 'Faturamento', 'y': 'Produto'})
                    st.plotly_chart(fig, use_container_width=True)
                with col_g4:
                    top_clientes = df_filtrado_daily.groupby('Cliente')['total_item'].sum().nlargest(10).sort_values()
                    fig = px.bar(top_clientes, y=top_clientes.index, x='total_item', orientation='h', title='Top 10 Clientes por Faturamento', labels={'total_item': 'Faturamento', 'y': 'Cliente'})
                    st.plotly_chart(fig, use_container_width=True)

                col_g5, col_g6 = st.columns(2)
                with col_g5:
                    top_estados = df_filtrado_daily.groupby('Estado')['total_item'].sum().nlargest(10).sort_values()
                    fig = px.bar(top_estados, y=top_estados.index, x='total_item', orientation='h', title='Top 10 Estados por Faturamento', labels={'total_item': 'Faturamento', 'y': 'Estado'})
                    st.plotly_chart(fig, use_container_width=True)
                with col_g6:
                    st.subheader("Produtos Comprados Juntos")
                    pedidos_com_produtos = df_filtrado_daily.groupby('order_id')['Produto'].apply(list)
                    product_pairs = collections.Counter()
                    for products_in_order in pedidos_com_produtos:
                        if len(products_in_order) >= 2:
                            unique_products = sorted(list(set(products_in_order)))
                            for p1, p2 in itertools.combinations(unique_products, 2):
                                product_pairs[(p1, p2)] += 1
                    
                    if product_pairs:
                        market_basket_df = pd.DataFrame(product_pairs.most_common(10), columns=['Par de Produtos', 'Frequência'])
                        market_basket_df['Par'] = market_basket_df['Par de Produtos'].apply(lambda x: f"{x[0]} & {x[1]}")
                        fig = px.bar(market_basket_df, x='Frequência', y='Par', orientation='h', title='Top 10 Pares de Produtos Mais Comprados Juntos')
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Não há dados suficientes para a análise de produtos comprados juntos.")
        else:
            st.info("Selecione um período de datas para iniciar a análise.")


#======================================================================
# ABAS 2, 3, 4: ANÁLISE DE CIDADES (CÓDIGO ORIGINAL)
#======================================================================
df_city = load_city_analysis_data()

if df_city.empty:
    st.warning("Não foi possível carregar os dados para as abas de análise de cidade. As abas ficarão desativadas.")
else:
    st.sidebar.header("⚙️ Filtros - Análise Cidades")
    
    available_months = sorted(df_city['Mês'].dt.to_period('M').unique().to_timestamp().tolist())
    selected_months_city = st.sidebar.multiselect(
        "Selecione o(s) Mês(es)",
        options=available_months,
        default=available_months,
        format_func=lambda x: x.strftime('%Y-%m'),
        key="city_month_filter"
    )

    all_estados_city = sorted(df_city['Estado'].unique())
    selected_estados_city = st.sidebar.multiselect(
        "Selecione o(s) Estado(s)",
        options=all_estados_city,
        default=all_estados_city,
        key="city_estado_filter"
    )

    if selected_estados_city:
        available_cidades_city = sorted(df_city[df_city['Estado'].isin(selected_estados_city)]['Cidade'].unique())
    else:
        available_cidades_city = sorted(df_city['Cidade'].unique())
    selected_cidades_city = st.sidebar.multiselect(
        "Selecione a(s) Cidade(s)",
        options=available_cidades_city,
        default=[],
        key="city_cidade_filter"
    )

    all_produtos_city = sorted(df_city['Produto'].unique())
    selected_produtos_city = st.sidebar.multiselect(
        "Selecione o(s) Produto(s)",
        options=all_produtos_city,
        default=[],
        key="city_produto_filter"
    )

    df_filtrado_city = df_city.copy()
    if selected_months_city:
        df_filtrado_city = df_filtrado_city[df_filtrado_city['Mês'].isin(selected_months_city)]
    if selected_estados_city:
        df_filtrado_city = df_filtrado_city[df_filtrado_city['Estado'].isin(selected_estados_city)]
    if selected_cidades_city:
        df_filtrado_city = df_filtrado_city[df_filtrado_city['Cidade'].isin(selected_cidades_city)]
    if selected_produtos_city:
        df_filtrado_city = df_filtrado_city[df_filtrado_city['Produto'].isin(selected_produtos_city)]

    with tab_produtos_cidade:
        st.header("📈 Análise de Desempenho de Produtos por Cidade")
        if df_filtrado_city.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            metric_produto = st.selectbox(
                "Selecionar Métrica para Top Produtos:",
                options=["Faturamento do Produto", "Unidades Compradas"],
                key='metric_produto_tab'
            )
            n_produtos = st.slider("Número de Produtos no Top N:", min_value=5, max_value=20, value=10, key='n_produtos_tab')

            top_produtos = df_filtrado_city.groupby('Produto')[metric_produto].sum().astype(float).nlargest(n_produtos).reset_index()
            top_produtos.columns = ['Produto', 'Total']

            fig_top_produtos = px.bar(top_produtos, x='Total', y='Produto', orientation='h', title=f"Top {n_produtos} Produtos por {metric_produto}")
            st.plotly_chart(fig_top_produtos, use_container_width=True)

    with tab_cidades:
        st.header("🏙️ Análise de Desempenho por Cidade")
        if df_filtrado_city.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            metric_cidade = st.selectbox(
                "Selecionar Métrica para Top Cidades:",
                options=["Faturamento Total da Cidade no Mês", "Unidades Compradas", "Pedidos com Produto"],
                key='metric_cidade_tab'
            )
            n_cidades = st.slider("Número de Cidades no Top N:", min_value=5, max_value=20, value=10, key='n_cidades_tab')

            if selected_produtos_city:
                top_cidades_data = df_filtrado_city.groupby('Cidade')["Faturamento do Produto"].sum().astype(float).nlargest(n_cidades).reset_index()
            else:
                top_cidades_agg = df_filtrado_city.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().reset_index()
                top_cidades_data = top_cidades_agg.groupby('Cidade')['Faturamento Total da Cidade no Mês'].sum().astype(float).nlargest(n_cidades).reset_index()

            top_cidades_data.columns = ['Cidade', 'Total']
            fig_top_cidades = px.bar(top_cidades_data, x='Total', y='Cidade', orientation='h', title=f"Top {n_cidades} Cidades por Faturamento")
            st.plotly_chart(fig_top_cidades, use_container_width=True)

    with tab_estados:
        st.header("🗺️ Análise de Desempenho por Estado")
        if df_filtrado_city.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            metric_estado = st.selectbox(
                "Selecionar Métrica para Top Estados:",
                options=["Faturamento Total da Cidade no Mês", "Unidades Compradas", "Pedidos com Produto"],
                key='metric_estado_tab'
            )
            n_estados = st.slider("Número de Estados no Top N:", min_value=5, max_value=20, value=10, key='n_estados_tab')

            if selected_produtos_city:
                top_estados_data = df_filtrado_city.groupby('Estado')["Faturamento do Produto"].sum().astype(float).nlargest(n_estados).reset_index()
            else:
                top_estados_agg = df_filtrado_city.groupby(['Mês', 'Estado'])['Faturamento Total da Cidade no Mês'].sum().reset_index()
                top_estados_data = top_estados_agg.groupby('Estado')['Faturamento Total da Cidade no Mês'].sum().astype(float).nlargest(n_estados).reset_index()

            top_estados_data.columns = ['Estado', 'Total']
            fig_top_estados = px.bar(top_estados_data, x='Total', y='Estado', orientation='h', title=f"Top {n_estados} Estados por Faturamento")
            st.plotly_chart(fig_top_estados, use_container_width=True)
# (Cole este código logo após o final da seção "with tab_estados:")

    st.markdown("---")

    # --- Comparativos de Período ---
    st.header("🔄 Comparativos de Período (Análise de Cidades)")

    with st.container():
        if selected_months_city:
            col_comp1, col_comp2 = st.columns(2)

            df_base_comp = df_city.copy()
            if selected_cidades_city:
                df_base_comp = df_base_comp[df_base_comp['Cidade'].isin(selected_cidades_city)]
            if selected_estados_city:
                df_base_comp = df_base_comp[df_base_comp['Estado'].isin(selected_estados_city)]

            # Lógica de cálculo para comparativos
            if selected_produtos_city:
                st.info("Comparativos da Análise de Cidades calculados usando 'Faturamento do Produto' e 'Pedidos com Produto'.")
                df_current_period_for_comp = df_base_comp[(df_base_comp['Mês'] >= min(selected_months_city)) & (df_base_comp['Mês'] <= max(selected_months_city)) & df_base_comp['Produto'].isin(selected_produtos_city)]
                current_faturamento_base_comp = df_current_period_for_comp['Faturamento do Produto'].sum()
                current_pedidos_base_comp = df_current_period_for_comp['Pedidos com Produto'].sum()
            else:
                st.info("Comparativos da Análise de Cidades calculados usando 'Faturamento Total da Cidade no Mês' e 'Total de Pedidos da Cidade no Mês'.")
                df_current_period_for_comp = df_base_comp[(df_base_comp['Mês'] >= min(selected_months_city)) & (df_base_comp['Mês'] <= max(selected_months_city))]
                current_faturamento_base_comp = df_current_period_for_comp.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum()
                current_pedidos_base_comp = df_current_period_for_comp.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum()

            # Período anterior
            prev_start_date = min(selected_months_city) - pd.DateOffset(months=1)
            df_previous_month = df_base_comp[(df_base_comp['Mês'] >= prev_start_date) & (df_base_comp['Mês'] < min(selected_months_city))]
            previous_faturamento_base_comp = df_previous_month['Faturamento do Produto'].sum() if selected_produtos_city else df_previous_month.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum()
            previous_pedidos_base_comp = df_previous_month['Pedidos com Produto'].sum() if selected_produtos_city else df_previous_month.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum()

            # Média dos 3 meses anteriores
            three_months_ago_start = min(selected_months_city) - pd.DateOffset(months=3)
            df_three_months_ago = df_base_comp[(df_base_comp['Mês'] >= three_months_ago_start) & (df_base_comp['Mês'] < min(selected_months_city))]
            num_unique_months_3m = len(df_three_months_ago['Mês'].dt.to_period('M').unique())
            avg_3m_faturamento = (df_three_months_ago['Faturamento do Produto'].sum() / num_unique_months_3m) if selected_produtos_city and num_unique_months_3m > 0 else (df_three_months_ago.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum() / num_unique_months_3m if num_unique_months_3m > 0 else 0)
            avg_3m_pedidos = (df_three_months_ago['Pedidos com Produto'].sum() / num_unique_months_3m) if selected_produtos_city and num_unique_months_3m > 0 else (df_three_months_ago.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum() / num_unique_months_3m if num_unique_months_3m > 0 else 0)

            # Cálculo das diferenças
            fat_diff_prev = current_faturamento_base_comp - previous_faturamento_base_comp
            ped_diff_prev = current_pedidos_base_comp - previous_pedidos_base_comp
            fat_diff_3m = current_faturamento_base_comp - avg_3m_faturamento
            ped_diff_3m = current_pedidos_base_comp - avg_3m_pedidos

            with col_comp1:
                st.subheader("Vs. Mês Anterior")
                st.metric(label="Faturamento", value=format_currency_br(current_faturamento_base_comp), delta=format_currency_br(fat_diff_prev))
                st.metric(label="Total Pedidos", value=format_integer_br(current_pedidos_base_comp), delta=format_integer_br(ped_diff_prev))

            with col_comp2:
                st.subheader("Vs. Média dos 3 Meses Anteriores")
                st.metric(label="Faturamento", value=format_currency_br(current_faturamento_base_comp), delta=format_currency_br(fat_diff_3m))
                st.metric(label="Total Pedidos", value=format_integer_br(current_pedidos_base_comp), delta=format_integer_br(ped_diff_3m))
        else:
            st.info("Selecione pelo menos um mês nos filtros para ver os comparativos de período.")

    st.markdown("---")

    # --- Tabela Detalhada ---
    st.header("📋 Dados Detalhados (Análise de Cidades)")

    columns_to_display = [
        'Mês', 'Cidade', 'Estado', 'Produto', 'Unidades Compradas',
        'Pedidos com Produto', 'Faturamento do Produto', 'Participação Faturamento Cidade Mês (%)',
        'Participação Pedidos Cidade Mês (%)', 'Ticket Médio do Produto'
    ]
    df_sorted = df_filtrado_city.sort_values(by='Faturamento do Produto', ascending=False)
    df_exibir_formatted = df_sorted[columns_to_display].copy()

    # Formatação para exibição
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

    # --- Download dos dados ---
    st.header("📥 Export de Dados (Análise de Cidades)")

    if not df_filtrado_city.empty:
        csv = df_filtrado_city.to_csv(index=False, decimal=',', sep=';').encode('utf-8-sig')
        st.download_button(
            label="📥 Download Dados Filtrados CSV",
            data=csv,
            file_name=f"dados_filtrados_cidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
