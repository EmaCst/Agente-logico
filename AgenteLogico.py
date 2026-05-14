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
    persona = [5, 5]
    
    print("--- SISTEMA DE IA: SELECCIÓN DE ALGORITMO ---")
    print("1. BFS (Búsqueda No Informada - Más Corta)")
    print("2. A* (Búsqueda Informada - Optimizada)")
    
    opcion = input("Selecciona el tipo de búsqueda (1 o 2): ")
    
    if opcion == "1":
        print("\nEjecutando BFS...")
        ruta = agente.buscar_bfs(persona)
    else:
        print("\nEjecutando A*...")
        ruta = agente.buscar_a_estrella(persona)

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