import argparse
import gzip
import shutil
from pathlib import Path

import osmnx as ox

RAIZ = Path(__file__).resolve().parent.parent
LUGAR = "Belo Horizonte, Minas Gerais, Brazil"
MALHA = RAIZ / "data" / "malha_bh.graphml.gz"
LIMITE = RAIZ / "data" / "limite_bh.geojson"


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
    print(f"malha: {len(G.nodes)} nós, {len(G.edges)} arestas")

    temporario = RAIZ / ".cache" / "malha_bh.graphml"
    ox.save_graphml(G, temporario)
    with open(temporario, "rb") as origem, gzip.open(MALHA, "wb", compresslevel=9) as destino:
        shutil.copyfileobj(origem, destino)
    temporario.unlink()
    print(f"gravado em {MALHA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
