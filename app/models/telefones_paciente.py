from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    text
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.dados_cliente import DadosCliente

class TelefonesPaciente(Base):
    __tablename__ = "telefones_paciente"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cliente_codigo = Column(BigInteger, ForeignKey("dados_cliente.id", ondelete="CASCADE"), nullable=False)
    numero = Column(String, nullable=True)
    tipo = Column(String, nullable=True)  # 'whatsapp', 'telefone fixo'
    is_principal = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    # Relacionamento para facilitar acesso reverso se necessário (patient.telefones)
    cliente = relationship("DadosCliente", backref="telefones")