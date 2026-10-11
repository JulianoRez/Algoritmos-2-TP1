import gzip

import numpy as np
import osmnx as ox
import shapely

from .geo import CRS_UTM


class Malha:
    def __init__(self, caminho_graphml_gz):
        with gzip.open(caminho_graphml_gz, "rt", encoding="utf-8") as f:
            G = ox.load_graphml(graphml_str=f.read())
        G = ox.project_graph(G, to_crs=CRS_UTM)
        arestas = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True).reset_index()
        self.geometrias = arestas.geometry.to_numpy()
        self._arvore = shapely.STRtree(self.geometrias)

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
