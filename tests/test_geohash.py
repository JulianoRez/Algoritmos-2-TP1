import random

import pytest

from geofrota import geohash


@pytest.mark.parametrize("lat, lon, esperado", [
    (42.6, -5.6, "ezs42"),
    (57.64911, 10.40744, "u4pruydq"),
    (-19.932, -43.938, "7h2y85mr"),   # Praça da Liberdade
    (0.0, 0.0, "s0000000"),
])
def test_codificar_valores_conhecidos(lat, lon, esperado):
    assert geohash.codificar(lat, lon, len(esperado)) == esperado


def test_precisao_limitada():
    with pytest.raises(ValueError):
        geohash.codificar(0, 0, 9)


def test_caixa_contem_o_ponto_e_tem_o_tamanho_da_precisao():
    rng = random.Random(1)
    for _ in range(2000):
        lat, lon = rng.uniform(-90, 90), rng.uniform(-180, 180)
        p = rng.randint(1, 8)
        gh = geohash.codificar(lat, lon, p)
        lat_min, lat_max, lon_min, lon_max = geohash.caixa(gh)
        assert lat_min <= lat <= lat_max and lon_min <= lon <= lon_max
        altura, largura = geohash.dimensoes(p)
        assert lat_max - lat_min == pytest.approx(altura)
        assert lon_max - lon_min == pytest.approx(largura)


def test_prefixo_corresponde_a_celula_maior():
    gh = geohash.codificar(-19.92, -43.94)
    for p in range(1, 8):
        assert geohash.codificar(-19.92, -43.94, p) == gh[:p]
