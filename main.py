# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

# Importamos tu clase lógica desde el archivo hermano
try:
    from AgenteLogico import AgenteRescate
except ImportError:
    # Esto es por si el archivo tiene un nombre ligeramente distinto o está en subcarpetas
    raise RuntimeError("No se encontró el archivo AgenteLogico.py en el mismo directorio.")

app = FastAPI(title="Rescue System UMG - Backend", version="1.0.0")

# Configuración de CORS alineada para desarrollo local con React (Vite / CRA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, cámbialo por el dominio específico de tu front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# MODELOS DE PYDANTIC (Estructura espejo de lo que envía Axios)
# =========================================================================
class Cell(BaseModel):
    id: int
    weather: str

class Mission(BaseModel):
    matrix: List[List[Cell]]
    start_pos: List[int]  # [X, Y] enviado desde React
    algorithm: str = "A*"

# =========================================================================
# ENDPOINT PRINCIPAL: SOLVE (CORREGIDO)
# =========================================================================
@app.post("/solve")
async def solve(data: Mission):
    if not data.matrix or not data.matrix[0]:
        return {"steps": [], "status": "La matriz enviada está vacía o corrupta."}

    filas = len(data.matrix)
    columnas = len(data.matrix[0])
    
    agente = AgenteRescate(filas=filas, columnas=columnas)
    
    # 1. Identificar mapa y cargar recuerdos
    if hasattr(agente, 'identificar_y_cargar_mapa'):
        agente.identificar_y_cargar_mapa(data.matrix)
    
    agente.personas_pendientes = []
    agente.bases = []
    baterias_disponibles = []
    
    # Invertimos coordenadas [X, Y] de la web a [Y, X] de tu backend
    agente.posicion_agente = [data.start_pos[1], data.start_pos[0]] 

    # 2. Inyección usando 'mapa_objetos' en español
    for y in range(filas):
        for x in range(columnas):
            celda_web = data.matrix[y][x]
            agente.mapa_clima[y][x] = celda_web.weather  
            
            if celda_web.id == 2:  # Persona
                agente.mapa_objetos[y][x] = 2
                agente.personas_pendientes.append([y, x])
                
            elif celda_web.id == 8:  # Zona Segura / Base
                agente.mapa_objetos[y][x] = 8
                agente.bases.append([y, x])
                
            elif celda_web.id == 1:  # Muro
                agente.mapa_objetos[y][x] = 1
                
            elif celda_web.id in [4, 5]:  # Baterías
                # Inicialmente el terreno está libre, pero guardamos su posición de recarga
                agente.mapa_objetos[y][x] = 0
                baterias_disponibles.append({"pos": [y, x], "tipo": celda_web.id})
            else:
                agente.mapa_objetos[y][x] = 0

    if not agente.personas_pendientes:
        return {"steps": [], "status": "No has colocado ninguna persona en el mapa interactivo."}
        
    if not agente.bases:
        return {"steps": [], "status": "Falta colocar al menos una Zona Segura (Base) en el mapa."}

    historial_simulacion = []

    # Frame inicial (Turno 0)
    historial_simulacion.append({
        "agent_pos": [agente.posicion_agente[1], agente.posicion_agente[0]],
        "weather_matrix": [list(fila) for fila in agente.mapa_clima],
        "bateria": agente.bateria  
    })

    personas_a_procesar = list(agente.personas_pendientes)
    algoritmo_elegido = data.algorithm

    # Bucle Principal de Búsqueda
    while personas_a_procesar and agente.bateria > 0:
        obj_p = personas_a_procesar[0]
        meta_actual = None
        
        if getattr(agente, 'tiene_pasajero', False):
            rutas_b = [
                agente.buscar_bfs(b) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(b) 
                for b in agente.bases
            ]
            rutas_validas = [r for r in rutas_b if r]
            if rutas_validas:
                meta_actual = min(rutas_validas, key=len)[-1]
        else:
            meta_actual = obj_p

        # Ejecución de los algoritmos
        if algoritmo_elegido == "BFS" and hasattr(agente, 'buscar_bfs'):
            ruta_actual = agente.buscar_bfs(meta_actual)
        elif hasattr(agente, 'buscar_a_estrella'):
            ruta_actual = agente.buscar_a_estrella(meta_actual)
        else:
            ruta_actual = []

        if not ruta_actual or len(ruta_actual) <= 1:
            if getattr(agente, 'tiene_pasajero', False) and agente.posicion_agente in agente.bases:
                agente.tiene_pasajero = False
                personas_a_procesar.pop(0) 
            elif not getattr(agente, 'tiene_pasajero', False) and agente.posicion_agente == obj_p:
                agente.tiene_pasajero = True
                agente.mapa_objetos[obj_p[0]][obj_p[1]] = 0
            else:
                personas_a_procesar.pop(0) 
            continue

        # Mover un paso
        siguiente_paso = ruta_actual[1]
        agente.mover_agente(siguiente_paso[0], siguiente_paso[1]) 
        
        # Gestión de recargas interactivas
        for b in list(baterias_disponibles):
            if agente.posicion_agente == b["pos"]:
                if b["tipo"] == 5: 
                    agente.bateria = 100
                elif b["tipo"] == 4: 
                    agente.bateria = min(100, agente.bateria + 40)
                baterias_disponibles.remove(b)

        historial_simulacion.append({
    "agent_pos": [siguiente_paso[1], siguiente_paso[0]], # <-- Debe ser [X, Y] para React
    "weather_matrix": [list(fila) for fila in agente.mapa_clima],
    "bateria": max(0, agente.bateria)
})

    if len(historial_simulacion) <= 1:
        return {
            "steps": [], 
            "status": "No se encontraron rutas accesibles o el agente se quedó sin energía."
        }

    return {
        "steps": historial_simulacion, 
        "status": f"Simulación calculada con éxito usando {algoritmo_elegido}."
    }


if __name__ == "__main__":
    # Levantar servidor Uvicorn en el puerto standard 8000
    uvicorn.run("main.py:app" if __name__ != "__main__" else app, host="127.0.0.1", port=8000, reload=True)