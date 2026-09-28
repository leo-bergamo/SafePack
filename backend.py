import asyncio
from datetime import date
from database import get_connection
import logging

# AVISO: este módulo duplica a lógica dos endpoints /registrar_entrega/ e
# /registrar_retirada/ já implementados em main.py (que é o backend ativo,
# usado pelo front-end em cadastro.html/retirada.html). Ele usa asyncpg puro
# em vez de SQLAlchemy e não está conectado a nenhum endpoint FastAPI.
# Mantenha apenas um dos dois caminhos de acesso a dados para evitar
# divergência de schema entre backend.py e database.py/main.py.

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Função para registrar a entrega de encomenda
async def registrar_entrega(cpf_morador, num_apartamento, id_recebedor, nome_recebedor, data_recebido, descricao=""):
    conn = await get_connection()
    try:
        # Validação de dados
        if not cpf_morador or not num_apartamento or not id_recebedor or not nome_recebedor or not data_recebido:
            raise ValueError("Todos os campos obrigatórios devem ser preenchidos.")

        # Inserir dados na tabela entrega
        await conn.execute(
            """
            INSERT INTO entrega (cpf_morador, num_apartamento, id_recebedor, nome_recebedor, data_recebido, descricao, status)
            VALUES ($1, $2, $3, $4, $5, $6, 'não entregue')
            """,
            cpf_morador, num_apartamento, id_recebedor, nome_recebedor, data_recebido, descricao
        )
        logger.info("✅ Entrega registrada com sucesso!")
    except ValueError as ve:
        logger.error(f"❌ Erro de validação: {ve}")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar entrega: {e}")
    finally:
        await conn.close()

# Função para registrar a retirada de encomenda
async def registrar_retirada(num_apartamento, cpf_morador, nome_morador, data_retirada):
    conn = await get_connection()
    try:
        # Validação de dados
        if not num_apartamento or not cpf_morador or not nome_morador or not data_retirada:
            raise ValueError("Todos os campos obrigatórios devem ser preenchidos.")

        # Inserindo na tabela de retiradas
        await conn.execute(
            """
            INSERT INTO retirada (num_apartamento, cpf_morador, nome_morador, data_retirada)
            VALUES ($1, $2, $3, $4)
            """,
            num_apartamento, cpf_morador, nome_morador, data_retirada
        )

        # Atualizando o status da entrega para "entregue"
        resultado = await conn.execute(
            """
            UPDATE entrega SET status = 'entregue'
            WHERE num_apartamento = $1 AND cpf_morador = $2
            """,
            num_apartamento, cpf_morador
        )

        # Verificação se algo foi atualizado
        if resultado.rowcount == 0:
            raise ValueError("Nenhuma entrega correspondente encontrada para atualizar.")

        logger.info("✅ Retirada registrada e status atualizado!")
    except ValueError as ve:
        logger.error(f"❌ Erro de validação: {ve}")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar retirada: {e}")
    finally:
        await conn.close()
