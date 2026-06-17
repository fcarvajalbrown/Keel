# Keel: programé gratis la mezcla y masterización que la industria te arrienda a 20 dólares al mes

Soy ingeniero de software y vivo, como la mayoría en este país, contando los
pesos hasta fin de mes. En el rato libre construyo herramientas para lo público
y las dejo gratis, de código abierto, porque tengo la idea fija de que lo que
sirve no debería venir con candado. Hace un tiempo me puse a averiguar cuánto
cuesta hoy que una canción suene "como en Spotify", y me topé con la trampa de
siempre: servicios de mezcla y *mastering* con "IA" que cobran veinte dólares al
mes. En Chile, veinte dólares al mes es plata de verdad para quien recién empieza.

Así que hice lo único que sé hacer bien. Me senté a escribir código.

## No es IA, es matemática que puedes leer

La industria del audio encontró la palabra mágica, la pegó en un botón y la
transformó en suscripción. "IA" para subirte el volumen, "IA" para que tu tema
"compita". Hay que ser justo: varias de esas herramientas funcionan, y a un
profesional con oficio le ahorran horas de pega. Pero a una banda de cabros que
recién parte no le venden una herramienta, le venden un peaje mensual y una caja
negra que nadie puede abrir.

Keel es lo contrario. No tiene IA, no adivina, no inventa. Es *código*
determinista: las mismas pistas entran, el mismo *master* sale, todas las veces.
Está construido sobre el estándar de *loudness* que usa la industria de verdad,
la norma ITU-R BS.1770-4, la misma de Spotify y YouTube. No es magia. Es
aritmética honesta que cualquiera puede leer en el repositorio, línea por línea.

## Cómo funciona, sin humo

Le entregas una carpeta de pistas ya terminadas, con sus efectos puestos. Keel
mide cada grupo de pistas, las equilibra por volumen percibido, las suma en una
mezcla estéreo y después masteriza esa mezcla: limpia los graves que sobran,
redondea los *peaks* más filudos con un *soft-clip* sobremuestreado, controla los
*true peaks* con un limitador a 4x y deja el tema en exactamente -14 LUFS, el
volumen óptimo para *streaming*, con el *true peak* siempre bajo el techo de -1
dBTP. Sin distorsión, sin reventar. Lo probé en multipistas reales, desde un kit
de batería crudo de 18 canales hasta un set ya pre-mezclado, y aguantó parejo.

No reemplaza a un ingeniero de mezcla con oído y años de oficio, y no lo
pretende. Un buen ingeniero cobra por canción, y lo vale, pero esa cuenta es
justo la que una banda de adolescentes o un proyecto de hobby no puede pagar.
Keel resuelve el escalón de abajo, el que hoy es un muro: que tu canción suene
pareja y a volumen competitivo sin una mensualidad y sin regalarle tu música a un
algoritmo cerrado.

## Por qué es gratis

Porque las herramientas para hacer música no deberían ser un peaje. El motor de
Keel es *open source* y va a seguir siéndolo. Si más adelante armo una aplicación
con ventana para quien no quiere tocar un terminal, costará una vez, barata, no
todos los meses hasta el fin de los tiempos. La diferencia con la suscripción no
es el precio. Es a quién sirve.

No soy estrella de nada. Programo estas cosas en el tiempo que me queda, y las
dejo abiertas, para que una banda de cabros en una pieza no tenga que elegir
entre comer y sonar.

Como cantaba Víctor Jara, "yo no canto por cantar ni por tener buena voz, canto
porque la guitarra tiene sentido y razón". Una herramienta también tiene sentido
cuando le sirve justo al que no tiene plata para comprarla. Para el resto, ya hay
de sobra.
