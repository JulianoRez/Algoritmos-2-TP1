import argparse
import gzip
import shutil
from pathlib import Path

import osmnx as ox

RAIZ = Path(__file__).resolve().parent.parent
LUGAR = "Belo Horizonte, Minas Gerais, Brazil"
MALHA = RAIZ / "data" / "malha_bh.graphml.gz"
LIMITE = RAIZ / "data" / "limite_bh.geojson"


def eh_faixa_de_onibus(highway):
    tipos = highway if isinstance(highway, list) else [highway]
    return "busway" in tipos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overpass", help="URL de um servidor Overpass alternativo")
    args = parser.parse_args()

    ox.settings.cache_folder = RAIZ / ".cache" / "osmnx"
    if args.overpass:
        ox.settings.overpass_url = args.overpass

    limite = ox.geocode_to_gdf(LUGAR)
    limite[["geometry"]].to_file(LIMITE, driver="GeoJSON")

    G = ox.graph_from_polygon(limite.geometry.iloc[0], network_type="drive")
    print(f"malha original: {len(G.nodes)} nós, {len(G.edges)} arestas")

    # O filtro "drive" do osmnx inclui as pistas exclusivas do MOVE.
    G.remove_edges_from([
        (u, v, k) for u, v, k, h in G.edges(keys=True, data="highway") if eh_faixa_de_onibus(h)
    ])
    # Mantém só a maior componente fortemente conexa, para que exista caminho
    # de qualquer ponto da malha até qualquer outro respeitando a mão das vias.
    G = ox.truncate.largest_component(G, strongly=True)
    print(f"malha final: {len(G.nodes)} nós, {len(G.edges)} arestas")

    temporario = RAIZ / ".cache" / "malha_bh.graphml"
    ox.save_graphml(G, temporario)
    with open(temporario, "rb") as origem, gzip.open(MALHA, "wb", compresslevel=9) as destino:
        shutil.copyfileobj(origem, destino)
    temporario.unlink()
    print(f"gravado em {MALHA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
