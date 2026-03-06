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

# calendario: https://www.fcf.cat/calendari-equip/2526/futbol-11/preferent-infantil-s14/grup-2/fundacio-academia-f-lhospitalet-a
# detalle: https://www.fcf.cat/acta/2526/futbol-11/preferent-infantil-s14/grup-2/pi14/lhospitalet-centre-esports-b/pi14/fundacio-academia-f-lhospitalet-a
# equipo: https://www.fcf.cat/equip/2526/pi14/fundacio-academia-f-lhospitalet-a


BASE_URL = "https://www.fcf.cat/"
TEMPORADA = "2526"
DISCIPLINA = "futbol-11"
COMPETICION = "preferent-infantil-s14"
GRUPO = "grup-2"
EQUIPO = "fundacio-academia-f-lhospitalet-a"

# FAF = "FUNDACIÓ ACADEMIA F. L\'HOSPITALET  A"
FAF = "FUNDACIÓ ACADEMIA F."

CALENDAR_URL = f"{BASE_URL}calendari-equip/{TEMPORADA}/{DISCIPLINA}/{COMPETICION}/{GRUPO}/{EQUIPO}"

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

soup = BeautifulSoup(response.text, "html.parser")
calendar = Calendar()

# resultados = soup.find_all("table", class_="fcftable")
partidos = soup.find("table", class_="fcftable").find('tbody').find_all('tr')
# print("partidos" + str(partidos))

# partidos = soup.select("table.fcftable tbody tr")

cache_estadis = {}

for partido in partidos:

    cols = partido.find_all("td")  

    jornada = cols[0].get_text(strip=True)
    fecha = cols[1].get_text(strip=True)
    hora = cols[2].get_text(strip=True)
    local = cols[3].a.get_text(strip=True).replace("L\'HOSPITALET", "L'HOSPITALET")
    local_link = cols[3].a.get('href').replace(f"{BASE_URL}equip/{TEMPORADA}/", '')
    visitante = cols[4].a.get_text(strip=True).replace("L\'HOSPITALET", "L'HOSPITALET")
    visitante_link = cols[4].a.get('href').replace(f"{BASE_URL}equip/{TEMPORADA}/", '')
    resultado = cols[5].get_text(strip=True)

    # print(f"--> {jornada} {fecha} {hora} {local} {visitante}")

    if FAF not in local and FAF not in visitante:
        continue

    # ---- Fecha con zona horaria ----
    fecha_raw = f"{fecha} {hora}"
    fecha = datetime.strptime(fecha_raw, "%d-%m-%Y %H:%M")
    fecha = fecha.replace(tzinfo=ZONA)

    # ---- Determinar condición ----
    if FAF in local:
        icono = "🏠"
        condicion = "Local"
    else:
        icono = "🚗"
        condicion = "Visitante"

    # ---- Enlace detalle partido ----
    enlace_detalle = f"{BASE_URL}acta/{TEMPORADA}/{DISCIPLINA}/{COMPETICION}/{GRUPO}/{local_link}/{visitante_link}"

    # ---- Extraer nombre del campo y dirección ----
    # nombre_campo, direccion, enlace_maps = obtener_estadi(enlace_detalle)

    if local not in cache_estadis:  # suponemos que el campo siempre depende solo del equipo local
        cache_estadis[local] = obtener_estadi(enlace_detalle)

    nombre_campo, direccion, enlace_maps = cache_estadis[local]

    
    # ---- Crear evento ----
    evento = Event()

    evento.name = f"{icono} {local} vs {visitante}"

    evento.begin = fecha
    evento.end = fecha + timedelta(hours=DURACION_HORAS)

    if nombre_campo:
        evento.location = f"{nombre_campo}, {direccion}"

    evento.url = enlace_detalle

    evento.description = (
        f"Jornada {jornada}\n\n"
        f"Condición: {condicion}\n"
        f"Local: {local}\n"
        f"Visitante: {visitante}\n\n"
        f"Campo: {nombre_campo}\n"
        f"Dirección: {direccion}\n"
        f"Google Maps: {enlace_maps}\n\n"
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

print("Calendario FAF generado correctamente.")
