// Panel /control. Sin scripts en línea (CSP 'self'): todo el comportamiento vive aquí.
(function () {
  "use strict";

  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll("[data-count-for]").forEach(function (counter) {
    var input = document.getElementById(counter.dataset.countFor);
    if (!input) return;
    var max = parseInt(counter.dataset.countMax || "0", 10);
    var update = function () {
      var len = (input.value || "").length;
      counter.textContent = max > 0 ? len + " / " + max : String(len);
      counter.classList.toggle("text-warning", max > 0 && len > max);
    };
    input.addEventListener("input", update);
    update();
  });

  var datos = document.getElementById("serie-datos");
  var lienzo = document.getElementById("grafico-serie");
  if (!datos || !lienzo || !window.Chart) return;

  var serie = JSON.parse(datos.textContent);
  new window.Chart(lienzo, {
    type: "bar",
    data: {
      labels: serie.map(function (r) { return String(r.dia).slice(5).split("-").reverse().join("/"); }),
      datasets: [
        { label: "Cuentas nuevas", data: serie.map(function (r) { return r.altas; }),
          backgroundColor: "#1c2541", borderRadius: 4 },
        { label: "Planes concedidos", type: "line", data: serie.map(function (r) { return r.suscripciones; }),
          borderColor: "#10b981", backgroundColor: "#10b981", tension: 0.3, pointRadius: 2 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } },
      plugins: { legend: { position: "bottom" } }
    }
  });
})();
