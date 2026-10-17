# Frota BH

Trabalho Prático 1 de Algoritmos 2 (DCC207, UFMG, 2026/2).

Sistema que encontra os entregadores que podem atender um restaurante de Belo Horizonte. As posições dos entregadores são codificadas em Geohash e guardadas em uma Trie compacta; a busca percorre a célula do restaurante e as vizinhas, filtra os candidatos pela distância e ordena o resultado pelo tempo estimado de chegada pela malha viária.

Integrantes: _preencher_

## Execução

Requer Python 3.12. A partir da raiz do repositório:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

A interface abre em http://127.0.0.1:8050. A inicializaçao leva cerca de 5 segundos, quase todos gastos lendo a malha viária.

Com Docker:

```
docker build -t frota-bh .
docker run --rm -p 8050:8050 frota-bh
```

No contêiner o servidor é o gunicorn, com um processo e quatro threads. Deve ser um processo só, porque a frota gerada fica na memória dele.

Testes e medições:

```
pip install -r requirements-dev.txt
python -m pytest
python -m scripts.medir
```

### Dados

Tudo o que a aplicação lê já está em `data/`. Os scripts só são necessários para refazer os arquivos, e devem rodar nesta ordem:

| Arquivo | Conteúdo | Gerado por |
|---|---|---|
| `bares.csv.gz` | base de bares e restaurantes fornecida com o enunciado | |
| `malha_bh.graphml.gz`, `limite_bh.geojson` | malha viária e limite do município, do OpenStreetMap | `python scripts/baixar_malha.py` |
| `restaurantes.csv` | `bares.csv.gz` com coordenadas | `python scripts/geocodificar.py` |

O `geocodificar.py` baixa a base de endereços da PBH (cerca de 130 MB) para `.cache/` na primeira execução. O `baixar_malha.py` aceita `--overpass URL` para usar um espelho do Overpass quando o servidor principal está sobrecarregado, o que aconteceu durante o desenvolvimento (usamos `https://maps.mail.ru/osm/tools/overpass/api`).

### Organização

```
app.py               interface (Dash e dash-leaflet)
geofrota/
  geohash.py         codificação, decodificação e cobertura de um retângulo por células
  trie.py            Trie compacta
  geo.py             haversine, retângulo envolvente de um círculo, conversão para UTM
  malha.py           malha viária: projeção na via mais próxima e distância pela rua
  frota.py           gerador de entregadores e busca
  restaurantes.py    leitura dos restaurantes e busca por nome
assets/              CSS e as funções JavaScript que desenham os pinos
scripts/             preparação dos dados e medições
tests/               testes (pytest)
docs/img/            capturas de tela usadas no relatório
```

Geohash, Trie, cobertura de células, distância haversine e a busca são implementação nossa. As bibliotecas de terceiros entram nas outras partes:

| Biblioteca | Uso |
|---|---|
| dash, dash-leaflet | página interativa e mapa |
| osmnx | download da malha viária do OpenStreetMap e conversão para grafo |
| shapely | índice espacial (STRtree) das ruas e projeção de pontos sobre elas |
| pyproj | conversão entre latitude/longitude e UTM |
| scipy | Dijkstra para a distância pela rua |
| numpy | sorteio das posições e operações vetoriais |

O osmnx traz pandas e geopandas como dependências. Nosso código não os usa diretamente, a não ser para ler as arestas que o osmnx devolve; os CSV são lidos com o módulo `csv` da biblioteca padrão.
