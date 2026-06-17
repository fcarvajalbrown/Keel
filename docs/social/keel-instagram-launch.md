# Keel — kit de lanzamiento para Instagram

Material para publicar el lanzamiento (pre-alpha) en Instagram.

## Recursos

- **Video (para editar):** `assets/keel-launch.mp4` (9:16, 1080x1920, ~19 s,
  H.264). Hecho para **loopear sin corte**: termina fundiéndose a negro = el
  primer frame, así Instagram lo repite (los replays suman watch time).
- **Listo para publicar (con audio):** `out/keel-launch-final.mp4` — el video +
  el audio ya mezclados, post-ready, sin pasar por un editor. No se commitea
  (lleva audio). Regenéralo muxeando con el ffmpeg de imageio-ffmpeg:
  `ffmpeg -y -i assets/keel-launch.mp4 -i out/keel_instagram_audio.wav -c:v copy -c:a aac -b:a 192k -shortest out/keel-launch-final.mp4`
- **GIF (preview):** `assets/keel-launch.gif` (720x1280) para vista rápida /
  README. En un editor de video usa el MP4 (el GIF tiene rarezas de timing).
- **Audio:** `out/keel_instagram_audio.wav` (19 s, 44.1 kHz, estéreo) — un
  extracto del máster de tu propio tema (song3) con una envolvente que sube de
  ~-22 a -14 LUFS (sincronizada con el contador) y luego **baja con fade-out**
  en el outro. No se commitea (es audio). `python scripts/make_launch_audio.py`.
- **Cinco escenas (texto en pantalla):** 1) reveal del logo —
  "Gratis · Abierta · Determinista"; 2) "De tus stems terminados" -> chips
  (drums/bajo/guitarra/voz/synth) -> "una mezcla y un máster"; 3)
  "Balance + master, en un clic" + el contador a -14.0 LUFS + "true peak -1.0
  dBTP · sin clipping"; 4) "Descárgalo gratis"; 5) outro: el mismo gráfico de
  loudness en reversa (-14 -> -22) con fade-out del audio, y funde a negro.
- Regenerar el video: `python scripts/make_launch_video.py` (saca MP4 + GIF).

## Caption (copiar y pegar)

> Mezcla y masteriza tu música gratis. Sin IA, sin suscripción.
>
> Programé Keel para que cualquier músico pueda sonar "como en streaming" sin
> pagar un peaje mensual. Le das tus stems ya terminados y te devuelve una
> mezcla balanceada y un máster listo: volumen exacto a -14 LUFS, true peak
> seguro, sin clipping. Determinista: las mismas pistas entran, el mismo máster
> sale, siempre. Código abierto, sin caja negra.
>
> Gratis para músicos. Descárgalo para Windows y macOS desde el link en mi
> perfil (releases de GitHub).
>
> Pre-alpha: se agradece el feedback.

## Hashtags

SEO 2026: la **caption con palabras clave pesa más que los hashtags**, y lo
recomendado son **3-5 hashtags relevantes** (no 30). Rota el set entre posts.

**Recomendados (5):**
`#produccionmusical #mastering #mezcla #homestudio #musicaindependiente`

**Pool para rotar:**
`#musicproducer #mixing #musicproduction #masterizacion #bedroomproducer`
`#audioengineer #estudiocasero #musicachilena #softwarelibre #lufs`

## Notas para publicar

- **Formato:** 9:16, ~19 s. Engancha en los primeros ~2 s (el reveal del logo);
  si quieres, agrega un texto-hook al inicio en tu editor.
- **Loop:** el MP4 ya cierra en negro = primer frame, así que loopea sin corte.
  Déjalo repetir; los replays suman watch time (un Reel corto que se reve varias
  veces rinde más que uno largo de una pasada).
- **Audio:** monta `assets/keel-launch.mp4` + `out/keel_instagram_audio.wav` en
  la misma línea de tiempo (misma duración, ya sincronizados) y exporta. Suena
  tu propio máster; un audio en tendencia daría más alcance pero pierdes el sync.
- **Link:** el link directo de descarga no es cliqueable en captions — pon
  "link en bio" apuntando a la página de releases.
- Front-load: la primera línea de la caption es la más importante para el
  algoritmo; deja ahí el gancho.
