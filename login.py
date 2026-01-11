import streamlit as st
import requests
import unicodedata
import pandas as pd
import io
import os
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO E SEGREDOS ---
try:
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
    ADMIN_USER = st.secrets["ADMIN_USER"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
except:
    st.error("⚠️ Configura DISCORD_WEBHOOK_URL, ADMIN_USER e ADMIN_PASSWORD nos Secrets!")
    st.stop()

# Ficheiro local para manter os dados enquanto a app corre
HIST_FILE = "historico_backup.csv"
LOGO_FILE = "logo.png"

def carregar_dados():
    if os.path.exists(HIST_FILE):
        return pd.read_csv(HIST_FILE)
    return pd.DataFrame(columns=[
        "📕 OCORRÊNCIA Nº", "🕜 HORA", "🦺 MOTIVO", "👨 SEXO/IDADE", 
        "📍 LOCALIDADE", "🏠 MORADA", "🚒 MEIOS", "👨🏻‍🚒 OPERACIONAIS", 
        "🚨 OUTROS MEIOS", "📅 DATA DO ENVIO"
    ])

def salvar_dados(df):
    df.to_csv(HIST_FILE, index=False)

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
    meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
             7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    try:
        d = pd.to_datetime(dt, dayfirst=True)
        return f"{meses[d.month]} de {d.year}"
    except: return "Data Inválida"

def criar_excel_oficial(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ocorrências', startrow=5)
        workbook, worksheet = writer.book, writer.sheets['Ocorrências']
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1})
        worksheet.write('C2', 'RELATÓRIO OFICIAL DE OCORRÊNCIAS - BVI', workbook.add_format({'bold': True, 'font_size': 14}))
        if os.path.exists(LOGO_FILE):
            worksheet.insert_image('A1', LOGO_FILE, {'x_scale': 0.4, 'y_scale': 0.4})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(5, col_num, value, fmt_header)
            worksheet.set_column(col_num, col_num, 20)
    return output.getvalue()

# --- INICIALIZAÇÃO ---
st.set_page_config(page_title="BVI - Gestão", page_icon="🚒", layout="wide")
if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, width=150)

if "autenticado" not in st.session_state: st.session_state.autenticado = False

# --- INTERFACE ---
st.title("🚒 Sistema BVI")
t1, t2 = st.tabs(["📝 Novo Registo", "🔐 Gestão"])

with t1:
    with st.form("f_novo", clear_on_submit=True):
        st.subheader("Registo de Ocorrência:")
        c1, c2 = st.columns(2)
        nr = c1.text_input("📕 OCORRÊNCIA Nº")
        hr = c2.text_input("🕜 HORA")
        mot = st.text_input("🦺 MOTIVO") 
        sex = st.text_input("👨 SEXO/IDADE") 
        loc = st.text_input("📍 LOCALIDADE")
        mor = st.text_input("🏠 MORADA")
        
        pessoal = sorted(["Luis Esmenio", "Denis Moreira", "Rafael Fernandes", "Marcia Mondego", 
                          "Francisco Oliveira", "Rui Parada", "Francisco Ferreira", "Pedro Veiga", 
                          "Rui Dias", "Artur Lima", "Óscar Oliveira", "Carlos Mendes", "Eric Mauricio", 
                          "José Melgo", "Andreia Afonso", "Roney Menezes", "EIP1", "EIP2", 
                          "Daniel Fernandes", "Danitiele Menezes", "Diogo Costa", "David Choupina", 
                          "Manuel Pinto", "Paulo Veiga", "Ana Maria", "Artur Parada", "Jose Fernandes", 
                          "Emilia Melgo", "Alex Gralhos", "Ricardo Costa", "Óscar Esmenio", 
                          "D. Manuel Pinto", "Rui Domingues"])
        mapa = {limpar_texto(n): n for n in pessoal}
        
        meios = st.multiselect("🚒 MEIOS", ["ABSC-03", "ABSC-04", "VFCI-04", "VFCI-05","VUCI-02", "VTTU-01", "VTTU-02", "VCOT-02","VLCI-01", "VLCI-03", "VETA-02"])
        ops = st.multiselect("👨🏻‍🚒 OPERACIONAIS", sorted(list(mapa.keys())))
        out = st.text_input("🚨 OUTROS MEIOS", value="Nenhum")
        
        if st.form_submit_button("SUBMETER", width='stretch'):
            if nr and hr and mot and loc and mor and meios and ops:
                nomes = [mapa[n] for n in ops]
                nova_linha = {
                    "📕 OCORRÊNCIA Nº": nr.upper(), "🕜 HORA": formatar_hora(hr), "🦺 MOTIVO": mot.title(),
                    "👨 SEXO/IDADE": formatar_sexo(sex), "📍 LOCALIDADE": loc.title(), "🏠 MORADA": mor.title(),
                    "🚒 MEIOS": ", ".join(meios), "👨🏻‍🚒 OPERACIONAIS": ", ".join(nomes),
                    "🚨 OUTROS MEIOS": out.title(), "📅 DATA DO ENVIO": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                
                # Guardar localmente
                df = carregar_dados()
                df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
                salvar_dados(df)
                
                # Enviar Discord
                msg = "\n".join([f"**{k}**: {v}" for k, v in nova_linha.items()])
                requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
                st.success("✅ Registado com sucesso!")
            else:
                st.error("⚠️ Preencha todos os campos!")

with t2:
    if not st.session_state.autenticado:
        u = st.text_input("Utilizador")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u == ADMIN_USER and s == ADMIN_PASSWORD:
                st.session_state.autenticado = True
                st.rerun()
            else: st.error("Incorreto.")
    else:
        st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"autenticado": False}))
        df = carregar_dados()
        if not df.empty:
            st.subheader("📊 Totais por Mês")
            df_resumo = df.copy()
            df_resumo['Mês'] = df_resumo['📅 DATA DO ENVIO'].apply(mes_extenso)
            st.table(df_resumo.groupby('Mês').size().reset_index(name='Ocorrências'))

            st.subheader("📋 Histórico")
            st.dataframe(df, width='stretch')
            
            # Botão para limpar histórico (Cuidado!)
            if st.button("Limpar Tudo"):
                if os.path.exists(HIST_FILE): os.remove(HIST_FILE)
                st.rerun()

            st.download_button("📥 Descarregar Excel", criar_excel_oficial(df), f"BVI_{datetime.now().year}.xlsx", width='stretch')
        else:
            st.info("Sem dados.")

st.markdown(f'<div style="text-align: right; color: gray; font-size: 0.8rem; margin-top: 50px;">{datetime.now().year} © BVI</div>', unsafe_allow_html=True)
