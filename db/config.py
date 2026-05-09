import os
from dotenv import load_dotenv

load_dotenv()

class DBConfig:
    def __init__(self):
        load_dotenv()  # called again inside to guarantee env is loaded
        self.host     = os.getenv("DB_HOST", "localhost")
        self.port     = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "chatdb")
        self.user     = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "")

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"