-- ============================================================================
-- Floodingnaque Community Chat — Supabase SQL Migration
--
-- Run this in the Supabase SQL Editor after the Alembic migration
-- to enable Realtime broadcasting and row-level security.
-- ============================================================================

-- 1. Enable Realtime on chat_messages
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;

-- 2. Row-Level Security
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Service role (backend) can do everything
CREATE POLICY "service_role_all" ON chat_messages
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Authenticated users can read non-deleted messages
CREATE POLICY "authenticated_read" ON chat_messages
  FOR SELECT
  TO authenticated
  USING (is_deleted = false);

-- 3. Chat channels lookup view (lightweight, avoids a separate table)
--    security_invoker = true prevents the "Security Definer View" warning
DROP VIEW IF EXISTS chat_channels;
CREATE VIEW chat_channels WITH (security_invoker = true) AS
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
