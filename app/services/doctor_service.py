from ..models.profissionais import Profissional

def get_or_create_professional(session, nome_medico: str, sistema_origem) -> int:
    """
    Busca um profissional pelo nome e sistema. Se não existir, cria um novo.
    Retorna o ID do profissional.
    """
    if not nome_medico:
        return None

    # Normaliza sistema_origem para string antes de qualquer operação
    sistema_str = sistema_origem.value if hasattr(sistema_origem, 'value') else sistema_origem

    # Tenta achar existente
    profissional = session.query(Profissional).filter_by(
        nome_exibicao=nome_medico,
        sistema_origem=sistema_str
    ).first()

    if profissional:
        return profissional.id

    # Se não existir, cria
    new_prof = Profissional(
        nome_completo=nome_medico,
        nome_exibicao=nome_medico,
        especialidade="Não Identificada",
        sistema_origem=sistema_str,
        codigo=None,
        ativo=True
    )
    session.add(new_prof)
    session.flush() # Importante para gerar o ID sem commitar a transação toda
    return new_prof.id