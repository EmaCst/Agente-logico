import { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const size = 15;
  const [matrix, setMatrix] = useState([]);
  const [backupMatrix, setBackupMatrix] = useState([]); // <--- NUEVO: Para guardar el mapa original antes de la simulación
  const [selectedTool, setSelectedTool] = useState(1);
  const [selectedWeather, setSelectedWeather] = useState('Despejado');
  const [agentPos, setAgentPos] = useState([0, 0]);
  const [initialAgentPos, setInitialAgentPos] = useState([0, 0]); // <--- NUEVO: Guarda la posición inicial elegida por el usuario
  const [turns, setTurns] = useState(0);
  const [battery, setBattery] = useState(100);
  const [energyConsumed, setEnergyConsumed] = useState(0); 
  const [algorithm, setAlgorithm] = useState('A*');

  const tools = [
    { id: 1, name: 'Muro', icon: '🧱' },
    { id: 2, name: 'Persona', icon: '👤' },
    { id: 4, name: 'Bat. 40%', icon: '🪫' },
    { id: 5, name: 'Bat. 100%', icon: '🔋' },
    { id: 8, name: 'Zona Segura', icon: '🏠' },
    { id: 7, name: 'Robot (Inicio)', icon: '🤖' },
    { id: 0, name: 'Borrador', icon: '🗑️' },
  ];

  const generarMapaAleatorio = () => {
    let nuevoMapa = Array(size).fill(0).map(() => 
      Array(size).fill(null).map(() => ({ id: 0, weather: 'Despejado' }))
    );

    const obtenerCoordAleatoria = () => {
      const x = Math.floor(Math.random() * size);
      const y = Math.floor(Math.random() * size);
      return [x, y];
    };

    setAgentPos([0, 0]);
    setInitialAgentPos([0, 0]); // Sincroniza posición inicial backup
    setBattery(100); 
    setEnergyConsumed(0); 

    let basesPuestas = 0;
    while (basesPuestas < 2) {
      const [x, y] = obtenerCoordAleatoria();
      if ((x !== 0 || y !== 0) && nuevoMapa[y][x].id === 0) {
        nuevoMapa[y][x].id = 8;
        basesPuestas++;
      }
    }

    let murosPuestos = 0;
    while (murosPuestos < 10) {
      const [x, y] = obtenerCoordAleatoria();
      if ((x !== 0 || y !== 0) && nuevoMapa[y][x].id === 0) {
        nuevoMapa[y][x].id = 1;
        murosPuestos++;
      }
    }

    let personasPuestas = 0;
    while (personasPuestas < 2) {
      const [x, y] = obtenerCoordAleatoria();
      if ((x !== 0 || y !== 0) && nuevoMapa[y][x].id === 0) {
        nuevoMapa[y][x].id = 2;
        personasPuestas++;
      }
    }

    const climas = ['Despejado', 'Lluvia', 'Tormenta'];
    const pesosClima = [0.70, 0.20, 0.10]; 

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if (x === 0 && y === 0) continue;

        const randClima = Math.random();
        let climaElegido = 'Despejado';
        if (randClima < pesosClima[0]) climaElegido = 'Despejado';
        else if (randClima < pesosClima[0] + pesosClima[1]) climaElegido = 'Lluvia';
        else climaElegido = 'Tormenta';

        nuevoMapa[y][x].weather = climaElegido;

        if (nuevoMapa[y][x].id === 0) {
          const randBat = Math.random();
          if (randBat < 0.10) {
            nuevoMapa[y][x].id = 5; 
          } else if (randBat < 0.20) {
            nuevoMapa[y][x].id = 4; 
          }
        }
      }
    }

    setMatrix(nuevoMapa);
    setBackupMatrix(JSON.parse(JSON.stringify(nuevoMapa))); // Guardamos copia pura del escenario inicial
    setTurns(0);
  };

  useEffect(() => {
    generarMapaAleatorio();
  }, []);

  const handleCellClick = (x, y) => {
    if (selectedTool === 7) {
      setAgentPos([x, y]);
      setInitialAgentPos([x, y]); // Si el usuario mueve el origen manualmente, lo guardamos en el backup
    } else {
      const newMatrix = [...matrix];
      newMatrix[y][x] = { id: selectedTool, weather: selectedWeather };
      setMatrix(newMatrix);
      setBackupMatrix(JSON.parse(JSON.stringify(newMatrix))); // Actualiza el backup con la edición manual del usuario
    }
  };

  // <--- NUEVO: Función para limpiar simulación actual y regresar al estado del escenario inicial
  const restaurarEscenarioOriginal = () => {
    setMatrix(JSON.parse(JSON.stringify(backupMatrix))); 
    setAgentPos([...initialAgentPos]);
    setBattery(100);
    setTurns(0);
    setEnergyConsumed(0);
  };

  const enviarAlBackend = async () => {
    try {
      setTurns(0);
      setEnergyConsumed(0);

      const res = await axios.post('http://127.0.0.1:8000/solve', {
  matrix: matrix,
  start_pos: agentPos,
  algorithm: algorithm 
});

      const { steps, status } = res.data;

      if (steps && steps.length > 0) {
        let acumuladorEnergia = 0;

        steps.forEach((step, index) => {
          setTimeout(() => {
            setAgentPos(step.agent_pos);
            setTurns(index);
            setBattery(step.bateria);

            if (index > 0) {
              const bateriaAnterior = steps[index - 1].bateria;
              const bateriaActual = step.bateria;
              
              if (bateriaActual < bateriaAnterior) {
                acumuladorEnergia += (bateriaAnterior - bateriaActual);
              }
              setEnergyConsumed(acumuladorEnergia);
            }

            setMatrix((prevMatrix) => {
              return prevMatrix.map((row, y) => 
                row.map((cell, x) => {
                  const nuevoClimaBackend = step.weather_matrix[y][x];
                  let nuevoId = cell.id;

                  if (step.agent_pos[0] === x && step.agent_pos[1] === y) {
                    if (cell.id === 2) nuevoId = 0;
                    if (cell.id === 4 || cell.id === 5) nuevoId = 0;
                  }

                  return {
                    ...cell,
                    weather: nuevoClimaBackend,
                    id: nuevoId
                  };
                })
              );
            });
          }, index * 450); 
        });
      } else {
        alert(status || "No se encontró una ruta válida.");
      }
    } catch (err) {
      alert("Error: Verifica que el servidor Python esté corriendo en el puerto 8000.");
    }
  };

  const getBatteryColor = (value) => {
    if (value > 50) return 'bg-emerald-500';
    if (value > 20) return 'bg-amber-500';
    return 'bg-rose-500 animate-pulse';
  };

  if (matrix.length === 0) return <div className="text-center text-cyan-400 mt-10">Cargando Mapa...</div>;

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-200 p-4 font-sans">
      <header className="max-w-6xl mx-auto mb-6 text-center">
        <h1 className="text-3xl font-black text-cyan-400">RESCUE SYSTEM UMG</h1>
      </header>

      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-6 justify-center">
        {/* PANEL DE HERRAMIENTAS */}
        <aside className="bg-slate-800/50 p-4 rounded-2xl border border-slate-700 w-full lg:w-60 space-y-4">
          <div>
            <p className="text-[10px] font-bold text-slate-500 mb-2 uppercase">Configurar Casilla</p>
            <div className="flex gap-2 mb-4">
              {['Despejado', 'Lluvia', 'Tormenta'].map(w => (
                <button key={w} onClick={() => setSelectedWeather(w)} 
                  className={`px-2 py-1 text-[10px] rounded border ${selectedWeather === w ? 'bg-cyan-600 border-cyan-400' : 'bg-slate-700 border-transparent'}`}>{w}</button>
              ))}
            </div>
            <div className="grid gap-2">
              {tools.map(t => (
                <button key={t.id} onClick={() => setSelectedTool(t.id)}
                  className={`flex items-center gap-3 p-2 rounded-xl transition-all ${selectedTool === t.id ? 'bg-blue-600' : 'bg-slate-700/50'}`}>
                  <span>{t.icon}</span> <span className="text-[10px] font-bold">{t.name}</span>
                </button>
              ))}
            </div>
          </div>
          <button onClick={generarMapaAleatorio} className="w-full py-2 bg-slate-700 hover:bg-slate-600 rounded-xl font-bold text-xs uppercase border border-slate-600 transition-all">
            🔄 Regenerar Mapa
          </button>
          {/* NUEVO BOTÓN DE RESTAURACIÓN INTEGRADO EN TU ASIDE */}
          <button onClick={restaurarEscenarioOriginal} className="w-full py-2 bg-amber-700/60 hover:bg-amber-600 rounded-xl font-bold text-xs uppercase border border-amber-600 transition-all">
            ⏪ Restaurar Escenario
          </button>
        </aside>

        {/* MAPA INTERACTIVO */}
        <section className="bg-slate-900 p-2 rounded-xl border-4 border-slate-800 shadow-2xl overflow-auto">
          <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))` }}>
            {matrix.map((row, y) => row.map((cell, x) => (
              <div key={`${x}-${y}`} onClick={() => handleCellClick(x, y)}
                className={`w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center cursor-pointer border border-white/5 relative transition-all duration-300
                  ${cell.id === 1 ? 'bg-slate-700' : 'bg-slate-900'}
                  ${cell.weather === 'Lluvia' ? 'border-b-blue-500 border-b-2 bg-blue-950/40' : ''}
                  ${cell.weather === 'Tormenta' ? 'border-b-purple-500 border-b-2 bg-purple-950/50 shadow-inner' : ''}
                  ${cell.weather === 'Despejado' ? 'border-b-transparent bg-slate-900' : ''}`}>
                
                {cell.id === 2 && <span>👤</span>}
                {cell.id === 4 && <span>🪫</span>}
                {cell.id === 5 && <span>🔋</span>}
                {cell.id === 8 && <span>🏠</span>}
                
                {agentPos[0] === x && agentPos[1] === y && (
                  <div className="absolute inset-1 flex items-center justify-center bg-blue-500 rounded z-10 animate-pulse text-xl shadow-lg">🤖</div>
                )}
              </div>
            )))}
          </div>
        </section>

        {/* CONTROLES Y PANEL DE ESTADO */}
        <aside className="w-full lg:w-64 space-y-4">
          <div className="bg-slate-800/50 p-4 rounded-2xl border border-slate-700">
            <p className="text-[10px] font-bold text-slate-500 mb-2 uppercase">Algoritmo de Búsqueda</p>
            <div className="flex gap-2">
              {['BFS', 'A*'].map(alg => (
                <button key={alg} onClick={() => setAlgorithm(alg)}
                  className={`flex-1 py-2 rounded-xl font-bold text-xs border transition-all ${algorithm === alg ? 'bg-cyan-600 border-cyan-400' : 'bg-slate-700/50 border-transparent text-slate-400'}`}>
                  {alg}
                </button>
              ))}
            </div>
          </div>

          {/* INDICADORES EN TIEMPO REAL */}
          <div className="bg-slate-800/30 p-4 rounded-2xl border border-slate-700 space-y-3">
             <div>
               <div className="flex justify-between items-center mb-1">
                 <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Energía Actual</p>
                 <span className={`text-xs font-mono font-bold ${battery <= 20 ? 'text-rose-400' : 'text-cyan-400'}`}>{battery}%</span>
               </div>
               <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden border border-slate-700">
                 <div 
                   className={`h-full transition-all duration-300 ${getBatteryColor(battery)}`}
                   style={{ width: `${battery}%` }}
                 />
               </div>
             </div>

             <div className="pt-2 border-t border-slate-700/50 space-y-1">
               <p className="text-[10px] text-slate-400 font-mono flex justify-between">
                 <span>TURNOS EN RUTA:</span> 
                 <span className="font-bold text-white">{turns}</span>
               </p>
               <p className="text-[10px] text-amber-400 font-mono flex justify-between">
                 <span>ENERGÍA CONSUMIDA:</span> 
                 <span className="font-bold">{energyConsumed} unidades</span>
               </p>
               <p className="text-[10px] text-slate-400 uppercase font-mono flex justify-between pt-1">
                 <span>PERSONAS RESTANTES:</span>
                 <span className="font-bold text-white">{matrix.flat().filter(c => c.id === 2).length}</span>
               </p>
             </div>
          </div>
          
          <button onClick={enviarAlBackend} className="w-full py-4 bg-blue-600 rounded-2xl font-bold uppercase tracking-widest hover:bg-blue-500 transition-all shadow-lg text-sm">
            INICIAR RESCATE
          </button>
        </aside>
      </div>
    </div>
  );
}

export default App;