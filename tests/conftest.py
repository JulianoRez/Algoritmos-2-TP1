from pathlib import Path

import pytest

from geofrota.malha import Malha
from geofrota.restaurantes import Restaurantes

DADOS = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="session")
def malha():
    return Malha(DADOS / "malha_bh.graphml.gz")


@pytest.fixture(scope="session")
def restaurantes():
    return Restaurantes(DADOS / "restaurantes.csv")
