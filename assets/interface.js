// O campo numérico ao lado do slider do raio só confirma o valor quando perde o
// foco. Enter também deveria confirmar.
document.addEventListener("keydown", function (evento) {
  var alvo = evento.target;
  if (evento.key === "Enter" && alvo.classList && alvo.classList.contains("dash-range-slider-input")) {
    alvo.blur();
  }
});
