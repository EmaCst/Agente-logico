import json
import random
import time
import heapq
import os
import hashlib
from collections import deque
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

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

# --- PERSISTENCIA JSON ADAPTADA ---
ARCHIVO_MEMORIA = "memoria_estados.json"

def cargar_memoria():
    if os.path.exists(ARCHIVO_MEMORIA):
        try:
            with open(ARCHIVO_MEMORIA, "r") as f:
                contenido = f.read()
                if not contenido: return {}
                data = json.loads(contenido)
                
                # Reconstruimos la estructura: { ID_MAPA: { ESTADO_STR: { (f,c): valores } } }
                memoria_reconstruida = {}
                for mapa_id, estados in data.items():
                    memoria_reconstruida[mapa_id] = {}
                    for estado_id, coordenadas in estados.items():
                        memoria_reconstruida[mapa_id][int(estado_id)] = {
                            tuple(map(int, k.split(','))): v for k, v in coordenadas.items()
                        }
                return memoria_reconstruida
        except Exception as e:
            return {}
    return {}

def guardar_memoria(memoria_global):
    # Serializamos las llaves numéricas y tuplas a strings para JSON
    data_serializable = {}
    for mapa_id, estados in memoria_global.items():
        data_serializable[mapa_id] = {}
        for estado_id, coordenadas in estados.items():
            data_serializable[mapa_id][str(estado_id)] = {
                f"{k[0]},{k[1]}": v for k, v in coordenadas.items()
            }
    with open(ARCHIVO_MEMORIA, "w") as f:
        json.dump(data_serializable, f)

MEMORIA_GLOBAL_MAPAS = cargar_memoria()

