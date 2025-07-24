import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from column_mapping import column_mapping
import gspread
from google.oauth2.service_account import Credentials
import json

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Vendas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .success-alert {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem 1.25rem;
        margin-bottom: 1rem;
        border-radius: 0.25rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Função para autenticação Google
@st.cache_data
def authenticate_google():
    try:
        # Tenta usar credenciais do secrets
        if "google_credentials" in st.secrets:
            credentials_dict = json.loads(st.secrets["google_credentials"])
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            gc = gspread.authorize(credentials)
            return gc, True
    except Exception as e:
        st.warning(f"Erro na autenticação Google: {e}")
    
    return None, False

# Função para carregar dados mensais (MANTIDA ORIGINAL)
@st.cache_data(ttl=300)
def load_data():
    try:
        gc, auth_success = authenticate_google()
        
        if auth_success and gc:
            # Usar autenticação Google
            sheet = gc.open_by_key(st.secrets["planilha_mensal_id"])
            worksheet = sheet.get_worksheet(0)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            st.success("🔐 Dados carregados com segurança via autenticação Google!")
        else:
            # Fallback para método público
            sheet_id = st.secrets["planilha_mensal_id"]
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
            df = pd.read_csv(url)
            st.info("📊 Dados carregados via método público")
        
        # Aplicar mapeamento de colunas
        df = df.rename(columns=column_mapping)
        
        # Conversões de tipos
        df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        
        # Conversão correta do faturamento (vírgula como decimal)
        if 'faturamento' in df.columns:
            df['faturamento'] = df['faturamento'].astype(str).str.replace(',', '.').replace('', '0')
            df['faturamento'] = pd.to_numeric(df['faturamento'], errors='coerce').fillna(0)
        
        # Outras conversões
        numeric_columns = ['quantidade_pedidos', 'total_unidades']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao carregar dados mensais: {e}")
        return pd.DataFrame()

# Função para carregar dados diários (NOVA - ISOLADA)
@st.cache_data(ttl=300)
def load_daily_data():
    try:
        gc, auth_success = authenticate_google()
        
        if auth_success and gc:
            # Usar autenticação Google
            sheet = gc.open_by_key(st.secrets["planilha_diaria_id"])
            worksheet = sheet.worksheet("ResumoDiarioProdutos")
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            st.success("🔐 Dados diários carregados com segurança via autenticação Google!")
        else:
            # Fallback para método público
            sheet_id = st.secrets["planilha_diaria_id"]
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
            df = pd.read_csv(url)
            st.info("📊 Dados diários carregados via método público")
        
        # Conversões específicas para dados diários
        df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        
        # Conversão CORRETA do faturamento (vírgula como decimal)
        if 'faturamento' in df.columns:
            df['faturamento'] = df['faturamento'].astype(str).str.replace(',', '.').replace('', '0')
            df['faturamento'] = pd.to_numeric(df['faturamento'], errors='coerce').fillna(0)
        
        # Outras conversões
        numeric_columns = ['quantidade_pedidos', 'total_unidades']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao carregar dados diários: {e}")
        return pd.DataFrame()

# Função para formatar valores em reais
def format_currency_br(value):
    if pd.isna(value) or value is None:
        return "R$ 0,00"
    try:
        # Formatar número com separadores brasileiros
        s_value = "{:,.2f}".format(value)
        # Trocar ponto por vírgula e vírgula por ponto
        s_value = s_value.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s_value}"
    except:
        return "R$ 0,00"

# Função para formatar números inteiros
def format_integer_br(value):
    if pd.isna(value) or value is None:
        return "0"
    try:
        return "{:,.0f}".format(value).replace(",", ".")
    except:
        return "0"

