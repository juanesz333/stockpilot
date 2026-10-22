#lee el .env y entrega los datos ordenados 
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# carga el archivo .env buscandolo en la raíz del proyecto
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

#es una dataclass que solo guarda datos
#Con frozen=true no se modificar despues de crarla 
@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

#lee las variables con os.environ[...]
#si falta alguna variable lanza un error con el nombre
#de la variable que falta
def load_database_config() -> DatabaseConfig:
    try:
        return DatabaseConfig(
            host=os.environ["DB_HOST"],
            port=int(os.environ["DB_PORT"]),
            name=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
        )
    except KeyError as exc:
        raise RuntimeError(
            f"Falta la variable {exc.args[0]}. Revisa tu archivo .env"
        ) from exc