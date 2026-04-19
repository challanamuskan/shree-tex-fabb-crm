-- =====================================================================
-- Satyam Tex Fabb CRM — Data Safety Migration
-- =====================================================================
-- Adds Row Level Security (RLS), soft-delete, and a recycle-bin view.
--
-- >>> READ THIS BEFORE APPLYING <<<
--
-- The Streamlit app currently connects to Supabase with the ANON key
-- (JWT role = 'anon') — it does NOT use Supabase Auth for per-user sign
-- in. Every save, update, image upload, and delete is an anon request.
--
-- Two RLS policy blocks are provided below:
--
--   BLOCK A — "permissive_anon" (ACTIVE by default)
--     Enables RLS but grants anon full CRUD. Matches current app
--     behavior exactly. Safe to apply today without breaking the site.
--
--   BLOCK B — "authenticated_write_only" (COMMENTED OUT)
--     The policy shape requested: authenticated users read/write,
--     anon read-only. ONLY enable this after the app migrates to
--     Supabase Auth (or switches to the service-role key on the
--     server), otherwise every write from the live site will fail
--     with 'new row violates row-level security policy'.
--
-- To tighten security later: comment out BLOCK A and uncomment BLOCK B
-- in a follow-up migration, after the auth change has shipped.
--
-- Backup policy:
--   Supabase Free/Pro projects include automatic daily backups
--   (7-day retention on Pro, point-in-time recovery on Team+).
--   Enable via Supabase Dashboard → Project Settings → Database →
--   Backups. This migration does not configure backups because that
--   is a project-level setting, not a SQL-level one.
-- =====================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Enable RLS on every user-data table
-- ─────────────────────────────────────────────────────────────────────
ALTER TABLE IF EXISTS parts             ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS categories        ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS customers         ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS payments          ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS purchase_orders   ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS sales_records     ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS purchase_records  ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS returns           ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS price_history     ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS email_log         ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS employees         ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS employee_tasks    ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS daily_reports     ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS attendance        ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS settings          ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users             ENABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────
-- 2. BLOCK A — permissive anon policies (ACTIVE)
--    Matches current app behavior. Safe to apply without breaking prod.
-- ─────────────────────────────────────────────────────────────────────
DO $$
DECLARE
  tbl text;
BEGIN
  FOR tbl IN SELECT unnest(ARRAY[
    'parts','categories','customers','payments','purchase_orders',
    'sales_records','purchase_records','returns','price_history',
    'email_log','employees','employee_tasks','daily_reports',
    'attendance','settings','users'
  ])
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'anon_full_access', tbl);
    EXECUTE format(
      'CREATE POLICY %I ON %I FOR ALL TO anon, authenticated USING (true) WITH CHECK (true)',
      'anon_full_access', tbl
    );
  END LOOP;
END $$;

-- ─────────────────────────────────────────────────────────────────────
-- 3. BLOCK B — authenticated write, anon read-only (COMMENTED OUT)
--    DO NOT uncomment until the app uses Supabase Auth or
--    a service-role key for writes. Uncommenting now breaks prod.
-- ─────────────────────────────────────────────────────────────────────
-- DO $$
-- DECLARE
--   tbl text;
-- BEGIN
--   FOR tbl IN SELECT unnest(ARRAY[
--     'parts','categories','customers','payments','purchase_orders',
--     'sales_records','purchase_records','returns','price_history',
--     'email_log','employees','employee_tasks','daily_reports',
--     'attendance','settings'
--   ])
--   LOOP
--     EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'anon_full_access',   tbl);
--     EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'anon_read',          tbl);
--     EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'authenticated_write',tbl);
--
--     EXECUTE format(
--       'CREATE POLICY %I ON %I FOR SELECT TO anon USING (true)',
--       'anon_read', tbl
--     );
--     EXECUTE format(
--       'CREATE POLICY %I ON %I FOR ALL TO authenticated USING (true) WITH CHECK (true)',
--       'authenticated_write', tbl
--     );
--   END LOOP;
-- END $$;
--
-- -- Users table: never expose to anon, even for read.
-- DROP POLICY IF EXISTS anon_full_access ON users;
-- CREATE POLICY users_authenticated_only ON users FOR ALL TO authenticated
--   USING (true) WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────────────
-- 4. Soft-delete columns
--    Nullable TIMESTAMPTZ. NULL = live row. Non-NULL = in recycle bin.
-- ─────────────────────────────────────────────────────────────────────
ALTER TABLE parts            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE customers        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE sales_records    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE purchase_records ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Indexes so "live rows only" queries stay fast.
CREATE INDEX IF NOT EXISTS parts_deleted_at_idx
  ON parts (deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS customers_deleted_at_idx
  ON customers (deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS sales_records_deleted_at_idx
  ON sales_records (deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS purchase_records_deleted_at_idx
  ON purchase_records (deleted_at) WHERE deleted_at IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────
-- 5. Recycle-bin view
--    Unified view across the four soft-delete tables. Admin page
--    reads this to show everything in the bin in one place.
-- ─────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW recycle_bin AS
  SELECT 'parts'::text            AS source_table, id::text AS id,
         part_name                 AS label,
         deleted_at,
         row_to_json(parts.*)::jsonb AS row_data
    FROM parts WHERE deleted_at IS NOT NULL
  UNION ALL
  SELECT 'customers'::text,        id::text,
         COALESCE(name, business_name, phone),
         deleted_at,
         row_to_json(customers.*)::jsonb
    FROM customers WHERE deleted_at IS NOT NULL
  UNION ALL
  SELECT 'sales_records'::text,    id::text,
         COALESCE(part_name || ' · ' || party_name, part_name, party_name),
         deleted_at,
         row_to_json(sales_records.*)::jsonb
    FROM sales_records WHERE deleted_at IS NOT NULL
  UNION ALL
  SELECT 'purchase_records'::text, id::text,
         COALESCE(part_name || ' · ' || supplier_name, part_name, supplier_name),
         deleted_at,
         row_to_json(purchase_records.*)::jsonb
    FROM purchase_records WHERE deleted_at IS NOT NULL;

COMMIT;
