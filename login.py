import streamlit as st
import requests
import unicodedata
import pandas as pd
import io
import os
from datetime import datetime
from supabase import create_client, Client

# --- CONFIGURAÇÃO E SEGREDOS ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
    ADMIN_USER = st.secrets["ADMIN_USER"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("⚠️ Verifica os Secrets no Streamlit Cloud!")
    st.stop()

LOGO_FILE = "logo.png"

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

def mes_extenso(dt_str):
    meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
             7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    try:
        dt = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
        return f"{meses[dt.month]} de {dt.year}"
    except: return "Data Inválida"

def criar_excel_oficial(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Ocorrências', startrow=5)
        workbook, worksheet = writer.book, writer.sheets['Ocorrências']
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'border': 1})
        worksheet.write('C2', 'RELATÓRIO OFICIAL BVI', workbook.add_format({'bold': True, 'font_size': 14}))
        if os.path.exists(LOGO_FILE):
            worksheet.insert_image('A1', LOGO_FILE, {'x_scale': 0.4, 'y_scale': 0.4})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(5, col_num, value, fmt_header)
            worksheet.set_column(col_num, col_num, 22)
    return output.getvalue()

# --- INTERFACE ---
st.set_page_config(page_title="BVI - Ocorrências ", page_icon="logo.png", layout="centered")
if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, width=150)

st.title("🚒 Ocorrências Ativas")
t1, t2 = st.tabs(["📝 Novo Registo", "🔐 Gestão"])

with t1:
    with st.form("f_novo", clear_on_submit=True):
        st.subheader("Nova Ocorrência:")
        nr = st.text_input("📕 OCORRÊNCIA Nº")
        hr = st.text_input("🕜 HORA")
        mot = st.text_input("🦺 MOTIVO") 
        sex = st.text_input("👨 SEXO/IDADE") 
        loc = st.text_input("📍 LOCALIDADE")
        mor = st.text_input("🏠 MORADA")
        
        pessoal = sorted(["Luis Esmenio", "Denis Moreira", "Rafael Fernandes", "Marcia Mondego", "Rui Parada", "Francisco Ferreira", "Pedro Veiga", "Rui Dias", "Artur Lima", "Óscar Oliveira", "Carlos Mendes", "Eric Mauricio", "José Melgo", "Andreia Afonso", "Roney Menezes", "EIP1", "EIP2", "Daniel Fernandes", "Danitiele Menezes", "Diogo Costa", "David Choupina", "Manuel Pinto", "Paulo Veiga", "Ana Maria", "Artur Parada", "Jose Fernandes", "Emilia Melgo", "Alex Gralhos", "Ricardo Costa", "Óscar Esmenio", "D. Manuel Pinto", "Rui Domingues"])
        mapa = {limpar_texto(n): n for n in pessoal}
        
        meios = st.multiselect("🚒 MEIOS", ["ABSC-03", "ABSC-04", "VFCI-04", "VFCI-05","VUCI-02", "VTTU-01", "VTTU-02", "VCOT-02","VLCI-01", "VLCI-03", "VETA-02"])
        ops = st.multiselect("👨🏻‍🚒 OPERACIONAIS", sorted(list(mapa.keys())))
        out = st.text_input("🚨 OUTROS MEIOS", value="Nenhum")
        
        if st.form_submit_button("SUBMETER", width='stretch'):
            if nr and hr and mot and loc and mor and meios and ops:
                nomes = [mapa[n] for n in ops]
                data_agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                # Dados para o Supabase
                nova_linha = {
                    "numero": nr.upper(), "hora": formatar_hora(hr), "motivo": mot.title(),
                    "sexo": formatar_sexo(sex), "localidade": loc.title(), "morada": mor.title(),
                    "meios": ", ".join(meios), "operacionais": ", ".join(nomes),
                    "outros": out.title(), "data_envio": data_agora
                }
                
                try:
                    # Grava na base de dados
                    supabase.table("ocorrencias").insert(nova_linha).execute()
                    
                    # Prepara cópia para o Discord SEM a data de envio
                    dados_discord = nova_linha.copy()
                    del dados_discord["data_envio"]
                    
                    mapa_discord = {
                        "numero": "📕 OCORRÊNCIA Nº", "hora": "🕜 HORA", "motivo": "🦺 MOTIVO",
                        "sexo": "👨 SEXO/IDADE", "localidade": "📍 LOCALIDADE", "morada": "🏠 MORADA",
                        "meios": "🚒 MEIOS", "operacionais": "👨🏻‍🚒 OPERACIONAIS", "outros": "🚨 OUTROS MEIOS"
                    }
                    
                    msg = "\n".join([f"**{mapa_discord[k]}** ▶️ {v}" for k, v in dados_discord.items()])
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
                    
                    st.success("✅ Sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro ao guardar: {e}")
            else:
                st.error("⚠️ Preencha tudo!")

with t2:
    if not st.session_state.get("autenticado", False):
        u = st.text_input("Utilizador", key="u_login")
        s = st.text_input("Senha", type="password", key="s_login")
        if st.button("Entrar"):
            if u == ADMIN_USER and s == ADMIN_PASSWORD:
                st.session_state.autenticado = True
                st.rerun()
    else:
        st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"autenticado": False}))
        
        try:
            res = supabase.table("ocorrencias").select("*").order("data_envio", desc=True).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                
                mapa_colunas = {
                    "numero": "📕 OCORRÊNCIA Nº", "hora": "🕜 HORA", "motivo": "🦺 MOTIVO",
                    "sexo": "👨 SEXO/IDADE", "localidade": "📍 LOCALIDADE", "morada": "🏠 MORADA",
                    "meios": "🚒 MEIOS", "operacionais": "👨🏻‍🚒 OPERACIONAIS", 
                    "outros": "🚨 OUTROS MEIOS", "data_envio": "📅 DATA DO ENVIO"
                }
                df_v = df.rename(columns=mapa_colunas)

                st.subheader("📊 Totais")
                df_v['Mês'] = df_v['📅 DATA DO ENVIO'].apply(mes_extenso)
                st.table(df_v.groupby('Mês').size().reset_index(name='Total'))

                st.subheader("📋 Histórico")
                if 'id' in df_v.columns: df_v = df_v.drop(columns=['id'])
                st.dataframe(df_v, use_container_width=True)
                
                st.download_button("📥 Excel", criar_excel_oficial(df_v), f"BVI_{datetime.now().year}.xlsx")
            else:
                st.info("Vazio.")
        except Exception as e:
            st.error(f"❌ Erro: {e}")

st.markdown(f'<div style="text-align: right; color: gray; font-size: 0.8rem; margin-top: 50px;">{datetime.now().year} © BVI</div>', unsafe_allow_html=True)


