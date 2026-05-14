import json
import random
import time
import heapq # Necesario para A* (cola de prioridad)
from collections import deque

class AgenteRescate:
    def __init__(self, filas=10, columnas=10):
        self.filas = filas
        self.columnas = columnas
        self.bateria = 100
        self.posicion_agente = [0, 0]
        self.mapa = [[0 for _ in range(columnas)] for _ in range(filas)]
        self.colocar_objetos()

    def colocar_objetos(self):
        # Objetos fijos
        self.mapa[3][3] = 1  # Obstáculo
        self.mapa[5][5] = 2  # Persona a rescatar

        # 2. Colocar Persona en posición aleatoria
        # Buscamos una celda que esté vacía (0) y que no sea la salida [0,0]
        persona_colocada = False
        while not persona_colocada:
            f = random.randint(0, self.filas - 1)
            c = random.randint(0, self.columnas - 1)
            if self.mapa[f][c] == 0 and (f != 0 or c != 0):
                self.mapa[f][c] = 2
                self.posicion_persona = [f, c] # Guardamos la posición para la búsqueda
                persona_colocada = True
        
        # Generar baterías aleatorias (Manejo de Incertidumbre)
        for f in range(self.filas):
            for c in range(self.columnas):
                if self.mapa[f][c] == 0:
                    prob = random.random()
                    if prob < 0.15: # 15% de probabilidad
                        self.mapa[f][c] = 5 # Batería Grande (+100%)
                    elif prob < 0.45: # 30% adicional
                        self.mapa[f][c] = 4 # Batería Pequeña (+40%)

    def obtener_clima(self):
        return random.choice(["Despejado", "Lluvia", "Tormenta"])

    def estado_actual_json(self):
        # Esta es la salida que tu compañero usará para el Front
        estado = {
            "agente": {
                "posicion": self.posicion_agente,
                "bateria": self.bateria,
            },
            "mapa": self.mapa
        }
        return json.dumps(estado)

    def buscar_bfs(self, objetivo):
        inicio = tuple(self.posicion_agente)
        meta = tuple(objetivo)
        cola = deque([(inicio, [])])
        visitados = {inicio}

        while cola:
            (fila, col), camino = cola.popleft()
            if (fila, col) == meta:
                return camino + [(fila, col)]

            for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nf, nc = fila + df, col + dc
                if (0 <= nf < self.filas and 0 <= nc < self.columnas and 
                    self.mapa[nf][nc] != 1 and (nf, nc) not in visitados):
                    visitados.add((nf, nc))
                    cola.append(((nf, nc), camino + [(fila, col)]))
        return None
    
    def buscar_a_estrella(self, objetivo):
        # El objetivo es [fila, columna]
        inicio = tuple(self.posicion_agente)
        meta = tuple(objetivo)
        
        # Priority Queue: (prioridad f, posicion actual, camino, costo g)
        # La prioridad f = g + h
        frontera = [(0, inicio, [], 0)]
        visitados = {} # Guardamos el costo 'g' más bajo para cada celda

        while frontera:
            f, (fila, col), camino, g = heapq.heappop(frontera)
            
            # Si llegamos a la meta
            if (fila, col) == meta:
                return camino + [(fila, col)]

            # Si ya visitamos esta celda con un costo menor, ignoramos
            if (fila, col) in visitados and visitados[(fila, col)] <= g:
                continue
            visitados[(fila, col)] = g

            # Explorar vecinos
            for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nf, nc = fila + df, col + dc
                
                # Verificar límites y obstáculos
                if (0 <= nf < self.filas and 0 <= nc < self.columnas and 
                    self.mapa[nf][nc] != 1):
                    
                    nuevo_g = g + 1 # Cada paso cuesta 1
                    
                    # Heurística: Distancia Manhattan (qué tan lejos está de la meta)
                    h = abs(nf - meta[0]) + abs(nc - meta[1])
                    
                    nuevo_f = nuevo_g + h
                    heapq.heappush(frontera, (nuevo_f, (nf, nc), camino + [(fila, col)], nuevo_g))
        
        return None # No se encontró camino

    def mover_agente(self, nueva_fila, nueva_columna):
        if 0 <= nueva_fila < self.filas and 0 <= nueva_columna < self.columnas:
            if self.mapa[nueva_fila][nueva_columna] != 1:
                
                # 1. Clima y Consumo
                clima = self.obtener_clima()
                costo = 1
                if clima == "Lluvia": costo += 10
                if clima == "Tormenta": costo += 30
                self.bateria -= costo
                
                # 2. Actualizar posición
                self.posicion_agente = [nueva_fila, nueva_columna]
                
                # 3. Lógica de Recarga (NUEVO: Consumir objetos 4 y 5)
                objeto = self.mapa[nueva_fila][nueva_columna]
                if objeto == 4:
                    self.bateria = min(100, self.bateria + 40)
                    print(f"-> ¡Batería encontrada! +40%")
                    self.mapa[nueva_fila][nueva_columna] = 0 # Se quita del mapa
                elif objeto == 5:
                    self.bateria = 100
                    print(f"-> ¡Supercarga encontrada! +100%")
                    self.mapa[nueva_fila][nueva_columna] = 0

                print(f"Movido a [{nueva_fila},{nueva_columna}] | Clima: {clima} | Batería: {self.bateria}%")
            else:
                print("¡Error! Obstáculo detectado.")
        else:
            print("¡Error! Límites del mapa excedidos.")

if __name__ == "__main__":
    agente = AgenteRescate()
    # Ahora obtenemos el objetivo directamente del mapa generado
    objetivo = agente.posicion_persona 
    
    print(f"--- INICIANDO MISIÓN DE RESCATE ---")
    print(f"Persona localizada aleatoriamente en: {objetivo}")
    
    print("1. BFS (Búsqueda No Informada)")
    print("2. A* (Búsqueda Informada)")
    seleccion = input("Selecciona el algoritmo (1 o 2): ")
    
    if seleccion == "1":
        ruta = agente.buscar_bfs(objetivo)
    else:
        ruta = agente.buscar_a_estrella(objetivo)

    if ruta:
        print(f"Ruta encontrada: {ruta}")
        for paso in ruta[1:]:
            agente.mover_agente(paso[0], paso[1])
            print(agente.estado_actual_json())
            time.sleep(0.5) # Un poco más rápido para pruebas
            if agente.bateria <= 0:
                print("¡FALLO! Sin energía.")
                break
    else:
        print("No hay ruta posible.")