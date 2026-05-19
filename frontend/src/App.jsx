import { useState } from 'react';
import axios from 'axios';

function App() {
  const size = 15;
  const [matrix, setMatrix] = useState(
    Array(size).fill(0).map(() => Array(size).fill({ id: 0, weather: 'Despejado' }))
  );
  const [selectedTool, setSelectedTool] = useState(1);
  const [selectedWeather, setSelectedWeather] = useState('Despejado');
  const [agentPos, setAgentPos] = useState([0, 0]);
  const [turns, setTurns] = useState(0);

  const tools = [
    { id: 1, name: 'Muro', icon: '⬛' },
    { id: 2, name: 'Persona', icon: '👤' },
    { id: 4, name: 'Bat. 40%', icon: '🔋' },
    { id: 5, name: 'Bat. 100%', icon: '⚡' },
    { id: 8, name: 'Zona Segura', icon: '🏠' },
    { id: 7, name: 'Robot (Inicio)', icon: '🤖' },
    { id: 0, name: 'Borrador', icon: '🗑️' },
  ];

  const handleCellClick = (x, y) => {
    if (selectedTool === 7) {
      setAgentPos([x, y]);
    } else {
      const newMatrix = [...matrix];
      newMatrix[y][x] = { id: selectedTool, weather: selectedWeather };
      setMatrix(newMatrix);
    }
  };

  const enviarAlBackend = async () => {
    try {
      const res = await axios.post('http://localhost:8000/solve', {
        matrix: matrix,
        start_pos: agentPos
      });
      // Animación de la ruta recibida
      res.data.ruta.forEach((paso, i) => {
        setTimeout(() => {
          setAgentPos([paso[1], paso[0]]);
          setTurns(i + 1);
        }, i * 400);
      });
    } catch (err) {
      alert("Error: Verifica que el servidor Python esté corriendo en el puerto 8000");
    }
  };

  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-200 p-4 font-sans">
      <header className="max-w-6xl mx-auto mb-6 text-center">
        <h1 className="text-3xl font-black text-cyan-400">RESCUE SYSTEM UMG</h1>
      </header>

      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-6 justify-center">
        {/* PANEL DE HERRAMIENTAS */}
        <aside className="bg-slate-800/50 p-4 rounded-2xl border border-slate-700 w-full lg:w-60">
          <p className="text-[10px] font-bold text-slate-500 mb-2 uppercase">Configurar Casilla</p>
          <div className="flex gap-2 mb-4">
            {['Despejado', 'Lluvia', 'Tormenta'].map(w => (
              <button key={w} onClick={() => setSelectedWeather(w)} 
                className={`px-2 py-1 text-[10px] rounded border ${selectedWeather === w ? 'bg-cyan-600' : 'bg-slate-700'}`}>{w}</button>
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
        </aside>

        {/* MAPA */}
        <section className="bg-slate-900 p-2 rounded-xl border-4 border-slate-800 shadow-2xl overflow-auto">
          <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))` }}>
            {matrix.map((row, y) => row.map((cell, x) => (
              <div key={`${x}-${y}`} onClick={() => handleCellClick(x, y)}
                className={`w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center cursor-pointer border border-white/5 relative
                  ${cell.id === 1 ? 'bg-slate-700' : 'bg-slate-900'}
                  ${cell.weather === 'Lluvia' ? 'border-b-blue-500 border-b-2' : ''}
                  ${cell.weather === 'Tormenta' ? 'border-b-purple-500 border-b-2' : ''}`}>
                {cell.id === 2 && <span>👤</span>}
                {cell.id === 4 && <span>🔋</span>}
                {cell.id === 5 && <span>⚡</span>}
                {cell.id === 8 && <span>🏠</span>}
                {agentPos[0] === x && agentPos[1] === y && (
                  <div className="absolute inset-1 flex items-center justify-center bg-blue-500 rounded z-10 animate-pulse text-xl">🤖</div>
                )}
              </div>
            )))}
          </div>
        </section>

        {/* BOTÓN ACCIÓN */}
        <aside className="w-full lg:w-64 space-y-4">
          <div className="bg-slate-800/30 p-4 rounded-2xl border border-slate-700">
             <p className="text-[10px] text-slate-400">TURNOS: {turns}</p>
             <p className="text-[10px] text-slate-400 uppercase">PERSONAS: {matrix.flat().filter(c => c.id === 2).length}</p>
          </div>
          <button onClick={enviarAlBackend} className="w-full py-4 bg-blue-600 rounded-2xl font-bold uppercase tracking-widest hover:bg-blue-500 transition-all shadow-lg">
            INICIAR RESCATE
          </button>
        </aside>
      </div>
    </div>
  );
}

export default App; // ESTA LÍNEA ES VITAL PARA TU ERROR