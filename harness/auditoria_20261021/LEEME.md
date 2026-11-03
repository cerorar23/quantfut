# Scripts de la auditoría del 21-oct-2026

Reproducen las cifras de `docs/auditoria_motores_20261021.md`. Son de solo lectura y ninguno se despliega.

- Servidor (dentro de `quantfut-worker-1`, copiados a `/tmp`): `convergencia.py`, `prueba_rapido.py`, `diag_a*.py`,
  `diag_cal.py [config]`, `wf_rapido.py nombre:hl:xb:ridge_crudo:activos`, `comparar_wf.py`, `robustez_c4.py`.
  Las salidas se guardan en `/srv/quantfut/artifacts/audit/`.
- Local, con la caché de football-data: `python audit_b.py .local/fd_cache`, `audit_b2.py` y `audit_c.py`.
- `dc_rapido.py` es el **prototipo** del ajuste con gradiente analítico. No es código de producción: para llevarlo a
  `model/dixon_coles.py` hacen falta pruebas (incluida `tests/test_cross_league.py` a 1e-9) y tu confirmación.
