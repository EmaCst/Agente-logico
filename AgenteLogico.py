import json
import random
import time
import heapq
import os
from collections import deque
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- CONFIGURACIÓN DE FASTAPI (PUENTE WEB) ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Cell(BaseModel):
    id: int
    weather: str

class MapData(BaseModel):
    matrix: List[List[Cell]]
    start_pos: List[int]
    algorithm: str


# --- TU CLASE ORIGINAL CON LAS NUEVAS REGLAS DE NEGOCIO ---
class AgenteRescate:
    def __init__(self, filas=15, columnas=15):
        self.filas = filas
        self.columnas = columnas
        self.bateria = 100
        self.posicion_agente = [0, 0]
        self.mapa_objetos = [[0 for _ in range(columnas)] for _ in range(filas)]
        self.mapa_clima = [["Despejado" for _ in range(columnas)] for _ in range(filas)]
        self.personas_pendientes = []
        self.bases = []
        self.tiene_pasajero = False
        
        # REGLA NUEVA: Contador global de turnos internos del agente
        self.turnos_globales = 0 
        
        self.colocar_objetos()
        self.actualizar_clima_mapa()

    def colocar_objetos(self):
        while len(self.bases) < 2:
            f, c = random.randint(0, self.filas - 1), random.randint(0, self.columnas - 1)
            if [f, c] != [0, 0] and [f, c] not in self.bases:
                self.bases.append([f, c])

        puestos = 0
        while puestos < 10:
            f, c = random.randint(0, self.filas - 1), random.randint(0, self.columnas - 1)
            if [f, c] != [0, 0] and [f, c] not in self.bases and self.mapa_objetos[f][c] == 0:
                self.mapa_objetos[f][c] = 1
                puestos += 1

        puestas = 0
        while puestas < 2:
            f, c = random.randint(0, self.filas - 1), random.randint(0, self.columnas - 1)
            if self.mapa_objetos[f][c] == 0 and [f, c] != [0, 0] and [f, c] not in self.bases:
                self.mapa_objetos[f][c] = 2
                self.personas_pendientes.append([f, c])
                puestas += 1
        
        for f in range(self.filas):
            for c in range(self.columnas):
                if self.mapa_objetos[f][c] == 0 and [f, c] not in self.bases and [f, c] != [0, 0]:
                    prob = random.random()
                    if prob < 0.10: self.mapa_objetos[f][c] = 5
                    elif prob < 0.20: self.mapa_objetos[f][c] = 4

    def actualizar_clima_mapa(self):
        # El clima muta de forma masiva en todo el mapa
        opciones = ["Despejado", "Lluvia", "Tormenta"]
        pesos = [70, 20, 10]
        for f in range(self.filas):
            for c in range(self.columnas):
                self.mapa_clima[f][c] = random.choices(opciones, weights=pesos, k=1)[0]

    def dibujar_consola(self, algoritmo):
        os.system('cls' if os.name == 'nt' else 'clear')
        clima_local = self.mapa_clima[self.posicion_agente[0]][self.posicion_agente[1]]
        
        print(f"\n--- MONITOR UMG | Algoritmo: {algoritmo} | Turno General: {self.turnos_globales} ---")
        print(f"Batería: {self.bateria}% | Clima Local: {clima_local}")
        print("-" * (self.columnas * 3))
        
        for f in range(self.filas):
            fila_txt = ""
            for c in range(self.columnas):
                if self.mapa_clima[f][c] == "Despejado": char = "."
                elif self.mapa_clima[f][c] == "Lluvia": char = "~"
                else: char = "Z"

                if [f, c] == self.posicion_agente: fila_txt += " A "
                elif [f, c] in self.bases: fila_txt += " S "
                elif self.mapa_objetos[f][c] == 1: fila_txt += " # "
                elif self.mapa_objetos[f][c] == 2: fila_txt += " P "
                elif self.mapa_objetos[f][c] == 5: fila_txt += " * "
                elif self.mapa_objetos[f][c] == 4: fila_txt += " o "
                else: fila_txt += f" {char} "
            print(fila_txt)
        print("-" * (self.columnas * 3))

    def buscar_a_estrella(self, objetivo):
        inicio, meta = tuple(self.posicion_agente), tuple(objetivo)
        frontera = [(0, inicio, [], 0)]
        visitados = {}
        costos_clima = {"Despejado": 1, "Lluvia": 5, "Tormenta": 20}
        penalizacion = 1 if self.tiene_pasajero else 0

        while frontera:
            f_val, (f, c), camino, g = heapq.heappop(frontera)
            if (f, c) == meta: return camino + [(f, c)]
            if (f, c) in visitados and visitados[(f, c)] <= g: continue
            visitados[(f, c)] = g

            for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nf, nc = f + df, c + dc
                if 0 <= nf < self.filas and 0 <= nc < self.columnas and self.mapa_objetos[nf][nc] != 1:
                    clima_celda = self.mapa_clima[nf][nc]
                    costo_paso = costos_clima[clima_celda] + penalizacion
                    
                    nuevo_g = g + costo_paso
                    h = abs(nf - meta[0]) + abs(nc - meta[1])
                    heapq.heappush(frontera, (nuevo_g + h, (nf, nc), camino + [(f, c)], nuevo_g))
        return None

    def buscar_bfs(self, objetivo):
        inicio, meta = tuple(self.posicion_agente), tuple(objetivo)
        cola = deque([(inicio, [])])
        visitados = {inicio}
        while cola:
            (f, c), camino = cola.popleft()
            if (f, c) == meta: return camino + [(f, c)]
            for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nf, nc = f + df, c + dc
                if 0 <= nf < self.filas and 0 <= nc < self.columnas and self.mapa_objetos[nf][nc] != 1 and (nf, nc) not in visitados:
                    visitados.add((nf, nc))
                    cola.append(((nf, nc), camino + [(f, c)]))
        return None

    def mover_agente(self, nf, nc):
        clima_destino = self.mapa_clima[nf][nc]
        costo = 1
        if clima_destino == "Lluvia": costo += 4
        if clima_destino == "Tormenta": costo += 19
        if self.tiene_pasajero: costo += 1
        
        self.bateria -= costo
        self.posicion_agente = [nf, nc]
        
        # MODIFICACIÓN CLAVE: Sumamos un turno por cada movimiento individual
        self.turnos_globales += 1
        
        # REGLA DE LOS 5 TURNOS: El clima cambia estrictamente si es múltiplo de 5
        if self.turnos_globales % 5 == 0:
            self.actualizar_clima_mapa()
        
        obj = self.mapa_objetos[nf][nc]
        if obj == 4: self.bateria = min(100, self.bateria + 40)
        elif obj == 5: self.bateria = 100
        if obj in [4, 5]: self.mapa_objetos[nf][nc] = 0
        return self.bateria > 0


