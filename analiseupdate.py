import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np
import time
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
COLOR_DANGER = "#B22222"
COLOR_HIGHLIGHT = "#006400"

# Configuração Base (Esqueleto)
DEFAULT_CONFIG = {
    'pesos_fornecedores': {
        'Conformidade Técnica': 1.0, 'Durabilidade': 1.0,
        'Pontualidade': 1.0, 'Estoque': 1.0, 'Embalagem': 1.0,
        'Preço': 1.0, 'Pagamento': 1.0, 'Suporte': 1.0, 'Comunicação': 1.0
    },
    'pesos_produtos': {
        'Qualidade Material': 1.0, 'Custo-Benefício': 1.0,
        'Durabilidade': 1.0, 'Acabamento': 1.0, 'Disponibilidade': 1.0,
        'Inovação': 1.0, 'Embalagem': 1.0, 'Sustentabilidade': 1.0
    },
    'tipo_periodo': 'Trimestral',
    'anos_disponiveis': [2024, 2025, 2026],
    'autosave': True
}

CATEGORIAS_FORN = ["Matéria Prima", "Embalagens", "Logística", "Manutenção", "Serviços", "Outros"]
CATEGORIAS_PROD = ["Vinho Tinto", "Vinho Branco", "Espumante", "Suco de Uva", "Kit Presente", "Outros"]

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Meu Garoto - Supply Chain", layout="wide", page_icon="🍷")

# ==============================================================================
# 2. ESTILOS (CSS)
# ==============================================================================

