BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
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
