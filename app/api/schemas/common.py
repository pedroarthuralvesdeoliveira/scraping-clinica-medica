from pydantic import BaseModel, Field
from typing import Optional


# ============================================================================
# REQUEST PAYLOADS (INPUT)
# ============================================================================

class SchedulePayload(BaseModel):
    """Payload para agendamento de consulta"""
    medico: str
    data_desejada: str = Field(..., description="Data no formato DD/MM/YYYY")
    horario_desejado: str = Field(..., description="Horário no formato HH:MM")
    nome_paciente: str
    data_nascimento: str = Field(..., description="Data no formato DD/MM/YYYY")
    cpf: str
    telefone: str
    tipo_atendimento: str
    convenio: Optional[str] = None


class CancelPayload(BaseModel):
    """Payload para cancelamento de consulta"""
    data_desejada: str = Field(..., description="Data no formato DD/MM/YYYY")
    horario_desejado: str = Field(..., description="Horário no formato HH:MM")
    medico: str
    nome_paciente: str
    cpf: Optional[str] = None


class SyncPayload(BaseModel):
    """Payload para sincronização de agendamentos"""
    cpf: str
    nome_paciente: Optional[str] = None
    medico: Optional[str] = None
    codigo: Optional[str] = None


class VerifyPayload(BaseModel):
    """Payload para verificação de disponibilidade"""
    data_desejada: Optional[str] = Field(None, description="Data no formato DD/MM/YYYY")
    horario_desejado: Optional[str] = Field(None, description="Horário no formato HH:MM")
    horario_inicial: Optional[str] = Field(None, description="Horário inicial no formato HH:MM")
    horario_final: Optional[str] = Field(None, description="Horário final no formato HH:MM")
    medico: str
