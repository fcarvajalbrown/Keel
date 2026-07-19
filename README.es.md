<p align="center"><a href="README.md">English</a> · <b>Español</b></p>

<p align="center">
  <img src="assets/keel-logo-black.png" width="540"
       alt="Keel — Mezcla + masterización automática para stems terminados">
</p>

<p align="center">
  <a href="https://github.com/fcarvajalbrown/Keel/releases/download/v0.7.0-beta/KeelSetup-0.7.0.exe">
    <img src="https://img.shields.io/badge/Descargar%20para%20Windows-Instalador%20Beta-2ea44f?style=for-the-badge&logo=windows&logoColor=white"
         alt="Descargar Keel para Windows — instalador beta">
  </a>
</p>
<p align="center"><sub>¿Usas un DAW? Descarga el <a href="https://github.com/fcarvajalbrown/Keel/releases/download/v0.7.0-beta/Keel-VST3-windows-0.7.0.zip">plugin VST3 (Windows)</a> o el <a href="https://github.com/fcarvajalbrown/Keel/releases/download/v0.7.0-beta/Keel-plugins-macos-0.7.0.zip">plugin VST3 + AU (macOS)</a>.</sub></p>
<p align="center"><sub>Beta sin firmar: Windows puede advertir — haz clic en <b>Más información &rarr; Ejecutar de todas formas</b>. macOS y otras descargas en la <a href="https://github.com/fcarvajalbrown/Keel/releases/latest">página de releases</a>.</sub></p>

> Un motor **determinista** de mezcla y masterización automática. Le das una
> carpeta de **stems ya terminados, con sus efectos impresos**; los
> **balancea por volumen percibido** en una mezcla estéreo y masteriza esa
> mezcla a un **loudness seguro para streaming** — sobre la medición
> **ITU-R BS.1770-4** y una cadena de máster con **limitador de true peak**.
> Los mismos stems entran, el mismo máster sale, siempre. Sin adivinanzas de
> IA, sin aleatoriedad.

<div align="center">

