import os
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import logging
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base



Base = declarative_base()

class Funcionario(Base):
    __tablename__ = 'funcionario'
    id_cracha = Column(Integer, primary_key=True, index=True)
    nome_func = Column(String, nullable=False)
    cpf_func = Column(String, nullable=False)  
    funcao = Column(String, nullable=False)

class Morador(Base):
    __tablename__ = 'morador'
    # PK própria — antes num_apartamento era a chave primária, o que impedia
    # cadastrar mais de um morador por apartamento (cenário comum: casal, família).
    id = Column(Integer, primary_key=True, autoincrement=True)
    num_apartamento = Column(Integer, nullable=False, index=True)
    torre = Column(String)
    nome_morador = Column(String, nullable=False)
    cpf_morador = Column(String, nullable=False, unique=True)

class Entrega(Base):
    __tablename__ = 'entrega'
    # PK própria (autoincrement) em vez de num_apartamento — permite múltiplas
    # encomendas para o mesmo apartamento, o que é o cenário real de uso.
    id = Column(Integer, primary_key=True, autoincrement=True)
    num_apartamento = Column(Integer, nullable=False, index=True)
    id_cracha = Column(Integer, nullable=False)
    data_recebido = Column(String, nullable=False)
    descricao = Column(String)
    cpf_morador = Column(String)
    status = Column(String, nullable=False)
    nome_recebedor = Column(String, nullable=False)
    nome_morador = Column(String)
    # Código gerado no recebimento; deve ser informado por quem for retirar a
    # encomenda, evitando que a retirada seja liberada só por saber o nome do morador.
    codigo_retirada = Column(String, nullable=True)
    # Vínculo com a retirada que baixou esta encomenda (preenchido no momento da
    # retirada). Sem isso, o histórico só podia juntar as tabelas pelo número do
    # apartamento, o que misturava retiradas/encomendas de datas diferentes assim
    # que havia mais de uma de cada por apartamento.
    retirada_id = Column(Integer, nullable=True, index=True)

class Retirada(Base):
    __tablename__ = 'retirada'
    id = Column(Integer, primary_key=True, autoincrement=True)
    num_apartamento = Column(Integer, nullable=False, index=True)
    cpf_morador = Column(String, nullable=False)
    nome_morador = Column(String, nullable=False)
    data_retirada = Column(String, nullable=False)

class Historico(Base):
    __tablename__ = 'historico'
    id = Column(Integer, primary_key=True, autoincrement=True)
    num_apartamento = Column(Integer, nullable=False, index=True)
    data_chegada = Column(String)
    data_retirada = Column(String)
    cpf_retirada = Column(String)
    nome_retirada = Column(String)

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Obter URL do banco de dados de uma variável de ambiente.
# Se não estiver definida (ex.: ambiente de teste local), cai para um banco
# SQLite local, permitindo rodar e testar o sistema sem credenciais reais.
DATABASE_URL = os.getenv("DATABASE_URL")
USANDO_SQLITE_LOCAL = not DATABASE_URL
if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///./safepack_local.db"
    logger.warning(
        "DATABASE_URL não configurada — usando banco local SQLite (%s) apenas para desenvolvimento/teste.",
        DATABASE_URL,
    )

# Configuração para SQLAlchemy
try:
    engine = create_async_engine(DATABASE_URL, echo=True)  # Desative o echo em produção
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Conexão com o banco de dados configurada com sucesso!")
except Exception as e:
    logger.error(f"Erro ao configurar o banco de dados: {e}")
    raise


async def criar_tabelas_se_sqlite():
    """Cria as tabelas automaticamente quando rodando com o SQLite local de teste
    (em produção com Postgres, as tabelas devem ser geridas por migração)."""
    if USANDO_SQLITE_LOCAL:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Migração leve para bancos locais já existentes (criados antes da coluna
            # retirada_id existir) — ignora o erro se a coluna já estiver presente.
            from sqlalchemy import text as _text
            try:
                await conn.execute(_text("ALTER TABLE entrega ADD COLUMN retirada_id INTEGER"))
            except Exception:
                pass  # coluna já existe


async def seed_dados_exemplo_se_sqlite():
    """Popula funcionário(s) e morador(es) de exemplo no banco local de teste,
    só na primeira vez (não faz nada se já existir dado ou se não for SQLite local)."""
    if not USANDO_SQLITE_LOCAL:
        return
    from sqlalchemy import text as _text
    async with AsyncSessionLocal() as session:
        existentes = await session.execute(_text("SELECT COUNT(*) FROM funcionario"))
        if existentes.scalar():
            return
        await session.execute(_text(
            "INSERT INTO funcionario (id_cracha, nome_func, cpf_func, funcao) VALUES "
            "(1, 'João Porteiro', '11144477735', 'Porteiro'), "
            "(2, 'Maria Zeladora', '52998224725', 'Zeladora')"
        ))
        await session.execute(_text(
            "INSERT INTO morador (num_apartamento, torre, nome_morador, cpf_morador) VALUES "
            "(101, 'A', 'Ana Souza', '39053344705'), "
            "(102, 'A', 'Carlos Lima', '85213648576')"
        ))
        await session.commit()
        logger.info("Dados de exemplo inseridos no banco local (funcionário/morador).")

# Função para obter uma sessão do banco de dados
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Erro durante a sessão do banco de dados: {e}")
            raise


# Conexão raw via asyncpg, usada por backend.py (queries manuais fora do SQLAlchemy).
# asyncpg não aceita o driver "+asyncpg" no DSN, então normalizamos a URL aqui.
async def get_connection():
    dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(dsn)
