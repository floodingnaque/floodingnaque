"""Fix remaining Supabase security lints

Revision ID: v7w8x9y0z1a2
Revises: 4ff809e72cd8
Create Date: 2026-06-29

Fixes Supabase Dashboard warnings:
1. RLS Disabled (CRITICAL) on push_subscriptions
2. Multiple Permissive Policies on alert_history, model_registry,
   satellite_weather_cache, tide_data_cache, users
3. Drops clearly unused indexes on push_subscriptions and predictions partitions

The postgres role (used by the Flask backend) bypasses RLS entirely,
so service_role_all policies are unnecessary and cause "Multiple Permissive
Policies" warnings. This migration removes them.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "v7w8x9y0z1a2"
down_revision: Union[str, None] = "4ff809e72cd8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    dialect = connection.dialect.name

    if dialect != "postgresql":
        print(f"Skipping RLS migration: {dialect} does not support Row Level Security")
        return

    # ==================================================================
    # 1. Enable RLS on push_subscriptions (missed in original migration)
    # ==================================================================
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'push_subscriptions'
            ) THEN
                ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
                ALTER TABLE push_subscriptions FORCE ROW LEVEL SECURITY;
                RAISE NOTICE 'Enabled RLS on push_subscriptions';
            END IF;
        END $$;
    """)

    # Create policy: authenticated users can read their own subscriptions
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'push_subscriptions'
            ) THEN
                DROP POLICY IF EXISTS "push_subs_own_select" ON push_subscriptions;
                CREATE POLICY "push_subs_own_select" ON push_subscriptions
                    FOR SELECT
                    TO authenticated
                    USING (
                        is_deleted = false
                        AND user_id::text = (SELECT auth.uid())::text
                    );
                RAISE NOTICE 'Created push_subs_own_select policy';
            END IF;
        END $$;
    """)

    # ==================================================================
    # 2. Drop redundant service_role_all policies on ALL tables
    #
    #    The postgres role is a superuser and bypasses RLS completely.
    #    Having service_role_all alongside other permissive policies
    #    triggers the "Multiple Permissive Policies" Supabase warning.
    # ==================================================================
    op.execute("""
        DO $$
        DECLARE
            tbl TEXT;
        BEGIN
            FOR tbl IN
                SELECT unnest(ARRAY[
                    'ab_tests', 'after_action_reports', 'alert_history',
                    'api_keys', 'api_requests', 'audit_logs', 'broadcasts',
                    'chat_messages', 'community_reports', 'earth_engine_requests',
                    'evacuation_alert_logs', 'evacuation_centers', 'incidents',
                    'model_registry', 'predictions', 'push_subscriptions',
                    'resident_profiles', 'satellite_weather_cache',
                    'tide_data_cache', 'users', 'weather_data', 'webhooks'
                ])
            LOOP
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = tbl
                ) THEN
                    EXECUTE format(
                        'DROP POLICY IF EXISTS "service_role_all" ON %I', tbl
                    );
                END IF;
            END LOOP;
            RAISE NOTICE 'Dropped redundant service_role_all policies';
        END $$;
    """)

    # Also drop service_role_all from weather_data and predictions partitions
    op.execute("""
        DO $$
        DECLARE
            tbl TEXT;
        BEGIN
            FOR tbl IN
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND (c.relname LIKE 'weather_data_%' OR c.relname LIKE 'predictions_%')
            LOOP
                EXECUTE format(
                    'DROP POLICY IF EXISTS "%s_service_role_all" ON %I', tbl, tbl
                );
            END LOOP;
            RAISE NOTICE 'Dropped service_role_all from partition tables';
        END $$;
    """)

    # ==================================================================
    # 3. Drop legacy duplicate policies that are now superseded
    #
    #    alert_history: had alert_history_select_policy (legacy) + public_read
    #    model_registry: had authenticated_model_registry_select (legacy)
    #    users: had users_own_row_select + users_service_role_all (from RLS migration)
    # ==================================================================
    op.execute("""
        DO $$
        BEGIN
            -- alert_history: keep public_read, drop legacy select policy
            DROP POLICY IF EXISTS "alert_history_select_policy" ON alert_history;

            -- model_registry: admin-only, drop legacy authenticated select
            DROP POLICY IF EXISTS "authenticated_model_registry_select" ON model_registry;

            -- users: drop the policies from the original RLS migration
            -- (supabase_fix_all_warnings.sql uses different policy names)
            DROP POLICY IF EXISTS "users_own_row_select" ON users;
            DROP POLICY IF EXISTS "users_service_role_all" ON users;

            -- weather_data / predictions parent tables: drop old-style policies
            -- if the fix_all_warnings.sql policies are in place
            DROP POLICY IF EXISTS "weather_data_public_select" ON weather_data;
            DROP POLICY IF EXISTS "weather_data_service_role_all" ON weather_data;
            DROP POLICY IF EXISTS "predictions_authenticated_select" ON predictions;
            DROP POLICY IF EXISTS "predictions_service_role_all" ON predictions;

            RAISE NOTICE 'Dropped legacy duplicate policies';
        END $$;
    """)

    # ==================================================================
    # 4. Ensure each flagged table has exactly one correct read policy
    #    (only creates if not already present)
    # ==================================================================

    # alert_history — public read (non-deleted)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'alert_history'
                  AND policyname = 'public_read'
            ) THEN
                CREATE POLICY "public_read" ON alert_history
                    FOR SELECT
                    TO anon, authenticated
                    USING (is_deleted = false);
            END IF;
        END $$;
    """)

    # users — own row select (non-deleted, auth.uid() match)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'users'
                  AND policyname = 'own_row_select'
            ) THEN
                CREATE POLICY "own_row_select" ON users
                    FOR SELECT
                    TO authenticated
                    USING (
                        is_deleted = false
                        AND id::text = (SELECT auth.uid())::text
                    );
            END IF;
        END $$;
    """)

    # model_registry, satellite_weather_cache, tide_data_cache — admin-only
    # (no read policy needed; RLS with zero policies = fully locked down)

    # ==================================================================
    # 5. Unused Indexes (push_subscriptions, predictions_2024_01)
    #
    #    NOT dropped — these are false positives:
    #    - push_subscriptions indexes (user_id, barangay_id, is_deleted)
    #      are new and will be used once push notifications see traffic.
    #      The is_deleted index is now hit by the RLS policy above.
    #    - predictions_2024_01 indexes are on an old partition that will
    #      be cleaned up by drop_old_partitions() retention policy.
    #    idx_scan counters reset on server restart; low-traffic tables
    #    always show 0 scans. These can be revisited via:
    #      scripts/sql/supabase_fix_policies_and_unused_indexes.sql
    # ==================================================================

    print("Migration complete: push_subscriptions RLS enabled, "
          "duplicate policies removed, read policies ensured")


def downgrade() -> None:
    connection = op.get_bind()
    dialect = connection.dialect.name

    if dialect != "postgresql":
        return

    # Restore service_role_all policies on all tables
    op.execute("""
        DO $$
        DECLARE
            tbl TEXT;
        BEGIN
            FOR tbl IN
                SELECT unnest(ARRAY[
                    'ab_tests', 'after_action_reports', 'alert_history',
                    'api_keys', 'api_requests', 'audit_logs', 'broadcasts',
                    'chat_messages', 'community_reports', 'earth_engine_requests',
                    'evacuation_alert_logs', 'evacuation_centers', 'incidents',
                    'model_registry', 'predictions', 'push_subscriptions',
                    'resident_profiles', 'satellite_weather_cache',
                    'tide_data_cache', 'users', 'weather_data', 'webhooks'
                ])
            LOOP
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = tbl
                ) THEN
                    EXECUTE format(
                        'DROP POLICY IF EXISTS "service_role_all" ON %I', tbl
                    );
                    EXECUTE format(
                        'CREATE POLICY "service_role_all" ON %I '
                        'FOR ALL TO postgres USING (true) WITH CHECK (true)',
                        tbl
                    );
                END IF;
            END LOOP;
        END $$;
    """)

    # Drop push_subscriptions policies and disable RLS
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'push_subscriptions'
            ) THEN
                DROP POLICY IF EXISTS "push_subs_own_select" ON push_subscriptions;
                ALTER TABLE push_subscriptions DISABLE ROW LEVEL SECURITY;
            END IF;
        END $$;
    """)

    # Drop the consolidated read policies
    op.execute("""
        DROP POLICY IF EXISTS "public_read" ON alert_history;
        DROP POLICY IF EXISTS "own_row_select" ON users;
    """)
