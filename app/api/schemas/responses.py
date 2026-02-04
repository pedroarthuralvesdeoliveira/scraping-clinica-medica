"""
Pydantic models for API responses and service return values.
These models define the structure of data returned by various services and endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional, List, Any, Dict
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class SistemaOrigemEnum(str, Enum):
    """Sistema de origem do dados"""
    OURO = "OURO"
    OF = "OF"


class StatusAppointmentEnum(str, Enum):
    """Status possíveis de um agendamento"""
    AGENDADO = "agendado"
    CONFIRMADO = "confirmado"
    REALIZADO = "realizado"
    CANCELADO = "cancelado"
    FALTA = "falta"


class TipoTelefoneEnum(str, Enum):
    """Tipos de telefone do paciente"""
    WHATSAPP = "whatsapp"
    TELEFONE_FIXO = "telefone fixo"


# ============================================================================
# PATIENT & CLIENT RESPONSES
# ============================================================================

class TelefoneResponse(BaseModel):
    """Resposta para dados de telefone do paciente"""
    id: int
    cliente_codigo: int
    numero: str
    tipo: TipoTelefoneEnum
    is_principal: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DadosClienteResponse(BaseModel):
    """Resposta para dados completos de um cliente"""
    id: int
    codigo: Optional[int] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None
    telefone: Optional[str] = None
    nomewpp: Optional[str] = None
    cad_telefone: Optional[str] = None
    atendimento_ia: Optional[str] = None
    setor: Optional[str] = None
    sistema_origem: SistemaOrigemEnum
    created_at: datetime
    telefones: List[TelefoneResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class DadosClienteSimpleResponse(BaseModel):
    """Resposta simplificada para dados de cliente"""
    id: int
    codigo: Optional[int] = None
    cpf: Optional[str] = None
    nomewpp: Optional[str] = None
    telefone: Optional[str] = None
    sistema_origem: SistemaOrigemEnum

    class Config:
        from_attributes = True


# ============================================================================
# PROFESSIONAL/DOCTOR RESPONSES
# ============================================================================

class ProfissionalResponse(BaseModel):
    """Resposta para dados de um profissional de saúde"""
    id: int
    nome_completo: str
    nome_exibicao: str
    especialidade: str
    crm_registro: Optional[str] = None
    codigo: Optional[str] = None
    duracao_consulta: Optional[int] = None
    intervalo_consultas: Optional[int] = None
    horarios_atendimento: Optional[Dict[str, Any]] = None
    ativo: bool
    aceita_novos_pacientes: bool
    email: Optional[str] = None
    telefone: Optional[str] = None
    observacoes: Optional[str] = None
    config_atendimento: Optional[Dict[str, Any]] = None
    rqe: Optional[str] = None
    sistema_origem: Optional[SistemaOrigemEnum] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfissionalSimpleResponse(BaseModel):
    """Resposta simplificada para profissional"""
    id: int
    nome_completo: str
    nome_exibicao: str
    especialidade: str
    ativo: bool

    class Config:
        from_attributes = True


# ============================================================================
# APPOINTMENT RESPONSES
# ============================================================================

class AgendamentoResponse(BaseModel):
    """Resposta para dados completos de um agendamento"""
    id: int
    id_cliente: Optional[int] = None
    codigo: Optional[int] = None
    cpf: Optional[str] = None
    nome_paciente: Optional[str] = None
    data_nascimento: Optional[date] = None
    telefone: Optional[str] = None
    profissional: Optional[str] = None
    especialidade: Optional[str] = None
    data_consulta: date
    hora_consulta: time
    status: Optional[StatusAppointmentEnum] = None
    observacoes: Optional[str] = None
    convenio: Optional[str] = None
    primeira_consulta: Optional[bool] = None
    confirmado_pelo_paciente: Optional[bool] = None
    lembrete_enviado: Optional[bool] = None
    canal_agendamento: Optional[str] = None
    procedimento: Optional[str] = None
    valor: Optional[float] = None
    retorno_ate: Optional[date] = None
    sistema_origem: Optional[SistemaOrigemEnum] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgendamentoSimpleResponse(BaseModel):
    """Resposta simplificada para agendamento"""
    id: int
    nome_paciente: Optional[str] = None
    profissional: Optional[str] = None
    data_consulta: date
    hora_consulta: time
    status: Optional[StatusAppointmentEnum] = None
    especialidade: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# TASK & JOB RESPONSES
# ============================================================================

class TaskStatusResponse(BaseModel):
    """Resposta para status de uma tarefa Celery"""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskQueuedResponse(BaseModel):
    """Resposta quando uma tarefa é enfileirada"""
    status: str = "tarefa_enfileirada"
    task_id: str


# ============================================================================
# SERVICE OPERATION RESPONSES
# ============================================================================

class SyncResultStats(BaseModel):
    """Estatísticas de resultado de sincronização"""
    total_processed: int = 0
    added: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: int = 0


class AppointmentSyncResponse(BaseModel):
    """Resposta para sincronização de agendamentos"""
    status: str
    message: Optional[str] = None
    sistema: Optional[SistemaOrigemEnum] = None
    stats: SyncResultStats
    details: Optional[Dict[str, Any]] = None


class PatientSyncResponse(BaseModel):
    """Resposta para sincronização de pacientes"""
    status: str
    message: Optional[str] = None
    sistema: Optional[SistemaOrigemEnum] = None
    total_scraped: int
    total_added: int
    total_updated: int
    total_phones: int
    details: Optional[Dict[str, Any]] = None


class PatientCodeSyncResponse(BaseModel):
    """Resposta para sincronização de códigos de pacientes"""
    status: str
    message: Optional[str] = None
    total_items: int
    updated: int
    failed: int
    search_type: Optional[str] = None


class HistorySeedResponse(BaseModel):
    """Resposta para sincronização de histórico de agendamentos"""
    status: str
    message: Optional[str] = None
    total_patients_processed: int
    appointments_added: int
    appointments_skipped_existing: int
    errors: int


class BulkSyncResponse(BaseModel):
    """Resposta para sincronização em lote"""
    status: str
    message: Optional[str] = None
    total_processed: int = 0
    total_success: int = 0
    total_failed: int = 0
    details: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# APPOINTMENT TYPE DETERMINATION
# ============================================================================

class AppointmentTypeInfo(BaseModel):
    """Informações sobre o tipo de agendamento"""
    is_first_appointment: bool
    is_follow_up: bool
    is_surgery: bool
    reason: Optional[str] = None
    latest_appointment: Optional[Dict[str, Any]] = None


# ============================================================================
# AVAILABILITY/CALENDAR RESPONSES
# ============================================================================

class TimeSlotResponse(BaseModel):
    """Resposta para um horário disponível"""
    hora: str
    disponivel: bool
    motivo: Optional[str] = None


class DayAvailabilityResponse(BaseModel):
    """Resposta para disponibilidade de um dia"""
    data: date
    slots: List[TimeSlotResponse]
    total_available: int


class ProfessionalAvailabilityResponse(BaseModel):
    """Resposta para disponibilidade de um profissional"""
    profissional: str
    especialidade: Optional[str] = None
    dias_disponiveis: List[DayAvailabilityResponse]
    proximo_slot_disponivel: Optional[Dict[str, Any]] = None


# ============================================================================
# ERROR RESPONSES
# ============================================================================

class ErrorDetail(BaseModel):
    """Detalhes de um erro"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Resposta de erro padrão"""
    status: str = "error"
    message: str
    error_code: Optional[str] = None
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None


# ============================================================================
# HEALTH CHECK RESPONSE
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Resposta do health check"""
    status: str
    timestamp: datetime
    version: Optional[str] = None
    services: Optional[Dict[str, str]] = None
