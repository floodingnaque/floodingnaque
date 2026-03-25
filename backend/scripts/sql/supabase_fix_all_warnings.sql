-- ============================================================================
-- Floodingnaque — Fix ALL Supabase Dashboard Warnings
--
-- Run this in the Supabase SQL Editor (https://supabase.com/dashboard/project/ckazvlqipxqdmwqakxue)
-- Addresses: RLS Disabled, Security Definer View, Duplicate Indexes
--
-- Generated: 2026-03-23
-- ============================================================================

-- ============================================================================
-- PART 1: ENABLE ROW-LEVEL SECURITY ON ALL TABLES
--
-- Since the Flask backend connects as the postgres (service_role) user,
-- RLS won't restrict backend operations — but it WILL protect against
-- direct Supabase client access from the frontend (anon/authenticated).
-- ============================================================================

-- Enable RLS on every table (idempotent — safe to re-run)
ALTER TABLE IF EXISTS ab_tests               ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS after_action_reports    ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS api_keys               ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS api_requests           ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs             ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS broadcasts             ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS chat_messages          ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS community_reports      ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS earth_engine_requests  ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS evacuation_alert_logs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS evacuation_centers     ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS incidents              ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS model_registry         ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS predictions            ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS resident_profiles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS satellite_weather_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tide_data_cache        ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS weather_data           ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS webhooks               ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS alert_history          ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- PART 2: RLS POLICIES
--
-- The Flask backend uses the postgres role (service_role) which bypasses RLS.
-- These policies only affect direct Supabase client connections (anon/authenticated).
-- Strategy: service_role gets full access; anon/authenticated get nothing on
-- sensitive tables, read-only on public-facing tables.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 2a. Service-role full access on ALL tables (backend bypasses RLS anyway,
--     but explicit policies prevent accidental lockout)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOR tbl IN
    SELECT unnest(ARRAY[
      'ab_tests', 'after_action_reports', 'api_keys', 'api_requests',
      'audit_logs', 'broadcasts', 'chat_messages', 'community_reports',
      'earth_engine_requests', 'evacuation_alert_logs', 'evacuation_centers',
      'incidents', 'model_registry', 'predictions', 'resident_profiles',
      'satellite_weather_cache', 'tide_data_cache', 'users',
      'weather_data', 'webhooks', 'alert_history'
    ])
  LOOP
    -- Drop existing service_role policy if it exists, then recreate
    EXECUTE format('DROP POLICY IF EXISTS "service_role_all" ON %I', tbl);
    EXECUTE format(
      'CREATE POLICY "service_role_all" ON %I FOR ALL TO postgres USING (true) WITH CHECK (true)',
      tbl
    );
  END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- 2b. Chat messages — authenticated users can read non-deleted messages
--     (needed for Supabase Realtime subscriptions)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "authenticated_read" ON chat_messages;
CREATE POLICY "authenticated_read" ON chat_messages
  FOR SELECT
  TO authenticated
  USING (is_deleted = false);

-- ---------------------------------------------------------------------------
-- 2c. Evacuation centers — public read access (shown on map)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "public_read_active" ON evacuation_centers;
CREATE POLICY "public_read_active" ON evacuation_centers
  FOR SELECT
  TO anon, authenticated
  USING (is_active = true AND is_deleted = false);

-- ---------------------------------------------------------------------------
-- 2d. Community reports — authenticated read access (non-deleted)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "authenticated_read" ON community_reports;
CREATE POLICY "authenticated_read" ON community_reports
  FOR SELECT
  TO authenticated
  USING (is_deleted = false);

-- ---------------------------------------------------------------------------
-- 2e. Broadcasts — authenticated read (non-deleted, public info)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "authenticated_read" ON broadcasts;
CREATE POLICY "authenticated_read" ON broadcasts
  FOR SELECT
  TO authenticated
  USING (is_deleted = false);

-- ---------------------------------------------------------------------------
-- 2f. Predictions — public read (non-deleted, public flood data)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "public_read" ON predictions;
CREATE POLICY "public_read" ON predictions
  FOR SELECT
  TO anon, authenticated
  USING (is_deleted = false);

-- ---------------------------------------------------------------------------
-- 2g. Weather data — public read (non-deleted)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "public_read" ON weather_data;
CREATE POLICY "public_read" ON weather_data
  FOR SELECT
  TO anon, authenticated
  USING (is_deleted = false);

-- ---------------------------------------------------------------------------
-- 2h. Alert history — public read (non-deleted, public safety info)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "public_read" ON alert_history;
CREATE POLICY "public_read" ON alert_history
  FOR SELECT
  TO anon, authenticated
  USING (is_deleted = false);

-- ---------------------------------------------------------------------------
-- 2i. Incidents — authenticated read (non-deleted)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "authenticated_read" ON incidents;
CREATE POLICY "authenticated_read" ON incidents
  FOR SELECT
  TO authenticated
  USING (is_deleted = false);

-- ---------------------------------------------------------------------------
-- NOTE: The following tables have NO public/authenticated policies (admin-only):
--   ab_tests, after_action_reports, api_keys, api_requests, audit_logs,
--   earth_engine_requests, evacuation_alert_logs, model_registry,
--   resident_profiles, satellite_weather_cache, tide_data_cache, users, webhooks
-- They are locked down — only the backend (service_role/postgres) can access them.
-- (resident_profiles.user_id is Integer, not UUID — can't use auth.uid())
-- ---------------------------------------------------------------------------


-- ============================================================================
-- PART 3: FIX SECURITY DEFINER VIEW (chat_channels)
--
-- Supabase warns when views use SECURITY DEFINER because they bypass RLS.
-- Our chat_channels view is a static lookup with no sensitive data, so we
-- recreate it with SECURITY INVOKER (the default, and the safe option).
-- ============================================================================

DROP VIEW IF EXISTS chat_channels;
CREATE VIEW chat_channels
  WITH (security_invoker = true)
AS
SELECT
  unnest(ARRAY[
    'baclaran', 'bf_homes', 'don_bosco', 'don_galo',
    'la_huerta', 'marcelo_green', 'merville', 'moonwalk',
    'san_antonio', 'san_dionisio', 'san_isidro',
    'san_martin_de_porres', 'sto_nino', 'sun_valley',
    'tambo', 'vitalez', 'citywide'
  ]) AS barangay_id,
  unnest(ARRAY[
    'Baclaran', 'BF Homes', 'Don Bosco', 'Don Galo',
    'La Huerta', 'Marcelo Green', 'Merville', 'Moonwalk',
    'San Antonio', 'San Dionisio', 'San Isidro',
    'San Martin de Porres', 'Sto. Niño', 'Sun Valley',
    'Tambo', 'Vitalez', 'Citywide Announcements'
  ]) AS display_name;

-- Grant read access so anon/authenticated can query channels
GRANT SELECT ON chat_channels TO anon, authenticated;


-- ============================================================================
-- PART 4: REMOVE DUPLICATE INDEXES
--
-- These are redundant indexes that waste storage and slow down writes.
-- We keep the more useful/composite index and drop the redundant one.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 4a. weather_data — is_deleted indexed 3 times, keep idx_weather_active
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_weather_data_is_deleted;    -- duplicate of idx_weather_active
DROP INDEX IF EXISTS idx_weather_deleted_id;         -- duplicate of idx_weather_active

-- ---------------------------------------------------------------------------
-- 4b. predictions — is_deleted indexed 3 times, keep idx_prediction_active
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_predictions_is_deleted;      -- duplicate of idx_prediction_active
DROP INDEX IF EXISTS idx_pred_deleted_id;             -- duplicate of idx_prediction_active

-- ---------------------------------------------------------------------------
-- 4c. alert_history — is_deleted duplicate
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_alert_history_is_deleted;    -- duplicate of idx_alert_active

-- ---------------------------------------------------------------------------
-- 4d. after_action_reports — incident_id indexed twice in same migration
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_after_action_reports_incident_id;  -- duplicate of idx_aar_incident

-- ---------------------------------------------------------------------------
-- 4e. evacuation_alert_logs — created_at indexed twice in same migration
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_evacuation_alert_logs_created_at;  -- duplicate of idx_alert_log_created

-- ---------------------------------------------------------------------------
-- 4f. api_requests — created_at duplicate
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_api_requests_created_at;     -- duplicate of idx_api_request_created

-- ---------------------------------------------------------------------------
-- 4g. api_requests — endpoint+status overlap (keep the one without is_deleted)
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_apireq_endpoint_status;     -- redundant with idx_api_request_endpoint_status

-- ---------------------------------------------------------------------------
-- 4h. community_reports — is_deleted simple index (composite covers it)
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_community_reports_is_deleted; -- covered by idx_report_active_created

-- ---------------------------------------------------------------------------
-- 4i. incidents — is_deleted simple index (composite covers it)
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_incidents_is_deleted;         -- covered by idx_incident_active

-- ---------------------------------------------------------------------------
-- 4j. evacuation_centers — is_deleted simple index (composite covers it)
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_evacuation_centers_is_deleted; -- covered by idx_evac_active

-- ---------------------------------------------------------------------------
-- 4k. webhooks — is_deleted duplicate
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_webhooks_is_deleted;          -- covered by idx_webhook_active

-- ---------------------------------------------------------------------------
-- 4l. audit_logs — created_at simple covered by composites
-- ---------------------------------------------------------------------------
DROP INDEX IF EXISTS ix_audit_logs_created_at;        -- covered by idx_audit_created_desc


-- ============================================================================
-- PART 5: ENABLE REALTIME (idempotent check)
-- ============================================================================

-- Only add if not already in publication
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime'
      AND tablename = 'chat_messages'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
  END IF;
END $$;


-- ============================================================================
-- DONE! Refresh the Supabase Dashboard to verify warnings are resolved.
-- ============================================================================
