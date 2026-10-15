import json
from dataclasses import dataclass
from time import perf_counter

import numpy as np
import shapely

from . import geohash
from .geo import caixa_envolvente, haversine, para_geo, para_utm
from .trie import TrieCompacta

VELOCIDADE_MEDIA_KMH = 25
MAX_CELULAS = 16


@dataclass
class Atendimento:
    id: str
    via: str
    lat: float
    lon: float
    distancia_m: float
    distancia_rua_m: float
    minutos: float


@dataclass
class Resultado:
    precisao: int
    celulas: list
    candidatos: list
    atendem: list
    tempos_ms: dict


def escolher_precisao(caixa):
    """Precisão mais fina em que a cobertura do retângulo usa até MAX_CELULAS células.

    Células menores descartam mais entregadores antes da filtragem por distância,
    mas cada célula é uma busca de prefixo a mais na Trie.
    """
    for precisao in range(geohash.PRECISAO_MAXIMA, 0, -1):
        if geohash.tamanho_cobertura(*caixa, precisao) <= MAX_CELULAS:
            return precisao
    return 1


def carregar_limite_utm(caminho_geojson):
    with open(caminho_geojson, encoding="utf-8") as f:
        geometria = json.load(f)["features"][0]["geometry"]

    def para_metros(coords):
        x, y = para_utm(coords[:, 1], coords[:, 0])
        return np.column_stack([x, y])

    return shapely.transform(shapely.geometry.shape(geometria), para_metros)


class Frota:
    def __init__(self, malha, restaurantes, caminho_limite):
        self.malha = malha
        lat = np.array([r.lat for r in restaurantes.lista])
        lon = np.array([r.lon for r in restaurantes.lista])
        self._centro_x, self._centro_y = para_utm(lat, lon)
        self._limite = carregar_limite_utm(caminho_limite)
        shapely.prepare(self._limite)

        self.indice = TrieCompacta()
        self.ids = []
        self.lat = []
        self.lon = []
        self.geohashes = []
        self.dispersao_m = None
        self._aresta = np.empty(0, dtype=int)
        self._desloc = np.empty(0)

    def __len__(self):
        return len(self.ids)

    def gerar(self, n, dispersao_m, semente=None):
        """Descarta a frota atual e sorteia `n` entregadores novos.

        Cada entregador recebe um restaurante como centro (os centros são uma
        permutação aleatória repetida, então nenhum recebe mais que um entregador
        a mais que outro) e uma posição normal em torno dele, com desvio padrão
        `dispersao_m` em cada eixo. Pontos fora do município são sorteados de novo,
        e o ponto final é projetado na via mais próxima.
        """
        rng = np.random.default_rng(semente)
        total_centros = len(self._centro_x)
        centros = rng.permutation(total_centros)[np.arange(n) % total_centros]
        x = self._centro_x[centros] + rng.normal(0, dispersao_m, n)
        y = self._centro_y[centros] + rng.normal(0, dispersao_m, n)
        for _ in range(50):
            fora = ~shapely.contains_xy(self._limite, x, y)
            if not fora.any():
                break
            k = int(fora.sum())
            x[fora] = self._centro_x[centros[fora]] + rng.normal(0, dispersao_m, k)
            y[fora] = self._centro_y[centros[fora]] + rng.normal(0, dispersao_m, k)

        x, y, aresta, desloc = self.malha.projetar(x, y)
        lat, lon = para_geo(x, y)
        lat, lon = lat.tolist(), lon.tolist()
        largura = len(str(n))
        ids = [f"E{i + 1:0{largura}d}" for i in range(n)]
        geohashes = [geohash.codificar(a, b) for a, b in zip(lat, lon)]

        self.indice.limpar()
        for i, gh in enumerate(geohashes):
            self.indice.inserir(gh, i)
        self.ids, self.lat, self.lon, self.geohashes = ids, lat, lon, geohashes
        self.dispersao_m = dispersao_m
        self._aresta, self._desloc = aresta, desloc

    def buscar(self, lat, lon, raio_m, precisao=None):
        """Entregadores a até `raio_m` metros (em linha reta) do ponto.

        `precisao` fixa o tamanho das células consultadas; sem ela, usa escolher_precisao.
        """
        inicio = perf_counter()
        caixa = caixa_envolvente(lat, lon, raio_m)
        precisao = precisao or escolher_precisao(caixa)
        celulas = geohash.cobertura(*caixa, precisao)
        candidatos = []
        for celula in celulas:
            candidatos.extend(self.indice.buscar_prefixo(celula))
        fim_trie = perf_counter()

        dentro = []
        for i in candidatos:
            d = haversine(lat, lon, self.lat[i], self.lon[i])
            if d <= raio_m:
                dentro.append((i, d))
        fim_filtro = perf_counter()

        atendem = []
        if dentro:
            x, y = para_utm(lat, lon)
            _, _, aresta, desloc = self.malha.projetar([x], [y])
            indices = np.array([i for i, _ in dentro])
            rua = self.malha.distancias_ate(
                aresta[0], desloc[0], self._aresta[indices], self._desloc[indices]
            )
            for (i, d), r in zip(dentro, rua.tolist()):
                minutos = r / 1000 / VELOCIDADE_MEDIA_KMH * 60
                via = self.malha.nomes[self._aresta[i]]
                atendem.append(Atendimento(self.ids[i], via, self.lat[i], self.lon[i], d, r, minutos))
            atendem.sort(key=lambda a: a.distancia_rua_m)
        fim = perf_counter()

        return Resultado(
            precisao=precisao,
            celulas=celulas,
            candidatos=candidatos,
            atendem=atendem,
            tempos_ms={
                "trie": 1000 * (fim_trie - inicio),
                "filtro": 1000 * (fim_filtro - fim_trie),
                "rotas": 1000 * (fim - fim_filtro),
                "total": 1000 * (fim - inicio),
            },
        )
