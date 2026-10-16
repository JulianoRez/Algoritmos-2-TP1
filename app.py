import json
import os
from pathlib import Path
from statistics import mean
from time import perf_counter

import dash_leaflet as dl
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from geofrota import geohash
from geofrota.frota import VELOCIDADE_MEDIA_KMH, Frota
from geofrota.geo import caixa_envolvente
from geofrota.malha import Malha
from geofrota.restaurantes import Restaurantes

DADOS = Path(__file__).resolve().parent / "data"
N_INICIAL = 1500
DISPERSAO_INICIAL = 500
N_MAXIMO = 20000
CENTRO_BH = [-19.918, -43.946]

malha = Malha(DADOS / "malha_bh.graphml.gz")
restaurantes = Restaurantes(DADOS / "restaurantes.csv")
frota = Frota(malha, restaurantes, DADOS / "limite_bh.geojson")
frota.gerar(N_INICIAL, DISPERSAO_INICIAL, semente=2026)
with open(DADOS / "limite_bh.geojson", encoding="utf-8") as f:
    LIMITE_BH = json.load(f)


def numero(valor, casas=0):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def distancia(metros):
    if metros < 1000:
        return f"{numero(metros)} m"
    return f"{numero(metros / 1000, 1)} km"


def minutos(valor):
    return "< 1 min" if valor < 1 else f"{numero(valor)} min"


def pontos(itens):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"tooltip": dica},
            }
            for lat, lon, dica in itens
        ],
    }


def retangulos(celulas):
    features = []
    for celula in celulas:
        lat_min, lat_max, lon_min, lon_max = geohash.caixa(celula)
        anel = [[lon_min, lat_min], [lon_max, lat_min], [lon_max, lat_max],
                [lon_min, lat_max], [lon_min, lat_min]]
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [anel]},
            "properties": {"tooltip": f"célula {celula}"},
        })
    return {"type": "FeatureCollection", "features": features}


def opcao(r, busca=""):
    return {
        "value": r.id,
        "label": f"{r.nome} — {r.endereco} · {r.bairro}",
        # O dropdown filtra de novo no navegador; repetir a busca aqui garante que
        # os resultados do servidor (que ignora acentos e a ordem das palavras) apareçam.
        "search": f"{busca} {r.nome} {r.endereco} {r.bairro}",
    }


def secao(titulo, *filhos, **kwargs):
    return html.Section([html.H2(titulo), *filhos], className="secao", **kwargs)


def estatistica(rotulo, valor, detalhe=None):
    itens = [html.Dt(rotulo), html.Dd(valor)]
    if detalhe:
        itens.append(html.Dd(detalhe, className="detalhe"))
    return html.Div(itens, className="estatistica")


def status_frota(n, ms):
    return f"{numero(n)} entregadores gerados em {numero(ms)} ms."


def resumo_indice():
    return f"{numero(len(frota))} entregadores · {numero(frota.indice.contar_nos())} nós na Trie"


def painel():
    return html.Aside(className="painel", children=[
        secao(
            "Restaurante",
            html.Label("Buscar por nome, rua ou bairro", htmlFor="restaurante", className="rotulo"),
            dcc.Dropdown(
                id="restaurante",
                options=[],
                placeholder="Ex.: Xapuri, Rua da Bahia, Savassi",
                labels={
                    "search": "Digite pelo menos 2 letras",
                    "no_options_found": "Nenhum restaurante encontrado",
                    "clear_selection": "Limpar",
                    "clear_search": "Limpar busca",
                },
                maxHeight=360,
            ),
            html.Div(id="restaurante-detalhe", className="restaurante-detalhe"),
        ),
        secao(
            "Raio de atendimento",
            html.Label("Distância máxima em linha reta (km)", htmlFor="raio", className="rotulo"),
            dcc.Slider(
                id="raio", min=0.5, max=5, step=0.1, value=2,
                marks={v: f"{numero(v, 1) if v % 1 else int(v)}" for v in (0.5, 1, 2, 3, 4, 5)},
                allow_direct_input=True,
                updatemode="mouseup",
            ),
        ),
        secao(
            "Frota simulada",
            html.Div(className="campos", children=[
                html.Div([
                    html.Label("Entregadores", htmlFor="n-entregadores", className="rotulo"),
                    dcc.Input(id="n-entregadores", type="number", min=1, max=N_MAXIMO, step=1,
                              value=len(frota), className="campo"),
                ]),
                html.Div([
                    html.Label("Dispersão (m)", htmlFor="dispersao", className="rotulo"),
                    dcc.Input(id="dispersao", type="number", min=50, max=3000, step=50,
                              value=frota.dispersao_m, className="campo"),
                ]),
            ]),
            html.P(
                "Posições sorteadas com distribuição normal em torno dos restaurantes "
                "e projetadas na via mais próxima. A dispersão é o desvio padrão.",
                className="ajuda",
            ),
            html.Button("Gerar entregadores", id="gerar", className="botao", n_clicks=0),
            html.P(id="status-frota", className="status", role="status",
                   children=f"{numero(len(frota))} entregadores na frota atual."),
        ),
        secao("Resultado", html.Div(id="resumo", **{"aria-live": "polite"})),
    ])


