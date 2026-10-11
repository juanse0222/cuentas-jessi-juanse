"""
Cuentas Jessi & Juanse — App de control financiero familiar
"""

import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

import importador
import impuestos

# ─── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Cuentas Jessi & Juanse",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Layout ──────────────────────────────────────────────── */
.block-container {
    padding: 0rem 1rem 5rem;
    max-width: 680px;
}

/* ── Header centrado ─────────────────────────────────────── */
.app-header {
    text-align: center;
    padding: 1.8rem 0 0.4rem;
}
.app-header h1 {
    font-size: 1.9rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #a78bfa, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0.3rem 0 0.1rem;
}
.app-header p {
    font-size: 0.82rem;
    opacity: 0.5;
    margin: 0;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ── Tabs ────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 3px;
    background: rgba(124,58,237,0.06);
    border-radius: 14px;
    padding: 4px;
    border: 1px solid rgba(124,58,237,0.12);
}
.stTabs [data-baseweb="tab"] {
    font-size: 12px;
    font-weight: 600;
    padding: 7px 8px;
    border-radius: 10px;
    color: rgba(31,27,46,0.55);
    border: none !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    background: #7c3aed !important;
    color: white !important;
}

/* ── Tarjetas métricas ───────────────────────────────────── */
div[data-testid="metric-container"] {
    background: rgba(124,58,237,0.1);
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 16px;
    padding: 14px 12px;
}
div[data-testid="metric-container"] label {
    font-size: 0.72rem !important;
    font-weight: 600;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    opacity: 0.65;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.25rem !important;
    font-weight: 700;
}

/* ── Botones ─────────────────────────────────────────────── */
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    font-size: 14px;
    border: 1px solid rgba(31,27,46,0.14);
    transition: all 0.15s ease;
}
.stButton > button:hover {
    border-color: #7c3aed;
    color: #a78bfa;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
    border: none !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #8b5cf6, #6d28d9) !important;
    color: white !important;
}

/* ── Barra de progreso ───────────────────────────────────── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #7c3aed, #a78bfa);
    border-radius: 99px;
}
.stProgress > div > div {
    background: rgba(31,27,46,0.08);
    border-radius: 99px;
}

/* ── Inputs ──────────────────────────────────────────────── */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    border-radius: 10px !important;
    border-color: rgba(31,27,46,0.14) !important;
    background: rgba(124,58,237,0.03) !important;
}

/* ── Divisores ───────────────────────────────────────────── */
hr { opacity: 0.18; margin: 0.5rem 0; }

/* ── Info / alertas ──────────────────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: 12px;
    border-left-width: 3px;
}

/* ── Expander ────────────────────────────────────────────── */
details summary {
    border-radius: 10px;
    font-weight: 600;
}

