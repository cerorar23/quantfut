SELECT t.store,t.plan_code,t.environment,t.created_at,
       (s.revoked_at IS NULL AND s.starts_at <= now() AND (s.ends_at IS NULL OR s.ends_at > now())) AS vip_active,
       s.ends_at
FROM store_transactions t
LEFT JOIN subscriptions s ON s.subscription_id=t.subscription_id
WHERE t.store='google_play' AND t.created_at > now()-interval '2 hours'
ORDER BY t.created_at DESC LIMIT 5;
