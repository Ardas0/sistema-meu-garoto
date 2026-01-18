import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np
import time
import copy 
from streamlit_option_menu import option_menu
from streamlit_gsheets import GSheetsConnection

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
COLOR_DANGER = "#B22222"        # Vermelho Crítico
COLOR_WARN = "#FF4500"          # Laranja/Vermelho (Ruim)
COLOR_ATTENTION = "#FFD700"     # Amarelo (Atenção)
COLOR_GOOD = "#228B22"          # Verde (Bom)
COLOR_EXCELLENT = "#006400"     # Verde Escuro (Excelente)
COLOR_HIGHLIGHT = "#006400"

# Configuração Base
DEFAULT_CONFIG = {
    'pesos_fornecedores': {
        'Conformidade Técnica': 1.0, 'Durabilidade': 1.0,
        'Pontualidade': 1.0, 'Estoque': 1.0, 'Embalagem': 1.0,
        'Preço': 1.0, 'Pagamento': 1.0, 'Suporte': 1.0, 'Comunicação': 1.0
    },
    'pesos_produtos': {
        'Rentabilidade': 1.0, 
        'Qualidade Material': 1.0, 'Custo-Benefício': 1.0,
        'Durabilidade': 1.0, 'Acabamento': 1.0, 'Disponibilidade': 1.0,
        'Inovação': 1.0, 'Embalagem': 1.0, 'Sustentabilidade': 1.0
    },
    'tipo_periodo': 'Trimestral',
    'anos_disponiveis': [2024, 2025, 2026],
    'autosave': True
}

# --- NOVO: GUIA DE REFERÊNCIA BASEADO NAS IMAGENS ---
GUIA_CRITERIOS = {
    "Pontualidade": {
        "5.0": "Atrasos frequentes (ou atraso 'médio' que atrapalha produção), precisa cobrar.",
        "6.0": "Atrasos acontecem, mas são pontuais e com aviso; impacto controlável.",
        "8.0": "Entrega no prazo quase sempre; comunicação proativa.",
        "10.0": "Entrega perfeita e previsível; antecipa riscos."
    },
    "Conformidade Técnica": {
        "5.0": "Produto/insumo frequentemente fora de especificação; precisa retrabalho/triagem.",
        "6.0": "Pequenas variações, mas dentro do tolerável; ajustes ocasionais.",
        "8.0": "Atende especificação com consistência.",
        "10.0": "Padrão impecável + documentação/controle excelente."
    },
    "Comunicação": {
        "5.0": "Demora para responder; resolução lenta; você corre atrás.",
        "6.0": "Responde, mas às vezes com atraso; resolve com alguma insistência.",
        "8.0": "Responde rápido, resolve sem fricção.",
        "10.0": "Acompanha, antecipa, resolve antes de virar problema."
    },
    "Suporte": { # Reaproveitando lógica de Comunicação se não houver específico
        "5.0": "Demora para responder; resolução lenta.",
        "6.0": "Responde, mas às vezes com atraso.",
        "8.0": "Suporte rápido e eficiente.",
        "10.0": "Suporte proativo, resolve antes de virar problema."
    },
    "Preço": {
        "5.0": "Preço instável ou 'barato que sai caro' (problema gera custo total).",
        "6.0": "Preço ok, mas negociação limitada; condições medianas.",
        "8.0": "Boa relação custo-benefício + condição coerente.",
        "10.0": "Excelente custo total + flexibilidade."
    },
    "Pagamento": { # Reaproveitando lógica de Preço/Flexibilidade
        "5.0": "Condições rígidas ou ruins para o fluxo de caixa.",
        "6.0": "Condições medianas/padrão de mercado.",
        "8.0": "Boas condições, ajuda no fluxo.",
        "10.0": "Flexibilidade total e parceria financeira."
    },
    "Qualidade Material": {
        "5.0": "Falhas visíveis, padrão inconsistente, risco de devolução/reclamação.",
        "6.0": "Padrão aceitável, mas variação de lote aparece.",
        "8.0": "Consistente, poucos problemas.",
        "10.0": "Padrão premium, praticamente zero não conformidade."
    },
    "Acabamento": { # Similar a Qualidade Material
        "5.0": "Falhas visíveis, padrão inconsistente.",
        "6.0": "Aceitável, mas com pequenas variações.",
        "8.0": "Consistente e bem acabado.",
        "10.0": "Acabamento premium/perfeito."
    },
    "Rentabilidade": {
        "5.0": "Margem baixa, giro ruim, 'come' esforço e caixa.",
        "6.0": "Margem ok, mas precisa ajustes (preço, canal, custo).",
        "8.0": "Margem boa e giro saudável.",
        "10.0": "Produto estrela (alta margem + alto giro + baixa perda)."
    },
    "Disponibilidade": {
        "5.0": "Falta com frequência; quebra venda.",
        "6.0": "Algumas rupturas, mas recupera rápido.",
        "8.0": "Disponibilidade alta e previsível.",
        "10.0": "Zero ruptura e planejamento perfeito."
    }
}

