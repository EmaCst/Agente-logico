import json
import random
import time
import heapq
import os
from collections import deque

class AgenteRescate:
    def __init__(self, filas=15, columnas=15):
        self.filas = filas
        self.columnas = columnas
        self.bateria = 100
        self.posicion_agente = [0, 0]
        # El mapa ahora guarda OBJETOS (0: libre, 1: obstáculo, 2: persona, etc.)
        self.mapa_objetos = [[0 for _ in range(columnas)] for _ in range(filas)]
        # El mapa_clima guarda el CLIMA de cada celda individualmente
        self.mapa_clima = [["Despejado" for _ in range(columnas)] for _ in range(filas)]
        self.personas_pendientes = []
        self.bases = []
        self.tiene_pasajero = False
        self.colocar_objetos()
        self.actualizar_clima_mapa() # Inicializamos el clima

    def colocar_objetos(self):
        # 1. Bases aleatorias
        while len(self.bases) < 2:
            f, c = random.randint(0, self.filas - 1), random.randint(0, self.columnas - 1)
            if [f, c] != [0, 0] and [f, c] not in self.bases:
                self.bases.append([f, c])

        # 2. Obstáculos
        puestos = 0
        while puestos < 10:
            f, c = random.randint(0, self.filas - 1), random.randint(0, self.columnas - 1)
            if [f, c] != [0, 0] and [f, c] not in self.bases and self.mapa_objetos[f][c] == 0:
                self.mapa_objetos[f][c] = 1
                puestos += 1

        # 3. Personas
        puestas = 0
        while puestas < 2:
            f, c = random.randint(0, self.filas - 1), random.randint(0, self.columnas - 1)
            if self.mapa_objetos[f][c] == 0 and [f, c] != [0, 0] and [f, c] not in self.bases:
                self.mapa_objetos[f][c] = 2
                self.personas_pendientes.append([f, c])
                puestas += 1
        
        # 4. Baterías
        for f in range(self.filas):
            for c in range(self.columnas):
                if self.mapa_objetos[f][c] == 0 and [f, c] not in self.bases and [f, c] != [0, 0]:
                    prob = random.random()
                    if prob < 0.10: self.mapa_objetos[f][c] = 5
                    elif prob < 0.20: self.mapa_objetos[f][c] = 4

    def actualizar_clima_mapa(self):
        # Cada celda decide su clima de forma independiente
        opciones = ["Despejado", "Lluvia", "Tormenta"]
        pesos = [70, 20, 10] # Más probable que esté despejado por celda
        for f in range(self.filas):
            for c in range(self.columnas):
                self.mapa_clima[f][c] = random.choices(opciones, weights=pesos, k=1)[0]

    def dibujar_consola(self, algoritmo):
        os.system('cls' if os.name == 'nt' else 'clear')
        clima_local = self.mapa_clima[self.posicion_agente[0]][self.posicion_agente[1]]
        
        print(f"\n--- MONITOR UMG | Algoritmo: {algoritmo} ---")
        print(f"Batería: {self.bateria}% | Clima Local: {clima_local}")
        print("-" * (self.columnas * 3))
        
        for f in range(self.filas):
            fila_txt = ""
            for c in range(self.columnas):
                # Determinar símbolo de fondo según clima de ESA celda
                if self.mapa_clima[f][c] == "Despejado": char = "."
                elif self.mapa_clima[f][c] == "Lluvia": char = "~"
                else: char = "Z"

                # Superponer objetos
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
                    # AQUÍ ESTÁ LA MAGIA: El costo depende del clima de la celda vecina (nf, nc)
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
        # El costo se basa en el clima de la celda a la que llega
        clima_destino = self.mapa_clima[nf][nc]
        costo = 1
        if clima_destino == "Lluvia": costo += 4
        if clima_destino == "Tormenta": costo += 19
        if self.tiene_pasajero: costo += 1
        
        self.bateria -= costo
        self.posicion_agente = [nf, nc]
        
        # El clima cambia un poco en cada paso (Simulación dinámica)
        self.actualizar_clima_mapa()
        
        obj = self.mapa_objetos[nf][nc]
        if obj == 4: self.bateria = min(100, self.bateria + 40)
        elif obj == 5: self.bateria = 100
        if obj in [4, 5]: self.mapa_objetos[nf][nc] = 0
        return self.bateria > 0

if __name__ == "__main__":
    agente = AgenteRescate()
    print("\n1. BFS | 2. A*")
    opcion = input("Algoritmo: ")
    nombre_alg = "BFS" if opcion == "1" else "A*"

    while agente.personas_pendientes and agente.bateria > 0:
        obj_p = agente.personas_pendientes[0]
        ruta = agente.buscar_bfs(obj_p) if opcion == "1" else agente.buscar_a_estrella(obj_p)
        
        if ruta:
            for paso in ruta[1:]:
                if not agente.mover_agente(paso[0], paso[1]): break
                agente.dibujar_consola(nombre_alg)
                time.sleep(0.4)
            
            if agente.posicion_agente == obj_p:
                agente.tiene_pasajero = True
                agente.mapa_objetos[obj_p[0]][obj_p[1]] = 0
                
                rutas_b = [agente.buscar_bfs(b) if opcion == "1" else agente.buscar_a_estrella(b) for b in agente.bases]
                rutas_validas = [r for r in rutas_b if r]
                if rutas_validas:
                    ruta_base = min(rutas_validas, key=len)
                    for paso in ruta_base[1:]:
                        if not agente.mover_agente(paso[0], paso[1]): break
                        agente.dibujar_consola(nombre_alg)
                        time.sleep(0.4)
                    if agente.posicion_agente in agente.bases:
                        agente.tiene_pasajero = False
                        agente.personas_pendientes.pop(0)
        else:
            print("No hay ruta. Reintentando...")
            agente = AgenteRescate()

    print("\n--- SIMULACIÓN FINALIZADA ---")