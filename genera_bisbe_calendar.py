import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import hashlib
import urllib.parse

BASE_URL = "https://consell-lh.playoffinformatica.com/"
ID_GRUP = "899"
CALENDAR_URL = BASE_URL + "peticioAjaxCompeticioPublica.php?peticioKey=peticio_competicio_publica_calendari" + "&idGrup=" + ID_GRUP

EQUIPO = "AFA INSTITUT BISBE BERENGUER"
DURACION_HORAS = 1
ZONA = ZoneInfo("Europe/Madrid")

response = requests.get(CALENDAR_URL)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
calendar = Calendar()
calendar.scale= "GREGORIAN"

resultados = soup.find_all("table", class_="table-resultats")
# partidos = soup.find_all("tr", class_="detallEnfrontament")

for resultado in resultados:
    jornada = resultado.find("caption").get_text(strip=True)
    partidos = resultado.find_all("tr", class_="detallEnfrontament")

    for partido in partidos:
    
        fecha_raw = partido.find("td", class_="data").get_text(strip=True)
        local = partido.find("td", class_="local").get_text(" ", strip=True)
        visitante = partido.find("td", class_="visitant").get_text(" ", strip=True)
        lugar_raw = partido.find("td", class_="lloc").get_text("\n", strip=True)
    
        if EQUIPO not in local and EQUIPO not in visitante:
            continue
    
        # ---- Fecha con zona horaria ----
        fecha_raw = fecha_raw.replace("h", "")
        fecha = datetime.strptime(fecha_raw, "%d-%m-%Y %H:%M")
        fecha = fecha.replace(tzinfo=ZONA)
    
        # ---- Determinar condición ----
        if EQUIPO in local:
            icono = "🏠"
            condicion = "Local"
        else:
            icono = "🚗"
            condicion = "Visitante"
    
        # ---- Extraer nombre pabellón y dirección ----
        partes_lugar = [p.strip() for p in lugar_raw.split("\n") if p.strip()]
    
        direccion = partes_lugar[0] if len(partes_lugar) > 0 else ""
        pabellon = partes_lugar[2] if len(partes_lugar) > 1 else direccion
    
        # Enlace Google Maps con dirección completa
        maps_query = urllib.parse.quote(direccion)
        enlace_maps = f"https://www.google.com/maps/search/?api=1&query={maps_query}"
    
        # ---- Enlace detalle partido ----
        data_href = partido.get("data-href")
        enlace_detalle = BASE_URL + data_href if data_href else BASE_URL
    
        # ---- Crear evento ----
        evento = Event()
    
        evento.name = f"{icono} {local} vs {visitante}"
    
        evento.begin = fecha
        evento.end = fecha + timedelta(hours=DURACION_HORAS)
    
        # Ubicación visible en calendario = nombre pabellón, dirección
        evento.location = f"{pabellon}, {direccion}"
    
        evento.url = enlace_detalle
    
        evento.description = (
            f"{jornada} liga escolar\n\n"
            f"Condición: {condicion}\n"
            f"Local: {local}\n"
            f"Visitante: {visitante}\n\n"
            f"Pabellón: {pabellon}\n"
            f"Dirección: {direccion}\n"
            f"Mapa: {enlace_maps}\n\n"
            f"Detalle del partido:\n{enlace_detalle}"
        )
    
        # ---- UID estable basado en idEvent (MEJOR DETECCIÓN CAMBIOS) ----
        if data_href and "idEvent=" in data_href:
            id_event = data_href.split("idEvent=")[1]
            evento.uid = f"{id_event}@bisbe-berenguer"
        else:
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


calendar.extra.append(ContentLine(name="X-WR-CALNAME", value="Futbol Sala Bisbe Berenguer 25/26"))
calendar.extra.append(ContentLine(name="X-WR-TIMEZONE", value="Europe/Madrid"))

# with open("site/bisbe_calendar.ics", "w", encoding="utf-8") as f:
#     f.writelines(calendar)
with open("site/bisbe_calendar.ics", "w", encoding="utf-8", newline='') as f:
    f.write(calendar.serialize())

print("Calendario PRO generado correctamente.")
