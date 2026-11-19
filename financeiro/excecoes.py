"""Exceções específicas do domínio financeiro.

Todas herdam de ErroFinanceiro, o que permite à interface capturar "qualquer erro
esperado do sistema" com um único except, sem esconder bugs reais (TypeError etc.).
"""


class ErroFinanceiro(Exception):
    """Base de todos os erros previstos pelo sistema."""


class ValidacaoError(ErroFinanceiro, ValueError):
    """Dado informado pelo usuário viola uma regra de validação."""


class TransacaoNaoEncontradaError(ErroFinanceiro, LookupError):
    """Não existe transação com o ID informado (para o usuário atual)."""


class MetaNaoEncontradaError(ErroFinanceiro, LookupError):
    """Não existe meta para a categoria informada."""


class AutenticacaoError(ErroFinanceiro):
    """Credenciais inválidas."""


class ArquivoError(ErroFinanceiro):
    """Falha ao ler ou gravar um arquivo (CSV, banco, etc.)."""


class BackupError(ArquivoError):
    """Falha ao criar ou restaurar um backup do banco."""
