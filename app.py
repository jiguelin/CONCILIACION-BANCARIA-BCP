"""
Conciliador Bancario RALUMIN — Streamlit
=========================================
Sube el PDF del estado de cuenta BCP y el Excel del contador.
La app hace match en 3 niveles (exacto, aproximado, regla aprendida),
deja que confirmes/edites manualmente y exporta el resultado a Excel.

Las reglas aprendidas se guardan en un JSON y se reutilizan cada mes.
Despliegue: Streamlit Community Cloud (gratis).
"""
import io
import json
import datetime as dt

import pandas as pd
import streamlit as st

from parsers import (
    parse_estado_cuenta_bcp,
    validar_estado_cuenta,
    parse_excel_contador,
)
from motor import conciliar, resumen_conciliacion, patron_sugerido, normaliza
from reglas_base import reglas_base

st.set_page_config(page_title="Conciliador BCP · RALUMIN", page_icon="🏦", layout="wide")

# ---------------------------------------------------------------------------
# Estilos suaves
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1300px;}
.metric-big {font-size: 1.5rem; font-weight: 600;}
div[data-testid="stMetricValue"] {font-size: 1.6rem;}
.estado-EXACTO {color:#1a7f37; font-weight:600;}
.estado-APROX {color:#9a6700; font-weight:600;}
.estado-REGLA {color:#0969da; font-weight:600;}
.estado-PENDIENTE {color:#cf222e; font-weight:600;}
.small {color:#666; font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------------------
if "reglas" not in st.session_state:
    st.session_state.reglas = []          # reglas aprendidas
if "resultados" not in st.session_state:
    st.session_state.resultados = None
if "asientos" not in st.session_state:
    st.session_state.asientos = None
if "movimientos" not in st.session_state:
    st.session_state.movimientos = None

ESTADOS_COLOR = {
    "EXACTO": "🟢 Exacto",
    "APROX": "🟡 Aproximado",
    "REGLA": "🔵 Regla",
    "PENDIENTE": "🔴 Pendiente",
}

# ===========================================================================
# SIDEBAR — carga de archivos y reglas
# ===========================================================================
with st.sidebar:
    st.header("🏦 Conciliador BCP")
    st.caption("Cuenta corriente dólares · RALUMIN E.I.R.L.")

    st.subheader("1 · Archivos del mes")
    pdf_file = st.file_uploader("Estado de cuenta (PDF del BCP)", type=["pdf"])
    xlsx_file = st.file_uploader("Excel del contador (.xlsx)", type=["xlsx", "xlsm"])

    st.subheader("2 · Reglas aprendidas")
    st.caption("Se aplican a los movimientos sin par en la conta. "
               "Las **reglas base** se cargan solas según la moneda del estado de cuenta.")

    # cargar reglas guardadas desde archivo (se suman a las que ya haya)
    reglas_file = st.file_uploader("Cargar reglas guardadas (.json)", type=["json"], key="reglas_up")
    if reglas_file is not None:
        try:
            cargadas = json.load(reglas_file)
            existentes = {normaliza(r["patron"]) for r in st.session_state.reglas}
            nuevas = [r for r in cargadas if normaliza(r.get("patron", "")) not in existentes]
            st.session_state.reglas.extend(nuevas)
            st.success(f"{len(nuevas)} reglas cargadas (las repetidas se omiten).")
        except Exception as e:
            st.error(f"No se pudo leer el JSON: {e}")

    tolerancia = st.slider("Tolerancia match aproximado (USD/PEN)", 0.0, 10.0, 2.0, 0.5,
                           help="Diferencia máxima de monto para considerar un match aproximado (ej. por ITF o redondeo).")

    st.divider()
    st.caption("Reglas actuales:")
    if st.session_state.reglas:
        st.dataframe(pd.DataFrame(st.session_state.reglas), use_container_width=True,
                     hide_index=True, height=180)
        st.download_button(
            "💾 Descargar reglas (.json)",
            data=json.dumps(st.session_state.reglas, ensure_ascii=False, indent=2),
            file_name="reglas_conciliacion.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.caption("— sin reglas —")


# ===========================================================================
# CUERPO PRINCIPAL
# ===========================================================================
st.title("Conciliación bancaria automática")
st.caption("Match del estado de cuenta BCP contra el Excel del contador, con asiento contable.")

if not pdf_file or not xlsx_file:
    st.info("👈 Sube el **PDF del estado de cuenta** y el **Excel del contador** en la barra lateral para comenzar.")
    with st.expander("¿Cómo funciona la conciliación?"):
        st.markdown("""
1. **Nivel exacto** 🟢 — el monto del banco coincide exacto con un asiento de la conta. Match automático con su número de asiento.
2. **Nivel aproximado** 🟡 — el monto difiere por unos centavos (típico por ITF o redondeo). Se sugiere y tú confirmas.
3. **Nivel regla** 🔵 — el movimiento no está en la conta (transferencias, ITF, portes, comisiones), pero coincide con una **regla aprendida** que le asigna su categoría.
4. **Pendiente** 🔴 — no se pudo conciliar; lo revisas a mano y, si quieres, **creas una regla** para que el próximo mes ya entre solo.
""")
    st.stop()

# ----- Parsear archivos -----
try:
    movimientos, resumen = parse_estado_cuenta_bcp(pdf_file.read())
except Exception as e:
    st.error(f"Error leyendo el PDF: {e}")
    st.stop()

try:
    asientos, saldo_ini_conta = parse_excel_contador(xlsx_file.read())
except Exception as e:
    st.error(f"Error leyendo el Excel: {e}")
    st.stop()

val = validar_estado_cuenta(movimientos, resumen)
moneda = (resumen.get("moneda", "") if resumen else "") or "?"
cuenta = (resumen.get("cuenta", "") if resumen else "") or "—"
simbolo = "S/" if moneda == "SOLES" else ("$" if moneda == "DOLARES" else "")

# ----- Cargar reglas base según la moneda detectada (una sola vez por moneda) -----
clave_base = f"_base_{moneda}"
if moneda in ("SOLES", "DOLARES") and not st.session_state.get(clave_base):
    base = reglas_base(moneda)
    existentes = {normaliza(r["patron"]) for r in st.session_state.reglas}
    nuevas = [r for r in base if normaliza(r["patron"]) not in existentes]
    st.session_state.reglas.extend(nuevas)
    st.session_state[clave_base] = True

# ----- Validación / confianza del PDF -----
etiqueta_moneda = {"SOLES": "🇵🇪 Soles", "DOLARES": "💵 Dólares"}.get(moneda, "—")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Moneda", etiqueta_moneda, help=f"Cuenta {cuenta}")
c2.metric("Movimientos banco", val["n_movimientos"])
c3.metric("Asientos conta", len(asientos))
if resumen:
    c4.metric("Saldo final banco", f"{simbolo} {resumen['saldo_final']:,.2f}")
    cuadre = val.get("cuadre_total", False)
    c5.metric("Cuadre con resumen", "✅ OK" if cuadre else "⚠️ Revisar")
else:
    c4.metric("Saldo final banco", "—")
    c5.metric("Cuadre con resumen", "—")

if resumen and not val.get("cuadre_total", False):
    st.warning("El PDF se leyó, pero la suma de movimientos no cuadra exactamente con el resumen del mes. "
               "Revisa que el PDF esté completo (todas las páginas).")

# ----- Ejecutar conciliación -----
resultados, no_usados = conciliar(
    movimientos, asientos,
    reglas=st.session_state.reglas,
    tolerancia=tolerancia,
)
st.session_state.resultados = resultados
st.session_state.asientos = asientos
st.session_state.movimientos = movimientos

rs = resumen_conciliacion(resultados)

st.divider()
st.subheader(f"Resultado: {rs['conciliados']} de {rs['total']} conciliados ({rs['pct']}%)")
st.progress(rs["pct"] / 100)

m1, m2, m3, m4 = st.columns(4)
pe = rs["por_estado"]
m1.metric("🟢 Exactos", pe.get("EXACTO", 0))
m2.metric("🟡 Aproximados", pe.get("APROX", 0))
m3.metric("🔵 Por regla", pe.get("REGLA", 0))
m4.metric("🔴 Pendientes", pe.get("PENDIENTE", 0))

# ----- Tabla de resultados -----
df = pd.DataFrame([{
    "Estado": ESTADOS_COLOR.get(r["estado"], r["estado"]),
    "Fecha": r["fecha"],
    "Descripción banco": r["descripcion"],
    "Monto banco": r["monto_banco"],
    "S/D": r["subdiario"],
    "Asiento": r["asiento_completo"],
    "Concepto conta / categoría": r["concepto_conta"] or r["categoria"],
    "Razón social": r["razon_social"],
    "Monto conta": r["monto_conta"],
    "Dif.": r["diferencia"],
} for r in resultados])

tabs = st.tabs(["📋 Todos", "🔴 Pendientes", "🟡 Aproximados (revisar)", "📊 Asientos no usados"])

with tabs[0]:
    filtro = st.text_input("Buscar en descripción", "")
    dff = df
    if filtro:
        dff = df[df["Descripción banco"].str.contains(filtro, case=False, na=False)]
    st.dataframe(
        dff, use_container_width=True, hide_index=True, height=460,
        column_config={
            "Monto banco": st.column_config.NumberColumn(format="$ %.2f"),
            "Monto conta": st.column_config.NumberColumn(format="$ %.2f"),
            "Dif.": st.column_config.NumberColumn(format="%.2f"),
        },
    )

with tabs[1]:
    pendientes = [r for r in resultados if r["estado"] == "PENDIENTE"]
    if not pendientes:
        st.success("🎉 No quedan movimientos pendientes.")
    else:
        st.caption(f"{len(pendientes)} movimientos sin conciliar. "
                   "Crea una regla para resolver los recurrentes en el futuro.")
        for r in pendientes:
            with st.container(border=True):
                cola, colb, colc = st.columns([3, 1, 2])
                cola.markdown(f"**{r['fecha']}** · {r['descripcion'][:60]}")
                colb.markdown(f"**$ {r['monto_banco']:,.2f}**")
                pat = patron_sugerido(r["descripcion"])
                with colc:
                    with st.popover("➕ Crear regla"):
                        st.write("Nueva regla para movimientos como este:")
                        np = st.text_input("Patrón (texto a buscar)", pat, key=f"pat_{r['idx_banco']}")
                        ncat = st.text_input("Categoría / concepto", "", key=f"cat_{r['idx_banco']}")
                        col_sd, col_asi = st.columns(2)
                        nsd = col_sd.text_input("S/D (subdiario)", "", key=f"sd_{r['idx_banco']}")
                        nasi = col_asi.text_input("N° asiento", "", key=f"asi_{r['idx_banco']}")
                        nsig = st.selectbox("Aplica a", ["cargo", "abono", "ambos"],
                                            index=0 if r["monto_banco"] < 0 else 1,
                                            key=f"sig_{r['idx_banco']}")
                        if st.button("Guardar regla", key=f"btn_{r['idx_banco']}"):
                            st.session_state.reglas.append({
                                "patron": np,
                                "categoria": ncat,
                                "subdiario": nsd,
                                "asiento": nasi,
                                "signo": "" if nsig == "ambos" else nsig,
                            })
                            st.rerun()

with tabs[2]:
    aprox = [r for r in resultados if r["estado"] == "APROX"]
    if not aprox:
        st.info("No hay matches aproximados en esta corrida.")
    else:
        st.caption("Estos matches difieren en monto (revisa que sean correctos):")
        st.dataframe(
            pd.DataFrame([{
                "Fecha": r["fecha"], "Descripción": r["descripcion"],
                "Monto banco": r["monto_banco"], "Monto conta": r["monto_conta"],
                "Dif.": r["diferencia"], "S/D": r["subdiario"],
                "Asiento": r["asiento_completo"],
                "Razón social": r["razon_social"],
            } for r in aprox]),
            use_container_width=True, hide_index=True,
            column_config={
                "Monto banco": st.column_config.NumberColumn(format="$ %.2f"),
                "Monto conta": st.column_config.NumberColumn(format="$ %.2f"),
                "Dif.": st.column_config.NumberColumn(format="%.2f"),
            },
        )

with tabs[3]:
    if not no_usados:
        st.success("Todos los asientos de la conta fueron usados.")
    else:
        st.caption(f"{len(no_usados)} asientos del Excel del contador que NO se cruzaron "
                   "con ningún movimiento del banco (pueden ser ajustes, o el banco los agrupó):")
        st.dataframe(
            pd.DataFrame([{
                "S/D": asientos[i]["subdiario"],
                "Asiento": f"{asientos[i]['subdiario']}-{asientos[i]['asiento']}"
                           if asientos[i]["subdiario"] else asientos[i]["asiento"],
                "Concepto": asientos[i]["concepto"],
                "Monto": asientos[i]["monto"],
                "Razón social": asientos[i]["razon_social"],
                "N° doc": asientos[i]["numero_doc"],
            } for i in no_usados]),
            use_container_width=True, hide_index=True,
            column_config={"Monto": st.column_config.NumberColumn(format="$ %.2f")},
        )

# ----- Exportar a Excel -----
st.divider()
st.subheader("Exportar")


def construir_excel(resultados, no_usados, asientos, resumen):
    buf = io.BytesIO()
    df_res = pd.DataFrame([{
        "Estado": r["estado"], "Fecha": r["fecha"],
        "Descripcion_banco": r["descripcion"], "Monto_banco": r["monto_banco"],
        "S/D": r["subdiario"], "Asiento_Nro": r["asiento"],
        "Asiento_completo": r["asiento_completo"],
        "Concepto_conta": r["concepto_conta"],
        "Categoria_regla": r["categoria"], "Razon_social": r["razon_social"],
        "Monto_conta": r["monto_conta"], "Diferencia": r["diferencia"],
    } for r in resultados])
    df_nou = pd.DataFrame([{
        "S/D": asientos[i]["subdiario"], "Asiento_Nro": asientos[i]["asiento"],
        "Concepto": asientos[i]["concepto"],
        "Monto": asientos[i]["monto"], "Razon_social": asientos[i]["razon_social"],
        "N_doc": asientos[i]["numero_doc"],
    } for i in no_usados])
    rs = resumen_conciliacion(resultados)
    df_resumen = pd.DataFrame([
        {"Métrica": "Total movimientos banco", "Valor": rs["total"]},
        {"Métrica": "Conciliados", "Valor": rs["conciliados"]},
        {"Métrica": "% conciliado", "Valor": rs["pct"]},
        {"Métrica": "Exactos", "Valor": rs["por_estado"].get("EXACTO", 0)},
        {"Métrica": "Aproximados", "Valor": rs["por_estado"].get("APROX", 0)},
        {"Métrica": "Por regla", "Valor": rs["por_estado"].get("REGLA", 0)},
        {"Métrica": "Pendientes", "Valor": rs["por_estado"].get("PENDIENTE", 0)},
        {"Métrica": "Generado", "Valor": dt.datetime.now().strftime("%Y-%m-%d %H:%M")},
    ])
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        df_resumen.to_excel(xl, sheet_name="Resumen", index=False)
        df_res.to_excel(xl, sheet_name="Conciliacion", index=False)
        if not df_nou.empty:
            df_nou.to_excel(xl, sheet_name="Conta_no_usada", index=False)
    buf.seek(0)
    return buf


excel_buf = construir_excel(resultados, no_usados, asientos, resumen)
st.download_button(
    "📥 Descargar conciliación en Excel",
    data=excel_buf,
    file_name=f"conciliacion_{dt.date.today().isoformat()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
st.caption("Recuerda descargar también las **reglas (.json)** desde la barra lateral "
           "para reutilizarlas el próximo mes.")
