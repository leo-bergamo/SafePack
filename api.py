from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from datetime import date
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

# Modelo de dados esperado pelo backend
class Encomenda(BaseModel):
    num_apartamento: int
    nome: str
    dataRecebimento: date
    recebidoPor: str
    descricaoProduto: str

    # Validador para garantir que o nome não seja vazio
    @validator("nome", "recebidoPor", "descricaoProduto")
    def nao_vazio(cls, v, field):
        if not v or not v.strip():
            raise ValueError(f"O campo '{field.name}' não pode estar vazio!")
        return v

@app.post("/registrar_encomenda/")
async def registrar_encomenda(encomenda: Encomenda, db: AsyncSession = Depends(get_db)):
    try:
        # Inserir dados no banco de dados
        query = """
            INSERT INTO entrega (num_apartamento, nome_morador, data_recebido, nome_recebedor, descricao, status)
            VALUES (:num_apartamento, :nome, :dataRecebimento, :recebidoPor, :descricaoProduto, 'não entregue')
        """
        await db.execute(query, encomenda.dict())
        await db.commit()

        logger.info(f"Encomenda registrada: {encomenda}")
        return {"message": "Encomenda registrada com sucesso!"}

    except Exception as e:
        logger.error(f"Erro ao registrar encomenda: {e}")
        raise HTTPException(status_code=400, detail="Erro ao registrar encomenda. Consulte os logs para mais detalhes.")
    
@app.get("/")
async def read_root():
    return {"message": "API do Controle de Encomendas funcionando!"}