# --- ENDPOINT CORREGIDO CON RECALCULACIÓN DINÁMICA ---
@app.post("/solve")
def solve_mission(data: MapData):
    filas = len(data.matrix)
    columnas = len(data.matrix[0])
    
    agente = AgenteRescate(filas=filas, columnas=columnas)
    agente.personas_pendientes = []
    agente.posicion_agente = [data.start_pos[1], data.start_pos[0]]
    agente.bases = []
    
    # Cargamos el mapa inicial provisto por el Front
    for f in range(filas):
        for c in range(columnas):
            celda_web = data.matrix[f][c]
            agente.mapa_objetos[f][c] = celda_web.id
            agente.mapa_clima[f][c] = celda_web.weather
            
            if celda_web.id == 2:
                agente.personas_pendientes.append([f, c])
            elif celda_web.id == 8:
                agente.bases.append([f, c])
                
    if not agente.personas_pendientes or not agente.bases:
        return {"ruta": [], "status": "Faltan personas o bases en el mapa interactivo"}

    ruta_python = [list(agente.posicion_agente)]
    algoritmo_elegido = data.algorithm
    personas_a_procesar = list(agente.personas_pendientes)

    # RECALCULACIÓN DINÁMICA PASO A PASO:
    while personas_a_procesar and agente.bateria > 0:
        obj_p = personas_a_procesar[0]
        
        # Decidimos el objetivo lógico basándonos en si tiene pasajero o no
        if agente.tiene_pasajero:
            rutas_b = [agente.buscar_bfs(b) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(b) for b in agente.bases]
            rutas_validas = [r for r in rutas_b if r]
            meta_actual = min(rutas_validas, key=len)[-1] if rutas_validas else None
        else:
            meta_actual = obj_p

        if not meta_actual:
            personas_a_procesar.pop(0)
            continue

        # Calculamos la ruta con las condiciones del mapa en este instante preciso
        if algoritmo_elegido == "BFS":
            ruta_calculada = agente.buscar_bfs(meta_actual)
        else:
            ruta_calculada = agente.buscar_a_estrella(meta_actual)

        # Si no hay camino viable o ya se encuentra sobre el objetivo
        if not ruta_calculada or len(ruta_calculada) <= 1:
            if agente.tiene_pasajero and agente.posicion_agente in agente.bases:
                agente.tiene_pasajero = False
                personas_a_procesar.pop(0) # Ciudadano salvado
            elif not agente.tiene_pasajero and agente.posicion_agente == obj_p:
                agente.tiene_pasajero = True
                agente.mapa_objetos[obj_p[0]][obj_p[1]] = 0 # Subió al vehículo
            else:
                personas_a_procesar.pop(0) # Inalcanzable
            continue

        # ¡AQUÍ ESTÁ EL CAMBIO DINÁMICO!: Avanza SOLO UN PASO. 
        # Al regresar al 'while', volverá a calcular usando las condiciones climáticas del siguiente turno.
        siguiente_paso = ruta_calculada[1]
        ruta_python.append(list(siguiente_paso))
        agente.mover_agente(siguiente_paso[0], siguiente_paso[1])

    ruta_frontend = [[paso[1], paso[0]] for paso in ruta_python]
    return {"ruta": ruta_frontend, "status": f"Ruta calculada con {algoritmo_elegido}"}


# --- CONTROL DE EJECUCIÓN ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)