st.markdown(f"""
<style>
    .stApp {{ background-color: {COLOR_BG}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_SIDEBAR}; }}
    h1, h2, h3, h4, p, label, span, div {{ font-family: 'Times New Roman', serif !important; }}
    .stMarkdown p, .stMarkdown label, h1, h2, h3 {{ color: {COLOR_TEXT_WHITE} !important; }}
    
    .kpi-card {{
        background-color: {COLOR_CARD_BG};
        border-radius: 8px; padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3); margin-bottom: 10px;
        color: {COLOR_TEXT_BLACK} !important;
    }}
    .kpi-card div, .kpi-card h2, .kpi-card span {{ color: {COLOR_TEXT_BLACK} !important; }}

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
        <div style="font-size: 14px; font-weight: bold; text-transform: uppercase;">{label}</div>
        <div style="font-size: 32px; font-weight: 800; color: {color_border} !important;">{value}</div>
        <div style="font-size: 12px; font-style: italic;">{desc}</div>
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
            self.config = DEFAULT_CONFIG.copy()
        
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
                config = DEFAULT_CONFIG.copy()
                loaded = json.loads(json_str)
                config.update(loaded)
                
                # Garante chaves essenciais
                if 'pesos_fornecedores' not in config: config['pesos_fornecedores'] = DEFAULT_CONFIG['pesos_fornecedores']
                if 'pesos_produtos' not in config: config['pesos_produtos'] = DEFAULT_CONFIG['pesos_produtos']
                return config
        except:
            pass
        return DEFAULT_CONFIG.copy()

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
# 4. FUNÇÃO DE PLOTAGEM (DASHBOARD COMPLETO COM EVOLUÇÃO)
# ==============================================================================
def plot_dashboard(df_aval, df_cad, criterios, tipo_label, manager):
    if df_aval.empty or df_cad.empty:
        st.info(f"Sem dados de {tipo_label} para exibir. Cadastre e avalie itens primeiro.")
        return

    # Limpeza de dados
    df_aval['Score Final'] = pd.to_numeric(df_aval['Score Final'], errors='coerce')
    df_valid = df_aval.dropna(subset=['Score Final']).copy()
    
    # Converte critérios para numérico
    for c in criterios:
        if c in df_valid.columns:
            df_valid[c] = pd.to_numeric(df_valid[c], errors='coerce').fillna(0)
    
    # Merge
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

    # Ranking e Radar Global
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("🏆 Ranking Geral")
        df_rank = df_completo.groupby('Nome', as_index=False)['Score Final'].mean().sort_values('Score Final')
        fig_bar = px.bar(df_rank, x='Score Final', y='Nome', orientation='h', 
                         text_auto='.2f', color='Score Final', color_continuous_scale=[COLOR_DANGER, "#FFFF00", COLOR_PRIMARY])
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), xaxis=dict(range=[0, 10]))
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        st.subheader("🕸️ Radar Global")
        medias = df_completo[criterios].mean().tolist()
        fig_avg = go.Figure(go.Scatterpolar(r=medias + [medias[0]], theta=criterios + [criterios[0]], fill='toself'))
        fig_avg.update_layout(polar=dict(radialaxis=dict(range=[0, 5], visible=True)), paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
        st.plotly_chart(fig_avg, use_container_width=True)

    st.markdown("---")
    
    # --- RAIO X (CORRIGIDO) ---
    st.subheader(f"🔍 Raio-X Individual: {tipo_label}")
    c_sel, c_rad = st.columns([1, 2])
    
    nomes_disp = df_completo['Nome'].unique()
    
    with c_sel:
        # Chave única para o selectbox não conflitar
        sel_nome = st.selectbox(f"Selecione:", nomes_disp, key=f"sel_{tipo_label}_raio_x")
        
        # Filtra dados do item selecionado
        df_item = df_completo[df_completo['Nome'] == sel_nome]
        
        # Proteção contra erro de índice se df_item estiver vazio
        if not df_item.empty:
            media_item = df_item['Score Final'].mean()
            cat_item = df_item['Categoria'].iloc[0]
            
            st.markdown(f"""
            <div style="background-color: {COLOR_CARD_BG}; padding: 15px; border-radius: 5px; color: black; margin-top: 20px;">
                <h3 style="color: black !important; margin:0;">{sel_nome}</h3>
                <p style="color: black !important;"><b>Categoria:</b> {cat_item}</p>
                <h1 style="color: {COLOR_PRIMARY} !important;">{media_item:.2f}</h1>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Erro ao carregar dados deste item.")

    with c_rad:
        if not df_item.empty:
            # Radar Individual
            vals_item = df_item[criterios].mean().tolist()
            vals_item += [vals_item[0]] # Fechar o ciclo
            
            # Média da Categoria
            df_cat = df_completo[df_completo['Categoria'] == cat_item]
            vals_cat = df_cat[criterios].mean().tolist()
            vals_cat += [vals_cat[0]] # Fechar o ciclo
            
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=vals_item, theta=criterios + [criterios[0]], fill='toself', name=sel_nome))
            fig_r.add_trace(go.Scatterpolar(r=vals_cat, theta=criterios + [criterios[0]], name=f'Média {cat_item}', line=dict(dash='dot')))
            fig_r.update_layout(polar=dict(radialaxis=dict(range=[0, 5])), paper_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), legend=dict(orientation="h"))
            st.plotly_chart(fig_r, use_container_width=True)

    # --- EVOLUÇÃO HISTÓRICA (NOVO) ---
    st.markdown("---")
    st.subheader(f"📈 Evolução Temporal: {sel_nome}")
    
    # Filtra histórico apenas deste item
    df_hist = df_valid[df_valid['Nome'] == sel_nome].copy()
    
    if len(df_hist) > 0:
        # Ordenação temporal
        periodos_ordem = manager.get_periodos()
        # Cria mapa de ordem
        map_p = {p: i for i, p in enumerate(periodos_ordem)}
        df_hist['sort_idx'] = df_hist['Periodo'].map(map_p).fillna(0)
        
        df_hist = df_hist.sort_values(['Ano', 'sort_idx'])
        df_hist['Timeline'] = df_hist['Periodo'].astype(str) + "/" + df_hist['Ano'].astype(str)
        
        fig_line = px.line(df_hist, x='Timeline', y='Score Final', markers=True, title=f"Histórico de Notas")
        fig_line.update_layout(yaxis=dict(range=[0, 10]), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
        fig_line.update_traces(line_color='#00FF00', line_width=4, marker_size=10)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Sem histórico suficiente para gerar gráfico de evolução.")


# ==============================================================================
# 5. APP PRINCIPAL
# ==============================================================================

if 'manager' not in st.session_state:
    st.session_state['manager'] = DataManager()

manager = st.session_state['manager']

# --- SIDEBAR ---
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

# --- 1. FORNECEDORES ---
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

# --- 2. PRODUTOS ---
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

# --- 3. AVALIAÇÃO ---
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

        with st.form("form_aval_unificada"):
            cols = st.columns(2)
            inpts = {}
            for i, crit in enumerate(criterios.keys()):
                inpts[crit] = cols[i%2].slider(crit, 0.0, 5.0, defaults[crit], 0.5)
            
            if st.form_submit_button("Salvar Avaliação"):
                nota = manager.calcular_nota(inpts, chave_tipo)
                nova = {'Nome': sel_item, 'Ano': sel_ano, 'Periodo': sel_per, 'Score Final': nota}
                nova.update(inpts)
                
                # Remove antiga e add nova
                df_hist = df_hist[~((df_hist['Nome'] == sel_item) & (df_hist['Ano'] == sel_ano) & (df_hist['Periodo'] == sel_per))]
                df_hist = pd.concat([df_hist, pd.DataFrame([nova])], ignore_index=True)
                
                # Atualiza no manager
                if tipo_aval == "Fornecedor": manager.df_aval_forn = df_hist
                else: manager.df_aval_prod = df_hist
                
                manager.save_all()
                st.success(f"Avaliação de {sel_item} salva! Nota: {nota:.2f}")
                time.sleep(1)
                st.rerun()

# --- 4. RELATÓRIOS ---
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

# --- 5. BASE DE DADOS (VISUAL CORRIGIDO) ---
elif opcao == "Base de Dados":
    st.title("📂 Dados Brutos")
    
    # Botão de salvar agora é limpo e funcional
    if st.button("☁️ Forçar Salvamento na Nuvem", type="primary"):
        if manager.save_all(): st.toast("Salvo com sucesso!", icon="☁️")

    # Área de Importação (Expandida e corrigida)
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

# --- 6. CONFIGURAÇÕES ---
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
