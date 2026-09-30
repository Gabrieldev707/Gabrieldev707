"""Dados sintéticos brasileiros: estruturalmente válidos, mas fictícios.

Todos os geradores recebem um `random.Random` para que o mundo seja
reprodutível a partir de uma seed.
"""

from __future__ import annotations

import random
import re


def _dv_mod11(digits: list[int], weights: list[int]) -> int:
    r = sum(d * w for d, w in zip(digits, weights)) % 11
    return 0 if r < 2 else 11 - r


def cpf(rng: random.Random) -> str:
    """CPF com dígitos verificadores válidos, formatado (000.000.000-00)."""
    while True:
        base = [rng.randint(0, 9) for _ in range(9)]
        if len(set(base)) > 1:  # evita 111.111.111-11 e afins
            break
    d1 = _dv_mod11(base, list(range(10, 1, -1)))
    d2 = _dv_mod11(base + [d1], list(range(11, 1, -1)))
    n = "".join(map(str, base + [d1, d2]))
    return f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"


def cpf_valido(valor: str) -> bool:
    n = [int(c) for c in re.sub(r"\D", "", valor)]
    if len(n) != 11 or len(set(n)) == 1:
        return False
    return (
        n[9] == _dv_mod11(n[:9], list(range(10, 1, -1)))
        and n[10] == _dv_mod11(n[:10], list(range(11, 1, -1)))
    )


_CNPJ_W1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_CNPJ_W2 = [6] + _CNPJ_W1


def cnpj(rng: random.Random, filial: int = 1) -> str:
    """CNPJ com dígitos verificadores válidos, formatado (00.000.000/0001-00)."""
    base = [rng.randint(0, 9) for _ in range(8)] + [int(c) for c in f"{filial:04d}"]
    d1 = _dv_mod11(base, _CNPJ_W1)
    d2 = _dv_mod11(base + [d1], _CNPJ_W2)
    n = "".join(map(str, base + [d1, d2]))
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def cnpj_valido(valor: str) -> bool:
    n = [int(c) for c in re.sub(r"\D", "", valor)]
    if len(n) != 14 or len(set(n)) == 1:
        return False
    return n[12] == _dv_mod11(n[:12], _CNPJ_W1) and n[13] == _dv_mod11(n[:13], _CNPJ_W2)


def _dv_chave_nfe(digits43: str) -> int:
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    total = sum(int(d) * pesos[i % 8] for i, d in enumerate(reversed(digits43)))
    r = total % 11
    return 0 if r < 2 else 11 - r


def chave_nfe(
    rng: random.Random,
    *,
    uf: int,
    aamm: str,
    cnpj_emitente: str,
    serie: int,
    numero: int,
) -> str:
    """Chave de acesso de NF-e (44 dígitos, modelo 55) com DV válido."""
    corpo = (
        f"{uf:02d}{aamm}{re.sub(r'[^0-9]', '', cnpj_emitente)}55"
        f"{serie:03d}{numero:09d}1{rng.randint(0, 99_999_999):08d}"
    )
    assert len(corpo) == 43
    chave = corpo + str(_dv_chave_nfe(corpo))
    return " ".join(chave[i : i + 4] for i in range(0, 44, 4))


def chave_nfe_valida(valor: str) -> bool:
    n = re.sub(r"\D", "", valor)
    return len(n) == 44 and int(n[43]) == _dv_chave_nfe(n[:43])


def brl(valor: float) -> str:
    """Formata em reais: 18450.0 -> 'R$ 18.450,00'."""
    inteiro, _, cent = f"{valor:,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{cent}"
