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
        self.mapa = [[0 for _ in range(columnas)] for _ in range(filas)]
        self.personas_pendientes = []
        self.clima_actual = "Despejado"
        self.colocar_objetos()

    def colocar_objetos(self):
        # 1. Colocar Obstáculos (10 aleatorios)
        for _ in range(10):
            # CORRECCIÓN AQUÍ: Llamadas separadas para f y c
            f = random.randint(0, self.filas - 1)
            c = random.randint(0, self.columnas - 1)
            if (f, c) != (0, 0): 
                self.mapa[f][c] = 1

        # 2. Colocar 2 Personas en posiciones aleatorias
        puestas = 0
        while puestas < 2:
            f = random.randint(0, self.filas - 1)
            c = random.randint(0, self.columnas - 1)
            if self.mapa[f][c] == 0 and (f != 0 or c != 0):
                self.mapa[f][c] = 2
                self.personas_pendientes.append([f, c])
                puestas += 1
        
        # 3. Generar baterías (15% Grande, 30% Pequeña)
        for f in range(self.filas):
            for c in range(self.columnas):
                if self.mapa[f][c] == 0:
                    prob = random.random()
                    if prob < 0.15: self.mapa[f][c] = 5 # Grande
                    elif prob < 0.45: self.mapa[f][c] = 4 # Pequeña

    def obtener_clima(self):
        self.clima_actual = random.choice(["Despejado", "Lluvia", "Tormenta"])
        return self.clima_actual

    def dibujar_consola(self):
        #os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\nESTADO DE LA MISIÓN")
        print(f"Batería: {self.bateria}% | Clima: {self.clima_actual}")
        print(f"Personas restantes: {len(self.personas_pendientes)}")
        print("-" * (self.columnas * 3))
        
        for f in range(self.filas):
            fila_texto = ""
            for c in range(self.columnas):
                if [f, c] == self.posicion_agente:
                    fila_texto += " A "  
                elif self.mapa[f][c] == 1:
                    fila_texto += " # "  
                elif self.mapa[f][c] == 2:
                    fila_texto += " P "  
                elif self.mapa[f][c] == 5:
                    fila_texto += " * "  
                elif self.mapa[f][c] == 4:
                    fila_texto += " o "  
                else:
                    fila_texto += " . "  
            print(fila_texto)
        print("-" * (self.columnas * 3))

    def estado_actual_json(self):
        estado = {
            "agente": {"posicion": self.posicion_agente, "bateria": self.bateria, "clima": self.clima_actual},
            "mapa": self.mapa
        }
        return json.dumps(estado)

    def buscar_bfs(self, objetivo):
        inicio, meta = tuple(self.posicion_agente), tuple(objetivo)
        cola = deque([(inicio, [])])
        visitados = {inicio}
        while cola:
            (f, c), camino = cola.popleft()
            if (f, c) == meta: return camino + [(f, c)]
            for df, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nf, nc = f+df, c+dc
                if 0<=nf<self.filas and 0<=nc<self.columnas and self.mapa[nf][nc]!=1 and (nf,nc) not in visitados:
                    visitados.add((nf,nc))
                    cola.append(((nf,nc), camino+[(f,c)]))
        return None

    def buscar_a_estrella(self, objetivo):
        inicio, meta = tuple(self.posicion_agente), tuple(objetivo)
        pq = [(0, inicio, [], 0)]
        visitados = {}
        while pq:
            f_val, (f, c), camino, g = heapq.heappop(pq)
            if (f, c) == meta: return camino + [(f, c)]
            if (f, c) in visitados and visitados[(f, c)] <= g: continue
            visitados[(f, c)] = g
            for df, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                nf, nc = f+df, c+dc
                if 0<=nf<self.filas and 0<=nc<self.columnas and self.mapa[nf][nc]!=1:
                    h = abs(nf - meta[0]) + abs(nc - meta[1])
                    heapq.heappush(pq, (g + 1 + h, (nf, nc), camino + [(f, c)], g + 1))
        return None

    def mover_agente(self, nf, nc):
        clima = self.obtener_clima()
        costo = 1
        if clima == "Lluvia": costo += 9
        if clima == "Tormenta": costo += 29
        
        self.bateria -= costo
        self.posicion_agente = [nf, nc]
        
        objeto = self.mapa[nf][nc]
        if objeto == 4: self.bateria = min(100, self.bateria + 40)
        elif objeto == 5: self.bateria = 100
        
        if objeto in [4, 5]: self.mapa[nf][nc] = 0
        return self.bateria > 0

if __name__ == "__main__":
    agente = AgenteRescate(10, 10)
    print("1. BFS | 2. A*")
    opc = input("Selecciona algoritmo: ")
    
    while agente.personas_pendientes and agente.bateria > 0:
        objetivo = agente.personas_pendientes[0]
        ruta = agente.buscar_bfs(objetivo) if opc == "1" else agente.buscar_a_estrella(objetivo)

        if ruta:
            for paso in ruta[1:]:
                if not agente.mover_agente(paso[0], paso[1]):
                    break
                agente.dibujar_consola()
                time.sleep(0.4)
            
            if agente.posicion_agente == objetivo:
                agente.mapa[objetivo[0]][objetivo[1]] = 0
                agente.personas_pendientes.pop(0)
        else:
            print(f"No hay ruta para la persona en {objetivo}")
            break

    if not agente.personas_pendientes:
        print("\n¡MISIÓN COMPLETADA! Todos a salvo.")
    else:
        print(f"\nMISIÓN FALLIDA. Batería: {agente.bateria}%")