from app.models.enums import SistemaOrigem
from sqlalchemy import (
    Column,
    BigInteger,
    DateTime,
    Text,
    SmallInteger,
    Date,
    Time,
    Boolean,
    Numeric,
    String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from app.core.database import Base


class Agendamento(Base):
    __tablename__ = "agendamentos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    id_cliente = Column(BigInteger, nullable=True) # Should be FK
    telefone = Column(Text, nullable=True)
    codigo = Column(SmallInteger, nullable=True)
    cpf = Column(Text, nullable=True)
    nome_paciente = Column(Text, nullable=True)
    data_nascimento = Column(Date, nullable=True)
    especialidade = Column(Text, nullable=True)
    profissional = Column(Text, nullable=True)
    data_consulta = Column(Date, nullable=False)
    hora_consulta = Column(Time, nullable=False)
    status = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    convenio = Column(String, nullable=True)
    primeira_consulta = Column(Boolean, nullable=True)
    confirmado_pelo_paciente = Column(Boolean, nullable=True)
    lembrete_enviado = Column(Boolean, nullable=True)
    canal_agendamento = Column(Text, nullable=True)
    procedimento = Column(String(255), nullable=True)
    valor = Column(Numeric(10, 2), nullable=True)

    retorno_ate = Column(Date, nullable=True)
    sistema_origem = Column(
        PG_ENUM(SistemaOrigem, name='sistema_origem_enum', create_type=False),
        nullable=True
    )
