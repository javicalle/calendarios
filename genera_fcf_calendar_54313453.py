import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import hashlib
import urllib.parse

# ==========================
# CONFIGURACIÓN
# ==========================

# calendario: https://www.fcf.cat/ca/competicio?temporadaId=22&disciplinaId=19308233&competicioId=58780226&grupId=59348622&tab=calendari
# detalle: https://www.fcf.cat/ca/competicio/acta/4200750
# equipo: https://www.fcf.cat/ca/clubs/40492704/categories/54313453
# partidos: https://www.fcf.cat/api/competition/partidos?grupId=59348622


BASE_URL = "https://www.fcf.cat/"
TEMPORADA = "22"
DISCIPLINA = "19308233"
COMPETICION = "58780226"
GRUPO = "59348622"
EQUIPO = "54313453"

# FAF = "FUNDACIÓ ACADEMIA F. L'HOSPITALET  A"
FAF = "FUNDACIÓ ACADEMIA F."

# CALENDAR_URL = f"{BASE_URL}calendari-equip/{TEMPORADA}/{DISCIPLINA}/{COMPETICION}/{GRUPO}/{EQUIPO}"
PARTIDOS_URL = f"{BASE_URL}api/competition/partidos?grupId={GRUPO}"

DURACION_HORAS = 1.5
ZONA = ZoneInfo("Europe/Madrid")

# función para recuperar los datos del estadio desde la página del acta
def obtener_estadi(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        tablas = soup.find_all("table", class_="acta-table")

        for tabla in tablas:
            th = tabla.find("th")
            if th and th.get_text(strip=True) == "Estadi":
                filas = tabla.find("tbody").find_all("tr")

                # 1️⃣ Nombre del campo
                nombre_campo = filas[0].find("a").get_text(strip=True)

                # 2️⃣ Enlace Google Maps
                enlace_maps = filas[1].find("a").get("href")

                # 3️⃣ Dirección
                direccion = filas[2].find("td").get_text(strip=True)

                return nombre_campo, direccion, enlace_maps

        return "", "", ""

    except Exception:
        return "", "", ""


response = requests.get(CALENDAR_URL)
response.raise_for_status()

# soup = BeautifulSoup(response.text, "html.parser")
jornadas = json.loads(response.text)
calendar = Calendar()
calendar.scale= "GREGORIAN"

# partidos = soup.find("table", class_="fcftable").find('tbody').find_all('tr')
# print("partidos" + str(partidos))

# partido:
# {
#   "CODGRUPO": "59348622",
#   "JORNADA": "1",
#   "CODACTA": "4200750",
#   "CODEQUIPO_CASA": "54316909",
#   "NOMBRE_CASA": "HORTA, U.AT. A",
#   "ESCUDO_CASA": null,
#   "CODEQUIPO_FUERA": "54313453",
#   "NOMBRE_FUERA": "FUNDACIÓ ACADEMIA F. L'HOSPITALET  A",
#   "ESCUDO_FUERA": "00100_0001226166_FAF.png",
#   "CAMPO": "CAMP DE FUTBOL MPAL. HORTA ",
#   "GOLES_CASA": "0",
#   "GOLES_FUERA": "0",
#   "COMIENZO1": "2026-09-27 12:00:00",
#   "CERRADA": "0",
#   "ESTADO": "0",
#   "GRUPO": "GRUP 9",
#   "LATITUD": "41.434667",
#   "LONGITUD": "2.160872",
#   "CODIGO_CAMPO": "384",
#   "CODCLUB_CASA": "1049",
#   "CODCLUB_FUERA": "40492704"
# },

cache_estadis = {}

for jornada in jornadas.values():
  for partido in jornada:

    jornada = partido("JORNADA")
    fecha = partido("COMIENZO1")
    # hora = partido("")
    nombre_campo = partido("CAMPO")
    codigo_campo = partido("CODIGO_CAMPO")
    enlace_maps = f"https://google.com/maps/search/?api=1&query={partido("LATITUD")},{partido("LONGITUD")}"
    
    local = partido("NOMBRE_CASA")
    local_link = partido("")
    visitante = partido("NOMBRE_FUERA")
    visitante_link = partido("")
    acta = partido("CODACTA")
    resultado = partido("GOLES_CASA") + " - " + partido("GOLES_CASA")  # solo si el partido ha acabado (¿ESTADO?)

    # print(f"--> {jornada} {fecha} {hora} {local} {visitante}")

    if FAF not in local and FAF not in visitante:
        continue

    # ---- Fecha con zona horaria ----
    fecha = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
    fecha = fecha.replace(tzinfo=ZONA)

    # ---- Determinar condición ----
    if EQUIPO == partido("CODEQUIPO_CASA"):
        icono = "🏠"
        condicion = "Local"
    else:
        icono = "🚗"
        condicion = "Visitante"

    # ---- Enlace detalle partido ----
    # enlace_detalle = f"{BASE_URL}acta/{TEMPORADA}/{DISCIPLINA}/{COMPETICION}/{GRUPO}/{local_link}/{visitante_link}"
    enlace_detalle = f"{BASE_URL}competicio/acta/{acta}"
    
    # ---- Crear evento ----
    evento = Event()

    evento.name = f"{icono} {local} vs {visitante}"

    evento.begin = fecha
    evento.end = fecha + timedelta(hours=DURACION_HORAS)

    # TODO: revisar como generar la location
    if nombre_campo:
        evento.location = f"{nombre_campo}"

    evento.url = enlace_detalle

    evento.description = (
        f"Jornada {jornada}\n\n"
        f"Condición: {condicion}\n"
        f"Local: {local}\n"
        f"Visitante: {visitante}\n\n"
        f"Campo: {nombre_campo}\n"
        f"  -> f"{BASE_URL}camps/{codigo_campo}"\n"
        f"Detalle del partido:\n{enlace_detalle}"
    )

    uid_source = f"{TEMPORADA}-{jornada}-{local}-{visitante}"
    evento.uid = hashlib.md5(uid_source.encode()).hexdigest()

    # # ---- Recordatorio automático (2 horas antes) ----
    # evento.alarms.append(
    #     {
    #         "action": "display",
    #         "trigger": timedelta(hours=-2),
    #         "description": "Recordatorio partido"
    #     }
    # )

    calendar.events.add(evento)

calendar.extra.append(ContentLine(name="X-WR-CALNAME", value="FAF Infantil S14 A"))
calendar.extra.append(ContentLine(name="X-WR-TIMEZONE", value="Europe/Madrid"))

# with open("faf_calendar.ics", "w", encoding="utf-8") as f:
#     f.writelines(calendar)
with open("site/faf_calendar.ics", "w", encoding="utf-8", newline='') as f:
    f.write(calendar.serialize())

print("Calendario FAF 26/27 generado correctamente.")
