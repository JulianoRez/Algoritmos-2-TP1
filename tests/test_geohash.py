import random

import pytest

from geofrota import geohash
from geofrota.geo import caixa_envolvente, haversine


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


def test_cobertura_de_retangulo_dentro_de_uma_celula():
    lat, lon = geohash.decodificar("7h2wn8")
    celulas = geohash.cobertura(lat - 1e-5, lat + 1e-5, lon - 1e-5, lon + 1e-5, 6)
    assert celulas == ["7h2wn8"]


def test_cobertura_nao_perde_pontos_do_circulo():
    rng = random.Random(2)
    for _ in range(300):
        lat0 = rng.uniform(-20.05, -19.78)
        lon0 = rng.uniform(-44.06, -43.86)
        raio = rng.uniform(50, 5000)
        p = rng.randint(4, 7)
        celulas = set(geohash.cobertura(*caixa_envolvente(lat0, lon0, raio), p))
        assert len(celulas) == geohash.tamanho_cobertura(*caixa_envolvente(lat0, lon0, raio), p)
        for _ in range(30):
            # Ponto aleatório no círculo, perto da borda de propósito.
            lat = lat0 + rng.uniform(-1, 1) * raio / 111_000
            lon = lon0 + rng.uniform(-1, 1) * raio / 104_000
            if haversine(lat0, lon0, lat, lon) <= raio:
                assert geohash.codificar(lat, lon, p) in celulas
