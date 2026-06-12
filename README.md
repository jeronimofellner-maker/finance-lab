# Finance Lab

Sistema personal de equity research + gestión de cartera (CEDEARs, acciones BYMA,
bonos soberanos AR, ONs, plazos fijos, MEP). Brief diario por mail, alertas
intradía, review de cartera y notas de cobertura quincenales.

> **Aviso (se dice una vez):** esto es una herramienta personal de análisis. No es
> asesoramiento financiero ni una recomendación de compra/venta para terceros.

---

## 0. Setup inicial (una vez)

```bash
cd ~/finance-lab
python3 -m pip install -r requirements.txt
cp .env.example .env          # después completá .env (paso 1)
```

---

## 1. Gmail: activar 2FA y crear App Password

El envío de mails usa **SMTP de Gmail con App Password** (no tu contraseña normal).
Requiere verificación en dos pasos activada.

**a) ¿Tenés 2FA?** Entrá a <https://myaccount.google.com/security> → "Verificación
en dos pasos".
- Si dice **Desactivado**: activala (te va a pedir tu celular). Sin esto, Google
  **no deja** crear App Passwords.
- Si dice **Activado**: seguí al paso b.

**b) Crear el App Password:** andá a <https://myaccount.google.com/apppasswords>
(buscá "Contraseñas de aplicaciones"). Poné un nombre (ej. `finance-lab`) y
generá. Te da **16 caracteres** tipo `abcd efgh ijkl mnop`.

**c) Cargalo en `.env`** SIN espacios:
```
GMAIL_USER=tu-mail@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
MAIL_TO=tu-mail@gmail.com
SEC_USER_AGENT=Tu Nombre tu-mail@example.com
```

**d) Probá el envío:**
```bash
python3 -c "import sys; sys.path.insert(0,'src'); from finlab.mail import smtp; \
  print('OK' if smtp.send('[Finance Lab] Test', '<b>Funciona</b>') else 'FALLÓ')"
```
Si llega el mail, listo. Si falla: revisá que el App Password no tenga espacios y
que 2FA esté activo.

---

## 2. Cargar tu cartera (`config/portfolio.yaml`)

Abrí `config/portfolio.yaml`. Tiene ejemplos comentados. **Borralos** y cargá tus
posiciones reales. Cada una lleva:

```yaml
- ticker: GGAL          # símbolo (ver convenciones en el header del archivo)
  asset_class: accion_ar # cedear | accion_ar | bono_ar | ons | us_equity | plazo_fijo | cash
  qty: 50
  ppc: 6800             # precio promedio de compra en `moneda`
  moneda: ARS
  sector: Bancos
  tesis: "Una línea. Obligatoria. Si no la podés escribir, sacá la posición."
```

Validá que toma precios:
```bash
python3 scripts/weekly_portfolio.py
```
Te imprime valuación en USD-MEP, exposición por clase y sugerencias de rebalanceo
contra `config/targets.yaml`. Si un ticker aparece "sin precio", revisá que el
símbolo sea el correcto del panel BYMA (no el de US).

---

## 3. Correr cada workflow a mano (primera vez)

```bash
# Brief diario — imprime el HTML sin enviar
python3 scripts/daily_brief.py --dry-run
# Brief diario — lo manda por mail
python3 scripts/daily_brief.py

# Alertas intradía — lista sin enviar, ignorando la ventana horaria
python3 scripts/intraday_alerts.py --force --dry-run
# Alertas — envía (respeta ventana 11:00-17:30 ART salvo --force)
python3 scripts/intraday_alerts.py --force

# Review de cartera
python3 scripts/weekly_portfolio.py
python3 scripts/weekly_portfolio.py --mail

# Nueva nota de cobertura
python3 scripts/new_note.py YPF --stance long --target 35
```

---

## 4. Brief diario automático (GitHub Actions)

El brief corre en la nube para que llegue **aunque tu Mac esté apagada**.

**a) Crear cuenta y repo:**
1. Creá cuenta en <https://github.com> si no tenés.
2. Instalá GitHub CLI: `brew install gh` y logueate: `gh auth login`.
3. Desde la carpeta del proyecto:
   ```bash
   cd ~/finance-lab
   git init
   git add .
   git commit -m "Finance Lab inicial"
   gh repo create finance-lab --private --source=. --push
   ```
   > El `.gitignore` ya excluye `.env`, así que tus secretos **no** se suben.

