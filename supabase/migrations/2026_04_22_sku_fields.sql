-- Commercial brand-level fields (scalars, useful for querying/filtering)
ALTER TABLE brands ADD COLUMN IF NOT EXISTS unit_velocity_range text;
ALTER TABLE brands ADD COLUMN IF NOT EXISTS slotting_fees_paid text;
ALTER TABLE brands ADD COLUMN IF NOT EXISTS best_seller_sku text;

-- Product catalog as JSON array (one object per SKU)
-- Schema of each object:
-- {
--   "sku_name": "string",
--   "upc": "string",
--   "case_pack": integer,
--   "cases_per_pallet": integer,
--   "net_weight": "string (e.g. '4 oz', '330 ml')",
--   "wholesale_cost": number,
--   "msrp": number,
--   "margin_pct": number,
--   "shelf_life_days": integer,
--   "storage_temp": "string (ambient|refrigerated|frozen)",
--   "launch_date": "string (YYYY-MM-DD or null)",
--   "ingredients": "string",
--   "allergens": "array of strings",
--   "is_flagship": boolean
-- }
ALTER TABLE brands ADD COLUMN IF NOT EXISTS products jsonb DEFAULT '[]'::jsonb;

-- Helpful index if we ever want to filter brands by product count or flagship SKU
CREATE INDEX IF NOT EXISTS brands_products_idx ON brands USING gin (products);
