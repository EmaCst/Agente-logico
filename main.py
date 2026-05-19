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
    
    # 1. Instanciamos tu agente original con las dimensiones del mapa actual
    agente = AgenteRescate(filas=filas, columnas=columnas)
    
    # Vaciamos los datos que genera el constructor aleatoriamente 
    # para usar la información real que configuraste en la pantalla
    agente.personas_pendientes = []
    agente.bases = []
    
    # Adaptación de coordenadas: de [x, y] de la interfaz a [fila, columna] del backend
    agente.posicion_agente = [data.start_pos[1], data.start_pos[0]] 

    # 2. Reconstruimos el entorno usando los nombres de tus variables originales
    for y in range(filas):
        for x in range(columnas):
            celda_web = data.matrix[y][x]
            agente.mapa_objetos[y][x] = celda_web.id  
            agente.mapa_clima[y][x] = celda_web.weather  
            
            if celda_web.id == 2:  
                agente.personas_pendientes.append([y, x])
            elif celda_web.id == 8:  
                agente.bases.append([y, x])

    if not agente.personas_pendientes:
        return {"ruta": [], "error": "No has colocado ninguna persona en el mapa"}

    ruta_python = [list(agente.posicion_agente)]
    personas_a_procesar = list(agente.personas_pendientes)
    algoritmo_elegido = data.algorithm

    # 3. Simulación del recorrido paso a paso aplicando tus reglas de negocio
    while personas_a_procesar and agente.bateria > 0:
        obj_p = personas_a_procesar[0]
        
        if algoritmo_elegido == "BFS":
            ruta_persona = agente.buscar_bfs(obj_p)
        else:
            ruta_persona = agente.buscar_a_estrella(obj_p)
            
        if not ruta_persona:
            personas_a_procesar.pop(0)
            continue
            
        # El agente avanza hacia la persona consumiendo batería bajo tus lógicas climáticas
        for paso in ruta_persona[1:]:
            ruta_python.append(list(paso))
            agente.mover_agente(paso[0], paso[1])
            if agente.bateria <= 0: break
            
        # Si llega a la persona, recoge al pasajero y busca la base disponible
        if agente.posicion_agente == obj_p and agente.bateria > 0:
            agente.tiene_pasajero = True
            agente.mapa_objetos[obj_p[0]][obj_p[1]] = 0
            
            rutas_b = [agente.buscar_bfs(b) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(b) for b in agente.bases]
            rutas_validas = [r for r in rutas_b if r]
            
            if rutas_validas:
                ruta_base = min(rutas_validas, key=len)
                for paso in ruta_base[1:]:
                    ruta_python.append(list(paso))
                    agente.mover_agente(paso[0], paso[1])
                    if agente.bateria <= 0: break
                    
                if agente.posicion_agente in agente.bases:
                    agente.tiene_pasajero = False
                    personas_a_procesar.pop(0)
            else:
                personas_a_procesar.pop(0)

    # 4. Traducción para la interfaz: Retornamos las coordenadas como [x, y] para la animación
    ruta_frontend = [[paso[1], paso[0]] for paso in ruta_python]
    
    if len(ruta_frontend) <= 1:
        return {"ruta": [], "error": "No se encontraron rutas accesibles para las metas actuales."}

    return {"ruta": ruta_frontend, "error": None}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)