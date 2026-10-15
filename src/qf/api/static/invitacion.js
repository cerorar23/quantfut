// Copiar el código de invitación (la CSP de la página solo admite scripts de /static).
document.addEventListener("click", function (e) {
  var b = e.target.closest("[data-copy]");
  if (!b) return;
  var campo = document.getElementById(b.getAttribute("data-copy"));
  if (!campo) return;
  campo.select();
  var listo = function () {
    var antes = b.innerHTML;
    b.textContent = b.getAttribute("data-copied");
    setTimeout(function () { b.innerHTML = antes; }, 1800);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(campo.value).then(listo, function () { document.execCommand("copy"); listo(); });
  } else { document.execCommand("copy"); listo(); }
});
