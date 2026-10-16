import random
from math import cos, pi, radians
from pathlib import Path
from statistics import median
from time import perf_counter

from geofrota import geohash
from geofrota.frota import Frota, escolher_precisao
from geofrota.geo import RAIO_TERRA_M, caixa_envolvente, haversine
from geofrota.malha import Malha
from geofrota.restaurantes import Restaurantes

DADOS = Path(__file__).resolve().parent.parent / "data"
REPETICOES = 30
METROS_POR_GRAU = pi * RAIO_TERRA_M / 180
CONSULTAS = {
    "54662": "Casa Cheia (Mercado Central, Centro)",
    "35912": "Café com Letras (Savassi)",
    "418442": "Bolão (Santa Tereza)",
    "51749": "Restaurante Xapuri (Pampulha)",
    "12242": "Fazenda Mineira (Venda Nova)",
    "936": "Tatu Rei do Angu (Barreiro)",
}


def br(valor, casas=0):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def cronometrar(funcao, repeticoes=REPETICOES):
    """Mediana do tempo de `repeticoes` execuções, em ms, e o último resultado."""
    tempos = []
    for _ in range(repeticoes):
        inicio = perf_counter()
        resultado = funcao()
        tempos.append(perf_counter() - inicio)
    return 1000 * median(tempos), resultado


def tabela(cabecalho, linhas):
    print("| " + " | ".join(cabecalho) + " |")
    print("|" + "|".join("---:" if i else "---" for i in range(len(cabecalho))) + "|")
    for linha in linhas:
        print("| " + " | ".join(str(c) for c in linha) + " |")
    print()


def nos_trie_simples(chaves):
    """Nós que uma trie não compacta teria: um por prefixo distinto, mais a raiz."""
    return 1 + len({c[:i] for c in chaves for i in range(1, len(c) + 1)})


def menor_lado_m(precisao, lat):
    altura, largura = geohash.dimensoes(precisao)
    return min(altura * METROS_POR_GRAU, largura * METROS_POR_GRAU * cos(radians(lat)))


def busca_linear(frota, lat, lon, raio_m):
    return [i for i in range(len(frota)) if haversine(lat, lon, frota.lat[i], frota.lon[i]) <= raio_m]


def busca_trie(frota, lat, lon, raio_m, precisao=None):
    """Trie + filtro por distância, sem o cálculo de rotas."""
    caixa = caixa_envolvente(lat, lon, raio_m)
    candidatos = []
    for celula in geohash.cobertura(*caixa, precisao or escolher_precisao(caixa)):
        candidatos.extend(frota.indice.buscar_prefixo(celula))
    return [i for i in candidatos if haversine(lat, lon, frota.lat[i], frota.lon[i]) <= raio_m]


def medir_carga():
    inicio = perf_counter()
    malha = Malha(DADOS / "malha_bh.graphml.gz")
    t_malha = perf_counter() - inicio
    inicio = perf_counter()
    restaurantes = Restaurantes(DADOS / "restaurantes.csv")
    t_rest = perf_counter() - inicio
    print("## Carga\n")
    tabela(["Etapa", "Tempo (s)"], [
        ["Malha viária (GraphML, projeção, índice espacial)", br(t_malha, 2)],
        [f"{br(len(restaurantes))} restaurantes + Trie de palavras", br(t_rest, 2)],
    ])
    return malha, restaurantes


def medir_geracao(frota):
    print("## Geração da frota (dispersão 500 m)\n")
    linhas = []
    for n in (1_000, 5_000, 20_000, 100_000):
        t, _ = cronometrar(lambda: frota.gerar(n, 500, semente=1), repeticoes=3)
        linhas.append([
            br(n), br(t), br(len(set(frota.geohashes))),
            br(frota.indice.contar_nos()), br(nos_trie_simples(frota.geohashes)),
        ])
    tabela(["N", "Tempo (ms)", "Geohashes distintos", "Nós (Trie compacta)", "Nós (Trie simples)"], linhas)


def medir_consultas(frota, restaurantes):
    frota.gerar(5_000, 500, semente=1)
    print("## Consultas (N = 5.000, dispersão 500 m, mediana de 30 execuções)\n")
    linhas = []
    for id_, rotulo in CONSULTAS.items():
        r = restaurantes.por_id[id_]
        for raio_km in (1, 2, 3):
            tempos = {"trie": [], "filtro": [], "rotas": [], "total": []}
            for _ in range(REPETICOES):
                res = frota.buscar(r, raio_km * 1000)
                for etapa in tempos:
                    tempos[etapa].append(res.tempos_ms[etapa])
            linhas.append([
                rotulo, raio_km, res.precisao, len(res.celulas), br(len(res.candidatos)),
                br(len(res.atendem)),
                *(br(median(tempos[e]), 3) for e in ("trie", "filtro", "rotas", "total")),
            ])
    tabela(["Restaurante", "Raio (km)", "Precisão", "Células", "Candidatos", "No raio",
            "Trie (ms)", "Filtro (ms)", "Rotas (ms)", "Total (ms)"], linhas)


