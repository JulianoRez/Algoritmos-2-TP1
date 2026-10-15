import csv
import re
import unicodedata
from dataclasses import dataclass

from .geo import para_utm
from .trie import TrieCompacta


@dataclass(frozen=True)
class Restaurante:
    id: str
    nome: str
    categoria: str
    endereco: str
    bairro: str
    lat: float
    lon: float
    x: float  # UTM 23S, em metros
    y: float


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).split()


class Restaurantes:
    """Estabelecimentos geocodificados e um índice de palavras para a busca por texto.

    O índice é a mesma Trie compacta usada para os geohashes, agora com as palavras
    do nome, do endereço e do bairro como chaves. Uma consulta como "bar sav"
    vira a interseção dos resultados de buscar_prefixo("bar") e buscar_prefixo("sav").
    """

    def __init__(self, caminho_csv):
        with open(caminho_csv, encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
        lat = [float(r["lat"]) for r in linhas]
        lon = [float(r["lon"]) for r in linhas]
        x, y = para_utm(lat, lon)
        self.lista = [
            Restaurante(r["id"], r["nome"], r["categoria"], r["endereco"], r["bairro"], *coords)
            for r, *coords in zip(linhas, lat, lon, x, y)
        ]
        self.por_id = {r.id: r for r in self.lista}
        self._nomes = [" ".join(normalizar(r.nome)) for r in self.lista]
        self._palavras = TrieCompacta()
        for i, r in enumerate(self.lista):
            for palavra in set(normalizar(f"{r.nome} {r.endereco} {r.bairro}")):
                self._palavras.inserir(palavra, i)

    def __len__(self):
        return len(self.lista)

    def buscar(self, texto, limite=30):
        termos = normalizar(texto)
        if not termos:
            return []
        achados = None
        for termo in termos:
            conjunto = set(self._palavras.buscar_prefixo(termo))
            achados = conjunto if achados is None else achados & conjunto
            if not achados:
                return []
        consulta = " ".join(termos)

        def ordem(i):
            nome = self._nomes[i]
            return (not nome.startswith(consulta), consulta not in nome, nome)

        return [self.lista[i] for i in sorted(achados, key=ordem)[:limite]]