CATEGORIAS_FORN = ["Matéria Prima", "Embalagens", "Logística", "Manutenção", "Serviços", "Outros"]
CATEGORIAS_PROD = ["Vinhos", "Cachaça", "Licor", "Embalagens", "Vestuário", "Doces", "Outros"]

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Meu Garoto - Supply Chain", layout="wide", page_icon="🍷")

# ==============================================================================
# 2. ESTILOS (CSS)
# ==============================================================================

st.markdown(f"""
<style>
    /* Fonte Global */
    .stApp, .stMarkdown, h1, h2, h3, h4, p, label, .stButton, .stSelectbox, .stTextInput {{
        font-family: 'Times New Roman', serif !important;
    }}
    
    .stApp {{ background-color: {COLOR_BG}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_SIDEBAR}; }}
    
    /* Textos gerais brancos */
    .stMarkdown p, .stMarkdown label, h1, h2, h3 {{ color: {COLOR_TEXT_WHITE} !important; }}
    
    /* KPI Cards e Áreas Claras - Força texto preto */
    .kpi-card {{
        background-color: {COLOR_CARD_BG};
        border-radius: 8px; padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3); margin-bottom: 10px;
        color: {COLOR_TEXT_BLACK} !important;
    }}
    .kpi-card div, .kpi-card h2, .kpi-card span, .kpi-card p, .kpi-card h1, .kpi-card h3 {{ 
        color: {COLOR_TEXT_BLACK} !important; 
    }}

    .stButton>button {{
        background-color: {COLOR_PRIMARY}; color: white !important;
        font-weight: bold; border-radius: 5px; border: none;
    }}
    .stButton>button:hover {{ background-color: {COLOR_HIGHLIGHT}; }}
    
    [data-testid="stDataFrame"] {{ background-color: {COLOR_CARD_BG}; color: black; }}
</style>
""", unsafe_allow_html=True)

def make_card_html(label, value, desc, color_border):
    return f"""
    <div class="kpi-card" style="border-left: 5px solid {color_border};">
        <div style="font-size: 14px; font-weight: bold; text-transform: uppercase; color: black !important;">{label}</div>
        <div style="font-size: 32px; font-weight: 800; color: {color_border} !important;">{value}</div>
        <div style="font-size: 12px; font-style: italic; color: black !important;">{desc}</div>
    </div>
    """

# ==============================================================================
# 3. GERENCIADOR DE DADOS
# ==============================================================================

