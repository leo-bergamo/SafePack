from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from datetime import date
import asyncpg
import re
import secrets
from database import get_db, criar_tabelas_se_sqlite, seed_dados_exemplo_se_sqlite
from database import Base
from database import Funcionario
from sqlalchemy import select
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession  # IMPORTANTE!
from sqlalchemy import text  # Import necessário
import logging

# Configurar o logger (precisa vir antes de qualquer uso de `logger`)
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    # Só tem efeito quando rodando com o SQLite local de teste (sem DATABASE_URL configurada)
    await criar_tabelas_se_sqlite()
    await seed_dados_exemplo_se_sqlite()


# Configuração de CORS
# ATENÇÃO: "*" combinado com allow_credentials=True é inseguro em produção.
# Trocar por uma lista explícita de origens (ex.: allow_origins=["https://seu-dominio.com"])
# antes de publicar o sistema.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir requisições de qualquer origem durante o desenvolvimento
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos os métodos HTTP (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos os cabeçalhos
)


# Modelo de dados para moradores
class MoradorResponse(BaseModel):
    moradores: list[str]


# Modelo para cadastro de entrega
class EntregaEntrada(BaseModel):
    num_apartamento: int
    nome_morador: str
    data_recebida: date
    nome_recebedor: str
    descricao: str = ""
    id_cracha: int  # Deve ser obrigatório e numérico


def _validar_cpf(valor: str) -> str:
    """Normaliza e valida um CPF (aceita com ou sem pontuação; checa os 11 dígitos e os dígitos verificadores)."""
    cpf = re.sub(r"\D", "", valor or "")
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValueError("CPF inválido. Informe os 11 dígitos do CPF.")

    def digito_verificador(cpf_parcial: str) -> str:
        soma = sum(int(d) * peso for d, peso in zip(cpf_parcial, range(len(cpf_parcial) + 1, 1, -1)))
        resto = (soma * 10) % 11
        return "0" if resto == 10 else str(resto)

    if digito_verificador(cpf[:9]) != cpf[9] or digito_verificador(cpf[:10]) != cpf[10]:
        raise ValueError("CPF inválido. Verifique os dígitos informados.")
    return cpf


class RetiradaEntrada(BaseModel):
    num_apartamento: int
    cpf_morador: str
    nome_morador: str
    data_retirada: date
    # Código gerado no recebimento; só é obrigatório quando a retirada é de UMA encomenda
    # específica. Quando "retirar_todas" é True (retirada de todas as pendências do
    # apartamento de uma vez), o código individual de cada etiqueta é dispensado.
    codigo_retirada: str | None = None
    retirar_todas: bool = False

    # OBS: a validação do CPF é feita manualmente dentro do endpoint (e não com um
    # @validator do Pydantic) para que o erro volte ao front como um HTTPException
    # normal (detail em texto), igual aos demais erros da API. Quando o Pydantic
    # valida o campo, o FastAPI responde 422 com "detail" sendo uma LISTA de objetos,
    # e o front (que espera uma string em erro.detail) mostrava uma mensagem confusa.


# Modelo para cadastro de morador
class MoradorEntrada(BaseModel):
    num_apartamento: int
    nome_morador: str
    cpf_morador: str
    torre: str = ""


# Endpoint para cadastrar um morador
@app.post("/moradores/")
async def registrar_morador(morador: MoradorEntrada, db: AsyncSession = Depends(get_db)):
    if not morador.nome_morador or not morador.nome_morador.strip():
        raise HTTPException(status_code=400, detail="O nome do morador não pode estar vazio.")
    try:
        cpf_normalizado = _validar_cpf(morador.cpf_morador)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    morador.nome_morador = morador.nome_morador.strip()
    morador.cpf_morador = cpf_normalizado

    try:
        query_check = text("SELECT COUNT(*) FROM morador WHERE cpf_morador = :cpf_morador")
        result = await db.execute(query_check, {"cpf_morador": morador.cpf_morador})
        if result.scalar():
            raise HTTPException(status_code=400, detail="Já existe um morador cadastrado com esse CPF.")

        query = text("""
            INSERT INTO morador (num_apartamento, torre, nome_morador, cpf_morador)
            VALUES (:num_apartamento, :torre, :nome_morador, :cpf_morador)
        """)
        await db.execute(query, morador.dict())
        await db.commit()
        return {"message": "Morador cadastrado com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cadastrar morador: {e}")
        raise HTTPException(status_code=400, detail="Erro ao cadastrar morador. Verifique os dados e tente novamente.")


