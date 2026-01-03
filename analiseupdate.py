import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np
from streamlit_option_menu import option_menu
from streamlit_gsheets import GSheetsConnection  # <--- NOVA IMPORTAÇÃO OBRIGATÓRIA

# ==============================================================================
# 1. CONSTANTES E CONFIGURAÇÕES GLOBAIS
# ==============================================================================

# Cores
COLOR_PRIMARY = "#228B22"       # Verde Floresta
COLOR_SECONDARY = "#2F4F4F"     # Dark Slate Gray
COLOR_BG = "#2F4F4F"            # Fundo Principal
COLOR_SIDEBAR = "#8FBC8F"       # Sidebar
COLOR_TEXT_WHITE = "#FFFFFF"
COLOR_TEXT_BLACK = "#000000"
COLOR_CARD_BG = "#FFFAFA"
COLOR_DANGER = "#B22222"
COLOR_HIGHLIGHT = "#006400"

# Configuração Padrão
DEFAULT_CONFIG = {
    'pesos': {
        'Conformidade Técnica': 4.0, 'Durabilidade': 4.0,
        'Pontualidade': 3.0, 'Estoque': 2.0, 'Embalagem': 1.0,
        'Preço': 2.0, 'Pagamento': 1.0,
        'Suporte': 2.0, 'Comunicação': 1.0
    },
    'tipo_periodo': 'Trimestral',
    'anos_disponiveis': [2024, 2025, 2026],
    'autosave': False
}

CATEGORIAS_PADRAO = [
    "Matéria Prima (Álcool de Cereais/Aguardente/Polpa)", 
    "Embalagens", 
    "Garrafas",
    "Logística e Transporte", 
    "Manutenção Industrial", 
    "Serviços Gerais",
    "Outros"
]

# --- CONFIGURAÇÃO DA PÁGINA (Deve ser o primeiro comando Streamlit) ---
st.set_page_config(page_title="Meu Garoto - Gestão de Fornecedores", layout="wide", page_icon="🍷")

# ==============================================================================
# 2. ESTILOS (CSS) E COMPONENTES VISUAIS
# ==============================================================================

def apply_css():
    st.markdown(f"""
    <style>
        /* Importar Fontes e Configurações Globais */
        html, body, [class*="css"] {{
            font-family: 'Times New Roman', Times, serif !important;
            font-size: 18px !important;
        }}

        /* Fundo Principal */
        .stApp {{ background-color: {COLOR_BG}; }}

        /* Sidebar */
        [data-testid="stSidebar"] {{ background-color: {COLOR_SIDEBAR}; }}
        
        /* Títulos */
        h1, h2, h3, h4 {{ 
            font-weight: bold !important; 
            color: {COLOR_TEXT_WHITE} !important; 
        }}
        
        /* Textos gerais no fundo escuro viram branco */
        .stMarkdown p, .stMarkdown label, .stMarkdown span, .stMarkdown div {{ 
            color: {COLOR_TEXT_WHITE} !important; 
        }}

        /* CLASSE ESPECÍFICA PARA FORÇAR PRETO NOS CARDS */
        .kpi-card, .kpi-card p, .kpi-card span, .kpi-card div, .kpi-card h2 {{
            color: {COLOR_TEXT_BLACK} !important;
        }}
        
        /* --- CORREÇÃO DO BUG DE COR --- */
        /* Forçar texto PRETO dentro dos alertas (Warnings, Success, Info, Error) */
        [data-testid="stAlert"] {{
            color: {COLOR_TEXT_BLACK} !important;
        }}
        [data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] div {{
            color: {COLOR_TEXT_BLACK} !important;
        }}

        /* Botões */
        .stButton>button {{ 
            background-color: {COLOR_PRIMARY}; 
            color: white !important; 
            border-radius: 8px; 
            border: 1px solid {COLOR_HIGHLIGHT};
            font-weight: bold;
            font-size: 20px !important;
            height: 50px;
        }}
        .stButton>button:hover {{
            background-color: {COLOR_CARD_BG}; 
            color: {COLOR_PRIMARY} !important;
            border-color: {COLOR_PRIMARY};
        }}

        /* Tabelas e Dataframes */
        [data-testid="stDataFrame"] {{ 
            background-color: {COLOR_CARD_BG}; 
            border: 1px solid #000;
            color: {COLOR_TEXT_BLACK} !important;
        }}
        [data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span {{
            color: {COLOR_TEXT_BLACK} !important;
        }}
        
        /* Inputs e Selectbox */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {{
            background-color: {COLOR_CARD_BG} !important;
            color: {COLOR_TEXT_BLACK} !important;
            font-family: 'Times New Roman', Times, serif !important;
        }}
        .stTextInput label, .stSelectbox label, .stNumberInput label {{
            color: {COLOR_TEXT_WHITE} !important;
        }}

        /* Ajustes do Menu Lateral */
        .nav-link {{
            font-family: 'Times New Roman', Times, serif !important;
            font-size: 18px !important;
            color: {COLOR_TEXT_BLACK} !important;
        }}
        
        /* Centralizar Logo da Sidebar */
        [data-testid="stSidebar"] img {{ display: block; margin-left: auto; margin-right: auto; }}
        
    </style>
    """, unsafe_allow_html=True)

