import random

from geofrota.trie import TrieCompacta


def test_busca_basica():
    t = TrieCompacta()
    for i, chave in enumerate(["romane", "romanus", "romulus", "rubens", "ruber", "rubicon", "rubicundus"]):
        t.inserir(chave, i)
    assert sorted(t.buscar_prefixo("rom")) == [0, 1, 2]
    assert sorted(t.buscar_prefixo("rub")) == [3, 4, 5, 6]
    assert sorted(t.buscar_prefixo("rubic")) == [5, 6]
    assert t.buscar_prefixo("romanus") == [1]
    assert sorted(t.buscar_prefixo("roma")) == [0, 1]
    assert t.buscar_prefixo("x") == []
    assert t.buscar_prefixo("romanusx") == []
    assert t.buscar_prefixo("rua") == []
    assert len(t.buscar_prefixo("")) == 7


def test_chave_que_e_prefixo_de_outra():
    t = TrieCompacta()
    t.inserir("bar", 1)
    t.inserir("barra", 2)
    t.inserir("ba", 3)
    assert sorted(t.buscar_prefixo("bar")) == [1, 2]
    assert sorted(t.buscar_prefixo("b")) == [1, 2, 3]
    assert t.buscar_prefixo("barr") == [2]


def test_valores_repetidos_na_mesma_chave():
    t = TrieCompacta()
    t.inserir("7h2y85mr", "a")
    t.inserir("7h2y85mr", "b")
    assert sorted(t.buscar_prefixo("7h2y")) == ["a", "b"]
    assert len(t) == 2


def test_igual_a_busca_por_forca_bruta():
    rng = random.Random(42)
    alfabeto = "0123456789bcdefghjkmnpqrstuvwxyz"
    chaves = ["7h2" + "".join(rng.choice(alfabeto[:6]) for _ in range(5)) for _ in range(2000)]
    t = TrieCompacta()
    for i, c in enumerate(chaves):
        t.inserir(c, i)
    for _ in range(500):
        p = rng.choice(chaves)[: rng.randint(0, 8)]
        assert sorted(t.buscar_prefixo(p)) == [i for i, c in enumerate(chaves) if c.startswith(p)]