# Endpoint para listar todos os moradores cadastrados (usado na tela de gestão)
@app.get("/moradores-cadastrados/")
async def listar_todos_moradores(db: AsyncSession = Depends(get_db)):
    query = text("SELECT id, num_apartamento, torre, nome_morador, cpf_morador FROM morador ORDER BY num_apartamento")
    result = await db.execute(query)
    return {"moradores": [dict(row) for row in result.mappings().all()]}


# Endpoint para excluir um morador cadastrado (usado na tela de gestão)
@app.delete("/moradores/{morador_id}")
async def excluir_morador(morador_id: int, db: AsyncSession = Depends(get_db)):
    query_check = text("SELECT COUNT(*) FROM morador WHERE id = :id")
    result = await db.execute(query_check, {"id": morador_id})
    if not result.scalar():
        raise HTTPException(status_code=404, detail="Morador não encontrado.")

    query_delete = text("DELETE FROM morador WHERE id = :id")
    await db.execute(query_delete, {"id": morador_id})
    await db.commit()
    return {"message": "Morador excluído com sucesso!"}


# Endpoint para listar as retiradas mais recentes (qualquer apartamento) — usado na tela
# de retirada para o porteiro conferir rapidamente quem já retirou encomendas há pouco.
@app.get("/retiradas/recentes")
async def listar_retiradas_recentes(limite: int = 10, db: AsyncSession = Depends(get_db)):
    limite = max(1, min(limite, 50))
    query = text("""
        SELECT num_apartamento, nome_morador, data_retirada
        FROM retirada
        ORDER BY id DESC
        LIMIT :limite
    """)
    result = await db.execute(query, {"limite": limite})
    return {
        "retiradas": [
            {
                "num_apartamento": row.num_apartamento,
                "nome_morador": row.nome_morador,
                "data_retirada": row.data_retirada,
            }
            for row in result.mappings().all()
        ]
    }


# Endpoint para listar moradores pelo número do apartamento
@app.get("/moradores/{num_apartamento}", response_model=MoradorResponse)
async def get_moradores(num_apartamento: int, db: AsyncSession = Depends(get_db)):
    query = text("SELECT nome_morador FROM morador WHERE num_apartamento = :num_apartamento")
    result = await db.execute(query, {"num_apartamento": num_apartamento})
    moradores = [row.nome_morador for row in result.mappings().all()]

    if not moradores:
        return {"moradores": []}  # Retorna uma lista vazia se nenhum morador for encontrado
    return {"moradores": moradores}


# Endpoint para listar os apartamentos que possuem encomenda pendente de retirada
# (usado na tela de retirada para o porteiro selecionar o apartamento em vez de digitar).
@app.get("/encomendas-pendentes/apartamentos")
async def listar_apartamentos_com_pendencia(db: AsyncSession = Depends(get_db)):
    query = text("""
        SELECT num_apartamento, COUNT(*) AS quantidade
        FROM entrega
        WHERE status = 'não entregue'
        GROUP BY num_apartamento
        ORDER BY num_apartamento
    """)
    result = await db.execute(query)
    return {
        "apartamentos": [
            {"num_apartamento": row.num_apartamento, "quantidade": row.quantidade}
            for row in result.mappings().all()
        ]
    }


