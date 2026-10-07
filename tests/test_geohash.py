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
