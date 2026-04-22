-- Canonical brand record. One row per brand the broker represents.
CREATE TABLE brands (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_name text NOT NULL UNIQUE,
  website_url text,
  category text,
  subcategory text,
  founded_year int,
  hq_city text,
  hq_state text,
  founder_name text,
  founder_email text,
  product_count int,
  flagship_sku text,
  wholesale_price_range text,
  retail_price_range text,
  margin_range text,
  distributor_list text[],
  current_retailers text[],
  target_retailers text[],
  certifications text[],
  brand_story text,
  key_differentiators text[],
  completeness_pct numeric DEFAULT 0,
  source_files text[],
  is_sandbox boolean DEFAULT false,
  onboarded_at timestamptz NOT NULL DEFAULT now(),
  last_verified_at timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'active'
);

-- Append-only event log. Memory layer for the Onboarding Agent.
CREATE TABLE brand_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  event_type text NOT NULL,
  field_name text,
  old_value jsonb,
  new_value jsonb,
  source text NOT NULL,
  confidence numeric,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Coordination blackboard: messages agents write to each other.
CREATE TABLE coordination_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  from_agent text NOT NULL,
  to_agent text NOT NULL,
  brand_id uuid REFERENCES brands(id) ON DELETE CASCADE,
  message_type text NOT NULL,
  payload jsonb NOT NULL,
  consumed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX brand_events_brand_id_idx ON brand_events(brand_id, created_at DESC);
CREATE INDEX coord_messages_to_agent_idx ON coordination_messages(to_agent, consumed_at);
