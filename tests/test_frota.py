import random

import pytest

from geofrota.frota import Frota
from geofrota.geo import haversine
from tests.conftest import DADOS


@pytest.fixture(scope="module")
def frota(malha, restaurantes):
    f = Frota(malha, restaurantes, DADOS / "limite_bh.geojson")
    f.gerar(3000, 500, semente=3)
    return f


def test_gerar_substitui_a_frota_anterior(malha, restaurantes):
    f = Frota(malha, restaurantes, DADOS / "limite_bh.geojson")
    f.gerar(500, 300, semente=1)
    f.gerar(120, 300, semente=2)
    assert len(f) == 120 == len(f.indice)
    assert len(set(f.ids)) == 120
    assert sorted(f.indice.buscar_prefixo("")) == list(range(120))


def test_busca_igual_a_forca_bruta(frota, restaurantes):
    rng = random.Random(5)
    for _ in range(40):
        r = restaurantes.lista[rng.randrange(len(restaurantes))]
        raio = rng.choice([300, 800, 1500, 2500, 4000])
        resultado = frota.buscar(r, raio)
        esperado = {
            frota.ids[i] for i in range(len(frota))
            if haversine(r.lat, r.lon, frota.lat[i], frota.lon[i]) <= raio
        }
        assert {a.id for a in resultado.atendem} == esperado
        rua = [a.distancia_rua_m for a in resultado.atendem]
        assert rua == sorted(rua)


def test_busca_por_nome(restaurantes):
    assert restaurantes.buscar("xapuri mandacaru")[0].nome == "Restaurante Xapuri"
    assert restaurantes.buscar("CAFÉ com letras")[0].nome == "Cafe com Letras"
    assert restaurantes.buscar("zzzzqq") == []
