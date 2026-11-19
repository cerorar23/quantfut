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

  // Traducción progresiva por lotes para evitar error 524 de Cloudflare
  var formsLote = document.querySelectorAll("form[data-batch-translate]");
  var modalLoteEl = document.getElementById("modal-traduccion-lote");
  if (formsLote.length > 0 && modalLoteEl) {
    var tituloEl = document.getElementById("traduccion-modal-titulo");
    var statusEl = document.getElementById("traduccion-status-texto");
    var contadorEl = document.getElementById("traduccion-contador");
    var barEl = document.getElementById("traduccion-progress-bar");
    var logEl = document.getElementById("traduccion-log");
    var badgeEstado = document.getElementById("traduccion-badge-estado");
    var btnCancelar = document.getElementById("btn-cancelar-traduccion");
    var btnFinalizar = document.getElementById("btn-finalizar-traduccion");
    var btnX = document.getElementById("btn-cerrar-modal-x");
    var cancelado = false;
    var enEjecucion = false;

    var abrirModal = function () {
      if (window.bootstrap && window.bootstrap.Modal) {
        window.bootstrap.Modal.getOrCreateInstance(modalLoteEl).show();
      } else {
        modalLoteEl.classList.add("show");
        modalLoteEl.style.display = "block";
        if (!document.getElementById("custom-modal-backdrop")) {
          var backdrop = document.createElement("div");
          backdrop.className = "modal-backdrop fade show";
          backdrop.id = "custom-modal-backdrop";
          document.body.appendChild(backdrop);
        }
      }
    };

    var cerrarModal = function () {
      if (window.bootstrap && window.bootstrap.Modal) {
        var inst = window.bootstrap.Modal.getInstance(modalLoteEl);
        if (inst) inst.hide();
      } else {
        modalLoteEl.classList.remove("show");
        modalLoteEl.style.display = "none";
        var backdrop = document.getElementById("custom-modal-backdrop");
        if (backdrop) backdrop.remove();
      }
    };

    if (btnCancelar) {
      btnCancelar.addEventListener("click", function () {
        if (enEjecucion) {
          cancelado = true;
          statusEl.textContent = "Deteniendo después del elemento actual...";
          btnCancelar.disabled = true;
        } else {
          cerrarModal();
        }
      });
    }

    if (btnFinalizar) {
      btnFinalizar.addEventListener("click", function () {
        cerrarModal();
        window.location.reload();
      });
    }

    if (btnX) {
      btnX.addEventListener("click", function () {
        cerrarModal();
        window.location.reload();
      });
    }

    var ejecutarTraduccionLote = async function (mode, csrfToken) {
      enEjecucion = true;
      cancelado = false;
      if (btnCancelar) {
        btnCancelar.disabled = false;
        btnCancelar.style.display = "inline-block";
        btnCancelar.textContent = "Cancelar";
      }
      if (btnFinalizar) btnFinalizar.style.display = "none";
      if (btnX) btnX.style.display = "none";

      tituloEl.textContent = mode === "all" ? "Re-traducción completa con APIMart" : "Traducción de pendientes con APIMart";
      statusEl.textContent = "Consultando catálogo de páginas...";
      contadorEl.textContent = "0 / 0";
      barEl.style.width = "0%";
      barEl.textContent = "0%";
      barEl.className = "progress-bar progress-bar-striped progress-bar-animated bg-primary fw-bold text-white";
      badgeEstado.textContent = "Consultando";
      badgeEstado.className = "badge bg-secondary-lt";
      logEl.innerHTML = "";

      abrirModal();

      try {
        var planRes = await fetch("/control/configuracion/traducir-lote/plan?mode=" + encodeURIComponent(mode), {
          headers: { "Accept": "application/json" }
        });
        if (!planRes.ok) throw new Error("No se pudo obtener la lista de pendientes (" + planRes.status + ").");
        var plan = await planRes.json();
        var items = plan.items || [];
        var total = items.length;

        if (total === 0) {
          statusEl.textContent = "No hay páginas pendientes de traducir.";
          barEl.style.width = "100%";
          barEl.textContent = "100%";
          barEl.className = "progress-bar bg-success fw-bold text-white";
          badgeEstado.textContent = "Al día";
          badgeEstado.className = "badge bg-success-lt";
          logEl.innerHTML = '<div class="text-secondary small p-2">Todas las páginas ya cuentan con traducciones vigentes.</div>';
          if (btnCancelar) btnCancelar.style.display = "none";
          if (btnFinalizar) {
            btnFinalizar.textContent = "Cerrar";
            btnFinalizar.style.display = "inline-block";
          }
          if (btnX) btnX.style.display = "inline-block";
          enEjecucion = false;
          return;
        }

        contadorEl.textContent = "0 / " + total;
        badgeEstado.textContent = "En progreso";
        badgeEstado.className = "badge bg-azure-lt";

        var doneCount = 0;
        var errorCount = 0;

        for (var i = 0; i < total; i++) {
          if (cancelado) {
            statusEl.textContent = "Proceso cancelado por el usuario.";
            badgeEstado.textContent = "Detenido";
            badgeEstado.className = "badge bg-warning-lt";
            break;
          }

          var it = items[i];
          statusEl.textContent = "Traduciendo " + it.label + " (" + it.lang_name + ")...";
          contadorEl.textContent = (i + 1) + " / " + total;

          var itemRow = document.createElement("div");
          itemRow.className = "small py-1 border-bottom d-flex justify-content-between align-items-center";
          itemRow.innerHTML = '<span><span class="spinner-border spinner-border-sm me-1 text-primary"></span> <b>' +
            it.label + '</b> <span class="badge bg-secondary-lt ms-1">' + it.target_lang.toUpperCase() + '</span></span>' +
            '<span class="badge bg-secondary-lt">En curso</span>';
          logEl.appendChild(itemRow);
          logEl.scrollTop = logEl.scrollHeight;

          try {
            var bodyData = new FormData();
            bodyData.append("target_lang", it.target_lang);
            bodyData.append("csrf", csrfToken);
            bodyData.append("return_to", "home");

            var trRes = await fetch("/control/configuracion/pagina/" + encodeURIComponent(it.page_key) + "/traducir", {
              method: "POST",
              headers: { "Accept": "application/json" },
              body: bodyData
            });

            if (trRes.ok) {
              var trJson = await trRes.json();
              doneCount++;
              itemRow.innerHTML = '<span><span class="text-success me-1">✔</span> <b>' +
                it.label + '</b> <span class="badge bg-secondary-lt ms-1">' + it.target_lang.toUpperCase() + '</span></span>' +
                '<span class="badge bg-success-lt">' + (trJson.model || "APIMart") + '</span>';
            } else {
              var errJson = await trRes.json().catch(function () { return {}; });
              errorCount++;
              itemRow.innerHTML = '<span><span class="text-danger me-1">✖</span> <b>' +
                it.label + '</b> <span class="badge bg-secondary-lt ms-1">' + it.target_lang.toUpperCase() + '</span></span>' +
                '<span class="badge bg-danger-lt" title="' + (errJson.error || "Error") + '">Error</span>';
            }
          } catch (itemErr) {
            errorCount++;
            itemRow.innerHTML = '<span><span class="text-danger me-1">✖</span> <b>' +
              it.label + '</b> <span class="badge bg-secondary-lt ms-1">' + it.target_lang.toUpperCase() + '</span></span>' +
              '<span class="badge bg-danger-lt">Fallo de red</span>';
          }

          var pct = Math.round(((i + 1) / total) * 100);
          barEl.style.width = pct + "%";
          barEl.textContent = pct + "%";
        }

        enEjecucion = false;
        if (!cancelado) {
          statusEl.textContent = "¡Completado! " + doneCount + " páginas traducidas" +
            (errorCount > 0 ? " (" + errorCount + " errores)." : " con éxito.");
          barEl.className = errorCount > 0 ? "progress-bar bg-warning fw-bold text-dark" : "progress-bar bg-success fw-bold text-white";
          badgeEstado.textContent = errorCount > 0 ? "Con observaciones" : "Finalizado";
          badgeEstado.className = errorCount > 0 ? "badge bg-warning-lt" : "badge bg-success-lt";
        }
      } catch (err) {
        enEjecucion = false;
        statusEl.textContent = "Error al procesar: " + err.message;
        badgeEstado.textContent = "Error";
        badgeEstado.className = "badge bg-danger-lt";
      }

      if (btnCancelar) btnCancelar.style.display = "none";
      if (btnFinalizar) {
        btnFinalizar.textContent = "Listo y recargar";
        btnFinalizar.style.display = "inline-block";
      }
      if (btnX) btnX.style.display = "inline-block";
    };

    formsLote.forEach(function (form) {
      form.addEventListener("submit", function (ev) {
        if (ev.defaultPrevented) return;
        ev.preventDefault();
        var csrfInput = form.querySelector('input[name="csrf"]');
        var csrfToken = csrfInput ? csrfInput.value : "";
        ejecutarTraduccionLote(form.dataset.batchTranslate || "pending", csrfToken);
      });
    });
  }

  // Deshabilitar botón y mostrar spinner al traducir una página individual
  document.querySelectorAll('form[action*="/traducir"]').forEach(function (f) {
    if (f.dataset.batchTranslate) return;
    f.addEventListener("submit", function () {
      var btn = f.querySelector('button[type="submit"]');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>';
      }
    });
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
