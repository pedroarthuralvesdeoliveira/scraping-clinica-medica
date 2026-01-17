from pydantic import BaseModel


class SchedulePayload(BaseModel):
    medico: str
    data_desejada: str
    horario_desejado: str
    nome_paciente: str
    data_nascimento: str
    cpf: str
    telefone: str
    tipo_atendimento: str
    convenio: str | None = None


class CancelPayload(BaseModel):
    data_desejada: str
    horario_desejado: str
    medico: str
    nome_paciente: str
    cpf: str | None = None


class SyncPayload(BaseModel):
    cpf: str
    nome_paciente: str | None = None
    medico: str | None = None


class VerifyPayload(BaseModel):
    data_desejada: str | None = None
    horario_desejado: str | None = None
    horario_inicial: str | None = None
    horario_final: str | None = None
    medico: str
