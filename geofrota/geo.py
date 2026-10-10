from math import asin, cos, degrees, radians, sin, sqrt

RAIO_TERRA_M = 6_371_008.8


def haversine(lat1, lon1, lat2, lon2):
    """Distância em metros sobre a esfera."""
    f1, f2 = radians(lat1), radians(lat2)
    dlat = f2 - f1
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(f1) * cos(f2) * sin(dlon / 2) ** 2
    return 2 * RAIO_TERRA_M * asin(sqrt(a))


def caixa_envolvente(lat, lon, raio_m):
    """Menor retângulo lat/lon que contém o círculo de raio `raio_m` em torno do ponto.

    Em latitude o círculo se estende exatamente raio/R radianos. Em longitude o
    ponto mais a leste do círculo fica em asin(sin(d) / cos(lat)), um pouco mais
    que d / cos(lat) (não vale perto dos polos, o que não é problema em BH).
    """
    d = raio_m / RAIO_TERRA_M
    dlat = degrees(d)
    dlon = degrees(asin(min(1.0, sin(d) / cos(radians(lat)))))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon
