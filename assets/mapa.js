(function () {
  function pino(cor, largura, altura) {
    var svg =
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 32" width="' + largura +
      '" height="' + altura + '" aria-hidden="true">' +
      '<path d="M12 .5C5.7.5.5 5.6.5 11.9c0 8.5 11.5 19.6 11.5 19.6s11.5-11.1 11.5-19.6C23.5 5.6 18.3.5 12 .5z"' +
      ' fill="' + cor + '" stroke="#ffffff" stroke-width="1.2"/>' +
      '<circle cx="12" cy="12" r="4.2" fill="#ffffff"/></svg>';
    return L.divIcon({
      className: "pino",
      html: svg,
      iconSize: [largura, altura],
      iconAnchor: [largura / 2, altura - 1],
      tooltipAnchor: [0, -altura + 6],
    });
  }

  var pinoAtende = pino("#c62828", 20, 27);
  var pinoRestaurante = pino("#1c1b19", 28, 37);

  window.mapa = {
    atende: function (feature, latlng) {
      return L.marker(latlng, { icon: pinoAtende, keyboard: false, riseOnHover: true });
    },
    descartado: function (feature, latlng) {
      return L.circleMarker(latlng, {
        radius: 3.5,
        color: "#ffffff",
        weight: 1,
        fillColor: "#8a8780",
        fillOpacity: 0.9,
      });
    },
    restaurante: function (feature, latlng) {
      return L.marker(latlng, { icon: pinoRestaurante, keyboard: false, zIndexOffset: 1000 });
    },
  };
})();