def medir_precisao(frota, restaurantes):
    print("## Efeito da precisão (N = 5.000, raio 2 km, média dos 6 restaurantes)\n")
    linhas = []
    for p in (4, 5, 6, 7):
        celulas = candidatos = tempo = 0
        for id_ in CONSULTAS:
            r = restaurantes.por_id[id_]
            t, _ = cronometrar(lambda: busca_trie(frota, r.lat, r.lon, 2000, p))
            res = frota.buscar(r, 2000, precisao=p)
            celulas += len(res.celulas)
            candidatos += len(res.candidatos)
            tempo += t
        k = len(CONSULTAS)
        linhas.append([p, br(celulas / k, 1), br(candidatos / k), br(tempo / k, 3)])
    tabela(["Precisão", "Células", "Candidatos", "Trie + filtro (ms)"], linhas)


def medir_linear(frota, restaurantes):
    print("## Trie x varredura linear (raio 2 km, média dos 6 restaurantes)\n")
    linhas = []
    for n in (1_000, 5_000, 20_000, 100_000):
        frota.gerar(n, 500, semente=1)
        t_trie = t_linear = 0
        for id_ in CONSULTAS:
            r = restaurantes.por_id[id_]
            a, com_trie = cronometrar(lambda: busca_trie(frota, r.lat, r.lon, 2000), 10)
            b, linear = cronometrar(lambda: busca_linear(frota, r.lat, r.lon, 2000), 3)
            assert sorted(com_trie) == linear
            t_trie += a
            t_linear += b
        k = len(CONSULTAS)
        linhas.append([br(n), br(t_trie / k, 3), br(t_linear / k, 3), f"{br(t_linear / t_trie, 1)}x"])
    tabela(["N", "Trie + filtro (ms)", "Varredura linear (ms)", "Razão"], linhas)


def medir_borda(frota, restaurantes):
    print("## Problema de borda (N = 5.000, 1.000 restaurantes sorteados)\n")
    frota.gerar(5_000, 500, semente=1)
    rng = random.Random(7)
    pontos = [restaurantes.lista[rng.randrange(len(restaurantes))] for _ in range(1000)]
    linhas = []
    for raio in (500, 1000, 2000):
        total = perdidos_celula = perdidos_grande = perdidos_cobertura = 0
        for r in pontos:
            certos = set(busca_linear(frota, r.lat, r.lon, raio))
            p = escolher_precisao(caixa_envolvente(r.lat, r.lon, raio))
            so_celula = set(frota.indice.buscar_prefixo(geohash.codificar(r.lat, r.lon, p)))
            # Uma célula só, mas grande o bastante para conter o círculo inteiro se
            # o restaurante estivesse no centro dela.
            p_grande = max(q for q in range(1, 9) if menor_lado_m(q, r.lat) >= 2 * raio)
            grande = set(frota.indice.buscar_prefixo(geohash.codificar(r.lat, r.lon, p_grande)))
            cobertura = set(busca_trie(frota, r.lat, r.lon, raio))
            total += len(certos)
            perdidos_celula += len(certos - so_celula)
            perdidos_grande += len(certos - grande)
            perdidos_cobertura += len(certos - cobertura)
        linhas.append([
            br(raio), br(total), f"{br(100 * perdidos_celula / total, 1)}%", p_grande,
            f"{br(100 * perdidos_grande / total, 1)}%", f"{br(100 * perdidos_cobertura / total, 1)}%",
        ])
    tabela(["Raio (m)", "Pares no raio", "Só a célula do restaurante", "Precisão da célula grande",
            "Só uma célula grande", "Cobertura com vizinhas"], linhas)


def main():
    malha, restaurantes = medir_carga()
    frota = Frota(malha, restaurantes, DADOS / "limite_bh.geojson")
    medir_geracao(frota)
    medir_consultas(frota, restaurantes)
    medir_precisao(frota, restaurantes)
    medir_linear(frota, restaurantes)
    medir_borda(frota, restaurantes)


if __name__ == "__main__":
    main()
