from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ENUM
from app.core.database import Base


class Profissional(Base):
    __tablename__ = "profissionais"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.now(timezone.utc))
    nome_completo = Column(String, nullable=False)
    nome_exibicao = Column(String, nullable=False)
    especialidade = Column(String, nullable=False)
    crm_registro = Column(String)
    duracao_consulta = Column(Integer)
    intervalo_consultas = Column(Integer)
    horarios_atendimento = Column(JSON)
    ativo = Column(Boolean)
    aceita_novos_pacientes = Column(Boolean, default=True)
    email = Column(String)
    telefone = Column(String)
    observacoes = Column(Text)
    config_atendimento = Column(JSON)
    rqe = Column(String)
    codigo = Column(String)
    sistema_origem = Column(ENUM("sistema_origem_enum", name="sistema_origem_enum"))

    __table_args__ = (
        Index("idx_profissionais_config_atendimento", "config_atendimento", postgresql_using="gin"),
        Index(
            "idx_profissionais_especialidade_ativo",
            "especialidade",
            "ativo",
            postgresql_where=text("ativo = true"),
        ),
        UniqueConstraint("codigo", "sistema_origem", name="idx_profissionais_unico"),
    )