# Endpoint para listar encomendas pendentes de retirada de um apartamento
@app.get("/encomendas/{num_apartamento}")
async def get_encomendas(num_apartamento: int, db: AsyncSession = Depends(get_db)):
    query = text("""
        SELECT id, num_apartamento, nome_morador, data_recebido, nome_recebedor, descricao
        FROM entrega
        WHERE num_apartamento = :num_apartamento AND status = 'não entregue'
        ORDER BY data_recebido
    """)
    result = await db.execute(query, {"num_apartamento": num_apartamento})
    encomendas = [
        {
            "id": row.id,
            "dataChegada": row.data_recebido,
            "nome": row.nome_morador,
            "descricao": row.descricao,
        }
        for row in result.mappings().all()
    ]
    return {"encomendas": encomendas}


# Endpoint para cadastrar entrega
@app.post("/registrar_entrega/")
async def registrar_entrega(entrega: EntregaEntrada, db: AsyncSession = Depends(get_db)):
    try:
        # Código de 6 dígitos que o morador (ou quem retirar) deverá informar na retirada
        codigo_retirada = f"{secrets.randbelow(1_000_000):06d}"
        dados = entrega.dict()
        dados["codigo_retirada"] = codigo_retirada

        query = text("""
            INSERT INTO entrega (num_apartamento, nome_morador, data_recebido, nome_recebedor, descricao, status, id_cracha, codigo_retirada)
            VALUES (:num_apartamento, :nome_morador, :data_recebida, :nome_recebedor, :descricao, 'não entregue', :id_cracha, :codigo_retirada)
        """)
        await db.execute(query, dados)
        await db.commit()
        return {
            "message": "Entrega registrada com sucesso!",
            "codigo_retirada": codigo_retirada,
        }
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Duplicação detectada. Verifique os dados.")
    except Exception as e:
        logger.error(f"Erro ao registrar entrega: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/entregas/pendentes/contagem")
async def contar_entregas_pendentes(db: AsyncSession = Depends(get_db)):
    """Total de encomendas ainda não retiradas — usado no painel inicial."""
    query = text("SELECT COUNT(*) FROM entrega WHERE status = 'não entregue'")
    result = await db.execute(query)
    return {"pendentes": result.scalar() or 0}


@app.get("/entregas/")
async def listar_entregas(db: AsyncSession = Depends(get_db)):
    # Corrigido: a tabela é "funcionario" (singular) e a PK é "id_cracha", não "funcionarios.id"
    query = text("""
        SELECT e.*, f.nome_func AS nome_recebedor
        FROM entrega e
        JOIN funcionario f ON e.id_cracha = f.id_cracha
    """)
    result = await db.execute(query)
    entregas = result.mappings().all()
    return {"entregas": [dict(entrega) for entrega in entregas]}


