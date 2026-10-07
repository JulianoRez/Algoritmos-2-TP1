BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
VALOR = {c: i for i, c in enumerate(BASE32)}
PRECISAO_MAXIMA = 8


def codificar(lat, lon, precisao=PRECISAO_MAXIMA):
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
