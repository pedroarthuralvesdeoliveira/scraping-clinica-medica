"""
Pydantic models específicos para dados de scraping e operações internas.
"""

from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional, List, Any, Dict
from enum import Enum


# ============================================================================
# SCRAPER DATA MODELS
# ============================================================================

class ScraperAppointmentData(BaseModel):
    """Dados de agendamento retornados pelo scraper"""
    codigo: Optional[int] = None
    nome_paciente: Optional[str] = None
    cpf: Optional[str] = None
    data_consulta: Optional[date] = None
    hora_consulta: Optional[time] = None
    profissional: Optional[str] = None
    especialidade: Optional[str] = None
    status: Optional[str] = None
    procedimento: Optional[str] = None
    tipo_atendimento: Optional[str] = None
    convenio: Optional[str] = None
    observacoes: Optional[str] = None
    telefone: Optional[str] = None
    primeira_consulta: Optional[bool] = None


class ScraperPatientData(BaseModel):
    """Dados de paciente retornados pelo scraper"""
    codigo: Optional[int] = None
    nomewpp: Optional[str] = None
    cad_telefone: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None


class ScraperHistoryData(BaseModel):
    """Dados de histórico de atendimento retornados pelo scraper"""
    profissional: Optional[str] = None
    data_atendimento: Optional[str] = None  # dd/mm/aaaa
    hora: Optional[str] = None  # HH:MM
    tipo: Optional[str] = None
    retorno_ate: Optional[str] = None  # dd/mm/aaaa


class ScraperResponseBase(BaseModel):
    """Resposta base do scraper"""
    status: str  # success, error, partial
    message: Optional[str] = None
    error: Optional[str] = None


class ScraperAppointmentsResponse(ScraperResponseBase):
    """Resposta do scraper com agendamentos"""
    appointments: List[ScraperAppointmentData] = Field(default_factory=list)
    count: int = 0


class ScraperPatientsResponse(ScraperResponseBase):
    """Resposta do scraper com pacientes"""
    patients: List[ScraperPatientData] = Field(default_factory=list)
    count: int = 0


class ScraperHistoryResponse(ScraperResponseBase):
    """Resposta do scraper com histórico"""
    appointments: List[ScraperHistoryData] = Field(default_factory=list)
    count: int = 0


# ============================================================================
# DATABASE OPERATION RESULTS
# ============================================================================

class DatabaseOperationResult(BaseModel):
    """Resultado de uma operação no banco de dados"""
    success: bool
    records_affected: int = 0
    error: Optional[str] = None


class BulkInsertResult(BaseModel):
    """Resultado de inserção em lote"""
    total_records: int
    inserted: int
    updated: int
    skipped: int
    errors: int
    error_details: Optional[List[Dict[str, Any]]] = None


class QueryResult(BaseModel):
    """Resultado de uma query"""
    status: str  # success, error
    count: int = 0
    data: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


# ============================================================================
# INTERNAL SERVICE RESPONSES
# ============================================================================

class GetOrCreateProfessionalResult(BaseModel):
    """Resultado da criação ou busca de um profissional"""
    professional_id: Optional[int] = None
    created: bool
    nome: str
    error: Optional[str] = None


class PatientPhoneExtractionResult(BaseModel):
    """Resultado da extração de telefones"""
    original: Optional[str] = None
    extracted_phones: List[str] = Field(default_factory=list)
    formatted_whatsapp: Optional[str] = None


class PhoneSyncResult(BaseModel):
    """Resultado da sincronização de telefones"""
    cliente_id: int
    new_phones_added: int
    existing_phones_skipped: int
    total_processed: int


# ============================================================================
# CELERY TASK DATA MODELS
# ============================================================================

class CeleryTaskBase(BaseModel):
    """Dados base de uma tarefa Celery"""
    task_id: str
    task_name: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ScheduleAppointmentTask(CeleryTaskBase):
    """Tarefa de agendamento"""
    medico: str
    data_desejada: str
    horario_desejado: str
    nome_paciente: str
    cpf: str
    resultado: Optional[Dict[str, Any]] = None


class CancelAppointmentTask(CeleryTaskBase):
    """Tarefa de cancelamento"""
    medico: str
    data_desejada: str
    horario_desejado: str
    nome_paciente: str
    resultado: Optional[Dict[str, Any]] = None


class VerifyAvailabilityTask(CeleryTaskBase):
    """Tarefa de verificação de disponibilidade"""
    medico: str
    data_desejada: Optional[str] = None
    horario_desejado: Optional[str] = None
    resultado: Optional[Dict[str, Any]] = None


class SyncAppointmentsTask(CeleryTaskBase):
    """Tarefa de sincronização de agendamentos"""
    cpf: str
    nome_paciente: Optional[str] = None
    resultado: Optional[Dict[str, Any]] = None


# ============================================================================
# PAGINATION & LIST RESPONSES
# ============================================================================

class PaginationParams(BaseModel):
    """Parâmetros de paginação"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    order: Optional[str] = Field(default="asc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseModel):
    """Resposta paginada genérica"""
    data: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


# ============================================================================
# VALIDATION & DATA PROCESSING
# ============================================================================

class ValidationError(BaseModel):
    """Erro de validação"""
    field: str
    value: Any
    error: str
    code: Optional[str] = None


class ValidationResult(BaseModel):
    """Resultado de validação"""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)


# ============================================================================
# STATISTICS & METRICS
# ============================================================================

class SyncMetrics(BaseModel):
    """Métricas de sincronização"""
    total_processed: int = 0
    total_added: int = 0
    total_updated: int = 0
    total_skipped: int = 0
    total_deleted: int = 0
    total_errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success_rate: Optional[float] = None


class OperationMetrics(BaseModel):
    """Métricas gerais de operação"""
    operation: str
    system: Optional[str] = None
    status: str
    metrics: SyncMetrics
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# APPOINTMENT COMPARISON
# ============================================================================

class AppointmentDifference(BaseModel):
    """Diferença entre agendamentos de diferentes fontes"""
    appointment_id: Optional[int] = None
    campo: str
    valor_banco: Any
    valor_website: Any


class AppointmentComparison(BaseModel):
    """Comparação de um agendamento entre banco e website"""
    appointment_id: int
    cpf: str
    data_consulta: date
    hora_consulta: time
    is_different: bool
    differences: List[AppointmentDifference] = Field(default_factory=list)
