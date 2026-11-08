-- Consentimiento de la medición publicitaria web (2026-11-08). Spec: docs/plan_seo_redes_web_20261108.md (F0).
-- Aditiva. Guarda la decisión de quien abrió el checkout para que el webhook de compra (Purchase/Subscribe
-- hacia Meta), que llega sin navegador, la respete. Las filas anteriores se crearon con la medición activa
-- por defecto (decisión del 2026-10-15), así que quedan en true.
ALTER TABLE whop_checkouts ADD COLUMN IF NOT EXISTS ads_consent boolean NOT NULL DEFAULT true;
