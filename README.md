# 🏦 Conciliador Bancario BCP — RALUMIN

Aplicativo web que **concilia automáticamente** los estados de cuenta corriente del BCP
(**en soles o en dólares**) contra el Excel de conciliación del contador, asignando a
cada movimiento del banco su **asiento contable** correspondiente.

Hecho con **Streamlit** · listo para desplegar gratis en **Streamlit Community Cloud**.

---

## ¿Qué hace?

Sube dos archivos cada mes:
1. **PDF del estado de cuenta** del BCP (la app detecta sola si es **soles** o **dólares**).
2. **Excel del contador** (la conciliación con la columna `ASIE` = número de asiento).

La app **detecta automáticamente la moneda** leyéndola del PDF, aplica el juego de reglas
correcto para esa cuenta, cruza ambos archivos y clasifica cada movimiento del banco en
4 niveles:

| Nivel | Significado |
|-------|-------------|
| 🟢 **Exacto** | El monto del banco coincide exacto con un asiento de la conta. Match automático. |
| 🟡 **Aproximado** | El monto difiere por centavos (ITF, redondeo). Se sugiere y tú confirmas. |
| 🔵 **Por regla** | El movimiento no está en la conta (transferencias, ITF, portes…) pero coincide con una **regla aprendida** que le asigna su categoría. |
| 🔴 **Pendiente** | No se pudo conciliar. Lo revisas a mano y creas una regla para el futuro. |

> **Importante:** la app **no inventa asientos**. El asiento que muestra es el que el
> contador ya escribió en el Excel. Cada asiento se identifica por **S/D (subdiario,
> columna C) + N° de asiento (columna D)**, y la app lo reporta completo, p. ej. `03-53`.
> La conciliación solo *encuentra* ese asiento y lo pega junto al movimiento del banco
> que le corresponde por monto.

> **Por qué hay menos movimientos en el Excel que en el banco:** la conciliación del
> contador es un trabajo en progreso. Primero se revisa qué ya está contabilizado y
> sobre eso se trabajan los pagos de facturas; los cobros/ingresos los registra otra
> persona. Por eso, al correr la app, los movimientos del banco que aún no tienen
> asiento aparecen como **pendientes**: son los que todavía faltan por contabilizar
> (o gastos que nunca se registran como cobro, como ITF o portes).

Con las **reglas base BCP** cargadas, la conciliación de un mes típico pasa de ~50 %
(solo match exacto) a **~94 % automático**.

### Reglas base por moneda (automáticas)
Al detectar la moneda, la app carga sola las **reglas base** de esa cuenta:
- **Comunes** (ambas): transferencias `A 19x`, CCE, ITF, portes, comisiones, etc.
- **Solo dólares**: traspasos a cuenta propia, AFP, descuento de facturas (`DSCTO. CP`), abonos del exterior.
- **Solo soles**: SUNAT, DHL, telefonía, luz/agua, CTS, planilla (`HABER`), préstamo, consumos POS, etc.

Con esto, un mes típico se concilia automáticamente en torno al **97 % (dólares)** y
**100 % (soles)**, dejando solo unos pocos movimientos para revisar a mano.

### Aprendizaje
Cuando un movimiento queda pendiente, creas una **regla** (ej. patrón `A 193 2602958`
→ "Traspaso a cuenta propia"). Las reglas se descargan como `.json` y se vuelven a
cargar el mes siguiente; se suman a las base sin duplicarse. Así la app **mejora con el uso**.

---

## Archivos del proyecto

```
conciliador/
├── app.py              # Interfaz Streamlit (detección de moneda incluida)
├── parsers.py          # Lectura del PDF del BCP (soles/dólares) y del Excel del contador
├── motor.py            # Motor de conciliación (3 niveles + reglas)
├── reglas_base.py      # Reglas base por moneda (comunes / soles / dólares)
├── requirements.txt    # Dependencias
├── .streamlit/
│   └── config.toml     # Tema y límite de subida
├── .gitignore          # Evita subir datos reales
└── README.md
```

---

## 🚀 Cómo desplegarlo (paso a paso)

### 1. Crear el repositorio en GitHub
1. Entra a [github.com](https://github.com) → **New repository**.
2. Nómbralo, por ejemplo, `conciliador-bcp`. Déjalo **Privado** (son datos contables).
3. Crea el repo (sin README, ya tienes uno).

### 2. Subir los archivos
Opción simple (web): en el repo → **Add file → Upload files** → arrastra todos los
archivos de esta carpeta → **Commit**.

Opción consola:
```bash
cd conciliador
git init
git add .
git commit -m "Conciliador BCP inicial"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/conciliador-bcp.git
git push -u origin main
```

### 3. Desplegar en Streamlit Community Cloud
1. Entra a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con GitHub.
2. **Create app** → **Deploy a public app from GitHub** (o conecta tu repo privado).
3. Selecciona:
   - **Repository:** `TU_USUARIO/conciliador-bcp`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. **Deploy**. En 1–2 minutos tendrás una URL tipo
   `https://conciliador-bcp.streamlit.app`.

> Si el repo es privado, en Streamlit Cloud autoriza el acceso a repos privados
> la primera vez (botón de permisos de GitHub).

### 4. Usarlo
1. Abre la URL.
2. Sube el **PDF** del estado de cuenta y el **Excel** del contador. La app detecta
   sola la moneda y carga las reglas base correctas.
3. Revisa los pendientes, crea reglas si hace falta.
4. Descarga la **conciliación en Excel** y las **reglas (.json)**.

---

## 🔒 Privacidad
- El `.gitignore` impide subir PDFs/Excel reales al repositorio.
- Streamlit Cloud procesa los archivos en memoria durante la sesión; no quedan
  guardados en el repositorio.
- Aun así, por tratarse de información contable, **mantén el repositorio privado**.

---

## 🛠️ Correr en tu PC (opcional)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Se abre en `http://localhost:8501`.

---

## Notas técnicas
- El PDF del BCP a veces llega con bytes extra (`$BOP$ … $EOP$`); el parser los
  recorta automáticamente al PDF válido.
- La lectura del PDF se **valida** contra la fila "Resumen del mes" (abonos, cargos
  y saldo final) y encadenando los saldos, así sabes si el PDF se leyó completo.
- El match exacto admite montos duplicados (varios movimientos del mismo importe)
  asignándolos uno a uno.
