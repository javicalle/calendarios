import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
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

response = requests.get(CALENDAR_URL)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
calendar = Calendar()

# resultados = soup.find_all("table", class_="fcftable")
partidos = soup.find("table", class_="fcftable").find('tbody').find_all('tr')
# print("partidos" + str(partidos))

# partidos = soup.select("table.fcftable tbody tr")

for partido in partidos:

    cols = partido.find_all("td")  

    jornada = cols[0].get_text(strip=True)
    fecha = cols[1].get_text(strip=True)
    hora = cols[2].get_text(strip=True)
    local = cols[3].a.get_text(strip=True)
    local_link = cols[3].a.get('href').replace(f"{BASE_URL}equip/{TEMPORADA}/", '')
    visitante = cols[4].a.get_text(strip=True)
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

    # # ---- Extraer nombre pabellón y dirección ----
    # partes_lugar = [p.strip() for p in lugar_raw.split("\n") if p.strip()]

    # direccion = partes_lugar[0] if len(partes_lugar) > 0 else ""
    # pabellon = partes_lugar[2] if len(partes_lugar) > 1 else direccion

    # # Enlace Google Maps con dirección completa
    # maps_query = urllib.parse.quote(direccion)
    # enlace_maps = f"https://www.google.com/maps/search/?api=1&query={maps_query}"

    # ---- Enlace detalle partido ----
    enlace_detalle = f"{BASE_URL}acta/{TEMPORADA}/{DISCIPLINA}/{COMPETICION}/{GRUPO}/{local_link}/{visitante_link}"

    # ---- Crear evento ----
    evento = Event()

    evento.name = f"{icono} {local} vs {visitante}"

    evento.begin = fecha
    evento.end = fecha + timedelta(hours=DURACION_HORAS)

    # # Ubicación visible en calendario = nombre pabellón
    # evento.location = pabellon

    evento.url = enlace_detalle

    evento.description = (
        f"Jornada {jornada}\n\n"
        f"Condición: {condicion}\n"
        f"Local: {local}\n"
        f"Visitante: {visitante}\n\n"
        f"Detalle del partido:\n{enlace_detalle}"
    )

    uid_source = f"{local}-{visitante}"
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

with open("faf_calendar.ics", "w", encoding="utf-8") as f:
    f.writelines(calendar)

print("Calendario FAF generado correctamente.")
