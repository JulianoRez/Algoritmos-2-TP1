import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class Restaurante:
    id: str
    nome: str
    categoria: str
    endereco: str
    bairro: str
    lat: float
    lon: float


class Restaurantes:
    def __init__(self, caminho_csv):
        with open(caminho_csv, encoding="utf-8") as f:
            self.lista = [
                Restaurante(r["id"], r["nome"], r["categoria"], r["endereco"], r["bairro"],
                            float(r["lat"]), float(r["lon"]))
                for r in csv.DictReader(f)
            ]
        self.por_id = {r.id: r for r in self.lista}

    def __len__(self):
        return len(self.lista)