# --- CLASE DEL AGENTE INTELIGENTE CON APRENDIZAJE ---
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
        self.turnos_globales = 0 
        self.id_mapa_actual = None
        
        # 1) REQUISITO: Contador del estado/fase del mapa (cada estado dura 5 turnos)
        self.estado_mapa_actual = 0
        # 2) REQUISITO: Contador de cuántos movimientos faltan para que cambie el clima
        self.movimientos_para_cambio = 5

    def es_transitable(self, f, c):
        # LOS MUROS (1) SON ESTÁTICOS Y ESTO LOS BLOQUEA SIEMPRE
        return 0 <= f < self.filas and 0 <= c < self.columnas and self.mapa_objetos[f][c] != 1

    def identificar_y_cargar_mapa(self, matrix_web):
        estructura_pura = [[celda.id for celda in fila] for fila in matrix_web]
        matriz_string = json.dumps(estructura_pura, sort_keys=True)
        self.id_mapa_actual = hashlib.md5(matriz_string.encode()).hexdigest()[:8]
        
        if self.id_mapa_actual not in MEMORIA_GLOBAL_MAPAS:
            print(f"🧠 [MEMORIA UMG]: Nuevo mapa detectado (ID: {self.id_mapa_actual}).")
            MEMORIA_GLOBAL_MAPAS[self.id_mapa_actual] = {}
        else:
            print(f"💾 [MEMORIA UMG]: Reconozco este escenario (ID: {self.id_mapa_actual}).")

    # NUEVO MÉTODO: El bot ahora guarda una "instantánea" de TODO el mapa cuando cambia el estado
    def guardar_instantanea_clima_mapa(self):
        if not self.id_mapa_actual: return
        
        if self.id_mapa_actual not in MEMORIA_GLOBAL_MAPAS:
            MEMORIA_GLOBAL_MAPAS[self.id_mapa_actual] = {}
            
        memoria_mapa = MEMORIA_GLOBAL_MAPAS[self.id_mapa_actual]
        
        # Si es la primera vez que vemos este estado en este mapa, creamos su diccionario
        if self.estado_mapa_actual not in memoria_mapa:
            memoria_mapa[self.estado_mapa_actual] = {}
            
        # Guardamos el clima observado casilla por casilla para ESTE estado específico
        for f in range(self.filas):
            for c in range(self.columnas):
                coord = (f, c)
                clima_observado = self.mapa_clima[f][c]
                
                if coord not in memoria_mapa[self.estado_mapa_actual]:
                    memoria_mapa[self.estado_mapa_actual][coord] = {"Despejado": 0, "Lluvia": 0, "Tormenta": 0}
                
                # Atenuación ligera y refuerzo
                memoria_mapa[self.estado_mapa_actual][coord][clima_observado] *= 0.95
                memoria_mapa[self.estado_mapa_actual][coord][clima_observado] += 1
                
        guardar_memoria(MEMORIA_GLOBAL_MAPAS)

    def actualizar_clima_mapa(self):
        random.seed(self.turnos_globales)
        opciones = ["Despejado", "Lluvia", "Tormenta"]
        pesos = [70, 20, 10]
        for f in range(self.filas):
            for c in range(self.columnas):
                self.mapa_clima[f][c] = random.choices(opciones, weights=pesos, k=1)[0]
        random.seed(None)

    def buscar_a_estrella(self, objetivo):
        inicio, meta = tuple(self.posicion_agente), tuple(objetivo)
        # La frontera guarda: (f_total, (f, c), camino, g_acumulado, turnos_simulados)
        frontera = [(0, inicio, [], 0, 0)]
        visitados = {}
        costos_clima = {"Despejado": 1, "Lluvia": 5, "Tormenta": 20}
        penalizacion = 1 if self.tiene_pasajero else 0
        memoria_mapa = MEMORIA_GLOBAL_MAPAS.get(self.id_mapa_actual, {})
        
        while frontera:
            f_val, (f, c), camino, g, turnos_sim = heapq.heappop(frontera)
            if (f, c) == meta: return camino + [(f, c)]
            
            estado_visita = ((f, c), turnos_sim)
            if estado_visita in visitados and visitados[estado_visita] <= g: continue
            visitados[estado_visita] = g
            
            # --- CÁLCULO DE ANTICIPACIÓN TEMPORAL ---
            movs_restantes_sim = self.movimientos_para_cambio - turnos_sim
            estado_mapa_sim = self.estado_mapa_actual
            
            if movs_restantes_sim <= 0:
                bloques_extra = (abs(movs_restantes_sim) // 5) + 1
                estado_mapa_sim += bloques_extra
            
            for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nf, nc = f + df, c + dc
                # VERIFICACIÓN ESTÁTICA
                if self.es_transitable(nf, nc):
                    
                    # 1. Costo base del clima del turno presente
                    clima_proyectado = self.mapa_clima[nf][nc]
                    costo_paso = costos_clima[clima_proyectado] + penalizacion
                    
                    # 2. ANTICIPACIÓN (Solo afecta al clima)
                    if estado_mapa_sim != self.estado_mapa_actual and estado_mapa_sim in memoria_mapa and (nf, nc) in memoria_mapa[estado_mapa_sim]:
                        historial_futuro = memoria_mapa[estado_mapa_sim][(nf, nc)]
                        total = sum(historial_futuro.values())
                        if total > 0:
                            prob_tormenta = historial_futuro["Tormenta"] / total
                            prob_lluvia = historial_futuro["Lluvia"] / total
                            costo_futuro_estimado = (prob_tormenta * 20) + (prob_lluvia * 5) + 1
                            costo_paso = int(costo_futuro_estimado) + penalizacion
                    
                    nuevo_g = g + costo_paso
                    h = abs(nf - meta[0]) + abs(nc - meta[1])
                    
                    heapq.heappush(frontera, (
                        nuevo_g + h, 
                        (nf, nc), 
                        camino + [(f, c)], 
                        nuevo_g, 
                        turnos_sim + 1
                    ))
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
                # VERIFICACIÓN ESTÁTICA
                if self.es_transitable(nf, nc) and (nf, nc) not in visitados:
                    visitados.add((nf, nc))
                    cola.append(((nf, nc), camino + [(f, c)]))
        return None

    def mover_agente(self, nf, nc):
        clima_destino = self.mapa_clima[nf][nc]
        costo = 1 + (4 if clima_destino == "Lluvia" else 0) + (19 if clima_destino == "Tormenta" else 0) + (1 if self.tiene_pasajero else 0)
        self.bateria -= costo
        
        obj = self.mapa_objetos[nf][nc]
        
        # Lógica de baterías: SOLO borra si es 4 o 5
        if obj == 4:
            self.bateria = min(100, self.bateria + 40)
            self.mapa_objetos[nf][nc] = 0
        elif obj == 5:
            self.bateria = 100
            self.mapa_objetos[nf][nc] = 0
            
        # El muro (1) es intocable aquí, no hay código que lo modifique.
        self.posicion_agente = [nf, nc]
        
        self.turnos_globales += 1
        self.movimientos_para_cambio -= 1
        clima_cambio = False
        
        if self.movimientos_para_cambio == 0:
            self.estado_mapa_actual += 1
            self.movimientos_para_cambio = 5
            self.actualizar_clima_mapa()
            self.guardar_instantanea_clima_mapa()
            clima_cambio = True
            
        return self.bateria > 0, clima_cambio

@app.post("/solve")
def solve_mission(data: MapData):
    filas = len(data.matrix)
    columnas = len(data.matrix[0])
    agente = AgenteRescate(filas=filas, columnas=columnas)
    agente.identificar_y_cargar_mapa(data.matrix)
    agente.personas_pendientes = []
    agente.posicion_agente = [data.start_pos[1], data.start_pos[0]]
    agente.bases = []
    for f in range(filas):
        for c in range(columnas):
            celda_web = data.matrix[f][c]
            agente.mapa_objetos[f][c] = celda_web.id
            agente.mapa_clima[f][c] = celda_web.weather
            if celda_web.id == 2: agente.personas_pendientes.append([f, c])
            elif celda_web.id == 8: agente.bases.append([f, c])
            
    if not agente.personas_pendientes or not agente.bases:
        return {"steps": [], "status": "Faltan personas o bases"}
        
    agente.guardar_instantanea_clima_mapa()
        
    algoritmo_elegido = data.algorithm
    personas_a_procesar = list(agente.personas_pendientes)
    steps_json = []
    steps_json.append({
        "agent_pos": [agente.posicion_agente[1], agente.posicion_agente[0]],
        "bateria": max(0, agente.bateria),
        "weather_matrix": [list(fila) for fila in agente.mapa_clima]
    })
    
    ruta_actual = []

    while personas_a_procesar and agente.bateria > 0:
        obj_p = personas_a_procesar[0]
        
        if agente.tiene_pasajero:
            rutas_b = [agente.buscar_bfs(b) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(b) for b in agente.bases]
            rutas_validas = [r for r in rutas_b if r]
            meta_actual = min(rutas_validas, key=len)[-1] if rutas_validas else None
        else:
            meta_actual = obj_p
            
        if not meta_actual:
            personas_a_procesar.pop(0)
            ruta_actual = []
            continue
            
        if not ruta_actual:
            ruta_actual = agente.buscar_bfs(meta_actual) if algoritmo_elegido == "BFS" else agente.buscar_a_estrella(meta_actual)
            
        if not ruta_actual or len(ruta_actual) <= 1:
            if agente.tiene_pasajero and agente.posicion_agente in agente.bases:
                agente.tiene_pasajero = False
                personas_a_procesar.pop(0) 
            elif not agente.tiene_pasajero and agente.posicion_agente == obj_p:
                agente.tiene_pasajero = True
                agente.mapa_objetos[obj_p[0]][obj_p[1]] = 0 
                if obj_p in personas_a_procesar: personas_a_procesar.remove(obj_p)
            else:
                personas_a_procesar.pop(0) 
            ruta_actual = []
            continue
            
        siguiente_paso = ruta_actual[1]
        continua_vivo, clima_cambio = agente.mover_agente(siguiente_paso[0], siguiente_paso[1])
        ruta_actual.pop(0)
        
        if clima_cambio:
            ruta_actual = []

        steps_json.append({
            "agent_pos": [agente.posicion_agente[1], agente.posicion_agente[0]],
            "bateria": max(0, agente.bateria),
            "weather_matrix": [list(fila) for fila in agente.mapa_clima]
        })
        if not continua_vivo: break
        
    return {"steps": steps_json, "status": f"Simulación exitosa con {algoritmo_elegido}"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)