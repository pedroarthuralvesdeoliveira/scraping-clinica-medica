from pydantic import BaseModel

class SchedulePayload(BaseModel):
    convenio: str | None = None
    cpf: str
    data_desejada: str
    data_nascimento: str
    horario_desejado: str
    medico: str
    nome_paciente: str
    telefone: str
    tipo_atendimento: str

class CancelPayload(BaseModel):
    data_desejada: str
    horario_desejado: str
    medico: str
    nome_paciente: str
    
class VerifyPayload(BaseModel):
    data_desejada: str | None = None
    horario_desejado: str | None = None
    horario_inicial: str | None = None
    horario_final: str | None = None
    medico: str
    