def make_card_html(label, value, desc, color_border):
    style_div = f"""
        background-color: {COLOR_CARD_BG}; 
        border-left: 8px solid {color_border}; 
        border-radius: 5px; 
        padding: 20px; 
        box-shadow: 3px 3px 8px rgba(0,0,0,0.5); 
        margin-bottom: 25px;
    """
    return f"""
    <div style="{style_div}" class="kpi-card">
        <div style="font-family: 'Times New Roman'; font-size: 18px; margin: 0; font-weight: bold; text-transform: uppercase;">{label}</div>
        <div style="color: {color_border} !important; font-family: 'Times New Roman'; font-size: 42px; margin: 5px 0; font-weight: 800;">{value}</div>
        <div style="font-family: 'Times New Roman'; font-size: 16px; margin: 0; font-style: italic;">{desc}</div>
    </div>
    """

# ==============================================================================
# 3. GERENCIADOR DE DADOS (VERSÃO GOOGLE SHEETS / NUVEM)
# ==============================================================================

class DataManager:
    def __init__(self):
        # Conexão com Google Sheets usando secrets.toml
        self.conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Carrega Configuração (Pesos, Anos, etc)
        self.config = self._load_config_from_sheet()
        
        # Carrega Tabelas Principais
        self.df_fornecedores = self._load_sheet("fornecedores", ['Nome', 'Categoria', 'Contato'])
        self.df_avaliacoes = self._load_sheet("avaliacoes", self._get_cols_avaliacao())
        
    def _get_cols_avaliacao(self):
        # Gera colunas baseadas nos pesos atuais
        return ['Nome', 'Ano', 'Periodo', 'Score Final'] + list(self.config['pesos'].keys())

    def _load_sheet(self, sheet_name, expected_cols):
        """Lê uma aba do Google Sheets. Retorna vazio se der erro ou não existir."""
        try:
            # ttl=0 obriga a baixar dados novos, sem usar cache antigo
            df = self.conn.read(worksheet=sheet_name, ttl=0)
            
            # Se a planilha estiver vazia ou com erro, retorna estrutura vazia
            if df.empty:
                return pd.DataFrame(columns=expected_cols)
            
            # Normalização de colunas legadas
            if 'Trimestre' in df.columns:
                df.rename(columns={'Trimestre': 'Periodo'}, inplace=True)
                
            return df
        except Exception:
            # Em caso de erro (ex: aba não existe), retorna DataFrame vazio
            return pd.DataFrame(columns=expected_cols)

    def _load_config_from_sheet(self):
        """Tenta ler a configuração salva na aba 'config'."""
        try:
            df = self.conn.read(worksheet="config", ttl=0)
            if not df.empty and 'JSON_DUMP' in df.columns:
                # Recupera o JSON salvo na primeira célula
                json_str = df.iloc[0]['JSON_DUMP']
                config = DEFAULT_CONFIG.copy()
                config.update(json.loads(json_str))
                # Garantir float nos pesos
                config['pesos'] = {k: float(v) for k, v in config['pesos'].items()}
                return config
        except Exception:
            pass
        return DEFAULT_CONFIG.copy()

    def save_all(self):
        """Salva todos os DataFrames no Google Sheets."""
        try:
            # 1. Salvar Fornecedores
            self.conn.update(worksheet="fornecedores", data=self.df_fornecedores)
            
            # 2. Salvar Avaliações
            self.conn.update(worksheet="avaliacoes", data=self.df_avaliacoes)
            
            # 3. Salvar Configuração (Transforma o dicionário em texto JSON)
            config_str = json.dumps(self.config, ensure_ascii=False)
            df_conf = pd.DataFrame([{'JSON_DUMP': config_str}])
            self.conn.update(worksheet="config", data=df_conf)
            
            # Limpa cache para garantir que a próxima leitura pegue o que acabamos de salvar
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar na nuvem: {e}")
            return False

    def check_autosave(self):
        # Autosave na nuvem pode ser lento, verifica se está habilitado
        if self.config.get('autosave', False):
            self.save_all()

    def calcular_nota_final(self, dados_dict):
        pesos_atuais = self.config['pesos']
        soma_ponderada = 0
        soma_pesos = sum(pesos_atuais.values())
        
        for criterio, peso in pesos_atuais.items():
            if criterio in dados_dict:
                val = pd.to_numeric(dados_dict[criterio], errors='coerce')
                if pd.isna(val): val = 0.0
                soma_ponderada += (val * peso)
                
        if soma_pesos == 0: return 0.0
        return soma_ponderada / soma_pesos

    def get_opcoes_periodo(self):
        if self.config['tipo_periodo'] == 'Trimestral':
            return ["1º Trimestre", "2º Trimestre", "3º Trimestre", "4º Trimestre"]
        else:
            return [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ]

    def recalcular_todas_notas(self):
        """Recalcula scores se os pesos mudarem."""
        if not self.df_avaliacoes.empty:
            criterios = list(self.config['pesos'].keys())
            def _recalc(row):
                dados = {k: row[k] for k in criterios if k in row}
                return self.calcular_nota_final(dados)
            self.df_avaliacoes['Score Final'] = self.df_avaliacoes.apply(_recalc, axis=1)

