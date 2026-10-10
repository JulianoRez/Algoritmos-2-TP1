from math import floor

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
VALOR = {c: i for i, c in enumerate(BASE32)}
PRECISAO_MAXIMA = 8


def codificar(lat, lon, precisao=PRECISAO_MAXIMA):
    if not 1 <= precisao <= PRECISAO_MAXIMA:
        raise ValueError(f"precisão deve estar entre 1 e {PRECISAO_MAXIMA}")
    lat_ini, lat_fim = -90.0, 90.0
    lon_ini, lon_fim = -180.0, 180.0
    caracteres = []
    valor = 0
    bits = 0
    eh_lon = True
    while len(caracteres) < precisao:
        if eh_lon:
            meio = (lon_ini + lon_fim) / 2
            if lon >= meio:
                valor = (valor << 1) | 1
                lon_ini = meio
            else:
                valor <<= 1
                lon_fim = meio
        else:
            meio = (lat_ini + lat_fim) / 2
            if lat >= meio:
                valor = (valor << 1) | 1
                lat_ini = meio
            else:
                valor <<= 1
                lat_fim = meio
        eh_lon = not eh_lon
        bits += 1
        if bits == 5:
            caracteres.append(BASE32[valor])
            valor = 0
            bits = 0
    return "".join(caracteres)


def caixa(geohash):
    """Limites (lat_min, lat_max, lon_min, lon_max) da célula."""
    lat_ini, lat_fim = -90.0, 90.0
    lon_ini, lon_fim = -180.0, 180.0
    eh_lon = True
    for c in geohash:
        valor = VALOR[c]
        for desloc in range(4, -1, -1):
            bit = (valor >> desloc) & 1
            if eh_lon:
                meio = (lon_ini + lon_fim) / 2
                if bit:
                    lon_ini = meio
                else:
                    lon_fim = meio
            else:
                meio = (lat_ini + lat_fim) / 2
                if bit:
                    lat_ini = meio
                else:
                    lat_fim = meio
            eh_lon = not eh_lon
    return lat_ini, lat_fim, lon_ini, lon_fim


def decodificar(geohash):
    """Centro da célula."""
    lat_ini, lat_fim, lon_ini, lon_fim = caixa(geohash)
    return (lat_ini + lat_fim) / 2, (lon_ini + lon_fim) / 2


def dimensoes(precisao):
    """Altura e largura da célula, em graus de latitude e de longitude."""
    bits = 5 * precisao
    bits_lon = (bits + 1) // 2
    bits_lat = bits // 2
    return 180.0 / (1 << bits_lat), 360.0 / (1 << bits_lon)


def _indices(lat_min, lat_max, lon_min, lon_max, precisao):
    altura, largura = dimensoes(precisao)
    return (
        floor((lon_min + 180.0) / largura),
        floor((lon_max + 180.0) / largura),
        floor((lat_min + 90.0) / altura),
        floor((lat_max + 90.0) / altura),
    )


def tamanho_cobertura(lat_min, lat_max, lon_min, lon_max, precisao):
    i_ini, i_fim, j_ini, j_fim = _indices(lat_min, lat_max, lon_min, lon_max, precisao)
    return (i_fim - i_ini + 1) * (j_fim - j_ini + 1)


def cobertura(lat_min, lat_max, lon_min, lon_max, precisao):
    """Geohashes de todas as células da precisão dada que tocam o retângulo.

    Na precisão p as células formam uma grade regular em latitude/longitude, então
    a célula (i, j) tem como vizinhas as células (i +- 1, j +- 1). Basta achar os
    índices das células dos cantos e percorrer a grade entre eles. Quando o
    retângulo cabe em uma célula, o resultado é a célula central e, no máximo,
    as vizinhas que ele alcança.
    """
    altura, largura = dimensoes(precisao)
    i_ini, i_fim, j_ini, j_fim = _indices(lat_min, lat_max, lon_min, lon_max, precisao)
    return [
        codificar(-90.0 + (j + 0.5) * altura, -180.0 + (i + 0.5) * largura, precisao)
        for j in range(j_ini, j_fim + 1)
        for i in range(i_ini, i_fim + 1)
    ]
