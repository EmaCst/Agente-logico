from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

# Importamos tu clase original intacta desde tu otro archivo
from AgenteLogico import AgenteRescate 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    
    agente = AgenteRescate(filas=filas, columnas=columnas)
    agente.personas_pendientes = []
    agente.bases = []
    
    # NUEVO: Lista para registrar dónde colocó el usuario las baterías en el Front
    baterias_disponibles = []
    
    agente.posicion_agente = [data.start_pos[1], data.start_pos[0]] 

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
                # NUEVO: Guardamos el tipo de batería (4 o 5) y su posición [fila, columna]
                baterias_disponibles.append({"pos": [y, x], "tipo": celda_web.id})
            else:
                agente.mapa_objetos[y][x] = 0

    if not list(agente.personas_pendientes):
        return {"steps": [], "status": "No has colocado ninguna persona en el mapa interactivo"}
        
    if not list(agente.bases):
        return {"steps": [], "status": "Falta colocar al menos una Zona Segura (Base) en el mapa"}

    historial_simulacion = []

    historial_simulacion.append({
        "agent_pos": [agente.posicion_agente[1], agente.posicion_agente[0]],
        "weather_matrix": [list(fila) for fila in agente.mapa_clima],
        "bateria": agente.bateria  
    })

    personas_a_procesar = list(agente.personas_pendientes)
    algoritmo_elegido = data.algorithm

    # Bucle principal de la simulación
    while personas_a_procesar and agente.bateria > 0:
        
        # =========================================================================
        # NUEVA LÓGICA DE DETECCIÓN CRÍTICA DE BATERÍA
        # =========================================================================
        # Si la batería baja de 40 y quedan consumibles en el mapa, recalculamos prioridad
        if agente.bateria <= 40 and baterias_disponibles:
            # Encontramos la batería numéricamente más cercana usando distancia Manhattan
            def distancia(b):
                return abs(agente.posicion_agente[0] - b["pos"][0]) + abs(agente.posicion_agente[1] - b["pos"][1])
            
            bateria_cercana = min(baterias_disponibles, key=distancia)
            pos_bat = bateria_cercana["pos"]
            
            # Buscamos la ruta hacia la BATERÍA en lugar de la persona
            ruta_bat = agente.buscar_bfs(pos_bat) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(pos_bat)
            
            if ruta_bat:
                # El agente camina hacia la batería
                for paso in ruta_bat[1:]:
                    agente.mover_agente(paso[0], paso[1])
                    
                    # Verificación si tu AgenteLogico no sube la batería automáticamente al pisarla:
                    if agente.posicion_agente == pos_bat:
                        # Forzamos la recarga en la simulación según el tipo
                        if bateria_cercana["tipo"] == 5:
                            agente.bateria = 100
                        elif bateria_cercana["tipo"] == 4:
                            agente.bateria = min(100, agente.bateria + 40)
                    
                    historial_simulacion.append({
                        "agent_pos": [paso[1], paso[0]], 
                        "weather_matrix": [list(fila) for fila in agente.mapa_clima],
                        "bateria": agente.bateria
                    })
                    if agente.bateria <= 0: break
                
                # Una vez consumida, la removemos de las existencias del mapa
                baterias_disponibles.remove(bateria_cercana)
                continue # Regresa al inicio del while para reevaluar la ruta a la persona con nueva energía
        # =========================================================================

        # Si tiene buena batería, sigue con su plan original de rescate
        obj_p = personas_a_procesar[0]
        ruta_persona = agente.buscar_bfs(obj_p) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(obj_p)
            
        if not ruta_persona:
            personas_a_procesar.pop(0)
            continue
            
        for paso in ruta_persona[1:]:
            agente.mover_agente(paso[0], paso[1]) 
            
            # Control de recarga casual (por si pisa una batería de camino a la persona sin estar en modo crítico)
            for b in list(baterias_disponibles):
                if agente.posicion_agente == b["pos"]:
                    if b["tipo"] == 5: agente.bateria = 100
                    elif b["tipo"] == 4: agente.bateria = min(100, agente.bateria + 40)
                    baterias_disponibles.remove(b)

            historial_simulacion.append({
                "agent_pos": [paso[1], paso[0]], 
                "weather_matrix": [list(fila) for fila in agente.mapa_clima],
                "bateria": max(0, agente.bateria)
            })
            if agente.bateria <= 0: break
            
        if agente.posicion_agente == obj_p and agente.bateria > 0:
            agente.tiene_pasajero = True
            agente.mapa_objetos[obj_p[0]][obj_p[1]] = 0
            
            rutas_b = [agente.buscar_bfs(b) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(b) for b in agente.bases]
            rutas_validas = [r for r in rutas_b if r]
            
            if rutas_validas:
                ruta_base = min(rutas_validas, key=len)
                for paso in ruta_base[1:]:
                    agente.mover_agente(paso[0], paso[1]) 
                    
                    # Control de recarga casual en el viaje de regreso
                    for b in list(baterias_disponibles):
                        if agente.posicion_agente == b["pos"]:
                            if b["tipo"] == 5: agente.bateria = 100
                            elif b["tipo"] == 4: agente.bateria = min(100, agente.bateria + 40)
                            baterias_disponibles.remove(b)

                    historial_simulacion.append({
                        "agent_pos": [paso[1], paso[0]],
                        "weather_matrix": [list(fila) for fila in agente.mapa_clima],
                        "bateria": max(0, agente.bateria)
                    })
                    if agente.bateria <= 0: break
                    
                if agente.posicion_agente in agente.bases:
                    agente.tiene_pasajero = False
                    personas_a_procesar.pop(0)
            else:
                personas_a_procesar.pop(0)

    if len(historial_simulacion) <= 1:
        return {"steps": [], "status": "No se encontraron rutas accesibles o el agente se quedó sin energía."}

    return {"steps": historial_simulacion, "status": f"Simulación calculada con éxito usando {algoritmo_elegido}"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)