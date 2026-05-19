# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

# Importamos tu clase lógica desde el archivo hermano
from AgenteLogico import AgenteRescate 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos para estructurar la información que envía la interfaz web
class Cell(BaseModel):
    id: int
    weather: str

class Mission(BaseModel):
    matrix: List[List[Cell]]
    start_pos: List[int]
    algorithm: str = "A*"

@app.post("/solve")
async def solve(data: Mission):
    filas = len(data.matrix)
    columnas = len(data.matrix[0])
    
    # Inicializamos el agente con las dimensiones solicitadas
    agente = AgenteRescate(filas=filas, columnas=columnas)
    agente.personas_pendientes = []
    agente.bases = []
    
    # Lista local para registrar dónde colocó el usuario las baterías en el Front
    baterias_disponibles = []
    
    # Mapeo de la posición inicial del agente de la interfaz [X, Y] a la matriz [Fila, Columna]
    agente.posicion_agente = [data.start_pos[1], data.start_pos[0]] 

    # Inyección exacta del escenario congelado del Frontend al Backend
    for y in range(filas):
        for x in range(columnas):
            celda_web = data.matrix[y][x]
            agente.mapa_clima[y][x] = celda_web.weather  
            
            if celda_web.id == 2:  
                agente.mapa_objetos[y][x] = 2
                agente.personas_pendientes.append([y, x])
            elif celda_web.id == 8:  
                agente.mapa_objetos[y][x] = 8
                agente.bases.append([y, x])
            elif celda_web.id == 1:
                agente.mapa_objetos[y][x] = 1 
            elif celda_web.id in [4, 5]:
                agente.mapa_objetos[y][x] = 0 
                # Registramos el consumible en el radar del planificador de energía
                baterias_disponibles.append({"pos": [y, x], "tipo": celda_web.id})
            else:
                agente.mapa_objetos[y][x] = 0

    if not list(agente.personas_pendientes):
        return {"steps": [], "status": "No has colocado ninguna persona en el mapa interactivo"}
        
    if not list(agente.bases):
        return {"steps": [], "status": "Falta colocar al menos una Zona Segura (Base) en el mapa"}

    historial_simulacion = []

    # Frame inicial (Turno 0) que congela las condiciones con las que inicia el mapa
    historial_simulacion.append({
        "agent_pos": [agente.posicion_agente[1], agente.posicion_agente[0]],
        "weather_matrix": [list(fila) for fila in agente.mapa_clima],
        "bateria": agente.bateria  
    })

    personas_a_procesar = list(agente.personas_pendientes)
    algoritmo_elegido = data.algorithm

    # =========================================================================
    # BUCLE PRINCIPAL CON RECALCULACIÓN PASO A PASO (SIN CICLOS FOR CIEGOS)
    # =========================================================================
    while personas_a_procesar and agente.bateria > 0:
        
        # 1. EVALUAR PRIORIDAD CRÍTICA DE BATERÍA (Batería <= 40)
        if agente.bateria <= 40 and baterias_disponibles:
            def distancia(b):
                return abs(agente.posicion_agente[0] - b["pos"][0]) + abs(agente.posicion_agente[1] - b["pos"][1])
            
            bateria_cercana = min(baterias_disponibles, key=distancia)
            pos_bat = bateria_cercana["pos"]
            
            # Buscamos la ruta hacia la BATERÍA en base al clima dinámico actual
            ruta_bat = agente.buscar_bfs(pos_bat) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(pos_bat)
            
            if ruta_bat and len(ruta_bat) > 1:
                # AVANZAMOS UN SOLO PASO HACIA LA BATERÍA
                paso = ruta_bat[1]
                agente.mover_agente(paso[0], paso[1])
                
                if agente.posicion_agente == pos_bat:
                    if bateria_cercana["tipo"] == 5: agente.bateria = 100
                    elif bateria_cercana["tipo"] == 4: agente.bateria = min(100, agente.bateria + 40)
                    baterias_disponibles.remove(bateria_cercana)
                
                historial_simulacion.append({
                    "agent_pos": [paso[1], paso[0]], 
                    "weather_matrix": [list(fila) for fila in agente.mapa_clima],
                    "bateria": max(0, agente.bateria)
                })
                continue # Forzamos reinicio del ciclo general para evaluar con el nuevo estado de energía

        # 2. DEFINIR LA RUTA SEGÚN EL OBJETIVO ACTUAL (Hacia Persona o Base)
        obj_p = personas_a_procesar[0]
        
        if agente.tiene_pasajero:
            rutas_b = [agente.buscar_bfs(b) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(b) for b in agente.bases]
            rutas_validas = [r for r in rutas_b if r]
            ruta_actual = min(rutas_validas, key=len) if rutas_validas else None
        else:
            ruta_actual = agente.buscar_bfs(obj_p) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(obj_p)

        # Evaluar si se llegó al destino, si está obstruido o si se debe cambiar de estado
        if not ruta_actual or len(ruta_actual) <= 1:
            if agente.tiene_pasajero and agente.posicion_agente in agente.bases:
                agente.tiene_pasajero = False
                personas_a_procesar.pop(0) # Ciudadano entregado a salvo en zona segura
            elif not agente.tiene_pasajero and agente.posicion_agente == obj_p:
                agente.tiene_pasajero = True
                agente.mapa_objetos[obj_p[0]][obj_p[1]] = 0 # Pasajero aborda el vehículo de rescate
            else:
                personas_a_procesar.pop(0) # Inalcanzable por clima o muros, se descarta
            continue

        # 3. AVANZAR UN ÚNICO PASO (Detección de Cambios Meteorológicos en Vivo)
        siguiente_paso = ruta_actual[1]
        agente.mover_agente(siguiente_paso[0], siguiente_paso[1]) 
        
        # Control de recarga casual en el camino (por si pisa una batería sin estar en modo crítico)
        for b in list(baterias_disponibles):
            if agente.posicion_agente == b["pos"]:
                if b["tipo"] == 5: agente.bateria = 100
                elif b["tipo"] == 4: agente.bateria = min(100, agente.bateria + 40)
                baterias_disponibles.remove(b)

        # Capturamos el frame exacto del entorno modificado tras dar este paso
        historial_simulacion.append({
            "agent_pos": [siguiente_paso[1], siguiente_paso[0]], 
            "weather_matrix": [list(fila) for fila in agente.mapa_clima],
            "bateria": max(0, agente.bateria)
        })

    if len(historial_simulacion) <= 1:
        return {"steps": [], "status": "No se encontraron rutas accesibles o el agente se quedó sin energía."}

    return {"steps": historial_simulacion, "status": f"Simulación calculada con éxito usando {algoritmo_elegido}"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)