mapa = html.Div(className="mapa", children=[
    dl.Map(
        id="mapa", center=CENTRO_BH, zoom=12, preferCanvas=True, style={"height": "100%"},
        children=[
            dl.TileLayer(
                url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                maxZoom=19,
            ),
            dl.GeoJSON(data=LIMITE_BH, interactive=False,
                       style={"color": "#5f5d57", "weight": 1.2, "dashArray": "4 4", "fill": False}),
            dl.GeoJSON(id="celulas",
                       style={"color": "#3d5a80", "weight": 1, "opacity": 0.6, "fillOpacity": 0.04}),
            dl.LayerGroup(id="raio-camada"),
            dl.GeoJSON(id="descartados", pointToLayer={"variable": "mapa.descartado"}),
            dl.GeoJSON(id="atendem", pointToLayer={"variable": "mapa.atende"}),
            dl.GeoJSON(id="restaurante-pino", pointToLayer={"variable": "mapa.restaurante"}),
            dl.ScaleControl(position="bottomright", imperial=False),
        ],
    ),
    html.Ul(className="legenda", children=[
        html.Li([html.Span(className="simbolo simbolo-restaurante"), "Restaurante"]),
        html.Li([html.Span(className="simbolo simbolo-atende"), "No raio"]),
        html.Li([html.Span(className="simbolo simbolo-descartado"), "Fora do raio"]),
        html.Li([html.Span(className="simbolo simbolo-celula"), "Células Geohash consultadas"]),
    ]),
])


# A frota fica na memória do servidor, então o layout é montado a cada carregamento
# da página para mostrar o estado atual dela.
def layout():
    return html.Div(className="app", children=[
        html.Header(className="topo", children=[
            html.Div([
                html.H1("Frota BH"),
                html.P("Entregadores próximos a restaurantes de Belo Horizonte", className="subtitulo"),
            ]),
            html.P(id="indice", className="indice", children=resumo_indice()),
        ]),
        html.Div(className="corpo", children=[
            painel(),
            html.Main(className="principal", children=[
                mapa,
                html.Section(id="lista", className="lista", **{"aria-label": "Entregadores no raio"}),
            ]),
        ]),
        dcc.Store(id="versao-frota", data=0),
    ])


app = Dash(__name__, title="Frota BH", update_title=None)
server = app.server
app.layout = layout


@app.callback(
    Output("restaurante", "options"),
    Input("restaurante", "search_value"),
    State("restaurante", "value"),
)
def sugerir(busca, atual):
    opcoes = []
    if busca and len(busca.strip()) >= 2:
        opcoes = [opcao(r, busca) for r in restaurantes.buscar(busca)]
    if atual and atual not in {o["value"] for o in opcoes}:
        opcoes.insert(0, opcao(restaurantes.por_id[atual], busca or ""))
    return opcoes


@app.callback(
    Output("versao-frota", "data"),
    Output("status-frota", "children"),
    Output("indice", "children"),
    Input("gerar", "n_clicks"),
    State("n-entregadores", "value"),
    State("dispersao", "value"),
    State("versao-frota", "data"),
    prevent_initial_call=True,
)
def gerar(_, n, dispersao, versao):
    if not n or not 1 <= n <= N_MAXIMO:
        return no_update, f"Informe entre 1 e {numero(N_MAXIMO)} entregadores.", no_update
    if not dispersao or not 50 <= dispersao <= 3000:
        return no_update, "A dispersão deve ficar entre 50 e 3.000 m.", no_update
    inicio = perf_counter()
    frota.gerar(int(n), float(dispersao))
    ms = 1000 * (perf_counter() - inicio)
    return versao + 1, status_frota(int(n), ms), resumo_indice()


def detalhe_restaurante(r):
    return [
        html.P(r.nome, className="restaurante-nome"),
        html.P(f"{r.categoria} · {r.bairro}", className="restaurante-meta"),
        html.P(r.endereco, className="restaurante-meta"),
        html.P(["Geohash ", html.Code(geohash.codificar(r.lat, r.lon))], className="restaurante-meta"),
    ]


