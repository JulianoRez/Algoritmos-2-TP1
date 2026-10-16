import numpy as np
import shapely

from geofrota.geo import para_utm


def test_projecao_cai_sobre_a_via(malha):
    rng = np.random.default_rng(0)
    x0, y0 = para_utm(-19.93, -43.94)
    x, y = x0 + rng.normal(0, 1000, 30), y0 + rng.normal(0, 1000, 30)
    px, py, aresta, desloc = malha.projetar(x, y)
    assert np.all(desloc >= 0) and np.all(desloc <= malha.comprimento[aresta] + 1e-6)
    # Comparação com a força bruta: distância de cada ponto a todas as vias.
    distancia = np.hypot(px - x, py - y)
    minima = shapely.distance(shapely.points(x, y)[:, None], malha.geometrias[None, :]).min(axis=1)
    np.testing.assert_allclose(distancia, minima, atol=1e-6)


def test_limite_do_dijkstra_nao_muda_o_resultado(malha):
    rng = np.random.default_rng(1)
    x0, y0 = para_utm(-19.92, -43.94)
    _, _, aresta, desloc = malha.projetar(x0 + rng.normal(0, 1500, 300), y0 + rng.normal(0, 1500, 300))
    _, _, destino, desloc_destino = malha.projetar([x0], [y0])
    sem_limite = malha.distancias_ate(destino[0], desloc_destino[0], aresta, desloc)
    for limite in (500, 2000, 6000):
        com_limite = malha.distancias_ate(destino[0], desloc_destino[0], aresta, desloc, limite_m=limite)
        np.testing.assert_allclose(com_limite, sem_limite)
    assert np.all(np.isfinite(sem_limite))
