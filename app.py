from datetime import date, datetime
import urllib.parse
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

st.set_page_config(page_title="Painel de Clientes - Nataly", layout="wide")

# Credenciais de acesso
USUARIO_CORRETO = "nataly"
SENHA_CORRETA = "studio123"

# Conexão com o Supabase via Pooler (IPv4 e nuvem)
def conectar_banco():
    db_url = "postgresql://postgres.ddfjybibhrulenpmnqra:PainelClientes99@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
    return psycopg2.connect(db_url)

# Controle de Sessão / Login
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acesso ao Painel")
    with st.form("form_login"):
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if user.strip().lower() == USUARIO_CORRETO and senha == SENHA_CORRETA:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# 4. A PARTIR DAQUI SÓ EXECUTA QUANDO LOGADO
with st.sidebar:
    st.write(f"Conectada como **{USUARIO_CORRETO}**")

    # Busca prévia de todas as clientes para usar nas ações rápidas
    try:
        conn_acoes = conectar_banco()
        cur_acoes = conn_acoes.cursor(cursor_factory=RealDictCursor)
        cur_acoes.execute("SELECT id, nome, silenciado FROM clientes ORDER BY nome ASC")
        todas_clientes = cur_acoes.fetchall()
        cur_acoes.close()
        conn_acoes.close()
    except Exception as e:
        st.error(f"Erro ao carregar clientes: {e}")
        todas_clientes = []

    # 1. Botão para gerenciar/silenciar clientes
    with st.popover("🔇 Silenciar Clientes", use_container_width=True):
        st.markdown("**Marque para silenciar:**")
        st.caption("Clientes marcadas não receberão alertas de manutenção.")

        for cli in todas_clientes:
            id_cli = cli["id"]
            nome_cli = cli["nome"]
            esta_silenciado = bool(cli["silenciado"])

            marcado = st.checkbox(nome_cli, value=esta_silenciado, key=f"silenciar_{id_cli}")

            if marcado != esta_silenciado:
                try:
                    conn_update = conectar_banco()
                    cur_update = conn_update.cursor()
                    cur_update.execute(
                        "UPDATE clientes SET silenciado = %s WHERE id = %s",
                        (int(marcado), id_cli),
                    )
                    conn_update.commit()
                    cur_update.close()
                    conn_update.close()
                    st.rerun()
                except Exception as err:
                    st.error(f"Erro ao atualizar status: {err}")

    # 2. Botão para registrar atendimento / manutenção avulsa
    with st.popover("💅 Registrar Atendimento", use_container_width=True):
        st.markdown("**Atualizar Manutenção:**")
        st.caption("Use para quem veio antes dos 15 dias ou fora da lista.")

        nomes_disponiveis = [cli["nome"] for cli in todas_clientes]
        if nomes_disponiveis:
            cliente_escolhida = st.selectbox("Selecione a Cliente:", nomes_disponiveis, key="sel_cli_avulsa")
            data_feita = st.date_input("Data do Atendimento:", value=date.today(), key="dt_cli_avulsa")

            if st.button("Salvar Manutenção", use_container_width=True, key="btn_salvar_avulsa"):
                id_selecionada = next(c["id"] for c in todas_clientes if c["nome"] == cliente_escolhida)
                try:
                    conn_avulsa = conectar_banco()
                    cur_avulsa = conn_avulsa.cursor()
                    cur_avulsa.execute(
                        "UPDATE clientes SET data_ultima_manutencao = %s WHERE id = %s",
                        (data_feita, id_selecionada),
                    )
                    conn_avulsa.commit()
                    cur_avulsa.close()
                    conn_avulsa.close()
                    st.success(f"Manutenção de {cliente_escolhida} atualizada!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Erro ao salvar: {err}")
        else:
            st.info("Nenhuma cliente cadastrada.")

    st.markdown("---")

    if st.button("Sair / Logout", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

# CORPO PRINCIPAL
st.title("💅 Gestão e Retenção - Studio Nataly")

# Expander para cadastro de novas clientes na tela principal
with st.expander("➕ Cadastrar Nova Cliente", expanded=False):
    with st.form("form_cadastrar_cliente", clear_on_submit=True):
        col_cad1, col_cad2 = st.columns(2)
        nome_novo = col_cad1.text_input("Nome da Cliente")
        whats_novo = col_cad2.text_input("WhatsApp (com DDD, ex: 5511999998888)")
        
        col_cad3, col_cad4 = st.columns(2)
        servico_novo = col_cad3.selectbox("Procedimento", ["Manutenção de Fibra", "Esmaltação em Gel", "Blindagem", "Alongamento Inicial"])
        data_novo = col_cad4.date_input("Data do Atendimento", value=date.today())
        
        if st.form_submit_button("Cadastrar Cliente", use_container_width=True):
            if nome_novo and whats_novo:
                try:
                    conn_novo = conectar_banco()
                    cur_novo = conn_novo.cursor()
                    cur_novo.execute(
                        "INSERT INTO clientes (nome, telefone, servico, data_ultima_manutencao, silenciado) VALUES (%s, %s, %s, %s, 0)",
                        (nome_novo, whats_novo, servico_novo, data_novo)
                    )
                    conn_novo.commit()
                    cur_novo.close()
                    conn_novo.close()
                    st.success(f"{nome_novo} cadastrada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")
            else:
                st.warning("Preencha ao menos Nome e WhatsApp.")

# Listagem de Clientes e Indicadores
try:
    conn_list = conectar_banco()
    cur_list = conn_list.cursor(cursor_factory=RealDictCursor)
    cur_list.execute("SELECT * FROM clientes ORDER BY data_ultima_manutencao ASC")
    dados = cur_list.fetchall()
    cur_list.close()
    conn_list.close()
    df = pd.DataFrame(dados)
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    df = pd.DataFrame()

if not df.empty:
    df["data_ultima_manutencao"] = pd.to_datetime(df["data_ultima_manutencao"]).dt.date
    hoje = date.today()
    df["dias"] = df["data_ultima_manutencao"].apply(lambda d: (hoje - d).days)
    
    # Status de alerta (21 dias ou mais)
    df["status"] = df["dias"].apply(lambda d: "🔴 Alerta (21+ dias)" if d >= 21 else "🟢 Em dia")

    # Indicadores
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Clientes", len(df))
    m2.metric("Em Alerta de Retorno", len(df[(df["status"].str.contains("🔴")) & (df["silenciado"] == 0)]))
    m3.metric("Clientes Silenciadas", len(df[df["silenciado"] == 1]))

    st.markdown("---")

    # Lista de clientes com botão do WhatsApp
    for _, row in df.iterrows():
        if row["silenciado"] == 1:
            continue  # Não exibe quem foi silenciada na lista principal

        c1, c2, c3, c4 = st.columns([3, 3, 2, 2])
        c1.write(f"**{row['nome']}**\n\n{row['servico']}")
        c2.write(f"Última: {row['data_ultima_manutencao'].strftime('%d/%m/%Y')}\n\n**{row['dias']} dias atrás**")
        c3.write(row["status"])

        msg = f"Oi {row['nome']}! Tudo bem? Passando para lembrar que já faz {row['dias']} dias desde o seu procedimento de {row['servico']}. Vamos garantir seu horário de manutenção?"
        link = f"https://wa.me/{row['telefone']}?text={urllib.parse.quote(msg)}"
        c4.link_button("📲 Chamar WhatsApp", link, use_container_width=True)
        st.divider()
else:
    st.info("Nenhuma cliente encontrada.")
