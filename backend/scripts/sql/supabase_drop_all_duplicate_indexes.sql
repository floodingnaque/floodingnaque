-- ============================================================================
-- Floodingnaque — Drop ALL Duplicate Indexes (Dynamic)
--
-- Run in Supabase SQL Editor.
-- This queries pg_catalog to find every pair of indexes on the same table
-- with the same column set, then drops the redundant one (keeps the shorter name).
--
-- Safe: Only targets the public schema. Uses IF EXISTS.
-- Skips: primary keys, unique constraints, partition child indexes.
-- ============================================================================

-- Step 1: Preview what will be dropped (SELECT only, no changes)

-- Preview duplicates:
WITH index_details AS (
  SELECT
    n.nspname AS schema_name,
    ct.relname AS table_name,
    ci.relname AS index_name,
    i.indisunique AS is_unique,
    i.indisprimary AS is_primary,
    pg_get_indexdef(i.indexrelid) AS index_def,
    -- Normalize: extract just the column/expression list for comparison
    regexp_replace(
      pg_get_indexdef(i.indexrelid),
      '^CREATE (UNIQUE )?INDEX .+ ON .+ USING \w+ \((.+)\)( WHERE .+)?$',
      '\2'
    ) AS columns_expr,
    -- Capture the WHERE clause for partial indexes
    regexp_replace(
      pg_get_indexdef(i.indexrelid),
      '^CREATE (UNIQUE )?INDEX .+ ON .+ USING \w+ \(.+\)( WHERE (.+))?$',
      '\3'
    ) AS where_clause,
    pg_relation_size(i.indexrelid) AS index_size
  FROM pg_index i
  JOIN pg_class ci ON ci.oid = i.indexrelid
  JOIN pg_class ct ON ct.oid = i.indrelid
  JOIN pg_namespace n ON n.oid = ct.relnamespace
  WHERE n.nspname = 'public'
    AND NOT i.indisprimary                       -- Never touch primary keys
    AND ct.relkind IN ('r', 'p')                 -- Regular + partitioned parent tables only
    AND NOT EXISTS (                              -- Skip partition child indexes
      SELECT 1 FROM pg_inherits inh
      WHERE inh.inhrelid = ct.oid
    )
),
duplicates AS (
  SELECT
    a.table_name,
    a.index_name AS keep_index,
    b.index_name AS drop_index,
    a.columns_expr,
    a.where_clause,
    a.is_unique AS keep_is_unique,
    b.is_unique AS drop_is_unique,
    pg_size_pretty(b.index_size) AS wasted_size
  FROM index_details a
  JOIN index_details b
    ON a.table_name = b.table_name
    AND a.columns_expr = b.columns_expr
    AND a.where_clause = b.where_clause
    AND a.index_name < b.index_name  -- Deterministic: keep alphabetically first
    AND a.is_unique = b.is_unique    -- Only compare like-with-like
)
SELECT table_name, keep_index, drop_index, columns_expr, wasted_size
FROM duplicates
ORDER BY table_name, keep_index;


-- ============================================================================
-- Step 2: Actually drop all duplicates
-- This DO block drops every redundant index found above.
-- ============================================================================

DO $$
DECLARE
  rec RECORD;
  drop_count INTEGER := 0;
BEGIN
  FOR rec IN
    WITH index_details AS (
      SELECT
        n.nspname AS schema_name,
        ct.relname AS table_name,
        ci.relname AS index_name,
        i.indisunique AS is_unique,
        i.indisprimary AS is_primary,
        regexp_replace(
          pg_get_indexdef(i.indexrelid),
          '^CREATE (UNIQUE )?INDEX .+ ON .+ USING \w+ \((.+)\)( WHERE .+)?$',
          '\2'
        ) AS columns_expr,
        regexp_replace(
          pg_get_indexdef(i.indexrelid),
          '^CREATE (UNIQUE )?INDEX .+ ON .+ USING \w+ \(.+\)( WHERE (.+))?$',
          '\3'
        ) AS where_clause,
        pg_relation_size(i.indexrelid) AS index_size
      FROM pg_index i
      JOIN pg_class ci ON ci.oid = i.indexrelid
      JOIN pg_class ct ON ct.oid = i.indrelid
      JOIN pg_namespace n ON n.oid = ct.relnamespace
      WHERE n.nspname = 'public'
        AND NOT i.indisprimary
        AND ct.relkind IN ('r', 'p')
        AND NOT EXISTS (
          SELECT 1 FROM pg_inherits inh WHERE inh.inhrelid = ct.oid
        )
    ),
    duplicates AS (
      SELECT
        a.index_name AS keep_index,
        b.index_name AS drop_index,
        a.table_name
      FROM index_details a
      JOIN index_details b
        ON a.table_name = b.table_name
        AND a.columns_expr = b.columns_expr
        AND a.where_clause = b.where_clause
        AND a.index_name < b.index_name
        AND a.is_unique = b.is_unique
    )
    SELECT DISTINCT drop_index, table_name, keep_index FROM duplicates
    ORDER BY table_name, drop_index
  LOOP
    BEGIN
      RAISE NOTICE 'Dropping %.% (duplicate of %)', rec.table_name, rec.drop_index, rec.keep_index;
      EXECUTE format('DROP INDEX IF EXISTS public.%I', rec.drop_index);
      drop_count := drop_count + 1;
    EXCEPTION WHEN dependent_objects_still_exist THEN
      RAISE NOTICE 'Skipped %.% — has dependent partition indexes', rec.table_name, rec.drop_index;
    END;
  END LOOP;

  RAISE NOTICE '✅ Dropped % duplicate indexes', drop_count;