[![estado](assets/badges/estado.svg)](ROADMAP.md)
[![motor: AGPL v3](assets/badges/motor.svg)](LICENSE)
[![uso comercial: USD 20/asiento](assets/badges/uso-comercial.svg)](COMMERCIAL-LICENSE.md)
[![Python](assets/badges/python.svg)](requirements.txt)
[![loudness](assets/badges/loudness.svg)](#bajo-el-capó-el-dsp)
[![render](assets/badges/render-determinista.svg)](#)

</div>

<p align="center">
  <a href="https://www.paypal.com/donate/?business=fcarvajalbrown%40protonmail.com&item_name=Support%20Keel%20development&currency_code=USD">
    <img src="https://img.shields.io/badge/Cómprame%20un%20café-FFDD00?style=for-the-badge&logo=paypal&logoColor=black"
         alt="Cómprame un café — donar vía PayPal">
  </a>
</p>

**Qué hace, en una línea:** convierte un montón de stems terminados en una
mezcla balanceada y un máster competitivo y seguro de picos, con un solo
comando — sin tocar tu tono.

Keel es para dos personas. El **productor** con buenos stems que no quiere (o no
puede) mezclar y masterizar a mano: un comando, listo. El **ingeniero** que
quiere una etapa de balance+máster determinista y scriptable dentro de un
pipeline: objetivos de LUFS exactos, un medidor real de true peak sobremuestreado,
reproducible a la muestra, con un reporte de control de calidad en cada corrida.
Keel también viene como una **app de escritorio (GUI)** y un **plugin VST3 / AU**
sobre el mismo motor determinista, así que puedes mezclar y masterizar desde una
ventana de escritorio o dentro de tu DAW — ver [`ROADMAP.md`](ROADMAP.md).

> Palabras clave: mezcla automática, masterización automática, normalización de
> loudness, medidor de LUFS, LUFS integrado, short-term LUFS, rango de loudness
> (LRA), limitador de true peak, ITU-R BS.1770-4, balance de stems, cadena de
> máster, medidor de reducción de ganancia, audio determinista, masterización
> reproducible, audio en Python, **plugin VST3**, **plugin AU**, masterización en
> DAW, plugin de bus máster, Logic Pro, GarageBand.

---

## De un vistazo

| | |
|---|---|
| **Entrada** | Cualquier número de stems terminados, con efectos impresos (`.wav` / `.flac`) |
| **Salida** | **Mezcla** estéreo balanceada + **máster** seguro de loudness (WAV 24-bit) + `REPORT.md` |
| **Loudness** | Normalizado a un **objetivo LUFS exacto** (por defecto **-14**), ITU-R BS.1770-4 |
| **Picos** | Limitación real de **true peak sobremuestreado 4x** a un techo dBTP (por defecto **-1.0**) |
| **Etiquetado** | **Autodetectado**, editable en `keel.json`; **1..N archivos por etiqueta** |
| **Masterización** | Cadena interna clip -> limit, **o** igualar una referencia comercial (Matchering) |
| **Determinismo** | Mismas entradas -> salida **idéntica**. Sin ML, sin aleatoriedad en el render |
| **Tono** | **Intacto** — Keel balancea y masteriza; nunca re-ecualiza tus stems |
| **Front-ends** | **CLI**, app de escritorio (**GUI**) y **plugin VST3 / AU** — un solo motor determinista compartido |

---

## Cómo funciona (la cadena de señal)

```
MEZCLA  stems -> [agrupar por etiqueta] -> [balancear loudness por grupo] -> [pan?] -> sumar -> mix.wav
MÁSTER  mezcla -> [tono/glue] -> [pre-normalizar] -> [soft-clip sobremuestreado]
               -> [limitador true peak 4x] -> [normalizar a LUFS exacto] -> [seguro TP] -> master.wav
```

Cada paso está guiado por medición y es determinista. La mezcla deja el bus
cerca de -6 dBFS para que el máster tenga espacio; el máster normaliza a tu
objetivo LUFS exacto y garantiza el techo de true peak.

---

## Instalación

Recomendado — un entorno virtual local (mantiene aisladas las dependencias de
Keel, corre igual en cualquier máquina). `setup.ps1` crea `.venv` e instala el
motor central **sin conexión** desde los wheels incluidos:

```powershell
.\setup.ps1                 # crea .venv + instala el motor offline desde vendor/
.\setup.ps1 -Online         # ...o desde PyPI
.\setup.ps1 -Matchering     # también instala el camino opcional de máster por referencia
.\.venv\Scripts\Activate.ps1   # activa, luego corre build.py
```

El `.venv` nunca se commitea — se reconstruye desde `requirements.txt` /
`vendor/` en cada máquina.

---

## Inicio rápido

**1. Pon tus stems en una carpeta** — cualquier cantidad, cualquier nombre. Keel
no exige un set fijo de stems; autodetecta una etiqueta por archivo, y la
corriges después.

**2. Córrelo:**
```powershell
python build.py --stems "C:\ruta\a\mi_cancion" --out out
```
En la primera corrida Keel escribe **`mi_cancion/keel.json`** (mapa autodetectado
archivo -> etiqueta + balance por etiqueta) y renderiza `out/mi_cancion_mix.wav`,
`out/mi_cancion_master.wav` y `out/REPORT.md`.

**3. Corrige las etiquetas y vuelve a correr.** La autodetección es solo una
suposición. Abre `keel.json`, reasigna cualquier archivo a la etiqueta correcta
(**una etiqueta puede tener 1 o 10 archivos** — se balancean como un grupo),
ajusta el balance por etiqueta, y corre el mismo comando otra vez.

### Más formas de correrlo

```powershell
python build.py --stems ./mi_cancion --scan                  # solo (re)escribe keel.json, sin render
python build.py --stems ./mi_cancion --preset loud           # perfil de loudness "house sound"
python build.py --list-presets                               # lista los presets con nombre
python build.py --stems ./mi_cancion --lufs -11 --tp -1      # más fuerte, fija el techo TP
python build.py --stems ./mi_cancion --ref "C:\refs\ref.wav" # igualar una referencia (Matchering)
python build.py --stems ./mi_cancion --mix-only              # detente tras la mezcla
python build.py --stems ./mi_cancion --master-only           # remasteriza una mezcla existente
python build.py --batch "C:\ruta\al\album" --out out         # cada subcarpeta (su propio keel.json)
```

---

## Bajo el capó (el DSP)

- **Loudness:** LUFS integrado vía `pyloudnorm` (ITU-R BS.1770-4, gated a 400 ms).
- **True peak:** un medidor real de sobremuestreo **FIR polifásico 4x** (scipy
  `resample_poly`, Kaiser beta 12) — atrapa picos inter-muestra que un medidor de
  pico de muestra pierde (hasta ~+3 dB).
- **Cadena de máster:** tono (HPF 28 / low-shelf / aire / glue suave) ->
  pre-normalizar -> **soft-clip tanh sobremuestreado** (redondea los transientes
  más filudos) -> **limitador de true peak sobremuestreado 4x** -> normalizar al
  objetivo exacto -> seguro de true peak. El par clip-luego-limita es el enfoque
  fuerte-pero-limpio: el clipper toma la punta para que el limitador quede limpio.
- **Máster por referencia (opcional):** `matchering` iguala el espectro, loudness
  y ancho estéreo de una referencia comercial; la referencia fija el loudness.
- **Por defecto:** máster **-14.0 LUFS / -1.0 dBTP** (óptimo para streaming);
  ancla interna por stem **-20 LUFS**. La cadena llega a -10/-11 limpio si se pide.

Cada corrida de `build.py` escribe `out/REPORT.md`: balance por etiqueta
(LUFS pre/post + ganancia) y el LUFS/dBTP final del máster vs. objetivo — un
vistazo para confirmar que aterrizó.

---

## Plugin (VST3 / AU) — masteriza dentro de tu DAW

Keel también viene como un **plugin de masterización en tiempo real y
autocontenido**: ponlo en tu bus máster, ajústalo contra medidores en vivo y
entrega exportando/bounceando desde tu DAW con el plugin activo — no hay un paso de
render aparte. Corre un port fiel en C++ de la cadena de máster del motor (tono ->
drive Makeup -> soft-clip sobremuestreado -> limitador de true peak 4x), así que lo
que monitoreas es el máster.

- **Formatos:** **VST3** (Windows + macOS) y **AU** (macOS — Logic Pro /
  GarageBand), ambos compilados y probados con pluginval en CI, versionados en
  bloque con la app.
- **Medición, pensada para streaming:** **LUFS integrado + short-term + momentáneo**
  (BS.1770-4) — apunta el Makeup al *integrado*, el número que normalizan Spotify /
  YouTube / Apple — más **rango de loudness (LRA)**, un **historial de loudness** y
  un **historial de reducción de ganancia** con scroll, un **peak-hold de true
  peak**, y un **A/B igualado en loudness** para escuchar el *carácter*, no solo el
  nivel. Carga una referencia para ver su LUFS integrado / true peak junto a los
  medidores en vivo.
- **Flujo / comodidades:** escalado hiDPI, deshacer/rehacer, presets de usuario,
  tooltips + nota de primer uso, automatización del host y etiquetas de
  accesibilidad, y un selector de **sobremuestreo 2x / 4x / 8x** solo del plugin
  (CPU vs. supresión de aliasing).
- **Spec exacto vs. máster en vivo:** el archivo byte-idéntico de **-14 LUFS /
  -1 dBTP** vive en la app / CLI; el plugin cambia esa exactitud por un máster en
  vivo autocontenido (el streaming re-normaliza el loudness de todos modos, y el
  techo de true peak se aplica en vivo, así que los exports quedan seguros de picos).

**Descarga:** toma `Keel-VST3-windows-<ver>.zip` (Windows) o
`Keel-plugins-macos-<ver>.zip` (macOS VST3 + AU) desde la
[última release](https://github.com/fcarvajalbrown/Keel/releases/latest),
descomprime en tu carpeta de plugins y reescanea en tu DAW. Beta sin firmar (aviso
de Gatekeeper / SmartScreen en el primer uso).

---

## Hacia dónde va Keel

Keel empezó como una herramienta de línea de comandos y hoy también viene como una
**app de escritorio (GUI)** y un **plugin VST3 / AU** sobre el mismo motor
determinista — el núcleo DSP está hecho y validado, y los tres front-ends usan una
sola librería compartida (el DSP nunca se bifurca). Lo que falta antes de un **1.0**
estable:

1. **Extensiones de DSP** — las dos opciones de tono sancionadas: un control
   determinista de **ancho estéreo** y una única perilla de **tilt** de banda ancha,
   ambas opcionales y apagadas por defecto para no cambiar el máster por defecto.
2. **Asentar el DSP** — un arnés de paridad Python↔C++ + tests de archivo dorado
   que fijan la cadena en vivo del plugin al motor antes de congelar el DSP.
3. **Lanzamiento** — landing page, firma de código / notarización (quita los avisos
   de SmartScreen / Gatekeeper) y el sello 1.0.

Ver [`ROADMAP.md`](ROADMAP.md) para el plan por etapas y [`docs/adr/`](docs/adr/)
para los registros de decisión (por qué el motor, la configuración, el toolkit, la
licencia y el empaquetado son como son).

---

## Apoya / Dona

Keel es gratis para la gente para la que está hecho, y sigue vivo gracias a las
donaciones. Si te ahorró un cobro de mezcla y máster o una suscripción mensual,
puedes aportar:

- **PayPal:** [Donar](https://www.paypal.com/donate/?business=fcarvajalbrown%40protonmail.com&item_name=Support%20Keel%20development&currency_code=USD)
  (o envía a `fcarvajalbrown@protonmail.com`)
- O usa el botón **Sponsor** arriba en el repo de GitHub.

Las donaciones son voluntarias y financian el desarrollo; no son una compra y no
otorgan derechos comerciales.

## Licencia

Keel se licencia en dos partes.

- **El motor** (librería Python + CLI) es **GNU AGPL-3.0** ([`LICENSE`](LICENSE)) —
  libre y de código abierto. Copyleft: si lo distribuyes o corres una versión
  modificada como servicio de red, debes liberar tu código bajo la AGPL también.
- **La GUI de escritorio** (la app `Keel.exe` / `Keel.app`) es **gratis para uso
  no comercial** y **gratis para músicos que hacen su propia música** — aunque la
  vendas — bajo la PolyForm Noncommercial License más una concesión adicional
  ([`LICENSE-NONCOMMERCIAL.md`](LICENSE-NONCOMMERCIAL.md)).

**No cobramos por la app.** Una **licencia comercial**
([`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md)) — **USD 20, pago único, por
asiento** — es una licencia de uso comercial, requerida solo cuando se usa Keel
para **ganar con material de otras personas o montar un negocio sobre él**:
**sellos discográficos**, **estudios profesionales de mezcla / mastering** e
**ingenieros freelance que hacen trabajo de clientes pagado**, ofrecer Keel como
producto/servicio de pago, redistribuirla dentro de otro producto, o integrar el
motor en un producto de código cerrado sin el copyleft de la AGPL. Ser
profesional no activa el cobro — sí lo hacen el trabajo de clientes pagado o
operar como sello/estudio/negocio.

En una línea: **haz tu propia música con él gratis, incluso como pro vendiendo tus
propios discos; paga solo si montas un negocio sobre él o cobras a clientes con
él.**

## Autor

Felipe Carvajal Brown — fcarvajalbrown@gmail.com

Copyright (C) 2026 Felipe Carvajal Brown.
