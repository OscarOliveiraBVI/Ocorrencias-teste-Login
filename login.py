import streamlit as st
import requests
import unicodedata
import json
import os
import pandas as pd
import io
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO E SEGREDOS ---
# Agora os dados sensíveis vêm do st.secrets
try:
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
    ADMIN_USER = st.secrets["ADMIN_USER"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
except:
    st.error("Erro: Segredos não configurados no Streamlit Cloud!")
    st.stop()

DB_FILE = "usuarios.json"
HIST_FILE = "historico.json"
LOGO_FILE = "logo.png" 

def carregar_dados(ficheiro, default):
    if not os.path.exists(ficheiro):
        salvar_dados(ficheiro, default)
        return default
    try:
        with open(ficheiro, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def salvar_dados(ficheiro, dados):
    with open(ficheiro, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def limpar_texto(txt):
    return ''.join(c for c in unicodedata.normalize('NFD', txt) 
                  if unicodedata.category(c) != 'Mn').upper()

def formatar_sexo(texto):
    if not texto.strip(): return "Não especificado"
    t = texto.strip().upper()
    genero = "Masculino" if t.startswith("M") else "Feminino" if t.startswith("F") else ""
    if genero:
        idade = ''.join(filter(str.isdigit, t))
        return f"{genero} de {idade} anos" if idade else genero
    return texto.capitalize()

def formatar_hora(texto):
    t = texto.strip().replace(":", "").replace(".", "")
    if len(t) == 4 and t.isdigit(): return f"{t[:2]}:{t[2:]}"
    return texto

def criar_excel_oficial(df):
    output = io.BytesIO()
    start_row = 5
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ocorrências', startrow=start_row)
        workbook  = writer.book
        worksheet = writer.sheets['Ocorrências']
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1, 'align': 'center'})
        cell_fmt = workbook.add_format({'border': 1})
        title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#1F4E78'})
        worksheet.write('C2', 'RELATÓRIO OFICIAL DE OCORRÊNCIAS - BVI', title_fmt)
        worksheet.write('C3', f'Exportado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
        if os.path.exists(LOGO_FILE):
            worksheet.insert_image('A1', LOGO_FILE, {'x_scale': 0.4, 'y_scale': 0.4, 'x_offset': 5, 'y_offset': 5})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(start_row, col_num, value, header_fmt)
            worksheet.set_column(col_num, col_num, 22, cell_fmt)
    return output.getvalue()

# --- INICIALIZAÇÃO ---
st.set_page_config(page_title="BVI - Ocorrências", page_icon="🚒", layout="centered")

if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, width=150)

if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "login_time" not in st.session_state: st.session_state.login_time = None

historico_db = carregar_dados(HIST_FILE, [])

# --- CONTROLO SESSÃO 1H ---
if st.session_state.autenticado and st.session_state.login_time:
    if datetime.now() - st.session_state.login_time > timedelta(hours=1):
        st.warning("⚠️ Sessão expirada!")
        c1, c2 = st.columns(2)
        if c1.button("Continuar"): 
            st.session_state.login_time = datetime.now()
            st.rerun()
        if c2.button("Sair"): 
            st.session_state.autenticado = False
            st.rerun()
        st.stop()

# --- LISTA PESSOAL ---
pessoal = sorted(["Luis Esmenio", "Denis Moreira", "Rafael Fernandes", "Marcia Mondego", 
                  "Francisco Oliveira", "Rui Parada", "Francisco Ferreira", "Pedro Veiga", 
                  "Rui Dias", "Artur Lima", "Óscar Oliveira", "Carlos Mendes", "Eric Mauricio", 
                  "José Melgo", "Andreia Afonso", "Roney Menezes", "EIP1", "EIP2", 
                  "Daniel Fernandes", "Danitiele Menezes", "Diogo Costa", "David Choupina", 
                  "Manuel Pinto", "Paulo Veiga", "Ana Maria", "Artur Parada", "Jose Fernandes", 
                  "Emilia Melgo", "Alex Gralhos", "Ricardo Costa", "Óscar Esmenio", 
                  "D. Manuel Pinto", "Rui Domingues"])
mapa_reverso = {limpar_texto(n): n for n in pessoal}
lista_sem_acentos = sorted(list(mapa_reverso.keys()))
lista_meios = sorted(["ABSC-03", "ABSC-04", "VFCI-04", "VFCI-05","VUCI-02", "VTTU-01", 
                "VTTU-02", "VCOT-02","VLCI-01", "VLCI-03", "VETA-02"])

# --- INTERFACE ---
st.title("🚒 Sistema BVI")
t1, t2 = st.tabs(["📝 Novo Registo", "🔐 Gestão"])

with t1:
    with st.form("f_novo", clear_on_submit=True):
        st.subheader("Registo de Ocorrências:")
        nr = st.text_input("📕 OCORRÊNCIA Nº")
        hr = st.text_input("🕜 HORA")
        mot = st.text_input("🦺 MOTIVO") 
        sex = st.text_input("👨 SEXO/IDADE (Opcional)") 
        loc = st.text_input("📍 LOCALIDADE")
        mor = st.text_input("🏠 MORADA")
        meios = st.multiselect("🚒 MEIOS", options=lista_meios)
        ops = st.multiselect("👨🏻‍🚒 OPERACIONAIS", options=lista_sem_acentos)
        out = st.text_input("🚨 OUTROS MEIOS", value="Nenhum")
        
        if st.form_submit_button("SUBMETER", use_container_width=True):
            if not (nr and hr and mot and loc and mor and meios and ops):
                st.error("⚠️ Preencha todos os campos obrigatórios!")
            else:
                nomes = [mapa_reverso[n] for n in ops]
                s_f, h_f = formatar_sexo(sex), formatar_hora(hr)
                dados_d = {
                    "📕 OCORRÊNCIA Nº": nr.upper(), "🕜 HORA": h_f, "🦺 MOTIVO": mot.title(),
                    "👨 SEXO/IDADE": s_f, "📍 LOCALIDADE": loc.title(), "🏠 MORADA": mor.title(),
                    "🚒 MEIOS": ", ".join(meios), "👨🏻‍🚒 OPERACIONAIS": ", ".join(nomes),
                    "🚨 OUTROS MEIOS": out.title()
                }
                dados_h = dados_d.copy()
                dados_h["📅 DATA DO ENVIO"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                msg = "\n".join([f"**{k}** ▶️ {v}" for k, v in dados_d.items()])
                try:
                    if requests.post(DISCORD_WEBHOOK_URL, json={"content": msg}).status_code == 204:
                        atual = carregar_dados(HIST_FILE, [])
                        atual.insert(0, dados_h)
                        salvar_dados(HIST_FILE, atual)
                        st.success("✅ Enviado!")
                    else: st.error("❌ Erro no Discord.")
                except: st.error("❌ Erro de ligação.")

with t2:
    if not st.session_state.autenticado:
        u = st.text_input("Utilizador")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u == ADMIN_USER and s == ADMIN_PASSWORD:
                st.session_state.autenticado = True
                st.session_state.login_time = datetime.now()
                st.rerun()
            else: st.error("Credenciais inválidas.")
    else:
        st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"autenticado": False}))
        hist = carregar_dados(HIST_FILE, [])
        if hist:
            df = pd.DataFrame(hist)
            df_t = df.copy()
            df_t['📅 DATA DO ENVIO'] = pd.to_datetime(df_t['📅 DATA DO ENVIO'], dayfirst=True)
            df_t['Mes_Ano'] = df_t['📅 DATA DO ENVIO'].dt.strftime('%m/%Y')
            st.subheader("📊 Totais por Mês")
            st.table(df_t.groupby('Mes_Ano').size().reset_index(name='Total'))

            excel = criar_excel_oficial(df)
            st.download_button(label="📥 Descarregar Excel Oficial", data=excel, 
                               file_name=f"BVI_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)

            st.subheader("🔍 Gestão e Edição")
            df_ed = st.data_editor(df, use_container_width=True, num_rows="dynamic")
            if st.button("Guardar Alterações"):
                salvar_dados(HIST_FILE, df_ed.to_dict('records'))
                st.success("Atualizado!")
                st.rerun()
        else: st.info("Histórico vazio.")


st.markdown(f'<div style="text-align: right; color: gray; font-size: 0.8rem; margin-top: 50px;">{datetime.now().year} © BVI</div>', unsafe_allow_html=True)
