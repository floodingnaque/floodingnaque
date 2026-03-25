-- ============================================================================
-- Floodingnaque — Fix Multiple Permissive Policies + Drop Unused Indexes
--
-- Run in Supabase SQL Editor after the RLS & duplicate index scripts.
-- ============================================================================


-- ============================================================================
-- PART 1: FIX MULTIPLE PERMISSIVE POLICIES
--
-- Problem: Tables have both "service_role_all" (FOR ALL TO postgres) AND
-- a read policy (FOR SELECT TO anon/authenticated). Supabase flags this as
-- "Multiple Permissive Policies" because two permissive policies OR together.
--
-- Fix: Drop the "service_role_all" policies entirely. The postgres role is
-- a superuser and BYPASSES RLS completely — it never needs a policy.
-- This leaves only the single read policy per table, resolving the warning.
-- ============================================================================

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
    EXECUTE format('DROP POLICY IF EXISTS "service_role_all" ON %I', tbl);
  END LOOP;

  RAISE NOTICE '✅ Removed all redundant service_role_all policies (postgres bypasses RLS)';
END $$;

-- For tables that had ONLY service_role_all and no other policy,
-- they now have RLS enabled with zero policies = fully locked down.
-- That's correct: only postgres (backend) can access them.
--
-- Tables with a remaining read policy (1 permissive each):
--   chat_messages     → authenticated_read
--   evacuation_centers → public_read_active
--   community_reports → authenticated_read
--   broadcasts        → authenticated_read
--   predictions       → public_read
--   weather_data      → public_read
--   alert_history     → public_read
--   incidents         → authenticated_read


-- ============================================================================
-- PART 2: DROP UNUSED INDEXES
--
-- Queries pg_stat_user_indexes for indexes with idx_scan = 0 (never used).
-- Only drops non-unique, non-primary, non-partition-child indexes in public.
-- Uses error handling to skip partition-dependent indexes gracefully.
--
-- NOTE: idx_scan resets on server restart. If the DB was recently restarted
-- or low-traffic, some indexes flagged as "unused" may actually be needed.
-- The script only drops indexes with ZERO scans since last stats reset.
-- ============================================================================

-- Step 1: Preview unused indexes
SELECT
  s.relname AS table_name,
  s.indexrelname AS index_name,
  s.idx_scan AS times_used,
  pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
  pg_get_indexdef(s.indexrelid) AS index_def
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
JOIN pg_class ct ON ct.oid = i.indrelid
WHERE s.schemaname = 'public'
  AND s.idx_scan = 0                              -- Never used
  AND NOT i.indisunique                            -- Keep unique constraints
  AND NOT i.indisprimary                           -- Keep primary keys
  AND NOT EXISTS (                                 -- Skip partition children
    SELECT 1 FROM pg_inherits inh WHERE inh.inhrelid = ct.oid
  )
ORDER BY pg_relation_size(s.indexrelid) DESC;


-- Step 2: Drop all unused indexes
DO $$
DECLARE
  rec RECORD;
  drop_count INTEGER := 0;
  skip_count INTEGER := 0;
  freed_bytes BIGINT := 0;
BEGIN
  FOR rec IN
    SELECT
      s.indexrelname AS index_name,
      s.relname AS table_name,
      pg_relation_size(s.indexrelid) AS index_size
    FROM pg_stat_user_indexes s
    JOIN pg_index i ON i.indexrelid = s.indexrelid
    JOIN pg_class ct ON ct.oid = i.indrelid
    WHERE s.schemaname = 'public'
      AND s.idx_scan = 0
      AND NOT i.indisunique
      AND NOT i.indisprimary
      AND NOT EXISTS (
        SELECT 1 FROM pg_inherits inh WHERE inh.inhrelid = ct.oid
      )
    ORDER BY pg_relation_size(s.indexrelid) DESC
  LOOP
    BEGIN
      EXECUTE format('DROP INDEX IF EXISTS public.%I', rec.index_name);
      drop_count := drop_count + 1;
      freed_bytes := freed_bytes + rec.index_size;
    EXCEPTION
      WHEN dependent_objects_still_exist THEN
        skip_count := skip_count + 1;
        RAISE NOTICE 'Skipped % — has dependent objects', rec.index_name;
      WHEN OTHERS THEN
        skip_count := skip_count + 1;
        RAISE NOTICE 'Skipped % — %', rec.index_name, SQLERRM;
    END;
  END LOOP;

  RAISE NOTICE '✅ Dropped % unused indexes (freed ~%), skipped %',
    drop_count, pg_size_pretty(freed_bytes), skip_count;
END $$;


-- Step 3: Verify remaining index count
SELECT
  s.relname AS table_name,
  count(*) AS total_indexes,
  count(*) FILTER (WHERE s.idx_scan = 0) AS still_unused,
  count(*) FILTER (WHERE s.idx_scan > 0) AS used
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.schemaname = 'public'
GROUP BY s.relname
ORDER BY still_unused DESC, total_indexes DESC;