class DataManager:
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.config = self._load_config()
            
            self.df_fornecedores = self._load_sheet("fornecedores", ['Nome', 'Categoria', 'Contato'])
            self.df_aval_forn = self._load_sheet("avaliacoes", self._get_cols_aval('fornecedores'))
            
            self.df_produtos = self._load_sheet("produtos", ['Nome', 'Categoria', 'Detalhes'])
            self.df_aval_prod = self._load_sheet("avaliacoes_produtos", self._get_cols_aval('produtos'))
            
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            self.df_fornecedores = pd.DataFrame()
            self.df_aval_forn = pd.DataFrame()
            self.df_produtos = pd.DataFrame()
            self.df_aval_prod = pd.DataFrame()
            self.config = copy.deepcopy(DEFAULT_CONFIG)
        
    def _get_cols_aval(self, tipo):
        key = 'pesos_fornecedores' if tipo == 'fornecedores' else 'pesos_produtos'
        dict_pesos = self.config.get(key, DEFAULT_CONFIG[key])
        return ['Nome', 'Ano', 'Periodo', 'Score Final'] + list(dict_pesos.keys())

    def _load_sheet(self, sheet_name, expected_cols):
        try:
            df = self.conn.read(worksheet=sheet_name, ttl=0)
            if df.empty: return pd.DataFrame(columns=expected_cols)
            if 'Trimestre' in df.columns: df.rename(columns={'Trimestre': 'Periodo'}, inplace=True)
            for col in expected_cols:
                if col not in df.columns: df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=expected_cols)

    def _load_config(self):
        try:
            df = self.conn.read(worksheet="config", ttl=0)
            if not df.empty and 'JSON_DUMP' in df.columns:
                json_str = df.iloc[0]['JSON_DUMP']
                loaded = json.loads(json_str)
                
                # FUSÃO INTELIGENTE: Começa com o padrão
                config = copy.deepcopy(DEFAULT_CONFIG)
                
                # Atualiza campos simples
                for k, v in loaded.items():
                    if k not in ['pesos_fornecedores', 'pesos_produtos']:
                        config[k] = v
                
                # Atualiza pesos preservando novos campos do Default
                if 'pesos_fornecedores' in loaded:
                    config['pesos_fornecedores'].update(loaded['pesos_fornecedores'])
                if 'pesos_produtos' in loaded:
                    config['pesos_produtos'].update(loaded['pesos_produtos'])
                    
                return config
        except:
            pass
        return copy.deepcopy(DEFAULT_CONFIG)

    def save_all(self):
        try:
            self.conn.update(worksheet="fornecedores", data=self.df_fornecedores)
            self.conn.update(worksheet="avaliacoes", data=self.df_aval_forn)
            self.conn.update(worksheet="produtos", data=self.df_produtos)
            self.conn.update(worksheet="avaliacoes_produtos", data=self.df_aval_prod)
            
            config_str = json.dumps(self.config, ensure_ascii=False)
            df_conf = pd.DataFrame([{'JSON_DUMP': config_str}])
            self.conn.update(worksheet="config", data=df_conf)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
            return False

    def calcular_nota(self, dados_dict, tipo):
        key = 'pesos_fornecedores' if tipo == 'fornecedor' else 'pesos_produtos'
        pesos_atuais = self.config[key]
        soma_ponderada = 0
        soma_pesos = sum(pesos_atuais.values())
        for criterio, peso in pesos_atuais.items():
            if criterio in dados_dict:
                val = pd.to_numeric(dados_dict[criterio], errors='coerce')
                if pd.isna(val): val = 0.0
                soma_ponderada += (val * peso)
        return soma_ponderada / soma_pesos if soma_pesos > 0 else 0.0

    def get_periodos(self):
        if self.config['tipo_periodo'] == 'Trimestral':
            return ["1º Trimestre", "2º Trimestre", "3º Trimestre", "4º Trimestre"]
        return ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    def recalcular_tudo(self):
        if not self.df_aval_forn.empty:
            self.df_aval_forn['Score Final'] = self.df_aval_forn.apply(lambda row: self.calcular_nota(row, 'fornecedor'), axis=1)
        if not self.df_aval_prod.empty:
            self.df_aval_prod['Score Final'] = self.df_aval_prod.apply(lambda row: self.calcular_nota(row, 'produto'), axis=1)