END $$;


-- ============================================================================
-- Step 3: Also drop indexes that are strict PREFIXES of a composite index
-- e.g. idx(col_a) is redundant when idx(col_a, col_b) exists
-- (The composite index serves single-column lookups via leftmost prefix)
-- ============================================================================

DO $$
DECLARE
  rec RECORD;
  drop_count INTEGER := 0;
BEGIN
  FOR rec IN
    WITH index_cols AS (
      SELECT
        ct.relname AS table_name,
        ci.relname AS index_name,
        i.indisunique AS is_unique,
        i.indisprimary AS is_primary,
        i.indkey::int[] AS col_nums,
        array_length(i.indkey, 1) AS num_cols,
        pg_get_indexdef(i.indexrelid) AS index_def
      FROM pg_index i
      JOIN pg_class ci ON ci.oid = i.indexrelid
      JOIN pg_class ct ON ct.oid = i.indrelid
      JOIN pg_namespace n ON n.oid = ct.relnamespace
      WHERE n.nspname = 'public'
        AND NOT i.indisprimary
        AND ct.relkind IN ('r', 'p')
        AND NOT EXISTS (
          SELECT 1 FROM pg_inherits inh WHERE inh.inhrelid = ct.oid
        )
        AND i.indexprs IS NULL      -- Only simple column indexes
        AND i.indpred IS NULL        -- Only non-partial indexes
    ),
    prefix_redundant AS (
      SELECT
        narrow.table_name,
        narrow.index_name AS drop_index,
        wide.index_name AS keep_index,
        narrow.num_cols AS narrow_cols,
        wide.num_cols AS wide_cols
      FROM index_cols narrow
      JOIN index_cols wide
        ON narrow.table_name = wide.table_name
        AND narrow.index_name != wide.index_name
        AND wide.num_cols > narrow.num_cols
        AND narrow.col_nums = wide.col_nums[1:narrow.num_cols]  -- prefix match
        AND NOT narrow.is_unique   -- Don't drop unique constraint indexes
        AND NOT wide.is_unique     -- Only if the wider one is also non-unique
    )
    SELECT DISTINCT drop_index, table_name, keep_index, narrow_cols, wide_cols
    FROM prefix_redundant
    ORDER BY table_name, drop_index
  LOOP
    BEGIN
      RAISE NOTICE 'Dropping %.% (%-col prefix of %-col %)',
        rec.table_name, rec.drop_index, rec.narrow_cols, rec.wide_cols, rec.keep_index;
      EXECUTE format('DROP INDEX IF EXISTS public.%I', rec.drop_index);
      drop_count := drop_count + 1;
    EXCEPTION WHEN dependent_objects_still_exist THEN
      RAISE NOTICE 'Skipped %.% — has dependent partition indexes', rec.table_name, rec.drop_index;
    END;
  END LOOP;

  RAISE NOTICE '✅ Dropped % prefix-redundant indexes', drop_count;
END $$;


-- ============================================================================
-- Step 4: Verify — show remaining index count per table
-- ============================================================================
SELECT
  ct.relname AS table_name,
  count(*) AS index_count
FROM pg_index i
JOIN pg_class ci ON ci.oid = i.indexrelid
JOIN pg_class ct ON ct.oid = i.indrelid
JOIN pg_namespace n ON n.oid = ct.relnamespace
WHERE n.nspname = 'public'
GROUP BY ct.relname
ORDER BY index_count DESC;
