"""
Motor de conciliación de 3 niveles para RALUMIN.

Niveles de match (de mayor a menor confianza):
  1. EXACTO   -> mismo monto exacto y mismo signo.
  2. APROX    -> monto cercano (tolerancia, p. ej. por ITF o redondeo) y mismo signo.
  3. REGLA    -> el movimiento del banco no tiene par en la conta, pero coincide
                 con una REGLA aprendida (por patrón de descripción). Se le asigna
                 una categoría/asiento estándar definido por el usuario.

Lo que no cae en ningún nivel queda PENDIENTE para revisión manual.

Las reglas aprendidas se guardan como una lista de dicts:
    {"patron": "A 193 2602958", "categoria": "Traspaso cuenta propia",
     "asiento": "", "signo": "cargo"}
El patrón se busca como substring (mayúsculas) dentro de la descripción del banco.
"""
import re
from collections import defaultdict


def normaliza(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "")).strip().upper()


def patron_sugerido(descripcion: str) -> str:
    """Propone un patrón estable a partir de una descripción del banco,
    quitando números de operación variables pero conservando la parte fija
    identificadora (p. ej. 'A 193 2602958')."""
    d = normaliza(descripcion)
    # casos típicos del BCP
    m = re.match(r"^(A \d{3} \d+)", d)
    if m:
        return m.group(1)
    for clave in ["TRANFERENCIA CCE", "TRANSF.EXT", "IMPUESTO ITF",
                  "LETRAS DESCUENTOS", "PORTES AUTOSOBRE", "PAGOS AFP",
                  "COM.MANTENIM", "ENVIO.EST.CTA", "FNF.DES",
                  "TRAN.CTAS.TERC", "TRANSF.BCO"]:
        if clave in d:
            return clave
    # por defecto, las primeras 3 palabras no numéricas
    palabras = [p for p in d.split() if not re.match(r"^[\d\.,-]+$", p)]
    return " ".join(palabras[:3])


def conciliar(movimientos_banco, asientos_conta, reglas=None,
              tolerancia=2.00):
    """
    Ejecuta la conciliación.

    Devuelve lista de resultados, uno por movimiento del banco, en el mismo
    orden. Cada resultado es un dict:
        idx_banco, fecha, descripcion, monto_banco,
        estado: 'EXACTO' | 'APROX' | 'REGLA' | 'PENDIENTE',
        asiento, concepto_conta, razon_social, monto_conta,
        diferencia, categoria (si REGLA), idx_conta (o None),
        patron (si REGLA).
    Además devuelve la lista de índices de asientos de la conta NO usados.
    """
    reglas = reglas or []
    # índice de la conta por monto exacto (permite duplicados)
    pool = defaultdict(list)
    for i, a in enumerate(asientos_conta):
        pool[a["monto"]].append(i)

    usados = set()
    resultados = []

    def fila_base(j, b):
        return {
            "idx_banco": j,
            "fecha": b["fecha"],
            "descripcion": b["descripcion"],
            "monto_banco": b["monto"],
            "estado": "PENDIENTE",
            "subdiario": "",
            "asiento": "",
            "asiento_completo": "",
            "concepto_conta": "",
            "razon_social": "",
            "monto_conta": None,
            "diferencia": None,
            "categoria": "",
            "patron": "",
            "idx_conta": None,
        }

    def fmt_asiento(a):
        """Combina subdiario + número en 'SD-ASIE' (p. ej. '03-53')."""
        sd = str(a.get("subdiario", "") or "").strip()
        nro = a.get("asiento", "")
        nro = "" if nro is None else str(nro).strip()
        if sd and nro:
            return f"{sd}-{nro}"
        return nro or sd

    # ---- Nivel 1: EXACTO ----
    for j, b in enumerate(movimientos_banco):
        r = fila_base(j, b)
        candidatos = [i for i in pool.get(b["monto"], []) if i not in usados]
        if candidatos:
            i = candidatos[0]
            usados.add(i)
            a = asientos_conta[i]
            r.update(estado="EXACTO", subdiario=a.get("subdiario", ""),
                     asiento=a["asiento"], asiento_completo=fmt_asiento(a),
                     concepto_conta=a["concepto"], razon_social=a["razon_social"],
                     monto_conta=a["monto"], diferencia=0.0, idx_conta=i)
        resultados.append(r)

    # ---- Nivel 2: APROX (tolerancia, mismo signo) ----
    for r in resultados:
        if r["estado"] != "PENDIENTE":
            continue
        b_monto = r["monto_banco"]
        mejor, mejor_dif = None, tolerancia + 1
        for i, a in enumerate(asientos_conta):
            if i in usados:
                continue
            if (a["monto"] < 0) != (b_monto < 0):
                continue
            dif = abs(abs(a["monto"]) - abs(b_monto))
            if dif <= tolerancia and dif < mejor_dif:
                mejor_dif, mejor = dif, i
        if mejor is not None:
            usados.add(mejor)
            a = asientos_conta[mejor]
            r.update(estado="APROX", subdiario=a.get("subdiario", ""),
                     asiento=a["asiento"], asiento_completo=fmt_asiento(a),
                     concepto_conta=a["concepto"], razon_social=a["razon_social"],
                     monto_conta=a["monto"], diferencia=round(mejor_dif, 2),
                     idx_conta=mejor)

    # ---- Nivel 3: REGLA aprendida (por patrón de descripción) ----
    for r in resultados:
        if r["estado"] != "PENDIENTE":
            continue
        desc = normaliza(r["descripcion"])
        for regla in reglas:
            pat = normaliza(regla.get("patron", ""))
            if not pat:
                continue
            if pat in desc:
                # validar signo si la regla lo especifica
                signo = regla.get("signo", "")
                if signo == "cargo" and r["monto_banco"] > 0:
                    continue
                if signo == "abono" and r["monto_banco"] < 0:
                    continue
                r.update(estado="REGLA",
                         categoria=regla.get("categoria", ""),
                         subdiario=regla.get("subdiario", ""),
                         asiento=regla.get("asiento", ""),
                         asiento_completo=fmt_asiento({
                             "subdiario": regla.get("subdiario", ""),
                             "asiento": regla.get("asiento", ""),
                         }),
                         patron=regla.get("patron", ""))
                break

    no_usados = [i for i in range(len(asientos_conta)) if i not in usados]
    return resultados, no_usados


def resumen_conciliacion(resultados):
    """Cuenta movimientos por estado y suma montos."""
    cont = defaultdict(int)
    suma = defaultdict(float)
    for r in resultados:
        cont[r["estado"]] += 1
        suma[r["estado"]] = round(suma[r["estado"]] + r["monto_banco"], 2)
    total = len(resultados)
    conciliados = cont["EXACTO"] + cont["APROX"] + cont["REGLA"]
    return {
        "total": total,
        "conciliados": conciliados,
        "pct": round(100 * conciliados / total, 1) if total else 0,
        "por_estado": dict(cont),
        "suma_por_estado": dict(suma),
    }