def tabela(r, raio_km, atendem):
    if not atendem:
        return html.P(
            f"Nenhum entregador a até {numero(raio_km, 1)} km de {r.nome}. "
            "Aumente o raio ou gere mais entregadores.",
            className="vazio",
        )
    cabecalho = html.Tr([
        html.Th("#", scope="col", className="num opcional"),
        html.Th("Entregador", scope="col"),
        html.Th("Onde está", scope="col"),
        html.Th("Linha reta", scope="col", className="num opcional"),
        html.Th("Pela rua", scope="col", className="num"),
        html.Th("Chegada", scope="col", className="num"),
    ])
    linhas = [
        html.Tr([
            html.Td(i, className="num opcional"),
            html.Td(a.id, className="id"),
            html.Td(a.via or "—"),
            html.Td(distancia(a.distancia_m), className="num opcional"),
            html.Td(distancia(a.distancia_rua_m), className="num"),
            html.Td(minutos(a.minutos), className="num"),
        ])
        for i, a in enumerate(atendem, start=1)
    ]
    return html.Table([
        html.Caption(f"{numero(len(atendem))} entregadores a até {numero(raio_km, 1)} km de {r.nome}, "
                     f"do que chega primeiro ao último"),
        html.Thead(cabecalho),
        html.Tbody(linhas),
    ])


def resumo(resultado, total):
    atendem = resultado.atendem
    t = resultado.tempos_ms
    itens = [estatistica("No raio", f"{numero(len(atendem))} de {numero(total)}")]
    if atendem:
        itens += [
            estatistica("Primeira chegada", minutos(atendem[0].minutos), atendem[0].id),
            estatistica("Chegada média", minutos(mean(a.minutos for a in atendem))),
            estatistica("Distância média", distancia(mean(a.distancia_rua_m for a in atendem)), "pela rua"),
        ]
    itens += [
        estatistica(
            "Candidatos da Trie", numero(len(resultado.candidatos)),
            f"{numero(len(resultado.celulas))} células de {resultado.precisao} caracteres",
        ),
        estatistica(
            "Tempo da consulta", f"{numero(t['total'], 1)} ms",
            f"Trie {numero(t['trie'], 2)} · filtro {numero(t['filtro'], 2)} · rotas {numero(t['rotas'], 1)}",
        ),
    ]
    return [
        html.Dl(itens, className="estatisticas"),
        html.P(f"Chegada estimada a {VELOCIDADE_MEDIA_KMH} km/h pelo menor caminho na malha viária.",
               className="ajuda"),
    ]


@app.callback(
    Output("atendem", "data"),
    Output("descartados", "data"),
    Output("celulas", "data"),
    Output("restaurante-pino", "data"),
    Output("raio-camada", "children"),
    Output("restaurante-detalhe", "children"),
    Output("resumo", "children"),
    Output("lista", "children"),
    Output("mapa", "viewport"),
    Input("restaurante", "value"),
    Input("raio", "value"),
    Input("versao-frota", "data"),
)
def consultar(restaurante_id, raio_km, _):
    vazio = pontos([])
    if not restaurante_id:
        todos = pontos(zip(frota.lat, frota.lon, frota.ids))
        dica = html.P("Escolha um restaurante para ver quem pode atendê-lo.", className="vazio")
        return vazio, todos, vazio, vazio, [], None, dica, dica, no_update

    r = restaurantes.por_id[restaurante_id]
    raio_km = min(max(raio_km or 2, 0.5), 5)
    raio_m = raio_km * 1000
    resultado = frota.buscar(r, raio_m)

    no_raio = {a.id for a in resultado.atendem}
    atendem = pontos(
        (a.lat, a.lon, f"<b>{a.id}</b><br>{a.via or 'sem nome'}<br>"
                       f"{distancia(a.distancia_rua_m)} pela rua · {minutos(a.minutos)}")
        for a in resultado.atendem
    )
    descartados = pontos(
        (lat, lon, i) for lat, lon, i in zip(frota.lat, frota.lon, frota.ids) if i not in no_raio
    )
    restaurante = pontos([(r.lat, r.lon, f"<b>{r.nome}</b><br>{r.endereco}")])
    circulo = [dl.Circle(
        center=[r.lat, r.lon], radius=raio_m, interactive=False,
        pathOptions={"color": "#c62828", "weight": 1.5, "dashArray": "6 4",
                     "fillColor": "#c62828", "fillOpacity": 0.05},
    )]

    viewport = no_update
    if ctx.triggered_id != "versao-frota":
        lat_min, lat_max, lon_min, lon_max = caixa_envolvente(r.lat, r.lon, raio_m * 1.1)
        viewport = {"bounds": [[lat_min, lon_min], [lat_max, lon_max]], "transition": "fitBounds"}

    return (
        atendem, descartados, retangulos(resultado.celulas), restaurante, circulo,
        detalhe_restaurante(r), resumo(resultado, len(frota)),
        tabela(r, raio_km, resultado.atendem), viewport,
    )


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8050)),
            debug=os.environ.get("DEBUG") == "1")