/* ── Selector de mes ─────────────────────────────────────── */
div[data-testid="stSelectbox"] label {
    font-size: 0.75rem;
    font-weight: 600;
    opacity: 0.6;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
</style>
""", unsafe_allow_html=True)

# ─── DATOS: PRESUPUESTO Y CATEGORÍAS ─────────────────────────────────────────

INGRESOS = {
    "Ingreso — Jessi": {
        "HUV": 3_000_000,
        "Consultas particulares": 0,
        "Otro": 0,
    },
    "Ingreso — Juanse": {
        "DIME": 8_750_000,
        "CIDEIM": 3_150_000,
        "UNISABANA": 1_750_000,
        "Otro": 0,
    },
    "Otro ingreso": {
        "Ingreso adicional": 0,
    },
}

GASTOS = {
    "🏠 Casa — Básico": {
        "Arriendo Sayab": 1_594_501,
        "Papás Juanse": 850_000,
        "Energía (Emcali)": 120_000,
        "Gas (Gases de Occidente)": 25_000,
        "Agua y alcantarillado": 120_000,
        "Internet (Claro)": 70_000,
        "Celular Jessi": 45_000,
        "Celular Juanse": 26_000,
        "Limpieza de la casa": 180_000,
        "Funeraria": 40_400,
        "Otro": 0,
    },
    "🚗 Transporte": {
        "Combustible": 150_000,
        "Lavada del carro": 70_000,
        "Mantenimiento del carro": 100_000,
        "Peajes": 0,
        "Arreglo de scooters": 0,
        "Otro": 0,
    },
    "🛡️ Seguro": {
        "Sura Póliza Salud": 1_120_000,
        "Póliza carro todo riesgo": 900_000,
        "Otro": 0,
    },
    "🍽️ Comida": {
        "Mercado mensual": 700_000,
        "Restaurantes": 800_000,
        "Mercado adicional": 200_000,
        "Domicilios": 0,
        "Otro": 0,
    },
    "💆 Cuidado Personal": {
        "Médicos / Salud": 200_000,
        "Pelo y uñas Jessi": 40_000,
        "Pelo y uñas Juanse": 45_000,
        "Ropa y calzado": 0,
        "Gimnasio": 300_000,
        "Personalizado Gimnasio": 500_000,
        "Tennis": 280_000,
        "Limpiezas faciales": 0,
        "Depilación laser": 150_000,
        "Otro": 0,
    },
    "🎬 Entretenimiento": {
        "Netflix": 54_000,
        "Plataformas (Disney/Apple)": 26_000,
        "Claude AI": 70_000,
        "Google One": 8_000,
        "iCloud Jessi": 15_000,
        "iCloud Juanse": 21_000,
        "Grammarly": 35_000,
        "Salidas / Ocio": 0,
        "Otro": 0,
    },
    "💳 Préstamos": {
        "Cuota carro T-Cross": 1_250_000,
        "Tarjeta Bancoomeva": 1_750_000,
        "Tarjeta Falabella": 470_000,
        "Tarjeta Alkosto": 1_600_000,
        "Otro": 0,
    },
    "📄 Impuestos": {
        "Impuesto carro / SOAT": 300_000,
        "Declaración de Renta": 120_000,
        "Otro": 0,
    },
    "💰 Ahorros e Inversiones": {
        "Cuenta de jubilación": 1_000_000,
        "Cuenta de inversión": 1_000_000,
        "Ahorros papás": 250_000,
        "Otro": 0,
    },
    "🎁 Regalos y Donaciones": {
        "Ofrenda / Iglesia": 0,
        "Regalos familia": 0,
        "Donaciones": 0,
        "Otro": 0,
    },
    "📚 Educación": {
        "Oxford / Idiomas": 0,
        "Cursos / Capacitación": 0,
        "Libros": 0,
        "Otro": 0,
    },
    "🐾 Mascotas": {
        "Alimentación": 0,
        "Veterinario": 0,
        "Medicamentos": 0,
        "Ropa y accesorios": 0,
        "Otro": 0,
    },
}

PERSONAS = ["Jessi", "Juanse", "Ambos"]

USUARIOS_PERMITIDOS = {"juansehurtado@gmail.com", "jessikanandez@gmail.com"}

TOTAL_INGRESOS_PREVISTOS = sum(v for src in INGRESOS.values() for v in src.values())
TOTAL_GASTOS_PREVISTOS = sum(v for cat in GASTOS.values() for v in cat.values())

MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

# ─── BASE DE DATOS ────────────────────────────────────────────────────────────

@st.cache_resource
def get_client() -> Client:
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except KeyError:
        st.error("⚠️ Supabase no está configurado. Revisa `.streamlit/secrets.toml`")
        st.stop()


def fmt(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "$0"
    return f"${v:,.0f}".replace(",", ".")


def mes_anterior(d: date) -> date:
    m = d.month - 1 or 12
    y = d.year - (1 if d.month == 1 else 0)
    return date(y, m, 1)


def cargar_mes(mes: date) -> pd.DataFrame:
    cols = ["id", "fecha", "mes_presupuestal", "persona", "tipo", "categoria", "subcategoria", "descripcion", "monto"]
    try:
        inicio = date(mes.year, mes.month, 1).isoformat()
        m_sig = mes.month % 12 + 1
        y_sig = mes.year + (1 if mes.month == 12 else 0)
        fin = date(y_sig, m_sig, 1).isoformat()
        res = (
            get_client()
            .table("transacciones")
            .select("*")
            .gte("mes_presupuestal", inicio)
            .lt("mes_presupuestal", fin)
            .order("fecha", desc=True)
            .execute()
        )
        if not res.data:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(res.data)
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        df["mes_presupuestal"] = pd.to_datetime(df["mes_presupuestal"]).dt.date
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
        return df
    except Exception as e:
        st.error(f"⚠️ Error cargando transacciones: `{e}`  \n\n**¿Corriste el SQL de configuración en Supabase?**")
        return pd.DataFrame(columns=cols)


def guardar(fecha, mes_presupuestal, persona, tipo, categoria, subcategoria, descripcion, monto):
    get_client().table("transacciones").insert({
        "fecha": fecha.isoformat(),
        "mes_presupuestal": mes_presupuestal.isoformat(),
        "persona": persona,
        "tipo": tipo,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "descripcion": descripcion or "",
        "monto": int(monto),
    }).execute()


def eliminar(id_: str):
    get_client().table("transacciones").delete().eq("id", id_).execute()


def actualizar(id_, fecha, mes_presupuestal, persona, tipo, categoria, subcategoria, descripcion, monto):
    get_client().table("transacciones").update({
        "fecha": fecha.isoformat(),
        "mes_presupuestal": mes_presupuestal.isoformat(),
        "persona": persona,
        "tipo": tipo,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "descripcion": descripcion or "",
        "monto": int(monto),
    }).eq("id", id_).execute()


# ── Items lista ───────────────────────────────────────────────────────────────

def cargar_items(mes: date) -> pd.DataFrame:
    cols = ["id", "mes_presupuestal", "nombre", "categoria", "subcategoria", "precio", "cantidad", "pagado"]
    try:
        inicio = date(mes.year, mes.month, 1).isoformat()
        m_sig = mes.month % 12 + 1
        y_sig = mes.year + (1 if mes.month == 12 else 0)
        fin = date(y_sig, m_sig, 1).isoformat()
        res = (
            get_client()
            .table("items_lista")
            .select("*")
            .gte("mes_presupuestal", inicio)
            .lt("mes_presupuestal", fin)
            .order("created_at", desc=False)
            .execute()
        )
        if not res.data:
            df = pd.DataFrame(columns=cols)
            df["total"] = pd.Series(dtype=float)
            return df
        df = pd.DataFrame(res.data)
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce").fillna(0)
        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(1).astype(int)
        df["total"] = df["precio"] * df["cantidad"]
        df["mes_presupuestal"] = pd.to_datetime(df["mes_presupuestal"]).dt.date
        return df
    except Exception:
        df = pd.DataFrame(columns=cols)
        df["total"] = pd.Series(dtype=float)
        return df


def guardar_item(mes_presupuestal, nombre, categoria, subcategoria, precio, cantidad):
    get_client().table("items_lista").insert({
        "mes_presupuestal": mes_presupuestal.isoformat(),
        "nombre": nombre,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "precio": int(precio),
        "cantidad": int(cantidad),
        "pagado": False,
    }).execute()


def eliminar_item(id_: str):
    get_client().table("items_lista").delete().eq("id", id_).execute()


def pagar_item(id_: str, fecha, mes_presupuestal, persona, monto, categoria, subcategoria, descripcion):
    guardar(fecha, mes_presupuestal, persona, "gasto", categoria, subcategoria, descripcion, monto)
    get_client().table("items_lista").update({"pagado": True}).eq("id", id_).execute()


# ── Historial de importaciones ─────────────────────────────────────────────────

def nombre_usuario_actual() -> str:
    email = getattr(st.user, "email", None) if hasattr(st, "user") else None
    if email == "jessikanandez@gmail.com":
        return "Jessi"
    if email == "juansehurtado@gmail.com":
        return "Juanse"
    return email or "Desconocido"


def guardar_log_importacion(fuente: str, reconocidos: int, omitidos: int, detalle: str = ""):
    get_client().table("importaciones_log").insert({
        "realizado_por": nombre_usuario_actual(),
        "fuente": fuente,
        "reconocidos": int(reconocidos),
        "omitidos": int(omitidos),
        "detalle": detalle,
    }).execute()


def cargar_log_importaciones(limite: int = 100) -> pd.DataFrame:
    cols = ["id", "fecha_hora", "realizado_por", "fuente", "reconocidos", "omitidos", "detalle"]
    try:
        res = (
            get_client().table("importaciones_log")
            .select("*")
            .order("fecha_hora", desc=True)
            .limit(limite)
            .execute()
        )
        if not res.data:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(res.data)
        df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
        return df
    except Exception:
        return pd.DataFrame(columns=cols)


# ─── PÁGINAS ──────────────────────────────────────────────────────────────────

def pagina_dashboard(df: pd.DataFrame, mes: date):
    st.subheader(f"📊 Salario de {MESES_ES[mes.month]} {mes.year}")
    st.caption(
        f"Todo lo pagado con el salario de {MESES_ES[mes.month]}, "
        "sin importar si el pago fue a finales de ese mes o primeros días del siguiente."
    )

    gastos_reales = float(df[df["tipo"] == "gasto"]["monto"].sum()) if not df.empty else 0.0
    ingresos_reales = float(df[df["tipo"] == "ingreso"]["monto"].sum()) if not df.empty else 0.0
    saldo = TOTAL_INGRESOS_PREVISTOS - gastos_reales

    col1, col2, col3 = st.columns(3)
    col1.metric("💼 Ingresos previstos", fmt(TOTAL_INGRESOS_PREVISTOS))
    col2.metric(
        "💸 Total pagado", fmt(gastos_reales),
        delta=f"{fmt(gastos_reales - TOTAL_GASTOS_PREVISTOS)} vs presupuesto",
        delta_color="inverse",
    )
    col3.metric("🏦 Saldo disponible", fmt(saldo))

    if saldo < 0:
        st.error(f"🚨 Los gastos superan los ingresos en **{fmt(abs(saldo))}**")
    elif saldo < 1_000_000:
        st.warning(f"⚠️ Saldo disponible bajo: **{fmt(saldo)}**")
    else:
        st.success(f"✅ Te quedan **{fmt(saldo)}** del salario de {MESES_ES[mes.month]}")

    st.divider()
    st.markdown("#### Uso del presupuesto por categoría")

    for cat, items in GASTOS.items():
        presupuestado = sum(items.values())
        if presupuestado == 0:
            continue
        gastado = float(df[(df["tipo"] == "gasto") & (df["categoria"] == cat)]["monto"].sum()) if not df.empty else 0.0
        ratio = gastado / presupuestado

        if ratio < 0.75:
            badge = "🟢"
        elif ratio < 0.90:
            badge = "🟡"
        elif ratio <= 1.0:
            badge = "🔴"
        else:
            badge = "🚨"

        col_a, col_b = st.columns([6, 4])
        with col_a:
            st.markdown(f"{badge} **{cat}**")
            st.progress(min(ratio, 1.0))
        with col_b:
            st.markdown(f"**{fmt(gastado)}** / {fmt(presupuestado)}")
            st.caption(f"{ratio * 100:.0f}% usado")

    if not df.empty:
        gastos_df = df[df["tipo"] == "gasto"].copy()
        if not gastos_df.empty:
            st.divider()
            gastos_df["fecha_str"] = gastos_df["fecha"].astype(str)
            daily = gastos_df.groupby("fecha_str")["monto"].sum().reset_index()
            daily["acumulado"] = daily["monto"].cumsum()

            fig = go.Figure()
            fig.add_bar(x=daily["fecha_str"], y=daily["monto"], name="Diario", marker_color="#FF7F7F")
            fig.add_scatter(
                x=daily["fecha_str"], y=daily["acumulado"],
                name="Acumulado", mode="lines+markers",
                line=dict(color="#4169E1", width=2),
            )
            fig.add_hline(
                y=TOTAL_GASTOS_PREVISTOS, line_dash="dash", line_color="gray",
                annotation_text="Presupuesto total",
            )
            fig.update_layout(
                title_text="Gastos del mes", height=280,
                margin=dict(l=5, r=5, t=40, b=5),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                yaxis_tickformat=",.0f",
            )
            st.plotly_chart(fig, use_container_width=True)


def pagina_agregar():
    st.subheader("➕ Registrar transacción")

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"], key="tipo_w")
    with col2:
        persona = st.selectbox("Quién", PERSONAS, key="persona_w")

    if tipo == "Gasto":
        categoria = st.selectbox("Categoría", list(GASTOS.keys()), key="cat_w")
        subcats = list(GASTOS[categoria].keys())
    else:
        fuente = st.selectbox("Fuente", list(INGRESOS.keys()), key="fuente_w")
        categoria = fuente
        subcats = list(INGRESOS[fuente].keys())

    hoy = date.today()

    # ── Selector de período salarial ──────────────────────────────────────────
    st.info(
        "💡 **¿Con qué salario se paga esto?**  \n"
        "El salario de julio paga: servicios de julio + arriendo de agosto (primeros 5 días) "
        "+ seguro de agosto (primeros 3 días). Todo eso se registra como **período Julio**."
    )

    opciones_mes = []
    for i in range(3):
        m = hoy.month - i
        y = hoy.year
        while m <= 0:
            m += 12
            y -= 1
        opciones_mes.append(date(y, m, 1))

    etiquetas_mes = []
    for i, d in enumerate(opciones_mes):
        label = f"Salario de {MESES_ES[d.month]} {d.year}"
        if i == 1:
            label += " ← sugerido"
        etiquetas_mes.append(label)

    # En los primeros 10 días del mes, el salario del mes anterior es el que está activo
    default_mes = 1 if hoy.day <= 10 else 0

    idx_mes = st.selectbox(
        "💼 ¿Con qué salario pagas esto?",
        range(len(etiquetas_mes)),
        format_func=lambda i: etiquetas_mes[i],
        index=default_mes,
    )
    mes_presupuestal = opciones_mes[idx_mes]

    with st.form("form_tx", clear_on_submit=True):
        subcategoria = st.selectbox("Subcategoría / Concepto", subcats)
        fecha = st.date_input("Fecha de pago", value=hoy)
        monto = st.number_input(
            "Monto ($COP)", min_value=1, step=1_000, format="%d",
            help="Valor en pesos colombianos",
        )
        descripcion = st.text_input("Descripción (opcional)")
        enviado = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")

        if enviado:
            try:
                tipo_db = "gasto" if tipo == "Gasto" else "ingreso"
                guardar(fecha, mes_presupuestal, persona, tipo_db, categoria, subcategoria, descripcion, monto)
                mes_label = f"{MESES_ES[mes_presupuestal.month]} {mes_presupuestal.year}"
                st.success(
                    f"✅ **{fmt(monto)}** registrado en *{subcategoria}* → mes de **{mes_label}**"
                )
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")


def pagina_historial(df: pd.DataFrame):
    st.subheader("📋 Historial")

    if "editando_id" not in st.session_state:
        st.session_state["editando_id"] = None

    if df.empty:
        st.info("📭 No hay transacciones registradas este mes.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        tipo_f = st.multiselect("Tipo", ["gasto", "ingreso"], default=["gasto", "ingreso"])
    with col2:
        persona_f = st.multiselect("Quién", PERSONAS, default=PERSONAS)
    with col3:
        cats = sorted(df["categoria"].unique().tolist())
        cat_f = st.multiselect("Categoría", cats, default=cats)

    mask = df["tipo"].isin(tipo_f) & df["persona"].isin(persona_f) & df["categoria"].isin(cat_f)
    filtrado = df[mask]

    t_gastos = float(filtrado[filtrado["tipo"] == "gasto"]["monto"].sum())
    t_ingresos = float(filtrado[filtrado["tipo"] == "ingreso"]["monto"].sum())
    col1, col2 = st.columns(2)
    col1.metric("💸 Gastos", fmt(t_gastos))
    col2.metric("💰 Ingresos", fmt(t_ingresos))

    st.divider()

    for _, row in filtrado.iterrows():
        row_id = str(row["id"])
        es_gasto = row["tipo"] == "gasto"
        emoji = "💸" if es_gasto else "💰"
        desc_extra = f" · {row['descripcion']}" if row.get("descripcion") else ""
        signo = "−" if es_gasto else "+"

        mes_pres = row.get("mes_presupuestal")
        pago_distinto = ""
        if mes_pres and hasattr(mes_pres, "month") and mes_pres.month != row["fecha"].month:
            pago_distinto = f" · <span style='color:#f0a500'>pagado el {row['fecha']}</span>"

        col_info, col_monto, col_edit, col_del = st.columns([5, 3, 1, 1])
        with col_info:
            st.markdown(
                f"{emoji} **{row['subcategoria']}**  \n"
                f"<small>{row['categoria']} · {row['persona']}{pago_distinto}{desc_extra}</small>",
                unsafe_allow_html=True,
            )
        with col_monto:
            st.markdown(f"**{signo}{fmt(row['monto'])}**")
        with col_edit:
            if st.button("✏️", key=f"edit_{row_id}", help="Editar"):
                st.session_state["editando_id"] = row_id
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{row_id}", help="Eliminar"):
                eliminar(row_id)
                st.rerun()

        # ── Formulario de edición inline ─────────────────────────────────────
        if st.session_state["editando_id"] == row_id:
            with st.expander("✏️ Editar transacción", expanded=True):
                tipo_actual = "Gasto" if row["tipo"] == "gasto" else "Ingreso"
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    tipo_ed = st.selectbox(
                        "Tipo", ["Gasto", "Ingreso"],
                        index=["Gasto", "Ingreso"].index(tipo_actual),
                        key=f"et_{row_id}",
                    )
                with col_e2:
                    per_idx = PERSONAS.index(row["persona"]) if row["persona"] in PERSONAS else 0
                    persona_ed = st.selectbox("Quién", PERSONAS, index=per_idx, key=f"ep_{row_id}")

                if tipo_ed == "Gasto":
                    cats_ed = list(GASTOS.keys())
                    cat_idx = cats_ed.index(row["categoria"]) if row["categoria"] in cats_ed else 0
                    cat_ed = st.selectbox("Categoría", cats_ed, index=cat_idx, key=f"ec_{row_id}")
                    subcats_ed = list(GASTOS[cat_ed].keys())
                else:
                    cats_ed = list(INGRESOS.keys())
                    cat_idx = cats_ed.index(row["categoria"]) if row["categoria"] in cats_ed else 0
                    cat_ed = st.selectbox("Fuente", cats_ed, index=cat_idx, key=f"ec_{row_id}")
                    subcats_ed = list(INGRESOS[cat_ed].keys())

                # Opciones de mes presupuestal (últimos 6 meses)
                hoy = date.today()
                opciones_mes_ed = []
                for i in range(6):
                    m = hoy.month - i
                    y = hoy.year
                    while m <= 0:
                        m += 12
                        y -= 1
                    opciones_mes_ed.append(date(y, m, 1))

                mes_pres_row = row.get("mes_presupuestal")
                if mes_pres_row and hasattr(mes_pres_row, "month"):
                    mes_pres_first = date(mes_pres_row.year, mes_pres_row.month, 1)
                    mes_ed_idx = next((i for i, d in enumerate(opciones_mes_ed) if d == mes_pres_first), 0)
                else:
                    mes_ed_idx = 0

                with st.form(f"form_edit_{row_id}"):
                    sub_idx = subcats_ed.index(row["subcategoria"]) if row["subcategoria"] in subcats_ed else 0
                    subcat_ed = st.selectbox("Subcategoría / Concepto", subcats_ed, index=sub_idx)

                    mes_ed = st.selectbox(
                        "💼 ¿Con qué salario?",
                        range(len(opciones_mes_ed)),
                        format_func=lambda i: f"Salario de {MESES_ES[opciones_mes_ed[i].month]} {opciones_mes_ed[i].year}",
                        index=mes_ed_idx,
                    )
                    mes_presupuestal_ed = opciones_mes_ed[mes_ed]

                    fecha_ed = st.date_input("Fecha de pago", value=row["fecha"])
                    monto_ed = st.number_input(
                        "Monto ($COP)", min_value=1, step=1_000,
                        format="%d", value=int(row["monto"]),
                    )
                    desc_ed = st.text_input("Descripción", value=row.get("descripcion") or "")

                    col_s, col_c = st.columns(2)
                    with col_s:
                        guardar_ed = st.form_submit_button("💾 Guardar cambios", use_container_width=True, type="primary")
                    with col_c:
                        cancelar_ed = st.form_submit_button("✖️ Cancelar", use_container_width=True)

                    if guardar_ed:
                        tipo_db_ed = "gasto" if tipo_ed == "Gasto" else "ingreso"
                        actualizar(row_id, fecha_ed, mes_presupuestal_ed, persona_ed,
                                   tipo_db_ed, cat_ed, subcat_ed, desc_ed, monto_ed)
                        st.session_state["editando_id"] = None
                        st.success("✅ Cambios guardados")
                        st.rerun()

                    if cancelar_ed:
                        st.session_state["editando_id"] = None
                        st.rerun()

        st.divider()

    neto = t_ingresos - t_gastos
    st.markdown(f"**Neto del período:** {fmt(neto)} ({'superávit' if neto >= 0 else 'déficit'})")


def pagina_analisis(df: pd.DataFrame):
    st.subheader("📈 Análisis")

    gastos = df[df["tipo"] == "gasto"] if not df.empty else pd.DataFrame()

    if gastos.empty:
        st.info("📭 No hay gastos registrados este mes para analizar.")
        return

    # Donut por categoría
    por_cat = gastos.groupby("categoria")["monto"].sum().reset_index()
    fig_donut = px.pie(
        por_cat, values="monto", names="categoria",
        title="Distribución de gastos por categoría",
        hole=0.45, color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig_donut.update_layout(height=370, margin=dict(l=5, r=5, t=45, b=5))
    fig_donut.update_traces(textinfo="percent+label", textfont_size=10)
    st.plotly_chart(fig_donut, use_container_width=True)

    # Por persona (solo si hay más de una)
    personas_presentes = gastos["persona"].unique()
    if len(personas_presentes) > 1:
        por_persona = gastos.groupby("persona")["monto"].sum().reset_index()
        fig_p = px.pie(
            por_persona, values="monto", names="persona",
            title="Gastos por persona", hole=0.45,
            color="persona",
            color_discrete_map={"Jessi": "#FF69B4", "Juanse": "#4169E1", "Ambos": "#90EE90"},
        )
        fig_p.update_layout(height=300, margin=dict(l=5, r=5, t=45, b=5))
        st.plotly_chart(fig_p, use_container_width=True)

    # Tabla presupuesto vs real
    st.markdown("#### Presupuesto vs Real por categoría")
    rows = []
    for cat, items in GASTOS.items():
        presupuestado = sum(items.values())
        if presupuestado == 0:
            continue
        gastado = float(gastos[gastos["categoria"] == cat]["monto"].sum())
        diferencia = presupuestado - gastado
        pct = (gastado / presupuestado * 100) if presupuestado > 0 else 0
        estado = "✅" if pct <= 90 else ("⚠️" if pct <= 100 else "🚨")
        rows.append({
            "": estado,
            "Categoría": cat,
            "Presupuesto": fmt(presupuestado),
            "Real": fmt(gastado),
            "Disponible": fmt(diferencia),
            "% Uso": f"{pct:.0f}%",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Top 5 gastos individuales
    st.markdown("#### Top 5 gastos individuales")
    top5 = gastos.nlargest(5, "monto")[["fecha", "subcategoria", "categoria", "persona", "monto"]].copy()
    top5["monto"] = top5["monto"].apply(fmt)
    top5.columns = ["Fecha", "Concepto", "Categoría", "Quién", "Monto"]
    st.dataframe(top5, use_container_width=True, hide_index=True)


def pagina_lista(items_df: pd.DataFrame, mes: date):
    st.subheader(f"🛒 Lista de Gastos — {MESES_ES[mes.month]} {mes.year}")

    if "pagando_item" not in st.session_state:
        st.session_state["pagando_item"] = None

    # ── Resumen ───────────────────────────────────────────────────────────────
    if not items_df.empty:
        total_l = float(items_df["total"].sum())
        pagado_l = float(items_df[items_df["pagado"] == True]["total"].sum())
        pendiente_l = total_l - pagado_l
        col1, col2, col3 = st.columns(3)
        col1.metric("📋 Total lista", fmt(total_l))
        col2.metric("✅ Pagado", fmt(pagado_l))
        col3.metric("⏳ Por pagar", fmt(pendiente_l))
        st.divider()

    # ── Formulario agregar ítem ───────────────────────────────────────────────
    hoy = date.today()
    opciones_mes_l = []
    for i in range(3):
        m = hoy.month - i
        y = hoy.year
        while m <= 0:
            m += 12
            y -= 1
        opciones_mes_l.append(date(y, m, 1))
    default_mes_l = 1 if hoy.day <= 10 else 0

    with st.expander("➕ Agregar ítem a la lista", expanded=items_df.empty):
        cat_l = st.selectbox("Categoría", list(GASTOS.keys()), key="cat_lista_w")
        subcats_l = list(GASTOS[cat_l].keys())

        with st.form("form_item_lista", clear_on_submit=True):
            nombre_l = st.text_input(
                "Nombre del ítem",
                placeholder="Ej: Queso, Pollo, Bombillo, Detergente...",
            )
            subcat_l = st.selectbox("Subcategoría", subcats_l)

            col_p, col_q = st.columns([3, 2])
            with col_p:
                precio_l = st.number_input("Precio unitario ($)", min_value=0, step=500, format="%d")
            with col_q:
                cantidad_l = st.number_input("Cantidad", min_value=1, step=1, value=1)

            mes_l_sel = st.selectbox(
                "💼 ¿Con qué salario?",
                range(len(opciones_mes_l)),
                format_func=lambda i: f"Salario {MESES_ES[opciones_mes_l[i].month]} {opciones_mes_l[i].year}",
                index=default_mes_l,
            )
            mes_pres_l = opciones_mes_l[mes_l_sel]

            if precio_l > 0:
                st.caption(f"Total: **{fmt(precio_l * cantidad_l)}**")

            agregar_l = st.form_submit_button("➕ Agregar a lista", use_container_width=True, type="primary")
            if agregar_l:
                if not nombre_l.strip():
                    st.error("Escribe el nombre del ítem.")
                elif precio_l == 0:
                    st.error("Ingresa el precio.")
                else:
                    guardar_item(mes_pres_l, nombre_l.strip(), cat_l, subcat_l, precio_l, cantidad_l)
                    st.success(f"✅ **{nombre_l}** agregado — {fmt(precio_l * cantidad_l)}")
                    st.rerun()

    st.divider()

    if items_df.empty:
        st.info("📭 Agrega ítems para planificar tus gastos del período.")
        return

    # ── Ítems agrupados por categoría ─────────────────────────────────────────
    grand_total = 0.0

    for cat in items_df["categoria"].unique():
        cat_items = items_df[items_df["categoria"] == cat]
        presupuesto_cat = sum(GASTOS.get(cat, {}).values())
        total_cat = float(cat_items["total"].sum())
        grand_total += total_cat
        pct = (total_cat / presupuesto_cat * 100) if presupuesto_cat > 0 else 0

        badge = "🟢" if pct < 75 else ("🟡" if pct < 90 else ("🔴" if pct <= 100 else "🚨"))
        col_ch, col_cs = st.columns([7, 3])
        with col_ch:
            st.markdown(f"**{badge} {cat}**")
        with col_cs:
            st.markdown(f"<div style='text-align:right'><small>{fmt(total_cat)} / {fmt(presupuesto_cat)}</small></div>",
                        unsafe_allow_html=True)
        if presupuesto_cat > 0:
            st.progress(min(pct / 100, 1.0))

        for _, item in cat_items.iterrows():
            item_id = str(item["id"])
            pagado = bool(item.get("pagado", False))
            total_item = float(item["total"])
            qty = int(item["cantidad"])

            col_n, col_amt, col_pay, col_del = st.columns([5, 3, 2, 1])
            with col_n:
                nombre_md = f"~~{item['nombre']}~~" if pagado else f"**{item['nombre']}**"
                qty_txt = f" ×{qty}" if qty > 1 else ""
                st.markdown(f"{nombre_md}{qty_txt}")
                st.caption(f"{item['subcategoria']} · {fmt(item['precio'])} c/u")
            with col_amt:
                t_md = f"~~{fmt(total_item)}~~" if pagado else fmt(total_item)
                st.markdown(t_md)
            with col_pay:
                if pagado:
                    st.markdown("✅")
                else:
                    if st.button("✓ Pagar", key=f"pay_{item_id}", use_container_width=True):
                        st.session_state["pagando_item"] = (
                            None if st.session_state["pagando_item"] == item_id else item_id
                        )
                        st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_item_{item_id}", help="Eliminar ítem"):
                    eliminar_item(item_id)
                    st.rerun()

            # ── Mini formulario de pago ───────────────────────────────────────
            if not pagado and st.session_state.get("pagando_item") == item_id:
                with st.form(f"form_pagar_{item_id}"):
                    st.markdown(f"**Registrar pago:** {item['nombre']} — {fmt(total_item)}")

                    opciones_mes_p = []
                    for i in range(3):
                        m = hoy.month - i
                        y = hoy.year
                        while m <= 0:
                            m += 12
                            y -= 1
                        opciones_mes_p.append(date(y, m, 1))

                    item_mes = item.get("mes_presupuestal")
                    if item_mes and hasattr(item_mes, "month"):
                        default_p = next(
                            (i for i, d in enumerate(opciones_mes_p)
                             if d.month == item_mes.month and d.year == item_mes.year), 0
                        )
                    else:
                        default_p = 1 if hoy.day <= 10 else 0

                    col_pp1, col_pp2 = st.columns(2)
                    with col_pp1:
                        persona_p = st.selectbox("Quién pagó", PERSONAS)
                    with col_pp2:
                        fecha_p = st.date_input("Fecha", value=hoy)

                    mes_p_idx = st.selectbox(
                        "💼 ¿Con qué salario?",
                        range(len(opciones_mes_p)),
                        format_func=lambda i: f"Salario {MESES_ES[opciones_mes_p[i].month]} {opciones_mes_p[i].year}",
                        index=default_p,
                    )
                    mes_pres_p = opciones_mes_p[mes_p_idx]

                    col_ps, col_pc = st.columns(2)
                    with col_ps:
                        confirmar_p = st.form_submit_button("💾 Confirmar pago", use_container_width=True, type="primary")
                    with col_pc:
                        cancelar_p = st.form_submit_button("✖️ Cancelar", use_container_width=True)

                    if confirmar_p:
                        pagar_item(item_id, fecha_p, mes_pres_p, persona_p,
                                   int(total_item), str(item["categoria"]),
                                   str(item["subcategoria"]), str(item["nombre"]))
                        st.session_state["pagando_item"] = None
                        st.success(f"✅ {item['nombre']} registrado como gasto")
                        st.rerun()
                    if cancelar_p:
                        st.session_state["pagando_item"] = None
                        st.rerun()

        st.divider()

    st.markdown(
        f"<div style='text-align:center; font-size:1.1rem; font-weight:700; padding:0.5rem 0;'>"
        f"💰 Total lista: {fmt(grand_total)}</div>",
        unsafe_allow_html=True,
    )


def pagina_pendientes(df: pd.DataFrame, mes: date):
    st.subheader(f"📝 Pendientes — Salario {MESES_ES[mes.month]} {mes.year}")

    if "registrando_item" not in st.session_state:
        st.session_state["registrando_item"] = None

    gastos_df = df[df["tipo"] == "gasto"] if not df.empty else pd.DataFrame()

    # ── Resumen general ───────────────────────────────────────────────────────
    total_items = sum(1 for cat in GASTOS.values() for k, v in cat.items() if v > 0 and k != "Otro")
    pagados_n = 0
    total_pendiente = 0

    for cat, items in GASTOS.items():
        for subcat, presupuesto in items.items():
            if presupuesto == 0 or subcat == "Otro":
                continue
            if not gastos_df.empty:
                match = gastos_df[(gastos_df["categoria"] == cat) & (gastos_df["subcategoria"] == subcat)]
                if not match.empty:
                    pagados_n += 1
                    continue
            total_pendiente += presupuesto

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("✅ Pagados", f"{pagados_n} / {total_items}")
    col_b.metric("⏳ Pendientes", f"{total_items - pagados_n} ítems")
    col_c.metric("💸 Por pagar", fmt(total_pendiente))

    progreso = pagados_n / total_items if total_items > 0 else 0
    st.progress(progreso, text=f"{progreso*100:.0f}% del presupuesto fijo registrado")
    st.divider()

    # ── Checklist por categoría ───────────────────────────────────────────────
    for cat, items in GASTOS.items():
        items_fijos = {k: v for k, v in items.items() if v > 0 and k != "Otro"}
        if not items_fijos:
            continue

        st.markdown(f"#### {cat}")

        for subcat, presupuesto in items_fijos.items():
            item_key = f"{cat}__{subcat}"

            # Verificar si ya está pagado
            pagado = False
            monto_pagado = 0.0
            fecha_pago = None
            if not gastos_df.empty:
                match = gastos_df[
                    (gastos_df["categoria"] == cat) & (gastos_df["subcategoria"] == subcat)
                ]
                if not match.empty:
                    pagado = True
                    monto_pagado = float(match["monto"].sum())
                    fecha_pago = match.iloc[0]["fecha"]

            col_icon, col_info, col_monto, col_accion = st.columns([1, 5, 3, 2])

            with col_icon:
                st.markdown("✅" if pagado else "⏳")
            with col_info:
                if pagado:
                    st.markdown(f"~~{subcat}~~")
                    st.caption(f"Pagado el {fecha_pago}")
                else:
                    st.markdown(f"**{subcat}**")
                    st.caption(fmt(presupuesto))
            with col_monto:
                if pagado:
                    st.markdown(f"{fmt(monto_pagado)}")
                    if abs(monto_pagado - presupuesto) > 1000:
                        diff = monto_pagado - presupuesto
                        st.caption(f"{'↑' if diff > 0 else '↓'} {fmt(abs(diff))} vs ppto")
            with col_accion:
                if not pagado:
                    if st.button("➕ Pagar", key=f"btn_{item_key}", use_container_width=True):
                        if st.session_state["registrando_item"] == item_key:
                            st.session_state["registrando_item"] = None
                        else:
                            st.session_state["registrando_item"] = item_key
                        st.rerun()

            # ── Mini formulario de registro rápido ────────────────────────────
            if st.session_state.get("registrando_item") == item_key:
                with st.container():
                    st.markdown("---")
                    hoy = date.today()
                    opciones_mes_r = []
                    for i in range(3):
                        m = hoy.month - i
                        y = hoy.year
                        while m <= 0:
                            m += 12
                            y -= 1
                        opciones_mes_r.append(date(y, m, 1))
                    default_mes_r = 1 if hoy.day <= 10 else 0

                    with st.form(f"form_pend_{item_key}", clear_on_submit=True):
                        st.markdown(f"**Registrar pago:** {subcat}")
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            fecha_r = st.date_input("Fecha de pago", value=hoy)
                        with col_f2:
                            persona_r = st.selectbox("Quién", PERSONAS)

                        mes_r_idx = st.selectbox(
                            "💼 ¿Con qué salario?",
                            range(len(opciones_mes_r)),
                            format_func=lambda i: f"Salario {MESES_ES[opciones_mes_r[i].month]} {opciones_mes_r[i].year}",
                            index=default_mes_r,
                        )
                        mes_presupuestal_r = opciones_mes_r[mes_r_idx]
                        monto_r = st.number_input(
                            "Monto ($COP)", min_value=1, step=1_000,
                            format="%d", value=presupuesto,
                        )
                        desc_r = st.text_input("Descripción (opcional)")

                        col_s, col_c2 = st.columns(2)
                        with col_s:
                            guardar_r = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
                        with col_c2:
                            cancelar_r = st.form_submit_button("✖️ Cancelar", use_container_width=True)

                        if guardar_r:
                            guardar(fecha_r, mes_presupuestal_r, persona_r, "gasto",
                                    cat, subcat, desc_r, monto_r)
                            st.session_state["registrando_item"] = None
                            st.success(f"✅ {subcat} registrado — {fmt(monto_r)}")
                            st.rerun()
                        if cancelar_r:
                            st.session_state["registrando_item"] = None
                            st.rerun()
                    st.markdown("---")

        st.divider()


def pagina_importar():
    st.subheader("📥 Importar extractos BBVA")
    st.caption(
        "Sube el Excel de movimientos, los PDF de extracto de cuenta, o busca directo en tu correo. "
        "Nada se guarda hasta que revises y confirmes abajo."
    )

    if "correo_dfs" not in st.session_state:
        st.session_state["correo_dfs"] = {}

    # ── Buscar en correo (IMAP) ──────────────────────────────────────────────
    cuentas_correo = [
        ("Juanse", "GMAIL_JUANSE_USER", "GMAIL_JUANSE_APP_PASSWORD"),
        ("Jessi", "GMAIL_JESSI_USER", "GMAIL_JESSI_APP_PASSWORD"),
    ]
    buscadores_correo = [
        ("BBVA", importador.buscar_correos_bbva),
        ("FVL", importador.buscar_correos_fvl),
        ("SURA", importador.buscar_correos_sura),
    ]

    for nombre, clave_user, clave_pass in cuentas_correo:
        usuario_correo = st.secrets.get(clave_user)
        clave_correo = st.secrets.get(clave_pass)

        with st.expander(f"📬 Buscar en el correo de {nombre}", expanded=False):
            if not (usuario_correo and clave_correo):
                st.info(
                    f"No configurado todavía. Agrega `{clave_user}` y "
                    f"`{clave_pass}` en `.streamlit/secrets.toml`."
                )
                continue

            dias = st.slider(
                "Buscar correos de los últimos N días", 1, 365, 90, key=f"dias_{nombre}",
            )
            if st.button(f"🔍 Buscar notificaciones ({nombre})", use_container_width=True, key=f"buscar_{nombre}"):
                partes_correo = []
                resumen = []
                with st.spinner(f"Conectando al correo de {nombre}…"):
                    for fuente, buscador in buscadores_correo:
                        try:
                            df_fuente = buscador(usuario_correo, clave_correo, dias)
                            if not df_fuente.empty:
                                partes_correo.append(df_fuente)
                            resumen.append(
                                f"{fuente}: {len(df_fuente)}/{df_fuente.attrs.get('total_mensajes', 0)}"
                            )
                        except Exception as e:
                            st.error(f"❌ {fuente} — no pude conectar al correo de {nombre}: {e}")
                st.session_state["correo_dfs"][nombre] = (
                    pd.concat(partes_correo, ignore_index=True) if partes_correo else pd.DataFrame()
                )
                if resumen:
                    st.success("✅ " + " · ".join(resumen) + " (reconocidos/encontrados)")

    archivos = st.file_uploader(
        "Archivos (.xlsx o .pdf)", type=["xlsx", "pdf"], accept_multiple_files=True,
    )
    clave_pdf = st.text_input(
        "🔒 Contraseña del PDF (solo si alguno la pide, ej. Banco de Bogotá)",
        type="password",
    )

    partes = []
    for nombre, df_correo in st.session_state["correo_dfs"].items():
        if df_correo is not None and not df_correo.empty:
            df_correo = df_correo.copy()
            df_correo["persona_sugerida"] = nombre
            partes.append(df_correo)
    for f in archivos or []:
        try:
            partes.append(importador.parsear_archivo(f, password=clave_pdf or None))
        except importador.PDFProtegidoError as e:
            st.warning(f"🔒 {e}")
        except Exception as e:
            st.error(f"❌ No pude leer **{f.name}**: {e}")

    if not partes:
        return

    df = pd.concat(partes, ignore_index=True)
    df = df.sort_values("fecha", ascending=False).reset_index(drop=True)

    # ── Detectar duplicados contra lo que ya está en la base ────────────────
    fecha_min, fecha_max = df["fecha"].min(), df["fecha"].max()
    try:
        existentes = (
            get_client().table("transacciones")
            .select("fecha,descripcion,monto")
            .gte("fecha", fecha_min.isoformat())
            .lte("fecha", fecha_max.isoformat())
            .execute()
        )
        # La misma compra real se ve distinto en cada fuente (Excel, PDF, correo),
        # así que el cruce se hace por fecha + monto, no por el texto exacto.
        ya_existe = {
            (row["fecha"], round(float(row["monto"])))
            for row in existentes.data
        }
    except Exception:
        ya_existe = set()

    def es_duplicado(row):
        return (row["fecha"].isoformat(), round(row["monto"])) in ya_existe

    df["ya_importado"] = df.apply(es_duplicado, axis=1)
    df["incluir"] = ~df["ya_importado"]
    df["mes_presupuestal"] = df["fecha"].apply(
        lambda f: mes_anterior(f) if f.day <= 10 else date(f.year, f.month, 1)
    )
    if "persona_sugerida" in df.columns:
        df["persona"] = df["persona_sugerida"].fillna("Ambos")
    else:
        df["persona"] = "Ambos"

    opciones_cat = ["❓ Sin categoría (revisar)"]
    opciones_cat += [f"{cat} → {sub}" for cat, subs in GASTOS.items() for sub in subs]
    opciones_cat += [f"{cat} → {sub}" for cat, subs in INGRESOS.items() for sub in subs]

    def cat_default(row):
        if row["categoria_sugerida"] and row["subcategoria_sugerida"]:
            return f"{row['categoria_sugerida']} → {row['subcategoria_sugerida']}"
        return "❓ Sin categoría (revisar)"

    df["categoria_subcategoria"] = df.apply(cat_default, axis=1)

    n_dup = int(df["ya_importado"].sum())
    n_sin_cat = int((df["categoria_subcategoria"] == "❓ Sin categoría (revisar)").sum())
    col1, col2, col3 = st.columns(3)
    col1.metric("📄 Movimientos leídos", len(df))
    col2.metric("♻️ Ya importados antes", n_dup)
    col3.metric("❓ Sin categoría sugerida", n_sin_cat)
    if n_sin_cat:
        st.info("Las filas **❓ Sin categoría** no se importarán hasta que les asignes una categoría válida.")

    st.markdown("#### Revisa antes de confirmar")
    columnas_visibles = [
        "incluir", "fecha", "descripcion", "monto", "tipo",
        "persona", "categoria_subcategoria", "mes_presupuestal", "ya_importado",
    ]
    editado = st.data_editor(
        df[columnas_visibles],
        key="editor_importar",
        use_container_width=True,
        hide_index=True,
        disabled=["ya_importado"],
        column_config={
            "incluir": st.column_config.CheckboxColumn("Incluir"),
            "fecha": st.column_config.DateColumn("Fecha"),
            "descripcion": st.column_config.TextColumn("Descripción banco", width="medium"),
            "monto": st.column_config.NumberColumn("Monto", format="$ %d"),
            "tipo": st.column_config.SelectboxColumn("Tipo", options=["gasto", "ingreso"]),
            "persona": st.column_config.SelectboxColumn("Quién", options=PERSONAS),
            "categoria_subcategoria": st.column_config.SelectboxColumn(
                "Categoría → Subcategoría", options=opciones_cat, width="large",
            ),
            "mes_presupuestal": st.column_config.DateColumn("Salario de"),
            "ya_importado": st.column_config.CheckboxColumn("¿Ya estaba?"),
        },
    )

    if st.button("💾 Confirmar importación", type="primary", use_container_width=True):
        insertados, omitidos = 0, 0
        conteo_fuente = {}  # fuente -> [insertados, omitidos]
        for idx, row in editado.iterrows():
            fuente = df.loc[idx, "origen"] if "origen" in df.columns else "Archivo"
            conteo_fuente.setdefault(fuente, [0, 0])

            if not row["incluir"] or row["categoria_subcategoria"] == "❓ Sin categoría (revisar)":
                omitidos += 1
                conteo_fuente[fuente][1] += 1
                continue

            categoria, subcategoria = row["categoria_subcategoria"].split(" → ", 1)
            guardar(
                row["fecha"], row["mes_presupuestal"], row["persona"], row["tipo"],
                categoria, subcategoria, row["descripcion"], row["monto"],
            )
            insertados += 1
            conteo_fuente[fuente][0] += 1

        for fuente, (n_ins, n_omit) in conteo_fuente.items():
            try:
                guardar_log_importacion(fuente, n_ins, n_omit)
            except Exception:
                pass  # el registro del log nunca debe bloquear la importación en sí

        st.success(f"✅ {insertados} movimientos importados · {omitidos} omitidos")
        if insertados:
            st.rerun()


def pagina_impuestos():
    st.subheader("💵 Resumen de Declaración de Renta")
    st.caption(
        "Sube tus Formularios 210 (DIAN) para ver patrimonio, ingresos e impuesto "
        "por año. Esto **no se guarda** — se procesa solo en esta sesión."
    )

    archivos = st.file_uploader(
        "Formulario 210 (PDF)", type=["pdf"], accept_multiple_files=True, key="pdfs_impuestos",
    )
    if not archivos:
        st.info("📭 Sube uno o más Formularios 210 para ver el resumen.")
        return

    resultados = impuestos.parsear_declaraciones(archivos)
    no_reconocidos = len(archivos) - len(resultados)
    if no_reconocidos:
        st.warning(f"⚠️ {no_reconocidos} archivo(s) no se reconocieron como Formulario 210.")
    if not resultados:
        return

    for r in resultados:
        st.markdown(f"#### Año gravable {r['anio']}")
        col1, col2, col3 = st.columns(3)
        col1.metric("🏦 Patrimonio líquido", fmt(r["patrimonio_liquido"]))
        col2.metric("💼 Renta líquida gravable", fmt(r["renta_liquida_gravable"]))
        saldo = r["saldo_a_pagar"] or 0
        favor = r["saldo_a_favor"] or 0
        if saldo > 0:
            col3.metric("📄 Saldo a pagar", fmt(saldo), delta="a pagar", delta_color="inverse")
        elif favor > 0:
            col3.metric("📄 Saldo a favor", fmt(favor), delta="a favor")
        else:
            col3.metric("📄 Saldo", fmt(0))
        with st.expander("Ver más detalle"):
            st.markdown(
                f"- Patrimonio bruto: {fmt(r['patrimonio_bruto'])}\n"
                f"- Deudas: {fmt(r['deudas'])}\n"
                f"- Impuesto a cargo: {fmt(r['impuesto_a_cargo'])}\n"
                f"- Retenciones: {fmt(r['retenciones'])}"
            )
        st.divider()

    if len(resultados) > 1:
        st.markdown("#### Tendencia entre años")
        df_tend = pd.DataFrame(resultados)
        fig = go.Figure()
        fig.add_bar(x=df_tend["anio"], y=df_tend["patrimonio_liquido"], name="Patrimonio líquido")
        fig.add_bar(x=df_tend["anio"], y=df_tend["renta_liquida_gravable"], name="Renta líquida gravable")
        fig.update_layout(
            barmode="group", height=320, margin=dict(l=5, r=5, t=20, b=5),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis_tickformat=",.0f",
        )
        st.plotly_chart(fig, use_container_width=True)


def pagina_historial_importaciones():
    st.subheader("🗂️ Historial de importaciones")
    st.caption("Registro de todo lo subido y procesado en la pestaña Importar: quién, cuándo, de dónde y cuánto.")

    log = cargar_log_importaciones()
    if log.empty:
        st.info("📭 Todavía no hay importaciones registradas.")
        return

    total_ins = int(log["reconocidos"].sum())
    total_omit = int(log["omitidos"].sum())
    col1, col2, col3 = st.columns(3)
    col1.metric("📥 Eventos de importación", len(log))
    col2.metric("✅ Total insertado", total_ins)
    col3.metric("⏭️ Total omitido", total_omit)
    st.divider()

    tabla = log.copy()
    tabla["fecha_hora"] = tabla["fecha_hora"].dt.strftime("%Y-%m-%d %H:%M")
    tabla = tabla.rename(columns={
        "fecha_hora": "Fecha y hora", "realizado_por": "Quién",
        "fuente": "Fuente", "reconocidos": "Insertados", "omitidos": "Omitidos",
    })
    st.dataframe(
        tabla[["Fecha y hora", "Quién", "Fuente", "Insertados", "Omitidos"]],
        use_container_width=True, hide_index=True,
    )


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def requerir_login():
    try:
        logueado = st.user.is_logged_in
    except AttributeError:
        logueado = False

    if not logueado:
        st.markdown("""
        <div class="app-header">
            <div style="font-size:2.4rem; line-height:1;">💰</div>
            <h1>Cuentas Jessi & Juanse</h1>
            <p>Control financiero familiar</p>
        </div>
        """, unsafe_allow_html=True)
        st.info("🔒 Esta app es privada. Inicia sesión con tu cuenta de Google para continuar.")
        if st.button("Iniciar sesión con Google", type="primary", use_container_width=True):
            try:
                st.login()
            except Exception:
                st.error(
                    "⚠️ El login con Google todavía no está configurado en "
                    "`.streamlit/secrets.toml` (sección `[auth]`)."
                )
        st.stop()

    if st.user.email not in USUARIOS_PERMITIDOS:
        st.error(f"🚫 **{st.user.email}** no tiene acceso a esta app.")
        if st.button("Cerrar sesión"):
            st.logout()
        st.stop()


def main():
    requerir_login()

    # ── Header centrado ───────────────────────────────────────────────────────
    st.markdown("""
    <div class="app-header">
        <div style="font-size:2.4rem; line-height:1;">💰</div>
        <h1>Cuentas Jessi & Juanse</h1>
        <p>Control financiero familiar</p>
    </div>
    """, unsafe_allow_html=True)

    col_sesion_l, col_sesion_r = st.columns([5, 1])
    with col_sesion_r:
        if st.button("🚪 Salir", use_container_width=True, help=st.user.email):
            st.logout()

    # ── Selector de mes centrado ──────────────────────────────────────────────
    hoy = date.today()
    opciones = []
    for i in range(7):
        m = hoy.month - i
        y = hoy.year
        while m <= 0:
            m += 12
            y -= 1
        opciones.append(date(y, m, 1))
    etiquetas = [f"{MESES_ES[d.month]} {d.year}" for d in opciones]

    col_l, col_mid, col_r = st.columns([1, 3, 1])
    with col_mid:
        idx = st.selectbox("📅 Período", range(len(etiquetas)), format_func=lambda i: etiquetas[i], label_visibility="collapsed")
    mes_sel = opciones[idx]

    st.markdown(
        f"<p style='text-align:center; font-size:0.78rem; opacity:0.45; margin-top:-0.5rem;'>"
        f"Salario de {MESES_ES[mes_sel.month]} {mes_sel.year}</p>",
        unsafe_allow_html=True,
    )

    df = cargar_mes(mes_sel)
    items_df = cargar_items(mes_sel)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 Inicio", "➕ Agregar", "🛒 Lista", "📝 Pendientes", "📋 Historial", "📈 Análisis",
        "📥 Importar", "💵 Impuestos", "🗂️ Log Importaciones",
    ])
    with tab1:
        pagina_dashboard(df, mes_sel)
    with tab2:
        pagina_agregar()
    with tab3:
        pagina_lista(items_df, mes_sel)
    with tab4:
        pagina_pendientes(df, mes_sel)
    with tab5:
        pagina_historial(df)
    with tab6:
        pagina_analisis(df)
    with tab7:
        pagina_importar()
    with tab8:
        pagina_impuestos()
    with tab9:
        pagina_historial_importaciones()


if __name__ == "__main__":
    main()
