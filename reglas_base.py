"""
Reglas base de conciliación BCP para RALUMIN, organizadas por moneda.

Cada regla:
    {"patron": <texto a buscar en la descripción del banco>,
     "categoria": <concepto legible>,
     "subdiario": "", "asiento": "",   # los completas tú si corresponde
     "signo": "cargo" | "abono" | ""}  # "" = aplica a ambos

El patrón se busca como substring (en mayúsculas) dentro de la descripción
del movimiento del banco. Estas reglas resuelven los movimientos repetitivos
que no suelen estar 1-a-1 en el Excel del contador (gastos bancarios,
transferencias, impuestos, servicios, etc.).
"""

# --- Reglas que aplican a AMBAS cuentas (soles y dólares) ---
REGLAS_COMUNES = [
    {"patron": "A 191", "categoria": "Transferencia a terceros", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "A 192", "categoria": "Transferencia a terceros", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "A 193", "categoria": "Transferencia a terceros", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "A 194", "categoria": "Transferencia a terceros", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "TRANFERENCIA CCE", "categoria": "Pago proveedor (CCE)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "TRANSF.EXT", "categoria": "Transferencia al exterior", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "TRAN.CTAS.TERC", "categoria": "Transferencia a terceros (abono)", "subdiario": "", "asiento": "", "signo": ""},
    {"patron": "IMPUESTO ITF", "categoria": "ITF (gasto bancario)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "REGULARIZACION ITF", "categoria": "Regularización ITF", "subdiario": "", "asiento": "", "signo": ""},
    {"patron": "PORTES", "categoria": "Portes (gasto bancario)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "COM.MANTENIM", "categoria": "Comisión mantenimiento", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "ENVIO.EST.CTA", "categoria": "Envío estado de cuenta", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "MANT TD ADIC", "categoria": "Mantenimiento tarjeta", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "MANT MAY", "categoria": "Mantenimiento mensual", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "LETRAS DESCUENTOS", "categoria": "Letras en descuento", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "DEVOL. PAGO", "categoria": "Devolución de pago", "subdiario": "", "asiento": "", "signo": ""},
]

# --- Reglas SOLO para la cuenta en DÓLARES ---
REGLAS_DOLARES = [
    {"patron": "A 193 2602958", "categoria": "Traspaso a cuenta propia", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "PAGOS AFP", "categoria": "Pago AFP", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "FNF.DES", "categoria": "Fondo de desembolso", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "DSCTO. CP", "categoria": "Descuento de factura (cobro)", "subdiario": "", "asiento": "", "signo": "abono"},
    {"patron": "AB.TR.EXT", "categoria": "Abono transferencia exterior", "subdiario": "", "asiento": "", "signo": "abono"},
]

# --- Reglas SOLO para la cuenta en SOLES ---
REGLAS_SOLES = [
    {"patron": "DE HECTORIR", "categoria": "Cobro Hectorir (ingreso)", "subdiario": "", "asiento": "", "signo": "abono"},
    {"patron": "SUNA", "categoria": "Pago SUNAT (impuestos)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "DHL", "categoria": "Pago DHL (courier)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "TELE", "categoria": "Pago telefonía", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "MOVI", "categoria": "Pago Movistar", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "PLUZ", "categoria": "Pago luz (Enel/Pluz)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "SEDA", "categoria": "Pago agua (Sedapal)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "CTS TLC", "categoria": "Depósito CTS", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "HABER TLC", "categoria": "Pago de haberes (planilla)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "DEB.AUTOM.PRESTAMO", "categoria": "Pago de préstamo", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "DEPOSITO AG", "categoria": "Depósito en agencia", "subdiario": "", "asiento": "", "signo": "abono"},
    {"patron": "TECN", "categoria": "Pago servicio (Tecnología)", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "MAPF", "categoria": "Pago Mapfre (seguro)", "subdiario": "", "asiento": "", "signo": "cargo"},
    # consumos con tarjeta / POS frecuentes
    {"patron": "OPENPAY", "categoria": "Consumo POS", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "EL TAMBO", "categoria": "Consumo POS", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "SODIMAC", "categoria": "Consumo POS", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "TUGO PERU", "categoria": "Consumo POS", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "EL HORNERO", "categoria": "Consumo POS", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "MOTORS TECHNIK", "categoria": "Consumo POS", "subdiario": "", "asiento": "", "signo": "cargo"},
    {"patron": "INVERSIONES PERU", "categoria": "Consumo POS", "subdiario": "", "asiento": "", "signo": "cargo"},
]


def reglas_base(moneda: str):
    """Devuelve la lista de reglas base apropiada según la moneda detectada
    ('SOLES' o 'DOLARES'). Siempre incluye las comunes."""
    m = (moneda or "").upper()
    if m == "SOLES":
        return REGLAS_COMUNES + REGLAS_SOLES
    if m == "DOLARES":
        return REGLAS_COMUNES + REGLAS_DOLARES
    # si no se detectó, devolver todas para máxima cobertura
    return REGLAS_COMUNES + REGLAS_DOLARES + REGLAS_SOLES
