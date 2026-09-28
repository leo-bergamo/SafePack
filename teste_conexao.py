from dotenv import load_dotenv
import os

load_dotenv()
database_url = os.getenv("DATABASE_URL")
if database_url:
    print("Variavel DATABASE_URL foi encontrada:", database_url)
else:
    print("A variavel DATABASE_URL nao esta definida!")