# ==============================================================================
# 4. DASHBOARD
# ==============================================================================
def plot_dashboard(df_aval, df_cad, criterios, tipo_label, manager):
    if df_aval.empty or df_cad.empty:
        st.info(f"Sem dados de {tipo_label} para exibir. Cadastre e avalie itens primeiro.")
        return

    cols_to_keep = [c for c in df_aval.columns if c != 'Categoria']
    df_aval_clean = df_aval[cols_to_keep].copy()
    
    df_aval_clean['Score Final'] = pd.to_numeric(df_aval_clean['Score Final'], errors='coerce')
    df_valid = df_aval_clean.dropna(subset=['Score Final']).copy()
    
    for c in criterios:
        if c in df_valid.columns:
            df_valid[c] = pd.to_numeric(df_valid[c], errors='coerce').fillna(0)
    
    df_completo = pd.merge(df_valid, df_cad[['Nome', 'Categoria']], on="Nome", how="inner")
    
    if df_completo.empty:
        st.warning(f"Existem avaliações, mas os nomes não batem com o cadastro de {tipo_label}.")
        return

    # Cards
    melhor = df_completo.loc[df_completo['Score Final'].idxmax()]
    pior = df_completo.loc[df_completo['Score Final'].idxmin()]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(make_card_html(f"Total {tipo_label}", f"{len(df_cad)}", "Cadastrados", COLOR_PRIMARY), unsafe_allow_html=True)
    c2.markdown(make_card_html("Média Geral", f"{df_completo['Score Final'].mean():.2f}", "Meta: > 7.5", COLOR_SECONDARY), unsafe_allow_html=True)
    c3.markdown(make_card_html("Destaque", f"{melhor['Score Final']:.2f}", melhor['Nome'], COLOR_HIGHLIGHT), unsafe_allow_html=True)
    c4.markdown(make_card_html("Atenção", f"{pior['Score Final']:.2f}", pior['Nome'], COLOR_DANGER), unsafe_allow_html=True)

    # Gráficos
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("🏆 Ranking Geral")
        df_rank = df_completo.groupby('Nome', as_index=False)['Score Final'].mean().sort_values('Score Final')
        fig_bar = px.bar(df_rank, x='Score Final', y='Nome', orientation='h', 
                         text_auto='.2f', color='Score Final', color_continuous_scale=[COLOR_DANGER, "#FFFF00", COLOR_PRIMARY])
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), xaxis=dict(range=[0, 10]))
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        st.subheader("🕸️ Radar Global (Médias)")
        medias = df_completo[criterios].mean().tolist()
        fig_avg = go.Figure(go.Scatterpolar(r=medias + [medias[0]], theta=criterios + [criterios[0]], fill='toself'))
        fig_avg.update_layout(polar=dict(radialaxis=dict(range=[0, 10], visible=True)), paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
        st.plotly_chart(fig_avg, use_container_width=True)

    st.markdown("---")
    
    # --- RAIO X ---
    st.subheader(f"🔍 Raio-X Individual: {tipo_label}")
    c_sel, c_rad = st.columns([1, 2])
    
    nomes_disp = df_completo['Nome'].unique()
    
    with c_sel:
        sel_nome = st.selectbox(f"Selecione:", nomes_disp, key=f"sel_{tipo_label}_raio_x")
        df_item = df_completo[df_completo['Nome'] == sel_nome]
        
        if not df_item.empty:
            media_item = df_item['Score Final'].mean()
            cat_item = df_item['Categoria'].iloc[0]
            
            st.markdown(f"""
            <div class="kpi-card" style="background-color: {COLOR_CARD_BG}; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
                <h3 style="color: black !important; margin: 0 0 10px 0;">{sel_nome}</h3>
                <p style="color: black !important; font-size: 16px;"><b>Categoria:</b> {cat_item}</p>
                <div style="font-size: 48px; font-weight: bold; color: {COLOR_PRIMARY} !important;">{media_item:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- MODIFICAÇÃO DE LÓGICA DE DIAGNÓSTICO ---
            st.markdown("#### Diagnóstico e Ação Sugerida:")
            
            if media_item < 3.0:
                texto_status = "CRÍTICO / TOTALMENTE INSATISFATÓRIO"
                texto_acao = "🚨 AÇÃO RECOMENDADA: ABANDONO OU SUBSTITUIÇÃO IMEDIATA"
                cor_box = COLOR_DANGER
                icone = "🚫"
            elif media_item < 5.0:
                texto_status = "RUIM / MUITOS PROBLEMAS"
                texto_acao = "🛑 AÇÃO RECOMENDADA: REVER CONTRATO (Risco Alto)"
                cor_box = COLOR_WARN
                icone = "👎"
            elif media_item < 7.0:
                texto_status = "REGULAR / ABAIXO DA META"
                texto_acao = "⚠️ AÇÃO RECOMENDADA: FICAR EM OBSERVAÇÃO"
                cor_box = COLOR_ATTENTION
                icone = "👀"
            elif media_item < 9.0:
                texto_status = "BOM / DENTRO DA META"
                texto_acao = "✅ AÇÃO RECOMENDADA: MANTER RELACIONAMENTO"
                cor_box = COLOR_GOOD
                icone = "👍"
            else:
                texto_status = "EXCELENTE / REFERÊNCIA"
                texto_acao = "🌟 AÇÃO RECOMENDADA: FORTALECER PARCERIA"
                cor_box = COLOR_EXCELLENT
                icone = "🏆"

            st.markdown(f"""
            <div style="background-color: {cor_box}; color: white; padding: 15px; border-radius: 8px; margin-top: 10px;">
                <div style="font-size: 14px; font-weight: bold; opacity: 0.9;">STATUS ATUAL:</div>
                <div style="font-size: 20px; font-weight: bold; margin-bottom: 8px;">{icone} {texto_status}</div>
                <hr style="margin: 5px 0; border-color: rgba(255,255,255,0.3);">
                <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; margin-top: 5px;">Decisão do Sistema:</div>
                <div style="font-size: 16px; font-weight: bold;">{texto_acao}</div>
            </div>
            """, unsafe_allow_html=True)
            # ---------------------------------------------
            
        else:
            st.error("Erro ao carregar dados.")

    with c_rad:
        if not df_item.empty:
            vals_item = df_item[criterios].mean().tolist()
            vals_item += [vals_item[0]]
            
            df_cat = df_completo[df_completo['Categoria'] == cat_item]
            vals_cat = df_cat[criterios].mean().tolist()
            vals_cat += [vals_cat[0]]
            
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=vals_item, theta=criterios + [criterios[0]], fill='toself', name=sel_nome))
            fig_r.add_trace(go.Scatterpolar(r=vals_cat, theta=criterios + [criterios[0]], name=f'Média {cat_item}', line=dict(dash='dot')))
            fig_r.update_layout(polar=dict(radialaxis=dict(range=[0, 10])), paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), legend=dict(orientation="h"))
            st.plotly_chart(fig_r, use_container_width=True)

    # --- EVOLUÇÃO TEMPORAL ---
    st.markdown("---")
    st.subheader(f"📈 Evolução Temporal")
    
    tipo_evolucao = st.radio("Modo de Visualização:", ["Individual", "Comparar com Categoria"], horizontal=True, key=f"rad_ev_{tipo_label}")
    
    if not df_item.empty:
        cat_atual = df_item['Categoria'].iloc[0]
        
        if tipo_evolucao == "Individual":
            df_chart = df_item.copy()
            color_arg = None
            title_txt = f"Histórico de Notas: {sel_nome}"
        else:
            df_chart = df_completo[df_completo['Categoria'] == cat_atual].copy()
            color_arg = 'Nome'
            title_txt = f"Comparativo - Categoria: {cat_atual}"

        if len(df_chart) > 0:
            periodos_ordem = manager.get_periodos()
            map_p = {p: i for i, p in enumerate(periodos_ordem)}
            df_chart['sort_idx'] = df_chart['Periodo'].map(map_p).fillna(0)
            df_chart = df_chart.sort_values(['Ano', 'sort_idx'])
            df_chart['Timeline'] = df_chart['Periodo'].astype(str) + "/" + df_chart['Ano'].astype(str)
            
            fig_line = px.line(df_chart, x='Timeline', y='Score Final', color=color_arg, markers=True, title=title_txt)
            fig_line.update_layout(yaxis=dict(range=[0, 10]), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
            if tipo_evolucao == "Individual":
                fig_line.update_traces(line_color='#00FF00', line_width=4, marker_size=10)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Sem histórico suficiente.")
    else:
        st.info("Selecione um item acima.")

# ==============================================================================
# 5. APP PRINCIPAL
# ==============================================================================

if 'manager' not in st.session_state:
    st.session_state['manager'] = DataManager()

manager = st.session_state['manager']

with st.sidebar:
    st.image("https://cdn.awsli.com.br/1964/1964962/logo/meu-garoto_marca-v-a-r-4qbs46wai7.png", use_container_width=True)
    st.markdown(f"<div style='text-align:center; background:{COLOR_PRIMARY}; padding:5px; border-radius:5px; color:white; font-weight:bold; margin-bottom:15px;'>Supply Chain Intelligence</div>", unsafe_allow_html=True)
    
    opcao = option_menu(
        menu_title=None,
        options=["Fornecedores", "Produtos", "Avaliação Unificada", "Relatórios", "Base de Dados", "Configurações"],
        icons=["truck", "box-seam", "clipboard-check", "file-text", "server", "gear"],
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "nav-link": {"font-family": "Times New Roman", "font-size": "16px", "text-align": "left", "margin":"2px"},
            "nav-link-selected": {"background-color": COLOR_PRIMARY, "color": "white"},
        }
    )

if opcao == "Fornecedores":
    st.title("🚚 Gestão de Fornecedores")
    tab_dash, tab_cad = st.tabs(["📊 Dashboard", "➕ Cadastrar Fornecedor"])
    with tab_dash:
        plot_dashboard(manager.df_aval_forn, manager.df_fornecedores, list(manager.config['pesos_fornecedores'].keys()), "Fornecedores", manager)
    with tab_cad:
        with st.form("cad_forn"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Empresa")
            cat = c1.selectbox("Categoria", CATEGORIAS_FORN)
            contato = c2.text_input("Contato")
            if st.form_submit_button("Salvar Fornecedor"):
                if nome and nome not in manager.df_fornecedores['Nome'].values:
                    novo = pd.DataFrame([{'Nome': nome, 'Categoria': cat, 'Contato': contato}])
                    manager.df_fornecedores = pd.concat([manager.df_fornecedores, novo], ignore_index=True)
                    manager.save_all()
                    st.success(f"{nome} cadastrado!")
                    st.rerun()
                else:
                    st.error("Nome inválido ou já existente.")

elif opcao == "Produtos":
    st.title("📦 Gestão de Produtos")
    tab_dash, tab_cad = st.tabs(["📊 Dashboard", "➕ Cadastrar Produto"])
    with tab_dash:
        plot_dashboard(manager.df_aval_prod, manager.df_produtos, list(manager.config['pesos_produtos'].keys()), "Produtos", manager)
    with tab_cad:
        with st.form("cad_prod"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome do Produto")
            cat = c1.selectbox("Categoria", CATEGORIAS_PROD)
            detalhe = c2.text_input("Detalhes/Safra/Lote")
            if st.form_submit_button("Salvar Produto"):
                if nome and nome not in manager.df_produtos['Nome'].values:
                    novo = pd.DataFrame([{'Nome': nome, 'Categoria': cat, 'Detalhes': detalhe}])
                    manager.df_produtos = pd.concat([manager.df_produtos, novo], ignore_index=True)
                    manager.save_all()
                    st.success(f"{nome} cadastrado!")
                    st.rerun()
                else:
                    st.error("Nome inválido ou já existente.")

elif opcao == "Avaliação Unificada":
    st.title("📝 Central de Avaliação")
    tipo_aval = st.radio("O que você vai avaliar?", ["Fornecedor", "Produto"], horizontal=True)
    
    if tipo_aval == "Fornecedor":
        df_alvo = manager.df_fornecedores
        df_hist = manager.df_aval_forn
        criterios = manager.config['pesos_fornecedores']
        chave_tipo = 'fornecedor'
    else:
        df_alvo = manager.df_produtos
        df_hist = manager.df_aval_prod
        criterios = manager.config['pesos_produtos']
        chave_tipo = 'produto'
        
    if df_alvo.empty:
        st.warning(f"Cadastre {tipo_aval}s primeiro.")
    else:
        c1, c2, c3 = st.columns(3)
        sel_item = c1.selectbox(f"Selecione o {tipo_aval}", df_alvo['Nome'].unique())
        sel_ano = c2.selectbox("Ano", sorted(manager.config['anos_disponiveis']))
        sel_per = c3.selectbox("Período", manager.get_periodos())

        existente = df_hist[(df_hist['Nome'] == sel_item) & (df_hist['Ano'] == sel_ano) & (df_hist['Periodo'] == sel_per)]
        defaults = {k: 5.0 for k in criterios.keys()}
        if not existente.empty:
            st.info(f"Editando avaliação existente. Nota: {existente.iloc[0]['Score Final']}")
            for k in criterios.keys():
                try: defaults[k] = float(existente.iloc[0][k])
                except: pass

        # --- GUIA DE REFERÊNCIA NA INTERFACE ---
        with st.expander("📖 Guia de Referência (Critérios)", expanded=False):
            st.markdown("Use este guia para padronizar as notas:")
            cols_guia = st.columns(3)
            for i, (crit_nome, descricoes) in enumerate(GUIA_CRITERIOS.items()):
                # Só exibe se o critério estiver na configuração atual
                if crit_nome in criterios:
                    with cols_guia[i % 3]:
                        st.markdown(f"**{crit_nome}**")
                        for nota_ref, texto in descricoes.items():
                            st.markdown(f"- **{nota_ref}**: {texto}")
                        st.markdown("---")

        with st.form("form_aval_unificada"):
            cols = st.columns(2)
            inpts = {}
            for i, crit in enumerate(criterios.keys()):
                inpts[crit] = cols[i%2].slider(crit, 0.0, 10.0, defaults[crit], 0.5)
            
            if st.form_submit_button("Salvar Avaliação"):
                nota = manager.calcular_nota(inpts, chave_tipo)
                nova = {'Nome': sel_item, 'Ano': sel_ano, 'Periodo': sel_per, 'Score Final': nota}
                nova.update(inpts)
                
                df_hist = df_hist[~((df_hist['Nome'] == sel_item) & (df_hist['Ano'] == sel_ano) & (df_hist['Periodo'] == sel_per))]
                df_hist = pd.concat([df_hist, pd.DataFrame([nova])], ignore_index=True)
                
                if tipo_aval == "Fornecedor": manager.df_aval_forn = df_hist
                else: manager.df_aval_prod = df_hist
                
                manager.save_all()
                st.success(f"Avaliação salva! Nota: {nota:.2f}")
                time.sleep(1)
                st.rerun()

elif opcao == "Relatórios":
    st.title("📑 Relatórios")
    tipo_rep = st.radio("Tipo:", ["Fornecedor", "Produto"], horizontal=True)
    df_dados = manager.df_aval_forn if tipo_rep == "Fornecedor" else manager.df_aval_prod
    
    if df_dados.empty:
        st.warning("Sem dados.")
    else:
        c1, c2 = st.columns(2)
        sel_nome = c1.selectbox("Nome", df_dados['Nome'].unique())
        sel_ano = c2.selectbox("Ano", sorted(manager.config['anos_disponiveis']))
        
        if st.button("Gerar Visualização"):
            filtrado = df_dados[(df_dados['Nome'] == sel_nome) & (df_dados['Ano'] == sel_ano)]
            st.dataframe(filtrado, use_container_width=True)

elif opcao == "Base de Dados":
    st.title("📂 Dados Brutos")
    
    if st.button("☁️ Forçar Salvamento na Nuvem", type="primary"):
        if manager.save_all(): st.toast("Salvo com sucesso!", icon="☁️")

    st.markdown("---")
    with st.expander("📤 Importar CSV"):
        st.warning("Dados importados serão anexados ao final da tabela existente.")
        destino = st.radio("Destino:", 
                           ["Fornecedores", "Avaliações Fornecedores", "Produtos", "Avaliações Produtos"], horizontal=True)
        up_file = st.file_uploader("Arquivo CSV", type=['csv'])
        
        if up_file:
            try:
                df_new = pd.read_csv(up_file)
                st.dataframe(df_new.head(3))
                if st.button("Confirmar Importação"):
                    if destino == "Fornecedores":
                        manager.df_fornecedores = pd.concat([manager.df_fornecedores, df_new], ignore_index=True)
                    elif destino == "Avaliações Fornecedores":
                        manager.df_aval_forn = pd.concat([manager.df_aval_forn, df_new], ignore_index=True)
                    elif destino == "Produtos":
                        manager.df_produtos = pd.concat([manager.df_produtos, df_new], ignore_index=True)
                    elif destino == "Avaliações Produtos":
                        manager.df_aval_prod = pd.concat([manager.df_aval_prod, df_new], ignore_index=True)
                    manager.save_all()
                    st.success("Importado!")
            except Exception as e:
                st.error(f"Erro: {e}")
    st.markdown("---")

    t1, t2, t3, t4 = st.tabs(["Fornecedores", "Aval. Fornecedores", "Produtos", "Aval. Produtos"])
    
    with t1:
        manager.df_fornecedores = st.data_editor(manager.df_fornecedores, num_rows="dynamic", use_container_width=True, key="edit_forn")
    with t2:
        manager.df_aval_forn = st.data_editor(manager.df_aval_forn, num_rows="dynamic", use_container_width=True, key="edit_aval_forn")
    with t3:
        manager.df_produtos = st.data_editor(manager.df_produtos, num_rows="dynamic", use_container_width=True, key="edit_prod")
    with t4:
        manager.df_aval_prod = st.data_editor(manager.df_aval_prod, num_rows="dynamic", use_container_width=True, key="edit_aval_prod")

elif opcao == "Configurações":
    st.title("⚙️ Configurações do Sistema")
    
    t1, t2, t3 = st.tabs(["Pesos Fornecedores", "Pesos Produtos", "Geral"])
    
    def render_weights_form(key_config, label_btn, key_suffix):
        nw_pesos = {}
        cols = st.columns(3)
        dict_pesos = manager.config.get(key_config, DEFAULT_CONFIG[key_config])
        
        for i, (k, v) in enumerate(dict_pesos.items()):
            nw_pesos[k] = cols[i%3].number_input(k, 0.0, 5.0, float(v), 0.5, key=f"{key_suffix}_{k}")
        
        if st.button(label_btn, key=f"btn_{key_suffix}"):
            manager.config[key_config] = nw_pesos
            manager.recalcular_tudo()
            manager.save_all()
            st.success("Pesos atualizados!")
            time.sleep(1)
            st.rerun()

    with t1:
        st.subheader("Critérios Fornecedores")
        render_weights_form('pesos_fornecedores', "Salvar Pesos Fornecedores", "forn")
    with t2:
        st.subheader("Critérios Produtos")
        render_weights_form('pesos_produtos', "Salvar Pesos Produtos", "prod")
    with t3:
        st.info("Configurações Gerais")
        atual = manager.config['tipo_periodo']
        novo = st.radio("Frequência", ["Trimestral", "Mensal"], index=0 if atual == "Trimestral" else 1)
        if novo != atual:
            manager.config['tipo_periodo'] = novo
            manager.save_all()
            st.rerun()
