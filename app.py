from datetime import date, datetime
import urllib.parse
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

st.set_page_config(page_title="Painel de Clientes - Nataly", layout="wide")

# CSS para acabamento limpo e containers compactos
st.markdown("""
<style>
    .block-container { 
        padding-top: 1.2rem; 
        padding-bottom: 2rem; 
    }

    /* Reduz a altura interna dos cards (containers com borda) */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding-top: 0.35rem !important;
        padding-bottom: 0.35rem !important;
        min-height: unset !important;
    }

    /* Diminui o espaçamento vertical entre os textos dentro do card */
    div[data-testid="stVerticalBlockBorderWrapper"] p {
        margin-bottom: 0.2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# CREDENCIAIS E CHAVE DE SEGURANÇA
USUARIO_CORRETO = "nataly"
SENHA_CORRETA = "studio123"
CHAVE_ACESSO_SECRETA = "nataly_vip_sec_2026"


def conectar_banco():
    db_url = "postgresql://postgres.ddfjybibhrulenpmnqra:PainelClientes99@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
    return psycopg2.connect(db_url)


# CONTROLE DE SESSÃO / LOGIN COM PROTEÇÃO
if "autenticado" not in st.session_state:
    # Se abrir pelo link especial no celular, autentica direto
    if st.query_params.get("key") == CHAVE_ACESSO_SECRETA:
        st.session_state["autenticado"] = True
    else:
        st.session_state["autenticado"] = False

# Se NÃO estiver autenticado, exibe APENAS a tela de login e bloqueia o resto
if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito - Studio Nataly")
    with st.form("form_login"):
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if user.strip().lower() == USUARIO_CORRETO and senha == SENHA_CORRETA:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    st.stop()  # O st.stop() aqui IMPEDE que qualquer dado de cliente seja carregado!

# A PARTIR DAQUI O CÓDIGO SÓ RODA SE ESTIVER AUTENTICADO
if "aba_ativa" not in st.session_state:
    st.session_state["aba_ativa"] = "alerta"

# BARRA LATERAL
with st.sidebar:
    st.write(f"Conectada como **{USUARIO_CORRETO}**")

    try:
        conn_acoes = conectar_banco()
        cur_acoes = conn_acoes.cursor(cursor_factory=RealDictCursor)
        cur_acoes.execute("SELECT id, nome, silenciado FROM clientes ORDER BY nome ASC")
        todas_clientes = cur_acoes.fetchall()
        cur_acoes.close()
        conn_acoes.close()
    except Exception as e:
        st.error(f"Erro: {e}")
        todas_clientes = []

    with st.popover("🔇 Silenciar Clientes", use_container_width=True):
        st.caption("Marque para pausar alertas de manutenção.")
        for cli in todas_clientes:
            id_cli = cli["id"]
            nome_cli = cli["nome"]
            esta_silenciado = bool(cli["silenciado"])
            marcado = st.checkbox(nome_cli, value=esta_silenciado, key=f"silenciar_{id_cli}")
            if marcado != esta_silenciado:
                try:
                    conn_update = conectar_banco()
                    cur_update = conn_update.cursor()
                    cur_update.execute("UPDATE clientes SET silenciado = %s WHERE id = %s", (int(marcado), id_cli))
                    conn_update.commit()
                    cur_update.close()
                    conn_update.close()
                    st.rerun()
                except Exception as err:
                    st.error(f"Erro: {err}")

    with st.popover("💅 Registrar Atendimento", use_container_width=True):
        nomes_disponiveis = [cli["nome"] for cli in todas_clientes]
        if nomes_disponiveis:
            cliente_escolhida = st.selectbox("Cliente:", nomes_disponiveis, key="sel_cli_avulsa")
            data_feita = st.date_input("Data:", value=date.today(), key="dt_cli_avulsa")
            if st.button("Salvar Manutenção", use_container_width=True, key="btn_salvar_avulsa"):
                id_selecionada = next(c["id"] for c in todas_clientes if c["nome"] == cliente_escolhida)
                try:
                    conn_avulsa = conectar_banco()
                    cur_avulsa = conn_avulsa.cursor()
                    cur_avulsa.execute("UPDATE clientes SET data_ultima_manutencao = %s WHERE id = %s",
                                       (data_feita, id_selecionada))
                    conn_avulsa.commit()
                    cur_avulsa.close()
                    conn_avulsa.close()
                    st.success("Atualizado com sucesso!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Erro: {err}")

    st.markdown("---")
    if st.button("Sair / Logout", use_container_width=True):
        st.session_state["autenticado"] = False
        st.query_params.clear()
        st.rerun()

# CORPO PRINCIPAL
st.title("💅 Painel de Clientes")

with st.expander("➕ Cadastrar Nova Cliente", expanded=False):
    with st.form("form_cadastrar_cliente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome_novo = col1.text_input("Nome da Cliente").strip()
        whats_novo = col2.text_input("WhatsApp (ex: 5511999998888)").strip()
        col3, col4 = st.columns(2)
        servico_novo = col3.selectbox("Procedimento",
                                      ["Manutenção de Fibra", "Esmaltação em Gel", "Blindagem", "Alongamento Inicial"])
        data_novo = col4.date_input("Data do Atendimento", value=date.today())

        if st.form_submit_button("Salvar", use_container_width=True):
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
                    st.success(f"{nome_novo} adicionada!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Erro ao cadastrar: {err}")

# CARREGAMENTO DOS DADOS
try:
    conn_list = conectar_banco()
    cur_list = conn_list.cursor(cursor_factory=RealDictCursor)
    cur_list.execute("SELECT * FROM clientes ORDER BY data_ultima_manutencao ASC")
    dados = cur_list.fetchall()
    cur_list.close()
    conn_list.close()
    df = pd.DataFrame(dados)
except Exception:
    df = pd.DataFrame()

if not df.empty:
    df["data_ultima_manutencao"] = pd.to_datetime(df["data_ultima_manutencao"]).dt.date
    hoje = date.today()
    df["dias"] = df["data_ultima_manutencao"].apply(lambda d: (hoje - d).days)
    df["status"] = df["dias"].apply(lambda d: "🔴 Alerta (21+ dias)" if d >= 21 else "🟢 Em dia")

    df_alerta = df[(df["dias"] >= 21) & (df["silenciado"] == 0)]
    df_em_dia = df[(df["dias"] < 21) & (df["silenciado"] == 0)]
    df_silenciadas = df[df["silenciado"] == 1]

    # BOTÕES DE FILTRO
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)

    with col_b1:
        tipo1 = "primary" if st.session_state["aba_ativa"] == "alerta" else "secondary"
        if st.button(f"🔴 Em Alerta ({len(df_alerta)})", use_container_width=True, type=tipo1):
            st.session_state["aba_ativa"] = "alerta"
            st.rerun()

    with col_b2:
        tipo2 = "primary" if st.session_state["aba_ativa"] == "em_dia" else "secondary"
        if st.button(f"🟢 Em Dia ({len(df_em_dia)})", use_container_width=True, type=tipo2):
            st.session_state["aba_ativa"] = "em_dia"
            st.rerun()

    with col_b3:
        tipo3 = "primary" if st.session_state["aba_ativa"] == "todas" else "secondary"
        if st.button(f"📋 Todas ({len(df)})", use_container_width=True, type=tipo3):
            st.session_state["aba_ativa"] = "todas"
            st.rerun()

    with col_b4:
        tipo4 = "primary" if st.session_state["aba_ativa"] == "silenciadas" else "secondary"
        if st.button(f"🔇 Silenciadas ({len(df_silenciadas)})", use_container_width=True, type=tipo4):
            st.session_state["aba_ativa"] = "silenciadas"
            st.rerun()

    if st.session_state["aba_ativa"] == "alerta":
        df_exibir = df_alerta
    elif st.session_state["aba_ativa"] == "em_dia":
        df_exibir = df_em_dia
    elif st.session_state["aba_ativa"] == "silenciadas":
        df_exibir = df_silenciadas
    else:
        df_exibir = df

    # CARDS COMPACTOS
    if df_exibir.empty:
        st.info("Nenhuma cliente nesta categoria.")
    else:
        for _, row in df_exibir.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2.5, 2, 2.5], vertical_alignment="center")

                c1.markdown(
                    f"**{str(row['nome']).strip()}**  \n<span style='color: gray; font-size: 0.85rem;'>{row['servico']}</span>",
                    unsafe_allow_html=True)
                c2.markdown(
                    f"<span style='font-size: 0.88rem;'>Última: {row['data_ultima_manutencao'].strftime('%d/%m/%Y')}</span>  \n**{row['dias']} dias atrás**",
                    unsafe_allow_html=True)

                badge = "🔇 Silenciada" if row["silenciado"] == 1 else row["status"]
                c3.write(badge)

                msg = f"Oi {str(row['nome']).strip()}! Tudo bem? Passando para lembrar que já faz {row['dias']} dias desde seu procedimento de {row['servico']}. Vamos garantir seu horário de manutenção?"
                link_zap = f"https://wa.me/{str(row['telefone']).strip()}?text={urllib.parse.quote(msg)}"
                c4.link_button("📲 Chamar WhatsApp", link_zap, use_container_width=True)
else:
    st.info("Nenhuma cliente encontrada.")
