from datetime import date, datetime
import urllib.parse
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

st.set_page_config(page_title="Painel de Clientes - Nataly", layout="wide")


# CONEXÃO VIA POOLER (SUPORTA IPV4 E STREAMLIT CLOUD)
def get_connection():
    db_url = "postgresql://postgres.ddfjybibhrulenpmnqra:PainelClientes99@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
    return psycopg2.connect(db_url)

# Funções de banco de dados
def carregar_clientes():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM clientes ORDER BY data_ultima_manutencao ASC")
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(dados)


def adicionar_cliente(nome, telefone, servico, data_manutencao):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO clientes (nome, telefone, servico, data_ultima_manutencao, silenciado)
        VALUES (%s, %s, %s, %s, 0)
    """,
        (nome, telefone, servico, data_manutencao),
    )
    conn.commit()
    cur.close()
    conn.close()


def alternar_silenciado(cliente_id, novo_status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE clientes SET silenciado = %s WHERE id = %s",
        (novo_status, cliente_id),
    )
    conn.commit()
    cur.close()
    conn.close()


# Layout Principal
st.title("💅 Painel de Gestão e Retenção - Nataly")

# Formulário lateral para cadastrar nova cliente
with st.sidebar:
    st.header("Cadastrar Nova Cliente")
    with st.form("form_novo_cliente", clear_on_submit=True):
        nome = st.text_input("Nome")
        telefone = st.text_input("WhatsApp (ex: 5519999999999)")
        servico = st.selectbox(
            "Serviço",
            ["Manutenção de Fibra", "Esmaltação em Gel", "Blindagem"],
        )
        data_atendimento = st.date_input("Data do Atendimento", value=date.today())
        enviado = st.form_submit_button("Salvar Cliente")

        if enviado:
            if nome and telefone:
                adicionar_cliente(nome, telefone, servico, data_atendimento)
                st.success("Cliente cadastrada com sucesso!")
                st.rerun()
            else:
                st.error("Preencha nome e telefone.")

# Carregamento e regras de prazo
df = carregar_clientes()

if not df.empty:
    df["data_ultima_manutencao"] = pd.to_datetime(
        df["data_ultima_manutencao"]
    ).dt.date
    hoje = date.today()
    df["dias_desde_atendimento"] = df["data_ultima_manutencao"].apply(
        lambda d: (hoje - d).days
    )

    # Regra: alerta sugerido a partir de 21 dias
    df["status"] = df["dias_desde_atendimento"].apply(
        lambda d: "🔴 Alerta (21+ dias)" if d >= 21 else "🟢 Em dia"
    )

    # Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Clientes", len(df))
    col2.metric("Clientes em Alerta", len(df[df["status"].str.contains("🔴")]))
    col3.metric("Silenciadas", len(df[df["silenciado"] == 1]))

    st.write("---")

    # Listagem de clientes com botões de ação
    for _, row in df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 3, 2, 2, 2])

        c1.write(f"**{row['nome']}**\n\n{row['servico']}")
        c2.write(
            f"Último: {row['data_ultima_manutencao'].strftime('%d/%m/%Y')}\n\n({row['dias_desde_atendimento']} dias)"
        )
        c3.write(row["status"])

        # Link formatado para WhatsApp
        msg = f"Olá {row['nome']}, tudo bem? Já faz {row['dias_desde_atendimento']} dias desde o seu último atendimento de {row['servico']}. Gostaria de agendar seu horário?"
        link_zap = f"https://wa.me/{row['telefone']}?text={urllib.parse.quote(msg)}"
        c4.link_button("📲 Chamar", link_zap)

        # Botão para silenciar/reativar
        status_silenciado = row["silenciado"] == 1
        btn_label = "Reativar" if status_silenciado else "Silenciar"
        if c5.button(btn_label, key=f"btn_{row['id']}"):
            alternar_silenciado(row["id"], 0 if status_silenciado else 1)
            st.rerun()
        st.divider()
else:
    st.info("Nenhuma cliente encontrada no banco de dados.")
