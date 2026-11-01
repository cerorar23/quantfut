# Mediciones de fases del Motor A (26-oct-2026)

Se lanzan con `scripts/entrenamiento_local/ejecutar.sh .local/entreno_AAAAMMDD <módulo>` o, los de esta carpeta, con el
Python del entorno (`source scripts/entrenamiento_local/entorno.sh` y `$PY -X utf8 <script> <argumentos>`).

- `solidez.py <oos.pkl> <salida.json>`: la puerta de `qf.model.ajuste` con 4 particiones de validación (20/30/40/50 % final).
- `diagonal.py <oos.pkl>`: inflación diagonal (Karlis y Ntzoufras, 2003) y corrección del nivel de goles sobre el OOS.
- `altitud_adelante.py`: RPS con y sin el factor de altitud en sombra sobre las predicciones ya jugadas (copia local).

- `wf.py`, `kalman_var.py`, `dinamico.py`, `dinamico_puerta.py`, `ascendidos.py` (modelo dinámico y prior de ascendidos; ver docstrings).

- `apilado.py`, `apilado_mercado.py`, `estaca.py`: factores de la literatura (pi-ratings, forma de xG, tiros, viaje, motivación) apilados sobre el DC y sobre el mercado.

Informes: `docs/fases_motor_a_20261026.md`, `docs/modelo_dinamico_y_ascendidos_20261026.md` y `docs/investigacion_modelos_y_factores_20261026.md`.