**b) Cargar los secretos en el repo** (equivalente a tu `.env`, pero en la nube):
```bash
gh secret set GMAIL_USER --body "tu-mail@gmail.com"
gh secret set GMAIL_APP_PASSWORD --body "abcdefghijklmnop"
gh secret set MAIL_TO --body "tu-mail@gmail.com"
gh secret set SEC_USER_AGENT --body "Tu Nombre tu-mail@example.com"
```

**c) Probarlo sin esperar al horario:** GitHub → pestaña **Actions** → "Daily Brief"
→ **Run workflow**. O por CLI: `gh workflow run "Daily Brief"`.

**Horario:** está seteado a `30 10 * * 1-5` (UTC) = **07:30 ART, lun-vie**.
Para cambiarlo editá el `cron` en `.github/workflows/daily-brief.yml`.
⚠️ El scheduler de Actions a veces demora 5-15 min; es normal.

---

## 5. Alertas intradía automáticas (launchd, local)

Las alertas corren en tu Mac (necesitan tu sesión activa). Cada 20' el job se
despierta y el script decide si está dentro de la ventana 11:00-17:30 ART.

**a) Editá las rutas del plist** si tu path de Python cambia. Verificá:
```bash
which python3   # debe coincidir con la ruta en launchd/com.finlab.alerts.plist
```

**b) Instalá el agente:**
```bash
cp launchd/com.finlab.alerts.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.finlab.alerts.plist
```

**c) Comandos útiles:**
```bash
launchctl list | grep finlab                 # ver si está cargado
tail -f logs/alerts.log                       # ver actividad
launchctl unload ~/Library/LaunchAgents/com.finlab.alerts.plist   # desactivar
```

> **Limitación:** si la Mac está dormida/apagada a esa hora, el job no corre.
> Para alertas no querés perderte nada crítico → considerá migrarlas a GitHub
> Actions más adelante (mismo patrón que el brief).

---

## 5b. Dashboard web (GitHub Pages)

Dashboard estático, dark, mobile-first, servido en
**https://jeronimofellner-maker.github.io/finance-lab/**

- Lo genera `scripts/build_dashboard.py` → `docs/index.html`.
- El workflow `daily-brief.yml` lo regenera y commitea automáticamente después del
  brief (lun-vie). GitHub Pages publica `main` / `docs`.
- **Privacidad:** `config/settings.yaml` → `dashboard.show_absolute_values: false`.
  Publica solo porcentajes (asignación, P&L %, pesos). No expone patrimonio,
  cantidades ni PPC. Para ver el detalle absoluto, usás el brief por mail (privado).
- Regenerar a mano: `python3 scripts/build_dashboard.py` y abrir `docs/index.html`.

## 6. Calendario de uso

| Cuándo | Qué | Cómo |
|---|---|---|
| Lun-Vie 07:30 ART | Brief diario | automático (Actions) |
| Lun-Vie 11:00-17:30 | Alertas intradía | automático (launchd) |
| Domingos | Review de cartera + nota quincenal | `weekly_portfolio.py` + `new_note.py` |
| Al operar | Actualizar `portfolio.yaml` | a mano |

---

## 7. Fuentes de datos y sus límites (conocelos)

| Fuente | Cubre bien | Limitación free-tier |
|---|---|---|
| **data912** | Precios BYMA (acciones, CEDEARs, bonos, ONs), MEP | Datos de mercado, sin fundamentals. Puede tener latencia. |
| **yfinance** | Precios y earnings US | No oficial; Yahoo a veces cambia y rompe. CEDEARs `.BA` con gaps. |
| **BCRA v4.0** | Reservas, base, A3500, tasas | Oficial y estable. Inflación con rezago (la publica INDEC). |
| **SEC EDGAR** | Filings de empresas listadas en US (YPF, VIST, PAM, GGAL, MELI, GLOB) | Solo US. Empresas solo-BYMA no tienen filings acá. |
| **RSS noticias** | Titulares macro AR + global | **FT/Bloomberg quedan afuera** (paywall). Cobertura "premium" requiere pago. |
| **ForexFactory** | Agenda económica USD/global | Eventos puramente locales de AR casi no aparecen. |
| **Rating actions** | — | **Best-effort vía keywords en noticias.** Sin fuente paga no hay garantía. |

Cuando algo de esto sea un cuello de botella real para tu research, lo charlamos y
evaluamos si vale la pena una fuente paga puntual.
