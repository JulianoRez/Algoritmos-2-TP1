import gzip

import numpy as np
import osmnx as ox
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from .geo import CRS_UTM


def nome_da_via(nome):
    # Arestas que juntam mais de um "way" do OSM trazem uma lista de nomes.
    if isinstance(nome, list):
        return nome[0]
    return nome if isinstance(nome, str) else ""


class Malha:
    def __init__(self, caminho_graphml_gz):
        with gzip.open(caminho_graphml_gz, "rt", encoding="utf-8") as f:
            G = ox.load_graphml(graphml_str=f.read())
        G = ox.project_graph(G, to_crs=CRS_UTM)
        arestas = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True).reset_index()

        posicao = {no: i for i, no in enumerate(G.nodes)}
        self.origem = arestas["u"].map(posicao).to_numpy()
        self.destino = arestas["v"].map(posicao).to_numpy()
        self.geometrias = arestas.geometry.to_numpy()
        self.comprimento = shapely.length(self.geometrias)
        self.nomes = [nome_da_via(n) for n in arestas["name"]]
        pares = set(zip(self.origem.tolist(), self.destino.tolist()))
        self.mao_dupla = np.array([(v, u) in pares for u, v in zip(self.origem, self.destino)])
        self._arvore = shapely.STRtree(self.geometrias)

        # Matriz de adjacência invertida (v -> u): um Dijkstra a partir do destino
        # nela dá a distância de todos os nós ATÉ o destino no grafo original.
        n = len(posicao)
        self._reverso = csr_matrix((self.comprimento, (self.destino, self.origem)), shape=(n, n))

    def __len__(self):
        return len(self.geometrias)

    def projetar(self, x, y):
        """Leva cada ponto (x, y) para o ponto mais próximo sobre a malha.

        Retorna (x, y, aresta, deslocamento), todos arrays.
        """
        pontos = shapely.points(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
        _, aresta = self._arvore.query_nearest(pontos, all_matches=False)
        linhas = self.geometrias[aresta]
        desloc = shapely.line_locate_point(linhas, pontos)
        projetados = shapely.line_interpolate_point(linhas, desloc)
        return shapely.get_x(projetados), shapely.get_y(projetados), aresta, desloc

    def distancias_ate(self, aresta, desloc, arestas_origem, desloc_origem):
        """Distância pela rua de cada posição de origem até a posição de destino,
        respeitando a mão das vias."""
        L = self.comprimento[aresta]
        dist_u, dist_v = dijkstra(self._reverso, indices=[self.origem[aresta], self.destino[aresta]])
        # Chegando pelo nó de origem da aresta, percorre `desloc`; chegando pelo
        # outro nó, só dá para seguir se a via for de mão dupla.
        ate = dist_u + desloc
        if self.mao_dupla[aresta]:
            ate = np.minimum(ate, dist_v + (L - desloc))

        uo = self.origem[arestas_origem]
        vo = self.destino[arestas_origem]
        Lo = self.comprimento[arestas_origem]
        total = (Lo - desloc_origem) + ate[vo]
        de_re = np.where(self.mao_dupla[arestas_origem], desloc_origem + ate[uo], np.inf)
        total = np.minimum(total, de_re)

        mesma = arestas_origem == aresta
        a_frente = mesma & (desloc_origem <= desloc)
        total = np.where(a_frente, desloc - desloc_origem, total)
        if self.mao_dupla[aresta]:
            atras = mesma & (desloc_origem > desloc)
            total = np.where(atras, desloc_origem - desloc, total)
        return total