# ==============================================================================
# 4. APLICAÇÃO PRINCIPAL (INTERFACE)
# ==============================================================================

# Aplica CSS
apply_css()

# Inicialização do DataManager (Singleton Pattern no Session State)
if 'manager' not in st.session_state:
    st.session_state['manager'] = DataManager()

manager = st.session_state['manager']
df_cad = manager.df_fornecedores
df_aval = manager.df_avaliacoes

# Variáveis de apoio
pesos = manager.config['pesos']
criterios_radar = list(pesos.keys())

# --- SIDEBAR ---
with st.sidebar:
    col_esq, col_centro, col_dir = st.columns([0.1, 3, 0.1])
    with col_centro:
        url_logo = "https://cdn.awsli.com.br/1964/1964962/logo/meu-garoto_marca-v-a-r-4qbs46wai7.png"
        st.image(url_logo, use_container_width=True)

    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 30px;">
            <p style="color: white !important; font-family: 'Times New Roman'; font-size: 16px; background-color: {COLOR_PRIMARY}; padding: 4px; border-radius: 4px; margin-top: 5px;">Supply Chain Intelligence</p>
        </div>
    """, unsafe_allow_html=True)

    opcao = option_menu(
        menu_title="Menu Principal",
        options=["Dashboard", "Cadastrar Fornecedor", "Avaliação Periódica", "Relatório Anual", "Base de Dados", "Configurações"],
        icons=["bar-chart-fill", "box-seam", "clipboard-data", "file-earmark-pdf", "server", "gear"],
        menu_icon="list",
        default_index=0,
        styles={
            "container": {"padding": "5px !important", "background-color": COLOR_CARD_BG, "border-radius": "10px"},
            "icon": {"color": "black", "font-size": "20px"}, 
            "nav-link": {"font-family": "Times New Roman", "font-size": "18px", "color": "black", "font-weight": "bold"},
            "nav-link-selected": {"background-color": COLOR_PRIMARY, "color": "white !important"},
            "menu-title": {"color": "black !important", "font-weight": "bold", "font-size": "20px"}
        }
    )

# --- 1. DASHBOARD ---
if opcao == "Dashboard":
    st.title("📊 Painel de Controle")
    st.markdown("**Visão geral da performance dos parceiros de negócio.**")

    c_ano, c_per = st.columns(2)
    lista_anos = sorted(manager.config['anos_disponiveis'])
    lista_periodos = manager.get_opcoes_periodo()
    
    ano_sel = c_ano.selectbox("Filtrar Ano", ["(Todos)"] + list(lista_anos))
    per_sel = c_per.selectbox("Filtrar Período", ["(Todos)"] + lista_periodos)

    # Filtragem Inicial
    df_filtrado = df_aval.copy()
    
    # Filtrar apenas fornecedores que ainda existem no cadastro
    if not df_cad.empty:
        fornecedores_ativos = df_cad['Nome'].unique()
        df_filtrado = df_filtrado[df_filtrado['Nome'].isin(fornecedores_ativos)]
    else:
        df_filtrado = pd.DataFrame(columns=df_filtrado.columns)
    
    if ano_sel != "(Todos)": df_filtrado = df_filtrado[df_filtrado['Ano'] == ano_sel]
    if per_sel != "(Todos)": df_filtrado = df_filtrado[df_filtrado['Periodo'] == per_sel]

    # Limpeza e Conversão
    df_filtrado['Score Final'] = pd.to_numeric(df_filtrado['Score Final'], errors='coerce')
    df_filtrado = df_filtrado.dropna(subset=['Score Final'])
    
    for k in criterios_radar:
        if k in df_filtrado.columns:
            df_filtrado[k] = pd.to_numeric(df_filtrado[k], errors='coerce').fillna(0)

    if not df_filtrado.empty:
        # Agregação
        df_agrupado = df_filtrado.groupby('Nome', as_index=False)[['Score Final'] + criterios_radar].mean()
        
        # Merge para pegar a Categoria
        df_completo = pd.merge(df_agrupado, df_cad[['Nome', 'Categoria']], on="Nome", how="inner")

        if not df_completo.empty:
            melhor = df_completo.loc[df_completo['Score Final'].idxmax()]
            pior = df_completo.loc[df_completo['Score Final'].idxmin()]

            # KPIs Cards
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(make_card_html("Fornecedores", f"{len(df_completo)}", "Ativos e Avaliados", COLOR_PRIMARY), unsafe_allow_html=True)
            with c2: st.markdown(make_card_html("Nota Média", f"{df_completo['Score Final'].mean():.2f}", "Meta: > 7.5", COLOR_SECONDARY), unsafe_allow_html=True)
            with c3: st.markdown(make_card_html("Destaque", f"{melhor['Nome']}", f"Nota: {melhor['Score Final']:.2f}", COLOR_HIGHLIGHT), unsafe_allow_html=True)
            with c4: st.markdown(make_card_html("Atenção", f"{pior['Nome']}", f"Nota: {pior['Score Final']:.2f}", COLOR_DANGER), unsafe_allow_html=True)

            st.markdown("---")
            
            # Gráficos Principais
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("🏆 Ranking Geral")
                fig_bar = px.bar(
                    df_completo.sort_values('Score Final', ascending=True), 
                    x='Score Final', y='Nome', orientation='h', text_auto='.2f',
                    color='Score Final', color_continuous_scale=[COLOR_DANGER, COLOR_CARD_BG, COLOR_PRIMARY]
                )
                fig_bar.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="white", family="Times New Roman", size=14),
                    xaxis=dict(range=[0, 10], showgrid=False), yaxis=dict(title=None),
                    coloraxis_colorbar=dict(title="Nota")
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_g2:
                st.subheader("🌎 Média Global")
                medias = df_completo[criterios_radar].mean().tolist()
                if medias:
                    medias += [medias[0]]
                    cats_ciclo = criterios_radar + [criterios_radar[0]]
                    fig_avg = go.Figure(go.Scatterpolar(
                        r=medias, theta=cats_ciclo, fill='toself', name='Média', 
                        line_color=COLOR_CARD_BG, fillcolor='rgba(255, 250, 250, 0.4)'
                    ))
                    fig_avg.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 10]), bgcolor="rgba(0,0,0,0)"),
                        paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white", family="Times New Roman", size=14)
                    )
                    st.plotly_chart(fig_avg, use_container_width=True)

            st.markdown("---")
            st.subheader("🔍 Raio-X do Fornecedor")

            # Seção Raio-X
            col_sel, col_radar = st.columns([1, 2])
            with col_sel:
                sel_forn = st.selectbox("Selecione Fornecedor:", df_completo['Nome'].unique())
                dados_f = df_completo[df_completo['Nome'] == sel_forn].iloc[0]
                
                st.markdown(f"""
                <div style="background-color: {COLOR_CARD_BG}; padding: 15px; border-radius: 5px;" class="kpi-card">
                    <div><b>Categoria:</b> {dados_f['Categoria']}</div>
                    <div><b>Nota Final:</b> {dados_f['Score Final']:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if dados_f['Score Final'] >= 7.5: st.success("Aprovado")
                elif dados_f['Score Final'] >= 6.0: st.warning("Em Observação")
                else: st.error("Risco Alto")

            with col_radar:
                vals = [dados_f[k] for k in criterios_radar] + [dados_f[criterios_radar[0]]]
                cats_c = criterios_radar + [criterios_radar[0]]
                
                media_cat = [0] * len(cats_c)
                df_cat = df_completo[df_completo['Categoria'] == dados_f['Categoria']]
                if not df_cat.empty:
                    media_cat = df_cat[criterios_radar].mean().tolist()
                    media_cat += [media_cat[0]]

                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(r=vals, theta=cats_c, fill='toself', name=sel_forn, line_color=COLOR_PRIMARY))
                fig_r.add_trace(go.Scatterpolar(r=media_cat, theta=cats_c, name='Média Categoria', line_color=COLOR_DANGER, line=dict(dash='dot')))
                fig_r.update_layout(
                    polar=dict(radialaxis=dict(range=[0, 10]), bgcolor="rgba(0,0,0,0)"),
                    paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), legend=dict(orientation="h")
                )
                st.plotly_chart(fig_r, use_container_width=True)

            # GRÁFICO DE EVOLUÇÃO
            st.markdown("### 📈 Evolução e Estatísticas")
            df_hist = df_aval[df_aval['Nome'] == sel_forn].copy()
            df_hist['Score Final'] = pd.to_numeric(df_hist['Score Final'], errors='coerce')
            df_hist = df_hist.dropna(subset=['Score Final'])

            if not df_hist.empty:
                ordem_p = manager.get_opcoes_periodo()
                map_p = {p: i for i, p in enumerate(ordem_p)}
                df_hist['idx'] = df_hist['Periodo'].map(map_p)
                df_hist = df_hist.sort_values(by=['Ano', 'idx'])
                df_hist['Timeline'] = df_hist['Periodo'] + " / " + df_hist['Ano'].astype(str)

                media_hist = df_hist['Score Final'].mean()
                std_hist = df_hist['Score Final'].std() if len(df_hist) > 1 else 0

                c_opt, c_stat = st.columns([1, 3])
                tipo_graf = c_opt.selectbox("Visualização:", ["Linha (Tendência)", "Histograma", "Área"])
                
                with c_stat:
                    st.markdown(f"**Média Histórica:** {media_hist:.2f} | **Desvio Padrão:** {std_hist:.2f}")

                fig_ev = go.Figure()
                if tipo_graf == "Histograma":
                    fig_ev.add_trace(go.Histogram(x=df_hist['Score Final'], marker_color=COLOR_PRIMARY, nbinsx=10, opacity=0.7))
                    fig_ev.add_vline(x=media_hist, line_dash="dash", line_color="yellow", annotation_text="Média")
                else:
                    mode = 'lines+markers' if "Linha" in tipo_graf else 'lines'
                    fill = 'tozeroy' if "Área" in tipo_graf else None
                    fig_ev.add_trace(go.Scatter(x=df_hist['Timeline'], y=df_hist['Score Final'], mode=mode, fill=fill, line=dict(color='#00FF7F', width=3)))
                    fig_ev.add_hline(y=media_hist, line_dash="dash", line_color="yellow", annotation_text="Média")
                    fig_ev.add_hline(y=media_hist + std_hist, line_dash="dot", line_color="cyan")
                    fig_ev.add_hline(y=media_hist - std_hist, line_dash="dot", line_color="cyan")
                    fig_ev.update_layout(yaxis=dict(range=[0, 10.5]))

                fig_ev.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,0.05)',
                    font=dict(color="white"), margin=dict(t=30, b=30)
                )
                st.plotly_chart(fig_ev, use_container_width=True)
            else:
                st.info("Histórico insuficiente para gráficos de evolução.")

        else:
            st.info("Nenhum dado encontrado para o filtro.")
    else:
        st.info("Nenhum dado encontrado.")

