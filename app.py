"""
Cuentas Jessi & Juanse — App de control financiero familiar
"""

import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# ─── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Cuentas Jessi & Juanse",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding: 1rem 0.75rem 3rem; max-width: 720px; }
    .stTabs [data-baseweb="tab"] { font-size: 13px; padding: 6px 10px; }
    div[data-testid="metric-container"] {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 12px 8px;
    }
    .stButton > button { border-radius: 8px; }
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
}

PERSONAS = ["Jessi", "Juanse", "Ambos"]

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
    cols = ["id", "fecha", "mes_presupuestal", "persona", "tipo", "categoria", "subcategoria", "descripcion", "monto"]
    if not res.data:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(res.data)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    df["mes_presupuestal"] = pd.to_datetime(df["mes_presupuestal"]).dt.date
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    return df


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
        es_gasto = row["tipo"] == "gasto"
        emoji = "💸" if es_gasto else "💰"
        desc_extra = f" · {row['descripcion']}" if row.get("descripcion") else ""
        signo = "−" if es_gasto else "+"

        # Mostrar aviso si la fecha de pago es de un mes diferente al mes presupuestal
        mes_pres = row.get("mes_presupuestal")
        pago_distinto = ""
        if mes_pres and hasattr(mes_pres, "month") and mes_pres.month != row["fecha"].month:
            pago_distinto = f" · <span style='color:#f0a500'>pagado el {row['fecha']}</span>"

        col_info, col_monto, col_del = st.columns([6, 3, 1])
        with col_info:
            st.markdown(
                f"{emoji} **{row['subcategoria']}**  \n"
                f"<small>{row['categoria']} · {row['persona']}{pago_distinto}{desc_extra}</small>",
                unsafe_allow_html=True,
            )
        with col_monto:
            st.markdown(f"**{signo}{fmt(row['monto'])}**")
        with col_del:
            if st.button("🗑️", key=f"del_{row['id']}", help="Eliminar"):
                eliminar(str(row["id"]))
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


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    col_titulo, col_mes = st.columns([3, 2])
    with col_titulo:
        st.markdown("## 💰 Cuentas Jessi & Juanse")
    with col_mes:
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
        idx = st.selectbox("📅 Mes", range(len(etiquetas)), format_func=lambda i: etiquetas[i])
        mes_sel = opciones[idx]

    df = cargar_mes(mes_sel)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Agregar", "📋 Historial", "📈 Análisis"])
    with tab1:
        pagina_dashboard(df, mes_sel)
    with tab2:
        pagina_agregar()
    with tab3:
        pagina_historial(df)
    with tab4:
        pagina_analisis(df)


if __name__ == "__main__":
    main()
