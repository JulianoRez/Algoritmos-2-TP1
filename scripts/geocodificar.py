import csv
import gzip
import re
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

import osmnx as ox
from pyproj import Transformer

RAIZ = Path(__file__).resolve().parent.parent
BARES = RAIZ / "data" / "bares.csv.gz"
MALHA = RAIZ / "data" / "malha_bh.graphml.gz"
SAIDA = RAIZ / "data" / "restaurantes.csv"
ENDERECOS = RAIZ / ".cache" / "endereco_pbh.csv"
URL_ENDERECOS = (
    "https://ckan.pbh.gov.br/dataset/394da7d4-3e74-4a2d-8fb6-6cb4d65d3451/resource/"
    "a4bde632-2924-41e6-a6cf-338455ebcc16/download/20261001_endereco.csv"
)
MAX_DIFERENCA_NUMERO = 100

CATEGORIAS = {
    "5611201": "Restaurante",
    "5611203": "Lanchonete",
    "5611204": "Bar",
    "5611205": "Bar",
}
TIPOS = {
    "RUA": "Rua", "AVE": "Avenida", "PCA": "Praça", "ROD": "Rodovia",
    "BEC": "Beco", "ALA": "Alameda", "EST": "Estrada", "TRV": "Travessa",
    "VIA": "Via", "VDP": "Via de Pedestre",
}
MINUSCULAS = {"DE", "DA", "DO", "DAS", "DOS", "E", "COM", "EM", "NA", "NO", "NAS", "NOS"}
ROMANOS = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(texto.upper().replace("-", " ").split())


def titulo(texto, inicio_de_frase=True):
    palavras = []
    for i, p in enumerate(texto.split()):
        if p in ROMANOS:
            palavras.append(p)
        elif (i > 0 or not inicio_de_frase) and p in MINUSCULAS:
            palavras.append(p.lower())
        else:
            palavras.append(p.capitalize())
    return " ".join(palavras)


def nome_exibicao(fantasia, razao_social):
    nome = fantasia.strip() or razao_social.strip()
    # Microempreendedores aparecem como "12.345.678 NOME" ou "NOME 12345678901".
    nome = re.sub(r"^\d{2}\.\d{3}\.\d{3}\s+", "", nome)
    nome = re.sub(r"\s+\d{11}$", "", nome)
    return titulo(nome)


def nomes_de_vias_osm():
    """Nomes das vias no OSM, indexados pela forma sem acentos e em maiúsculas."""
    if not MALHA.exists():
        return {}
    with gzip.open(MALHA, "rt", encoding="utf-8") as f:
        G = ox.load_graphml(graphml_str=f.read())
    nomes = {}
    for _, _, nome in G.edges(data="name"):
        for n in nome if isinstance(nome, list) else [nome]:
            if isinstance(n, str):
                nomes[normalizar(n)] = n
    return nomes


def baixar_enderecos():
    if ENDERECOS.exists():
        return
    ENDERECOS.parent.mkdir(exist_ok=True)
    print(f"Baixando base de endereços da PBH para {ENDERECOS} (~130 MB)...")
    pedido = urllib.request.Request(URL_ENDERECOS, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(pedido) as resp, open(ENDERECOS, "wb") as f:
        while bloco := resp.read(1 << 20):
            f.write(bloco)


def carregar_enderecos():
    """Indexa a base da PBH por (tipo, logradouro) -> número -> [(bairro, x, y)]."""
    indice = defaultdict(lambda: defaultdict(list))
    ponto = re.compile(r"POINT \(([\d.]+) ([\d.]+)\)")
    with open(ENDERECOS, encoding="utf-8") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            m = ponto.match(linha["GEOMETRIA"])
            if not m or not linha["NUMERO_IMOVEL"].isdigit():
                continue
            rua = (linha["SIGLA_TIPO_LOGRADOURO"], normalizar(linha["NOME_LOGRADOURO"]))
            indice[rua][int(linha["NUMERO_IMOVEL"])].append(
                (linha["NOME_BAIRRO_POPULAR"], float(m.group(1)), float(m.group(2)))
            )
    return indice


def escolher(candidatos, bairro):
    for c in candidatos:
        if normalizar(c[0]) == bairro:
            return c
    return candidatos[0]


def localizar(indice, bar):
    numeros = indice.get((bar["DESC_LOGRADOURO"], normalizar(bar["NOME_LOGRADOURO"])))
    if not numeros or not bar["NUMERO_IMOVEL"].isdigit():
        return None, "sem logradouro"
    numero = int(bar["NUMERO_IMOVEL"])
    bairro = normalizar(bar["NOME_BAIRRO"])
    if numero in numeros:
        return escolher(numeros[numero], bairro), "exato"
    proximo = min(numeros, key=lambda n: abs(n - numero))
    if abs(proximo - numero) > MAX_DIFERENCA_NUMERO:
        return None, "número distante"
    return escolher(numeros[proximo], bairro), "número vizinho"


def main():
    baixar_enderecos()
    indice = carregar_enderecos()
    vias_osm = nomes_de_vias_osm()
    utm_para_geo = Transformer.from_crs("EPSG:31983", "EPSG:4326", always_xy=True)

    contagem = defaultdict(int)
    saida = []
    with gzip.open(BARES, "rt", encoding="utf-8") as f:
        for bar in csv.DictReader(f):
            achado, situacao = localizar(indice, bar)
            contagem[situacao] += 1
            if achado is None:
                continue
            bairro, x, y = achado
            lon, lat = utm_para_geo.transform(x, y)
            tipo = TIPOS.get(bar["DESC_LOGRADOURO"], bar["DESC_LOGRADOURO"].title())
            via = f"{tipo} {titulo(bar['NOME_LOGRADOURO'], False)}"
            via = vias_osm.get(normalizar(via), via)
            saida.append({
                "id": bar["_id"],
                "nome": nome_exibicao(bar["NOME_FANTASIA"], bar["NOME"]),
                "categoria": CATEGORIAS.get(bar["CNAE_PRINCIPAL"], "Restaurante"),
                "endereco": f"{via}, {bar['NUMERO_IMOVEL']}",
                "bairro": bairro,
                "lat": f"{lat:.6f}",
                "lon": f"{lon:.6f}",
            })

    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(saida[0]))
        escritor.writeheader()
        escritor.writerows(saida)

    total = sum(contagem.values())
    for situacao, n in sorted(contagem.items(), key=lambda kv: -kv[1]):
        print(f"{situacao:>16}: {n:6d} ({100 * n / total:.2f}%)")
    print(f"{len(saida)} de {total} estabelecimentos gravados em {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
