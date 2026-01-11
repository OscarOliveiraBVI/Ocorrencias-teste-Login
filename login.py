import streamlit as st
import requests
import unicodedata
import pandas as pd
import io
import os
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO E SEGREDOS ---
try:
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
    ADMIN_USER = st.secrets["ADMIN_USER"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    GSHEETS_URL = st.secrets["GSHEETS_URL"]
except Exception as e:
    st.error("⚠️ Erro: Configura os 'Secrets' no painel do Streamlit Cloud.")
    st.stop()

LOGO_FILE = "logo.png"

# --- CONEXÃO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_nuvem():
    try:
        return conn.read(spreadsheet=GSHEETS_URL)
    except:
        return pd.DataFrame()

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

def mes_extenso(dt):
    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    return f"{meses[dt.month]} de {dt.year}"

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
st.set_page_config(page_title="BVI - Ocorrencias Ativas", page_icon="🚒", layout="centered")

if os.path.exists(LOGO_FILE):
    st.sidebar.image(LOGO_FILE, width=150)

if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "login_time" not in st.session_state: st.session_state.login_time = None

# --- LISTAS ---
pessoal = sorted(["Luis Esmenio", "Denis Moreira", "Rafael Fernandes", "Marcia Mondego", 
                  "Francisco Oliveira", "Rui Parada", "Francisco Ferreira", "Pedro Veiga", 
                  "Rui Dias", "Artur Lima", "Óscar Oliveira", "Carlos Mendes", "Eric Mauricio", 
                  "José Melgo", "Andreia Afonso", "Roney Menezes", "EIP1", "EIP2", 
                  "Daniel Fernandes", "Danitiele Menezes", "Diogo Costa", "David Choupina", 
                  "Manuel Pinto", "Paulo Veiga", "Ana Maria", "Artur Parada", "Jose Fernandes", 
                  "Emilia Melgo", "Alex Gralhos", "Ricardo Costa", "Óscar Esmenio", 
                  "D. Manuel Pinto", "Rui Domingues"])
mapa_reverso = {limpar_texto(n): n for n in pessoal}
lista_meios = sorted(["ABSC-03", "ABSC-04", "VFCI-04", "VFCI-05","VUCI-02", "VTTU-01", 
                "VTTU-02", "VCOT-02","VLCI-01", "VLCI-03", "VETA-02"])

st.title("Ocorrencias Ativas")
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
        ops = st.multiselect("👨🏻‍🚒 OPERACIONAIS", options=sorted(list(mapa_reverso.keys())))
        out = st.text_input("🚨 OUTROS MEIOS", value="Nenhum")
        
        if st.form_submit_button("SUBMETER", width='stretch'):
            if not (nr and hr and mot and loc and mor and meios and ops):
                st.error("⚠️ Preencha os campos obrigatórios!")
            else:
                nomes = [mapa_reverso[n] for n in ops]
                s_f, h_f = formatar_sexo(sex), formatar_hora(hr)
                data_envio = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                nova_linha = {
                    "📕 OCORRÊNCIA Nº": nr.upper(), "🕜 HORA": h_f, "🦺 MOTIVO": mot.title(),
                    "👨 SEXO/IDADE": s_f, "📍 LOCALIDADE": loc.title(), "🏠 MORADA": mor.title(),
                    "🚒 MEIOS": ", ".join(meios), "👨🏻‍🚒 OPERACIONAIS": ", ".join(nomes),
                    "🚨 OUTROS MEIOS": out.title(), "📅 DATA DO ENVIO": data_envio
                }
                
                try:
                    df_atual = carregar_dados_nuvem()
                    df_novo = pd.concat([df_atual, pd.DataFrame([nova_linha])], ignore_index=True)
                    conn.update(spreadsheet=GSHEETS_URL, data=df_novo)
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": "\n".join([f"**{k}** ▶️ {v}" for k, v in nova_linha.items()])})
                    st.success("✅ Guardado e Enviado!")
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

with t2:
    if not st.session_state.autenticado:
        u = st.text_input("Utilizador")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u == ADMIN_USER and s == ADMIN_PASSWORD:
                st.session_state.autenticado = True
                st.session_state.login_time = datetime.now()
                st.rerun()
            else: st.error("Acesso negado.")
    else:
        st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"autenticado": False}))
        df_nuvem = carregar_dados_nuvem()
        
        if not df_nuvem.empty:
            # Converter coluna para data e criar coluna do mês por extenso
            df_nuvem['📅 DATA DO ENVIO'] = pd.to_datetime(df_nuvem['📅 DATA DO ENVIO'], dayfirst=True)
            df_nuvem['Mês'] = df_nuvem['📅 DATA DO ENVIO'].apply(mes_extenso)
            
            st.subheader("📊 Totais por Mês")
            resumo = df_nuvem.groupby('Mês').size().reset_index(name='Total de Ocorrências')
            st.table(resumo)

            st.subheader("📋 Histórico Completo")
            st.dataframe(df_nuvem, width='stretch')
            
            excel = criar_excel_oficial(df_nuvem.drop(columns=['Mês']))
            st.download_button(label="📥 Relatório Excel", data=excel, 
                               file_name=f"BVI_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               width='stretch')
        else:
            st.info("A folha está vazia.")

st.markdown(f'<div style="text-align: right; color: gray; font-size: 0.8rem; margin-top: 50px;">{datetime.now().year} © BVI</div>', unsafe_allow_html=True)
