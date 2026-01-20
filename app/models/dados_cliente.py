from sqlalchemy import (
    Column,
    String,
    Date,
    SmallInteger,
    BigInteger,
    DateTime,
)
from app.core.database import Base
from datetime import datetime, timezone


class DadosCliente(Base):
    __tablename__ = "dados_cliente"

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    telefone = Column(String(20), nullable=True)
    nomewpp = Column(String(100), nullable=True)
    atendimento_ia = Column(String(100), nullable=True)
    setor = Column(String(100), nullable=True)
    cpf = Column(String(11), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    cad_telefone = Column(String(20), nullable=True)
    codigo = Column(SmallInteger, nullable=True)
