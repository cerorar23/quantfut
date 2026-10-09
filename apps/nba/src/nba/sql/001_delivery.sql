-- Applied only to an explicit, isolated nba_* database by its schema owner.
CREATE SCHEMA nba_delivery;
CREATE TABLE nba_delivery.events (
    seq bigint PRIMARY KEY, received_at text NOT NULL, kind text NOT NULL,
    payload text NOT NULL CHECK (jsonb_typeof(payload::jsonb)='object'),
    previous_hash text NOT NULL, event_hash text NOT NULL UNIQUE,
    canonical_event text NOT NULL
);
CREATE TABLE nba_delivery.messages (
    id text PRIMARY KEY, payload text NOT NULL,
    sealed_hash text NOT NULL REFERENCES nba_delivery.events(event_hash),
    expires_at timestamptz NOT NULL,
    state text NOT NULL CHECK(state IN ('queued','sending','sent','unknown','rejected')),
    outcome text
);
CREATE FUNCTION nba_delivery.immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable NBA evidence'; END $$;
CREATE TRIGGER events_immutable BEFORE UPDATE OR DELETE ON nba_delivery.events
FOR EACH ROW EXECUTE FUNCTION nba_delivery.immutable();
CREATE TRIGGER events_no_truncate BEFORE TRUNCATE ON nba_delivery.events
EXECUTE FUNCTION nba_delivery.immutable();
CREATE TRIGGER messages_no_delete BEFORE DELETE ON nba_delivery.messages
FOR EACH ROW EXECUTE FUNCTION nba_delivery.immutable();
CREATE TRIGGER messages_no_truncate BEFORE TRUNCATE ON nba_delivery.messages
EXECUTE FUNCTION nba_delivery.immutable();
CREATE FUNCTION nba_delivery.validate_event() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE previous nba_delivery.events%ROWTYPE;
BEGIN
    PERFORM pg_advisory_xact_lock(74754154);
    SELECT * INTO previous FROM nba_delivery.events ORDER BY seq DESC LIMIT 1;
    IF NEW.seq != coalesce(previous.seq,0)+1 OR NEW.previous_hash != coalesce(previous.event_hash,repeat('0',64)) THEN
        RAISE EXCEPTION 'NBA chain sequence mismatch';
    END IF;
    IF NEW.canonical_event::jsonb != jsonb_build_object('seq',NEW.seq,'received_at',NEW.received_at,
        'kind',NEW.kind,'payload',NEW.payload,'previous_hash',NEW.previous_hash)
        OR encode(sha256(convert_to(NEW.canonical_event,'UTF8')),'hex') != NEW.event_hash THEN
        RAISE EXCEPTION 'NBA event hash mismatch';
    END IF;
    IF NEW.received_at::timestamptz < statement_timestamp()-interval '5 seconds'
        OR NEW.received_at::timestamptz > clock_timestamp()+interval '1 second' THEN
        RAISE EXCEPTION 'NBA event receipt must use current server clock';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER events_validate BEFORE INSERT ON nba_delivery.events
FOR EACH ROW EXECUTE FUNCTION nba_delivery.validate_event();
CREATE FUNCTION nba_delivery.validate_message() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE seal nba_delivery.events%ROWTYPE;
BEGIN
    IF TG_OP='UPDATE' THEN
        IF ROW(NEW.id,NEW.payload,NEW.sealed_hash,NEW.expires_at) IS DISTINCT FROM
           ROW(OLD.id,OLD.payload,OLD.sealed_hash,OLD.expires_at) THEN
            RAISE EXCEPTION 'immutable NBA message';
        END IF;
        IF NOT ((OLD.state='queued' AND NEW.state IN ('sending','rejected')) OR
                (OLD.state='sending' AND NEW.state IN ('sent','unknown','rejected'))) THEN
            RAISE EXCEPTION 'invalid NBA message transition';
        END IF;
    ELSE
        SELECT * INTO seal FROM nba_delivery.events WHERE event_hash=NEW.sealed_hash;
        IF NEW.state!='queued' OR NEW.outcome IS NOT NULL OR seal.kind IS DISTINCT FROM 'notification_sealed_before_queue'
            OR seal.payload::jsonb IS DISTINCT FROM jsonb_build_object('id',NEW.id,'payload',NEW.payload::jsonb)
            OR NEW.id != encode(sha256(convert_to(NEW.payload,'UTF8')),'hex')
            OR NEW.payload::jsonb->>'kind' IS DISTINCT FROM 'operational_test'
            OR NEW.expires_at IS DISTINCT FROM (NEW.payload::jsonb->>'expires_at_utc')::timestamptz THEN
            RAISE EXCEPTION 'invalid NBA seal or payload';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER messages_validate BEFORE INSERT OR UPDATE ON nba_delivery.messages
FOR EACH ROW EXECUTE FUNCTION nba_delivery.validate_message();
REVOKE ALL ON SCHEMA nba_delivery FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA nba_delivery FROM PUBLIC;
GRANT USAGE ON SCHEMA nba_delivery TO nba_worker;
GRANT SELECT,INSERT ON nba_delivery.events TO nba_worker;
GRANT SELECT,INSERT ON nba_delivery.messages TO nba_worker;
GRANT UPDATE(state,outcome) ON nba_delivery.messages TO nba_worker;
