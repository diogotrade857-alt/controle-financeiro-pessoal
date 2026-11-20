"""Hash de senhas com PBKDF2-HMAC-SHA256 (biblioteca padrão, sem dependências).

Formato armazenado:  pbkdf2_sha256$<iterações>$<sal hex>$<hash hex>
A senha nunca é gravada em texto puro, e cada usuário tem um sal aleatório.
"""
import hashlib
import hmac
import os

ITERACOES = 120_000
_ALGORITMO = "pbkdf2_sha256"


def gerar_hash(senha):
    """Gera o hash da senha com PBKDF2-SHA256 e um sal aleatório."""
    sal = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)
    return f"{_ALGORITMO}${ITERACOES}${sal.hex()}${h.hex()}"


def verificar(senha, armazenado):
    """Confere se a senha corresponde ao hash armazenado (comparação em tempo constante)."""
    try:
        alg, iteracoes, sal, esperado = armazenado.split("$")
        if alg != _ALGORITMO:
            return False
        calculado = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), bytes.fromhex(sal), int(iteracoes))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(calculado.hex(), esperado)   # tempo constante
