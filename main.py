from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Mission(BaseModel):
    matrix: List[List[dict]]
    start_pos: List[int]

@app.post("/solve")
async def solve(data: Mission):
    # Aquí es donde llamas a la clase AgenteLogico de tu compañero
    # Por ahora devolvemos una ruta de prueba:
    return {"ruta": [[0,0], [0,1], [0,2], [1,2], [2,2]]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)