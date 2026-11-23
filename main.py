from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from motor_licitacoes import (
    calcular_distancia,
    consultar_oportunidades,
    obter_licitacoes_cacheadas,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Buscador de Licitações - SRE Divinópolis")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class DistanciaRequest(BaseModel):
    endereco_empresa: dict
    endereco_licitacao: str


@app.get("/")
def pagina_inicial():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status_documento():
    try:
        cache = obter_licitacoes_cacheadas(forcar=False)
        return {
            "ok": True,
            "mes_referencia": cache["mes_referencia"],
            "total_licitacoes": len(cache["licitacoes"]),
            "atualizado_em": cache["atualizado_fmt"],
            "url": cache["url"],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/atualizar")
def atualizar_documento():
    try:
        cache = obter_licitacoes_cacheadas(forcar=True)
        return {
            "ok": True,
            "mes_referencia": cache["mes_referencia"],
            "total_licitacoes": len(cache["licitacoes"]),
            "atualizado_em": cache["atualizado_fmt"],
            "url": cache["url"],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/consultar/{cnpj}")
def consultar_cnpj(cnpj: str):
    try:
        return consultar_oportunidades(cnpj)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/distancia")
def rota_distancia(payload: DistanciaRequest):
    resultado = calcular_distancia(payload.endereco_empresa, payload.endereco_licitacao)
    return {"distancia": resultado}