# --- 2. CADASTRO ---
elif opcao == "Cadastrar Fornecedor":
    st.title("🆕 Novo Fornecedor")
    with st.container(border=True):
        with st.form("form_cadastro"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da Empresa")
            categoria = c1.selectbox("Categoria", CATEGORIAS_PADRAO)
            contato = c2.text_input("E-mail / Telefone")
            
            if st.form_submit_button("💾 Salvar Cadastro"):
                if nome and nome not in manager.df_fornecedores['Nome'].values:
                    novo = pd.DataFrame([{'Nome': nome, 'Categoria': categoria, 'Contato': contato}])
                    manager.df_fornecedores = pd.concat([manager.df_fornecedores, novo], ignore_index=True)
                    manager.check_autosave()
                    st.success(f"{nome} cadastrado!")
                    st.rerun()
                elif nome:
                    st.warning("Fornecedor já existe.")
                else:
                    st.error("Nome obrigatório.")

# --- 3. AVALIAÇÃO ---
elif opcao == "Avaliação Periódica":
    st.title("📝 Avaliação de Desempenho")
    if manager.df_fornecedores.empty:
        st.warning("Cadastre fornecedores primeiro.")
    else:
        c1, c2, c3 = st.columns(3)
        sel_forn = c1.selectbox("Fornecedor:", manager.df_fornecedores['Nome'].unique())
        sel_ano = c2.selectbox("Ano:", sorted(manager.config['anos_disponiveis']))
        sel_per = c3.selectbox("Período:", manager.get_opcoes_periodo())

        existente = manager.df_avaliacoes[
            (manager.df_avaliacoes['Nome'] == sel_forn) & 
            (manager.df_avaliacoes['Ano'] == sel_ano) & 
            (manager.df_avaliacoes['Periodo'] == sel_per)
        ]
        
        defaults = {k: 5.0 for k in criterios_radar}
        if not existente.empty:
            st.info("✏️ Editando avaliação existente.")
            for k in criterios_radar:
                try: defaults[k] = float(existente.iloc[0][k])
                except: pass

        with st.form("form_aval"):
            col_list = st.columns(2)
            inputs = {}
            for i, crit in enumerate(criterios_radar):
                with col_list[i % 2]:
                    inputs[crit] = st.slider(crit, 0.0, 10.0, defaults[crit], step=0.1)
            
            if st.form_submit_button("✅ Concluir Avaliação"):
                nota = manager.calcular_nota_final(inputs)
                nova_linha = {'Nome': sel_forn, 'Ano': sel_ano, 'Periodo': sel_per, 'Score Final': nota}
                nova_linha.update(inputs)
                
                manager.df_avaliacoes = manager.df_avaliacoes[
                    ~((manager.df_avaliacoes['Nome'] == sel_forn) & 
                      (manager.df_avaliacoes['Ano'] == sel_ano) & 
                      (manager.df_avaliacoes['Periodo'] == sel_per))
                ]
                manager.df_avaliacoes = pd.concat([manager.df_avaliacoes, pd.DataFrame([nova_linha])], ignore_index=True)
                manager.check_autosave()
                st.success(f"Avaliação salva! Nota: {nota:.2f}")
                st.rerun()

# --- 4. RELATÓRIO ---
elif opcao == "Relatório Anual":
    st.title("📑 Relatório Oficial")
    if manager.df_avaliacoes.empty:
        st.warning("Sem dados.")
    else:
        c1, c2, c3 = st.columns([2,1,1])
        sel_forn = c1.selectbox("Fornecedor", manager.df_fornecedores['Nome'].unique())
        sel_ano = c2.selectbox("Ano", sorted(manager.df_avaliacoes['Ano'].unique()))
        
        if c3.button("Gerar Relatório"):
            periodos_ativos = manager.get_opcoes_periodo()
            df_rep = manager.df_avaliacoes[(manager.df_avaliacoes['Nome'] == sel_forn) & (manager.df_avaliacoes['Ano'] == sel_ano)]
            pesos_atuais = manager.config['pesos']

            notas_map = {c: {p: "-" for p in periodos_ativos} for c in criterios_radar}
            totais_periodo = {p: 0 for p in periodos_ativos}

            for _, row in df_rep.iterrows():
                p = row['Periodo']
                if p in periodos_ativos:
                    for crit in criterios_radar:
                        try: notas_map[crit][p] = f"{float(row[crit]):.1f}"
                        except: notas_map[crit][p] = "0.0"
                    try: totais_periodo[p] = float(row['Score Final'])
                    except: totais_periodo[p] = 0.0

            header_periods = "".join([f"<th>{p}</th>" for p in periodos_ativos])
            
            def get_status_color(valor):
                if valor == 0: return "transparent"
                if valor >= 7.5: return "#90EE90" 
                if valor >= 6.0: return "#FAFAD2" 
                return "#FFB6C1"

            html_table = f"""
            <div style="padding: 20px; background-color: {COLOR_CARD_BG}; border: 2px solid {COLOR_PRIMARY}; border-radius: 5px; overflow-x: auto;">
                <h2 style="text-align:center; color:black !important;">FICHA DE AVALIAÇÃO - {sel_ano}</h2>
                <h3 style="text-align:center; color:black !important;">Fornecedor: {sel_forn}</h3>
                <table style="width:100%; border-collapse: collapse; color: black;">
                <tr style="background-color: {COLOR_PRIMARY}; color: white;">
                    <th style="padding:8px; border:1px solid black;">Critério</th>
                    <th style="padding:8px; border:1px solid black;">Peso</th>
                    {header_periods}
                </tr>
            """
            
            for item in criterios_radar:
                html_table += f"<tr><td style='padding:8px; border:1px solid black;'>{item}</td>"
                html_table += f"<td style='padding:8px; border:1px solid black; text-align:center;'>{pesos_atuais.get(item, 0)}</td>"
                for p in periodos_ativos:
                    html_table += f"<td style='padding:8px; border:1px solid black; text-align:center;'>{notas_map[item][p]}</td>"
                html_table += "</tr>"
            
            html_table += "<tr><td colspan='2' style='padding:8px; border:1px solid black; font-weight:bold; text-align:right;'>NOTA FINAL:</td>"
            for p in periodos_ativos:
                val = totais_periodo[p]
                html_table += f"<td style='padding:8px; border:1px solid black; font-weight:bold; text-align:center; background-color:{get_status_color(val)}'>{val:.2f}</td>"
            
            html_table += "</table></div>"
            st.markdown(html_table, unsafe_allow_html=True)

# --- 5. BASE DE DADOS (CLOUD) ---
elif opcao == "Base de Dados":
    st.title("📂 Gerenciamento de Dados")
    
    st.info("☁️ **Conectado ao Google Sheets**")
    st.caption("Os dados estão sendo salvos automaticamente na sua planilha do Google.")

    c_auto, c_save = st.columns(2)
    
    auto = c_auto.toggle("Autosave (Salvar ao alterar)", value=manager.config.get('autosave', False))
    if auto != manager.config.get('autosave', False):
        manager.config['autosave'] = auto
        if auto: manager.save_all()
    
    if c_save.button("💾 Salvar Tudo na Nuvem Agora"):
        if manager.save_all(): st.success("Salvo com sucesso no Google Sheets!")
        else: st.error("Erro ao salvar.")

    # --- NOVO: ÁREA DE IMPORTAÇÃO CSV ---
    st.markdown("---")
    with st.expander("📤 Importar Arquivo CSV (Migração de Dados)"):
        st.warning("⚠️ Atenção: Os dados importados serão adicionados ao final da tabela atual.")
        tipo_importacao = st.radio("Destino da Importação:", ["Fornecedores", "Avaliações"], horizontal=True)
        uploaded_file = st.file_uploader("Selecione seu arquivo .csv", type=["csv"])

        if uploaded_file:
            try:
                df_novo = pd.read_csv(uploaded_file)
                st.markdown("**Pré-visualização dos dados:**")
                st.dataframe(df_novo.head(3))

                if st.button("Confirmar Importação"):
                    if tipo_importacao == "Fornecedores":
                        manager.df_fornecedores = pd.concat([manager.df_fornecedores, df_novo], ignore_index=True)
                        st.success(f"{len(df_novo)} fornecedores carregados! Clique em 'Salvar Tudo' para enviar para a nuvem.")
                    else:
                        manager.df_avaliacoes = pd.concat([manager.df_avaliacoes, df_novo], ignore_index=True)
                        st.success(f"{len(df_novo)} avaliações carregadas! Clique em 'Salvar Tudo' para enviar para a nuvem.")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
    st.markdown("---")

    tab1, tab2 = st.tabs(["Fornecedores", "Avaliações"])
    with tab1:
        edit_forn = st.data_editor(manager.df_fornecedores, num_rows="dynamic", use_container_width=True)
        if st.button("Atualizar Tabela Fornecedores"):
            manager.df_fornecedores = edit_forn
            manager.check_autosave()
            st.rerun()
            
    with tab2:
        edit_aval = st.data_editor(manager.df_avaliacoes, num_rows="dynamic", use_container_width=True)
        if st.button("Atualizar Tabela Avaliações"):
            manager.df_avaliacoes = edit_aval
            manager.check_autosave()
            st.rerun()

# --- 6. CONFIGURAÇÕES ---
elif opcao == "Configurações":
    st.title("⚙️ Configurações")
    t1, t2, t3 = st.tabs(["Pesos", "Período", "Anos"])
    
    with t1:
        st.markdown("**Defina os pesos (Precisão 0.5):**")
        with st.form("pesos"):
            cols = st.columns(3)
            novos_pesos = {}
            for i, (k, v) in enumerate(manager.config['pesos'].items()):
                novos_pesos[k] = cols[i%3].number_input(f"Peso {k}", 0.0, 5.0, float(v), step=0.5)
            
            if st.form_submit_button("Salvar Pesos"):
                manager.config['pesos'] = novos_pesos
                manager.recalcular_todas_notas()
                manager.check_autosave()
                st.success("Pesos atualizados e notas recalculadas!")
                st.rerun()
    
    with t2:
        atual = manager.config['tipo_periodo']
        novo = st.radio("Frequência", ["Trimestral", "Mensal"], index=0 if atual == "Trimestral" else 1)
        if novo != atual and st.button("Alterar Período"):
            manager.config['tipo_periodo'] = novo
            manager.check_autosave()
            st.rerun()

    with t3:
        col_add, col_del = st.columns(2)
        novo_a = col_add.number_input("Add Ano", 2000, 2100, 2027)
        if col_add.button("Adicionar"):
            if novo_a not in manager.config['anos_disponiveis']:
                manager.config['anos_disponiveis'].append(novo_a)
                manager.config['anos_disponiveis'].sort()
                manager.check_autosave()
                st.rerun()
        
        rem_a = col_del.multiselect("Remover", manager.config['anos_disponiveis'])
        # CORREÇÃO: "Abutton" removido, agora é "button"
        if rem_a and col_del.button("Remover Selecionados"):
            for a in rem_a: manager.config['anos_disponiveis'].remove(a)
            manager.check_autosave()
            st.rerun()