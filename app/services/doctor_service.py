import unicodedata
from sqlalchemy import func
from ..models.profissionais import Profissional


def _normalize(name: str) -> str:
    """Remove acentos e converte para minúsculo para comparação."""
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def get_or_create_professional(session, nome_medico: str, sistema_origem) -> int:
    """
    Busca um profissional pelo nome. Retorna o ID se encontrar, None caso contrário.
    Não cria novos profissionais automaticamente.
    """
    if not nome_medico:
        return None

    # Busca exata por nome_completo
    profissional = session.query(Profissional).filter_by(
        nome_completo=nome_medico,
    ).first()

    if profissional:
        return profissional.id

    # Busca aproximada: ignora acentos (ex: "Raissa" vs "Raíssa")
    nome_norm = _normalize(nome_medico)
    todos = session.query(Profissional).all()
    for p in todos:
        if _normalize(p.nome_completo) == nome_norm:
            return p.id

    return None