@app.get("/funcionario/")
async def listar_funcionarios(id_cracha: int, db: AsyncSession = Depends(get_db)):
    try:
        query = select(Funcionario).where(Funcionario.id_cracha == id_cracha)
        result = await db.execute(query)
        funcionarios = result.scalars()
        return {
            "funcionario": [
                {"id_cracha": f.id_cracha, "nome_func": f.nome_func} for f in funcionarios
            ]
        }
    except Exception as e:
        logger.error(f"Erro ao listar funcionários: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@app.get("/funcionarios/")
async def listar_todos_funcionarios(db: AsyncSession = Depends(get_db)):
    query = select(Funcionario)
    result = await db.execute(query)
    funcionarios = result.scalars().all()
    return {"funcionarios": [{"id_cracha": f.id_cracha, "nome_func": f.nome_func} for f in funcionarios]}


# Endpoint para registrar uma retirada
@app.post("/registrar_retirada/")
async def registrar_retirada(retirada: RetiradaEntrada, db: AsyncSession = Depends(get_db)):
    try:
        retirada.cpf_morador = _validar_cpf(retirada.cpf_morador)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        if retirada.retirar_todas:
            # Retirada de TODAS as encomendas pendentes do apartamento de uma vez: não
            # exige o código individual de cada etiqueta, e não filtra por nome do
            # destinatário (cada encomenda pode ter um destinatário diferente dentro do
            # mesmo apartamento) — considera só o número do apartamento e o status.
            query_check = text("""
                SELECT COUNT(*)
                FROM entrega
                WHERE num_apartamento = :num_apartamento
                  AND status = 'não entregue'
            """)
            result = await db.execute(query_check, retirada.dict())
            count = result.scalar()

            if count == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Nenhuma entrega pendente encontrada para este apartamento.",
                )
        else:
            # Retirada de UMA encomenda específica: exige o código de retirada da etiqueta.
            if not retirada.codigo_retirada or not retirada.codigo_retirada.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Informe o código de retirada que está na etiqueta da encomenda.",
                )

            # Verificar se a entrega existe, está pendente e o código de retirada confere
            query_check = text("""
                SELECT COUNT(*)
                FROM entrega
                WHERE num_apartamento = :num_apartamento AND nome_morador = :nome_morador
                  AND status = 'não entregue' AND codigo_retirada = :codigo_retirada
            """)
            result = await db.execute(query_check, retirada.dict())
            count = result.scalar()

            if count == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Nenhuma entrega pendente encontrada com esse código para este morador. Verifique o código informado na etiqueta.",
                )

        # Insere primeiro a retirada, para termos o "id" dela e vincular corretamente
        # às encomendas que ela baixou (evita que o histórico misture retiradas e
        # encomendas de datas diferentes quando há mais de uma por apartamento).
        query_insert = text("""
            INSERT INTO retirada (num_apartamento, cpf_morador, nome_morador, data_retirada)
            VALUES (:num_apartamento, :cpf_morador, :nome_morador, :data_retirada)
        """)
        insert_result = await db.execute(query_insert, retirada.dict())
        retirada_id = insert_result.lastrowid

        if retirada.retirar_todas:
            query_update = text("""
                UPDATE entrega SET status = 'entregue', retirada_id = :retirada_id
                WHERE num_apartamento = :num_apartamento
                  AND status = 'não entregue'
            """)
            await db.execute(query_update, {**retirada.dict(), "retirada_id": retirada_id})
        else:
            # Atualiza o status na tabela entrega
            query_update = text("""
                UPDATE entrega SET status = 'entregue', retirada_id = :retirada_id
                WHERE num_apartamento = :num_apartamento AND nome_morador = :nome_morador
                  AND codigo_retirada = :codigo_retirada
            """)
            await db.execute(query_update, {**retirada.dict(), "retirada_id": retirada_id})

        await db.commit()

        return {"message": "Retirada registrada com sucesso!"}
    except HTTPException:
        raise
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Duplicação detectada. Verifique os dados.")
    except Exception as e:
        logger.error(f"Erro ao registrar retirada: {e}")
        raise HTTPException(status_code=400, detail="Erro ao registrar retirada. Consulte os logs para mais detalhes.")


# Endpoint de histórico: encomendas já retiradas de um apartamento
@app.get("/historico/{num_apartamento}")
async def get_historico(num_apartamento: int, db: AsyncSession = Depends(get_db)):
    # Junta pelo vínculo real (entrega.retirada_id = retirada.id) em vez de só pelo
    # número do apartamento — antes, apartamentos com mais de uma encomenda/retirada
    # geravam combinações erradas (produto cartesiano) e o histórico ficava incorreto.
    query = text("""
        SELECT e.nome_morador, e.data_recebido, e.descricao,
               r.nome_morador AS retirado_por, r.data_retirada
        FROM entrega e
        JOIN retirada r ON r.id = e.retirada_id
        WHERE e.num_apartamento = :num_apartamento AND e.status = 'entregue'
        ORDER BY r.data_retirada DESC
    """)
    result = await db.execute(query, {"num_apartamento": num_apartamento})
    historico = [
        {
            "destinatario": row.nome_morador,
            "dataChegada": row.data_recebido,
            "descricao": row.descricao,
            "retiradoPor": row.retirado_por,
            "dataRetirada": row.data_retirada,
        }
        for row in result.mappings().all()
    ]
    return {"historico": historico}


@app.get("/test-db/")
async def test_db(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        return {"status": "Conexão OK!", "resultado": result.scalar()}
    except Exception as e:
        logger.error(f"Erro na conexão: {e}")
        return {"status": "Erro", "detalhes": str(e)}


@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API do sistema de controle de encomendas!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