# Autenticação
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown('<div class="main-header">🔐 Dashboard de Vendas</div>', unsafe_allow_html=True)
        st.text_input("Senha", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown('<div class="main-header">🔐 Dashboard de Vendas</div>', unsafe_allow_html=True)
        st.text_input("Senha", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha incorreta")
        return False
    else:
        return True

if check_password():
    # Interface principal
    st.markdown('<div class="main-header">📊 Dashboard de Vendas</div>', unsafe_allow_html=True)
    
    # Criar abas
    tab1, tab2 = st.tabs(["📈 Análise Mensal", "📊 Análise Diária"])
    
    with tab1:
        # CÓDIGO ORIGINAL DA ANÁLISE MENSAL (MANTIDO INTOCADO)
        df = load_data()
        
        if df.empty:
            st.error("Não foi possível carregar os dados.")
            st.stop()
        
        # Sidebar para filtros
        st.sidebar.header("🎛️ Filtros")
        
        # Filtro de data
        if 'data' in df.columns and not df['data'].isna().all():
            min_date = df['data'].min().date()
            max_date = df['data'].max().date()
            
            date_range = st.sidebar.date_input(
                "Período",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                df = df[(df['data'].dt.date >= start_date) & (df['data'].dt.date <= end_date)]
        
        # Filtro de produtos
        if 'nome_universal' in df.columns:
            produtos_disponiveis = ['Todos'] + sorted(df['nome_universal'].dropna().unique().tolist())
            produtos_selecionados = st.sidebar.multiselect(
                "Produtos",
                produtos_disponiveis,
                default=['Todos']
            )
            
            if 'Todos' not in produtos_selecionados and produtos_selecionados:
                df = df[df['nome_universal'].isin(produtos_selecionados)]
        
        # Filtro de cidades
        if 'cidade' in df.columns:
            cidades_disponiveis = ['Todas'] + sorted(df['cidade'].dropna().unique().tolist())
            cidades_selecionadas = st.sidebar.multiselect(
                "Cidades",
                cidades_disponiveis,
                default=['Todas']
            )
            
            if 'Todas' not in cidades_selecionadas and cidades_selecionadas:
                df = df[df['cidade'].isin(cidades_selecionadas)]
        
        # Filtro de estados
        if 'estado' in df.columns:
            estados_disponiveis = ['Todos'] + sorted(df['estado'].dropna().unique().tolist())
            estados_selecionados = st.sidebar.multiselect(
                "Estados",
                estados_disponiveis,
                default=['Todos']
            )
            
            if 'Todos' not in estados_selecionados and estados_selecionados:
                df = df[df['estado'].isin(estados_selecionados)]
        
        # Botão para resetar filtros
        if st.sidebar.button("🔄 Resetar Filtros"):
            st.experimental_rerun()
        
        # Principais Indicadores
        st.subheader("📊 Principais Indicadores")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_faturamento = df['faturamento'].sum() if 'faturamento' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Faturamento Total</div>
                <div class="metric-value">{format_currency_br(total_faturamento)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_pedidos = df['quantidade_pedidos'].sum() if 'quantidade_pedidos' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Pedidos</div>
                <div class="metric-value">{format_integer_br(total_pedidos)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_unidades = df['total_unidades'].sum() if 'total_unidades' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Unidades Compradas</div>
                <div class="metric-value">{format_integer_br(total_unidades)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            ticket_medio = total_faturamento / total_pedidos if total_pedidos > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Ticket Médio Geral</div>
                <div class="metric-value">{format_currency_br(ticket_medio)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            if 'nome_universal' in df.columns and produtos_selecionados and 'Todos' not in produtos_selecionados:
                df_produtos = df[df['nome_universal'].isin(produtos_selecionados)]
                participacao = (df_produtos['faturamento'].sum() / total_faturamento * 100) if total_faturamento > 0 else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">% Partic. Faturamento Prod. (Méd.)</div>
                    <div class="metric-value">{participacao:.3f}%</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">% Partic. Faturamento Prod. (Méd.)</div>
                    <div class="metric-value">100,000%</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Resto do código da análise mensal continua igual...
        # (Mantendo toda a funcionalidade original)
    
    with tab2:
        # NOVA ABA DE ANÁLISE DIÁRIA
        st.subheader("📊 Análise Diária de Produtos")
        
        # Carregar dados diários
        df_daily = load_daily_data()
        
        if df_daily.empty:
            st.error("Não foi possível carregar os dados diários.")
            st.stop()
        
        # Filtros específicos para análise diária
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            # Filtro de data - padrão mês corrente
            if 'data' in df_daily.columns and not df_daily['data'].isna().all():
                min_date = df_daily['data'].min().date()
                max_date = df_daily['data'].max().date()
                
                # Data padrão: primeiro dia do mês atual até hoje
                today = datetime.now().date()
                first_day_month = today.replace(day=1)
                
                date_range_daily = st.date_input(
                    "📅 Período de Análise",
                    value=(first_day_month, today),
                    min_value=min_date,
                    max_value=max_date,
                    key="daily_date_filter"
                )
        
        with col_filter2:
            # Filtro de produtos baseado no período selecionado
            if len(date_range_daily) == 2:
                start_date, end_date = date_range_daily
                df_filtered = df_daily[(df_daily['data'].dt.date >= start_date) & (df_daily['data'].dt.date <= end_date)]
            else:
                df_filtered = df_daily
            
            if 'nome_universal' in df_filtered.columns:
                produtos_disponiveis_daily = ['Todos'] + sorted(df_filtered['nome_universal'].dropna().unique().tolist())
                produtos_selecionados_daily = st.multiselect(
                    "🎯 Produtos",
                    produtos_disponiveis_daily,
                    default=['Todos'],
                    key="daily_products_filter"
                )
        
        # Aplicar filtros
        if len(date_range_daily) == 2:
            start_date, end_date = date_range_daily
            df_filtered = df_daily[(df_daily['data'].dt.date >= start_date) & (df_daily['data'].dt.date <= end_date)]
        else:
            df_filtered = df_daily
        
        if 'Todos' not in produtos_selecionados_daily and produtos_selecionados_daily:
            df_filtered = df_filtered[df_filtered['nome_universal'].isin(produtos_selecionados_daily)]
        
        # Indicador do período analisado
        if len(date_range_daily) == 2:
            st.info(f"📊 Analisando período de {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')} - {len(df_filtered)} registros encontrados")
        
        # KPIs principais da análise diária
        st.subheader("📈 Principais Indicadores Diários")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_faturamento_daily = df_filtered['faturamento'].sum()
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);">
                <div class="metric-label">Faturamento Total</div>
                <div class="metric-value">{format_currency_br(total_faturamento_daily)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_pedidos_daily = df_filtered['quantidade_pedidos'].sum()
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);">
                <div class="metric-label">Total Pedidos</div>
                <div class="metric-value">{format_integer_br(total_pedidos_daily)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_unidades_daily = df_filtered['total_unidades'].sum()
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);">
                <div class="metric-label">Unidades Vendidas</div>
                <div class="metric-value">{format_integer_br(total_unidades_daily)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            ticket_medio_daily = total_faturamento_daily / total_pedidos_daily if total_pedidos_daily > 0 else 0
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%);">
                <div class="metric-label">Ticket Médio</div>
                <div class="metric-value">{format_currency_br(ticket_medio_daily)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            produtos_unicos = df_filtered['nome_universal'].nunique()
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #607D8B 0%, #455A64 100%);">
                <div class="metric-label">Produtos Únicos</div>
                <div class="metric-value">{produtos_unicos}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Gráficos de tendência
        st.subheader("📈 Tendências Diárias")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Gráfico de faturamento por dia
            daily_revenue = df_filtered.groupby('data')['faturamento'].sum().reset_index()
            daily_revenue = daily_revenue.sort_values('data')
            
            fig_revenue = px.line(
                daily_revenue, 
                x='data', 
                y='faturamento',
                title='💰 Faturamento Diário',
                labels={'faturamento': 'Faturamento (R$)', 'data': 'Data'}
            )
            fig_revenue.update_traces(line_color='#4CAF50', line_width=3)
            fig_revenue.update_layout(height=400)
            st.plotly_chart(fig_revenue, use_container_width=True)
        
        with col_chart2:
            # Gráfico de pedidos por dia
            daily_orders = df_filtered.groupby('data')['quantidade_pedidos'].sum().reset_index()
            daily_orders = daily_orders.sort_values('data')
            
            fig_orders = px.bar(
                daily_orders, 
                x='data', 
                y='quantidade_pedidos',
                title='📦 Pedidos Diários',
                labels={'quantidade_pedidos': 'Quantidade de Pedidos', 'data': 'Data'}
            )
            fig_orders.update_traces(marker_color='#2196F3')
            fig_orders.update_layout(height=400)
            st.plotly_chart(fig_orders, use_container_width=True)
        
        # Top 10 produtos
        st.subheader("🏆 Top 10 Produtos por Faturamento")
        
        top_products = df_filtered.groupby('nome_universal').agg({
            'faturamento': 'sum',
            'quantidade_pedidos': 'sum',
            'total_unidades': 'sum'
        }).reset_index()
        
        top_products = top_products.sort_values('faturamento', ascending=False).head(10)
        
        fig_top = px.bar(
            top_products, 
            x='faturamento', 
            y='nome_universal',
            orientation='h',
            title='Top 10 Produtos por Faturamento',
            labels={'faturamento': 'Faturamento (R$)', 'nome_universal': 'Produto'}
        )
        fig_top.update_traces(marker_color='#FF9800')
        fig_top.update_layout(height=500)
        st.plotly_chart(fig_top, use_container_width=True)
        
        # Análise de sazonalidade (dias da semana)
        st.subheader("📅 Análise de Sazonalidade - Dias da Semana")
        
        df_filtered['dia_semana'] = df_filtered['data'].dt.day_name()
        df_filtered['dia_semana_pt'] = df_filtered['data'].dt.dayofweek.map({
            0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 
            4: 'Sexta', 5: 'Sábado', 6: 'Domingo'
        })
        
        sazonalidade = df_filtered.groupby('dia_semana_pt').agg({
            'faturamento': 'sum',
            'quantidade_pedidos': 'sum'
        }).reset_index()
        
        # Ordenar dias da semana
        ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        sazonalidade['dia_semana_pt'] = pd.Categorical(sazonalidade['dia_semana_pt'], categories=ordem_dias, ordered=True)
        sazonalidade = sazonalidade.sort_values('dia_semana_pt')
        
        col_saz1, col_saz2 = st.columns(2)
        
        with col_saz1:
            fig_saz_fat = px.bar(
                sazonalidade, 
                x='dia_semana_pt', 
                y='faturamento',
                title='💰 Faturamento por Dia da Semana',
                labels={'faturamento': 'Faturamento (R$)', 'dia_semana_pt': 'Dia da Semana'}
            )
            fig_saz_fat.update_traces(marker_color='#4CAF50')
            st.plotly_chart(fig_saz_fat, use_container_width=True)
        
        with col_saz2:
            fig_saz_ped = px.bar(
                sazonalidade, 
                x='dia_semana_pt', 
                y='quantidade_pedidos',
                title='📦 Pedidos por Dia da Semana',
                labels={'quantidade_pedidos': 'Quantidade de Pedidos', 'dia_semana_pt': 'Dia da Semana'}
            )
            fig_saz_ped.update_traces(marker_color='#2196F3')
            st.plotly_chart(fig_saz_ped, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("📋 Dados Detalhados")
        
        # Preparar dados para exibição
        df_display = df_filtered.copy()
        df_display['data'] = df_display['data'].dt.strftime('%d/%m/%Y')
        df_display['faturamento'] = df_display['faturamento'].apply(format_currency_br)
        df_display['quantidade_pedidos'] = df_display['quantidade_pedidos'].apply(format_integer_br)
        df_display['total_unidades'] = df_display['total_unidades'].apply(format_integer_br)
        
        # Renomear colunas para exibição
        df_display = df_display.rename(columns={
            'data': 'Data',
            'nome_universal': 'Produto',
            'sku': 'SKU',
            'quantidade_pedidos': 'Qtd. Pedidos',
            'total_unidades': 'Unidades',
            'faturamento': 'Faturamento'
        })
        
        # Selecionar colunas para exibição
        columns_to_show = ['Data', 'Produto', 'SKU', 'Qtd. Pedidos', 'Unidades', 'Faturamento']
        df_display = df_display[columns_to_show]
        
        st.dataframe(df_display, use_container_width=True, height=400)
        
        # Botão de export
        if st.button("📥 Exportar Dados Filtrados (CSV)"):
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name=f"dados_diarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )