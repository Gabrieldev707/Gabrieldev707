import random

from swa import br


def test_cpf_gerado_e_valido():
    rng = random.Random(1)
    for _ in range(200):
        assert br.cpf_valido(br.cpf(rng))


def test_cpf_invalido():
    assert not br.cpf_valido("111.111.111-11")
    assert not br.cpf_valido("123.456.789-00")


def test_cnpj_gerado_e_valido():
    rng = random.Random(2)
    for _ in range(200):
        c = br.cnpj(rng)
        assert br.cnpj_valido(c)
        assert c[11:15] == "0001"


def test_cnpj_conhecido():
    # CNPJ de exemplo amplamente usado em documentação (dígitos válidos).
    assert br.cnpj_valido("11.222.333/0001-81")
    assert not br.cnpj_valido("11.222.333/0001-80")


def test_chave_nfe_valida():
    rng = random.Random(3)
    chave = br.chave_nfe(rng, uf=35, aamm="2609", cnpj_emitente="11.222.333/0001-81", serie=1, numero=123)
    assert br.chave_nfe_valida(chave)
    digits = chave.replace(" ", "")
    assert len(digits) == 44 and digits[:2] == "35" and digits[20:22] == "55"


def test_brl():
    assert br.brl(18450) == "R$ 18.450,00"
    assert br.brl(7920.5) == "R$ 7.920,50"
    assert br.brl(0.99) == "R$ 0,99"
