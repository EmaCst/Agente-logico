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

    # 2. Reconstruimos el entorno traduciendo los IDs para el buscador
    for y in range(filas):
        for x in range(columnas):
            celda_web = data.matrix[y][x]
            agente.mapa_clima[y][x] = celda_web.weather  
            
            # CORRECCIÓN DE NOMBRES: 'mapa_objects' cambiado a 'mapa_objetos' para coincidir con tu backend
            if celda_web.id == 2:  
                agente.mapa_objetos[y][x] = 2
                agente.personas_pendientes.append([y, x])
            elif celda_web.id == 8:  
                agente.mapa_objetos[y][x] = 8
                agente.bases.append([y, x])
            elif celda_web.id == 1:
                # Los muros bloquean el paso en el buscador de Python
                agente.mapa_objetos[y][x] = 1 
            elif celda_web.id in [4, 5]:
                # Las baterías son transitables. Les ponemos 0 para que 
                # los métodos buscar_bfs y buscar_a_estrella no las traten como obstáculos.
                agente.mapa_objetos[y][x] = 0 
            else:
                agente.mapa_objetos[y][x] = 0

    # Validaciones de seguridad con respuesta sincronizada al frontend
    if not list(agente.personas_pendientes):
        return {"steps": [], "status": "No has colocado ninguna persona en el mapa interactivo"}
        
    if not list(agente.bases):
        return {"steps": [], "status": "Falta colocar al menos una Zona Segura (Base) en el mapa"}

    # Lista que guardará el estado de TODO el entorno en cada movimiento del robot
    historial_simulacion = []

    # Guardamos el estado inicial (Paso 0) antes de comenzar a movernos
    historial_simulacion.append({
        "agent_pos": [agente.posicion_agente[1], agente.posicion_agente[0]], # [x, y] para React
        "weather_matrix": [list(fila) for fila in agente.mapa_clima]          # Copia exacta del clima actual
    })

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
            agente.mover_agente(paso[0], paso[1]) # Al moverse, altera dinámicamente los climas del mapa
            
            # Registramos la posición y el estado del clima modificado tras este paso
            historial_simulacion.append({
                "agent_pos": [paso[1], paso[0]], 
                "weather_matrix": [list(fila) for fila in agente.mapa_clima] 
            })
            
            if agente.bateria <= 0: 
                break
            
        # Si llega a la persona, recoge al pasajero y busca la base disponible
        if agente.posicion_agente == obj_p and agente.bateria > 0:
            agente.tiene_pasajero = True
            agente.mapa_objetos[obj_p[0]][obj_p[1]] = 0
            
            rutas_b = [agente.buscar_bfs(b) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(b) for b in agente.bases]
            rutas_validas = [r for r in rutas_b if r]
            
            if rutas_validas:
                ruta_base = min(rutas_validas, key=len)
                for paso in ruta_base[1:]:
                    agente.mover_agente(paso[0], paso[1]) # El clima se sigue alterando dinámicamente de regreso
                    
                    # Registramos el avance en el viaje de retorno
                    historial_simulacion.append({
                        "agent_pos": [paso[1], paso[0]],
                        "weather_matrix": [list(fila) for fila in agente.mapa_clima]
                    })
                    
                    if agente.bateria <= 0: 
                        break
                    
                if agente.posicion_agente in agente.bases:
                    agente.tiene_pasajero = False
                    personas_a_procesar.pop(0)
            else:
                personas_a_procesar.pop(0)

    # 4. Validación final del recorrido acumulado
    if len(historial_simulacion) <= 1:
        return {"steps": [], "status": "No se encontraron rutas accesibles para las metas actuales o el agente se quedó sin energía."}

    return {"steps": historial_simulacion, "status": f"Simulación calculada con éxito usando {algoritmo_elegido}"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)