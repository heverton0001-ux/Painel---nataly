from datetime import date
import urllib.parse
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

st.set_page_config(page_title="Painel de Clientes - Nataly", layout="wide")

# CSS: botão azul pulsante (aplicado pelo container com key="pulsar_azul")
st.markdown("""
<style>
.st-key-pulsar_azul button {
    background-color: #1E88E5 !important;
    color: white !important;
    border: none !important;
    animation: pulsar-azul 1.5s infinite;
}
@keyframes pulsar-azul {
    0%   { box-shadow: 0 0 0 0 rgba(30,136,229,0.7); }
    70%  { box-shadow: 0 0 0 12px rgba(30,136,229,0); }
    100% { box-shadow: 0 0 0 0 rgba(30,136,229,0); }
}
@media (prefers-reduced-motion: reduce) {
    .st-key-pulsar_azul button { animation: none; }
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
    if st.query_params.get("key") == CHAVE_ACESSO_SECRETA:
        st.session_state["autenticado"] = True
    else:
        st.session_state["autenticado"] = False

# Se NÃO estiver autenticado, exibe APENAS a tela de login e bloqueia o resto
if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito - Studio Nataly")
    with st.form("form_login"):
        user = st.text_input("Usuário", autocomplete="username")
        senha = st.text_input("Senha", type="password", autocomplete="current-password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if user.strip().lower() == USUARIO_CORRETO and senha == SENHA_CORRETA:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Credenciais inválidas.")

    st.stop()  # Impede renderizar qualquer dado antes do login

# A PARTIR DAQUI O CÓDIGO SÓ RODA SE ESTIVER AUTENTICADO
if "aba_ativa" not in st.session_state:
    st.session_state["aba_ativa"] = "lembrete_15"

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
                    cur_avulsa.execute("UPDATE clientes SET data_ultima_manutencao = %s WHERE id = %s", (data_feita, id_selecionada))
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
        servico_novo = col3.selectbox("Procedimento", ["Manutenção de Fibra", "Esmaltação em Gel", "Blindagem", "Alongamento Inicial"])
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

    def classificar_status(dias):
        if dias >= 21:
            return "🔴 Alerta (21+ dias)"
        elif 15 <= dias <= 20:
            return "🔵 Lembrete (15 a 20 dias)"
        else:
            return "🟢 Em dia"

    df["status"] = df["dias"].apply(classificar_status)

    # SEGMENTAÇÃO POR FAIXAS DE DIAS
    df_lembrete = df[(df["dias"] >= 15) & (df["dias"] <= 20) & (df["silenciado"] == 0)]
    df_alerta = df[(df["dias"] >= 21) & (df["silenciado"] == 0)]
    df_em_dia = df[(df["dias"] < 15) & (df["silenciado"] == 0)]
    df_silenciadas = df[df["silenciado"] == 1]

    # BANNER DE ALARME PARA A FAIXA DE OURO (15 A 20 DIAS)
    if len(df_lembrete) > 0:
        st.warning(
            f"🚨 **ATENÇÃO NATALY:** Você tem **{len(df_lembrete)} cliente(s)** na janela ideal de 15 a 20 dias! "
            f"Envie o lembrete hoje para que elas garantam vaga na agenda antes de estourar os 20 dias."
        )

    # 5 BOTÕES DE FILTRO EM COLUNAS
    col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)

    with col_b1:
        # Bloco único: o container com key aplica o efeito pulsante ao botão
        tipo1 = "primary" if st.session_state["aba_ativa"] == "lembrete_15" else "secondary"
        chave_container = "pulsar_azul" if len(df_lembrete) > 0 else "lembrete_normal"
        with st.container(key=chave_container):
            if st.button(f"🔵 Lembrete 15d ({len(df_lembrete)})", use_container_width=True,
                         type=tipo1, key="btn_lembrete_15"):
                st.session_state["aba_ativa"] = "lembrete_15"
                st.rerun()

    with col_b2:
        tipo2 = "primary" if st.session_state["aba_ativa"] == "alerta" else "secondary"
        if st.button(f"🔴 Em Alerta ({len(df_alerta)})", use_container_width=True, type=tipo2):
            st.session_state["aba_ativa"] = "alerta"
            st.rerun()

    with col_b3:
        tipo3 = "primary" if st.session_state["aba_ativa"] == "em_dia" else "secondary"
        if st.button(f"🟢 Em Dia ({len(df_em_dia)})", use_container_width=True, type=tipo3):
            st.session_state["aba_ativa"] = "em_dia"
            st.rerun()

    with col_b4:
        tipo4 = "primary" if st.session_state["aba_ativa"] == "todas" else "secondary"
        if st.button(f"📋 Todas ({len(df)})", use_container_width=True, type=tipo4):
            st.session_state["aba_ativa"] = "todas"
            st.rerun()

    with col_b5:
        tipo5 = "primary" if st.session_state["aba_ativa"] == "silenciadas" else "secondary"
        if st.button(f"🔇 Silenciadas ({len(df_silenciadas)})", use_container_width=True, type=tipo5):
            st.session_state["aba_ativa"] = "silenciadas"
            st.rerun()

    # Seleção de registros pelo filtro selecionado
    if st.session_state["aba_ativa"] == "lembrete_15":
        df_exibir = df_lembrete
    elif st.session_state["aba_ativa"] == "alerta":
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

                c1.markdown(f"**{str(row['nome']).strip()}**  \n{row['servico']}", unsafe_allow_html=True)
                c2.markdown(f"Última: {row['data_ultima_manutencao'].strftime('%d/%m/%Y')}  \n**{row['dias']} dias atrás**", unsafe_allow_html=True)

                badge = "🔇 Silenciada" if row["silenciado"] == 1 else row["status"]
                c3.write(badge)

                # MENSAGEM DO WHATSAPP ADAPTADA POR FAIXA
                if 15 <= row["dias"] <= 20:
                    dias_restantes = 20 - row["dias"]
                    msg = (
                        f"Oi {str(row['nome']).strip()}! Tudo bem? Passando para avisar que já faz {row['dias']} dias "
                        f"desde seu procedimento de {row['servico']}. Para garantir a durabilidade e a saúde da sua unha, "
                        f"o ideal é realizarmos a manutenção em até 20 dias (restam {dias_restantes} dias de margem). "
                        f"Vamos já reservar seu horário na agenda para não ficar sem vaga?"
                    )
                elif row["dias"] >= 21:
                    msg = (
                        f"Oi {str(row['nome']).strip()}! Tudo bem? Já fazem {row['dias']} dias desde seu procedimento de "
                        f"{row['servico']}. Ultrapassamos o prazo ideal de 20 dias. Vamos agendar seu horário "
                        f"o quanto antes para não danificar suas unhas?"
                    )
                else:
                    msg = f"Oi {str(row['nome']).strip()}! Tudo bem? Passando para saber como estão suas unhas de {row['servico']}!"

                link_zap = f"https://wa.me/{str(row['telefone']).strip()}?text={urllib.parse.quote(msg)}"
                c4.link_button("📲 Chamar WhatsApp", link_zap, use_container_width=True)
else:
    st.info("Nenhuma cliente cadastrada ainda. Use \"Cadastrar Nova Cliente\" acima para começar.")
