PRAGMA foreign_keys = ON;

-- =========================
--  CATALOGUE
-- =========================

CREATE TABLE IF NOT EXISTS suppliers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS materials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS cores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS panel_formats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  width_mm INTEGER NOT NULL CHECK(width_mm > 0),
  height_mm INTEGER NOT NULL CHECK(height_mm > 0),
  label TEXT NOT NULL UNIQUE
);

-- grain_rule:
-- NONE      = pas de sens de fibre
-- OPTIONAL  = sens possible (choix V/H) selon commande/atelier
-- REQUIRED  = fibre obligatoire (V/H doit être défini)
CREATE TABLE IF NOT EXISTS colors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  material_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  grain_rule TEXT NOT NULL CHECK (grain_rule IN ('NONE','OPTIONAL','REQUIRED')),
  notes TEXT,
  UNIQUE(material_id, name),
  FOREIGN KEY(material_id) REFERENCES materials(id)
);

-- finitions: UNICOLORE / BICOLORE / etc.
-- multiplier: coefficient global, surcharge: ajout fixe (optionnel)
CREATE TABLE IF NOT EXISTS finishes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  multiplier REAL NOT NULL DEFAULT 1.0,
  surcharge REAL NOT NULL DEFAULT 0.0,
  notes TEXT
);

-- SKU = une référence panneau vendable/utilisable
-- color_back_id NULL => unicolore (ou face unique)
CREATE TABLE IF NOT EXISTS panel_skus (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier_id INTEGER NOT NULL,
  material_id INTEGER NOT NULL,
  core_id INTEGER NOT NULL,
  thickness_mm INTEGER NOT NULL CHECK(thickness_mm > 0),
  format_id INTEGER NOT NULL,
  color_front_id INTEGER NOT NULL,
  color_back_id INTEGER,
  finish_id INTEGER NOT NULL,
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  notes TEXT,
  FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
  FOREIGN KEY(material_id) REFERENCES materials(id),
  FOREIGN KEY(core_id) REFERENCES cores(id),
  FOREIGN KEY(format_id) REFERENCES panel_formats(id),
  FOREIGN KEY(color_front_id) REFERENCES colors(id),
  FOREIGN KEY(color_back_id) REFERENCES colors(id),
  FOREIGN KEY(finish_id) REFERENCES finishes(id)
);

-- Prix: PER_SHEET (par panneau) ou PER_M2 (au m²)
-- Historisation via valid_from/valid_to
CREATE TABLE IF NOT EXISTS panel_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  panel_sku_id INTEGER NOT NULL,
  pricing_mode TEXT NOT NULL CHECK (pricing_mode IN ('PER_SHEET','PER_M2')),
  price_value REAL NOT NULL CHECK(price_value >= 0),
  currency TEXT NOT NULL DEFAULT 'EUR',
  valid_from TEXT NOT NULL, -- ISO date: YYYY-MM-DD
  valid_to TEXT,            -- NULL = toujours valable
  notes TEXT,
  FOREIGN KEY(panel_sku_id) REFERENCES panel_skus(id)
);

-- Ajustements optionnels (si tu veux ajouter des règles souples)
-- Ex: +12€ si bicolore, *1.05 si finition spéciale, etc.
CREATE TABLE IF NOT EXISTS price_adjustments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier_id INTEGER,
  material_id INTEGER,
  panel_sku_id INTEGER,
  color_id INTEGER,
  finish_id INTEGER,
  condition_bicolor INTEGER, -- NULL = ignore, 0 = unicolore, 1 = bicolore
  adjust_type TEXT NOT NULL CHECK (adjust_type IN ('ADD','MULTIPLY')),
  value REAL NOT NULL,
  reason TEXT,
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
  FOREIGN KEY(material_id) REFERENCES materials(id),
  FOREIGN KEY(panel_sku_id) REFERENCES panel_skus(id),
  FOREIGN KEY(color_id) REFERENCES colors(id),
  FOREIGN KEY(finish_id) REFERENCES finishes(id)
);

-- Stock (optionnel)
CREATE TABLE IF NOT EXISTS panel_stock (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  panel_sku_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
  location TEXT,
  last_update TEXT,
  FOREIGN KEY(panel_sku_id) REFERENCES panel_skus(id)
);

-- =========================
--  COMMANDES / PIECES
-- =========================

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cde_number TEXT NOT NULL UNIQUE,
  delivery_date TEXT NOT NULL, -- YYYY-MM-DD
  customer TEXT,
  notes TEXT,
  created_at TEXT NOT NULL
);

-- grain_constraint pour chaque pièce:
-- NONE / VERTICAL / HORIZONTAL (si tu veux "INHERIT", ajoute-le plus tard)
CREATE TABLE IF NOT EXISTS order_parts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  label TEXT NOT NULL,
  qty INTEGER NOT NULL CHECK(qty > 0),
  width_mm INTEGER NOT NULL CHECK(width_mm > 0),
  height_mm INTEGER NOT NULL CHECK(height_mm > 0),
  material_id INTEGER NOT NULL,
  core_id INTEGER NOT NULL,
  thickness_mm INTEGER NOT NULL CHECK(thickness_mm > 0),
  color_front_id INTEGER NOT NULL,
  color_back_id INTEGER,
  finish_id INTEGER NOT NULL,
  grain_constraint TEXT NOT NULL CHECK (grain_constraint IN ('NONE','VERTICAL','HORIZONTAL')),
  rotation_allowed INTEGER NOT NULL DEFAULT 1 CHECK(rotation_allowed IN (0,1)),
  notes TEXT,
  FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY(material_id) REFERENCES materials(id),
  FOREIGN KEY(core_id) REFERENCES cores(id),
  FOREIGN KEY(color_front_id) REFERENCES colors(id),
  FOREIGN KEY(color_back_id) REFERENCES colors(id),
  FOREIGN KEY(finish_id) REFERENCES finishes(id)
);

-- =========================
--  PLANS / NESTING (GUILLOTINE)
-- =========================

CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  algorithm TEXT NOT NULL DEFAULT 'GUILLOTINE',
  params_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  total_efficiency REAL NOT NULL DEFAULT 0,
  panel_count INTEGER NOT NULL DEFAULT 0,
  total_cost REAL NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'EUR',
  FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- grain_direction du panneau utilisé (NONE/V/H). Pour REQUIRED, V ou H.
CREATE TABLE IF NOT EXISTS plan_sheets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id INTEGER NOT NULL,
  sheet_index INTEGER NOT NULL,
  panel_sku_id INTEGER NOT NULL,
  width_mm INTEGER NOT NULL,
  height_mm INTEGER NOT NULL,
  grain_direction TEXT NOT NULL CHECK (grain_direction IN ('NONE','VERTICAL','HORIZONTAL')),
  efficiency REAL NOT NULL DEFAULT 0,
  sheet_cost REAL NOT NULL DEFAULT 0,
  FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE,
  FOREIGN KEY(panel_sku_id) REFERENCES panel_skus(id),
  UNIQUE(plan_id, sheet_index)
);

CREATE TABLE IF NOT EXISTS plan_parts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_sheet_id INTEGER NOT NULL,
  order_part_id INTEGER NOT NULL,
  part_instance_index INTEGER NOT NULL DEFAULT 1,
  x_mm INTEGER NOT NULL,
  y_mm INTEGER NOT NULL,
  w_mm INTEGER NOT NULL,
  h_mm INTEGER NOT NULL,
  rotated INTEGER NOT NULL DEFAULT 0 CHECK(rotated IN (0,1)),
  FOREIGN KEY(plan_sheet_id) REFERENCES plan_sheets(id) ON DELETE CASCADE,
  FOREIGN KEY(order_part_id) REFERENCES order_parts(id)
);

-- Lignes de coupe (optionnel mais utile pour guillotine)
CREATE TABLE IF NOT EXISTS plan_cuts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_sheet_id INTEGER NOT NULL,
  cut_index INTEGER NOT NULL,
  orientation TEXT NOT NULL CHECK (orientation IN ('V','H')),
  position_mm INTEGER NOT NULL,
  start_mm INTEGER NOT NULL,
  end_mm INTEGER NOT NULL,
  FOREIGN KEY(plan_sheet_id) REFERENCES plan_sheets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS panel_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  panel_sku_id INTEGER NOT NULL,
  pricing_mode TEXT NOT NULL CHECK (pricing_mode IN ('PER_SHEET','PER_M2')),
  price_value REAL NOT NULL CHECK(price_value >= 0), -- BRUT
  discount_value REAL NOT NULL DEFAULT 0 CHECK(discount_value >= 0), -- REMISE (même unité que brut)
  waste_rate_pct REAL NOT NULL DEFAULT 0 CHECK(waste_rate_pct >= 0), -- TAUX DE CHUTE (%)
  coefficient REAL NOT NULL DEFAULT 1 CHECK(coefficient > 0), -- COEFF pour prix pièce
  currency TEXT NOT NULL DEFAULT 'EUR',
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  notes TEXT,
  FOREIGN KEY(panel_sku_id) REFERENCES panel_skus(id)
);

ALTER TABLE panel_prices ADD COLUMN discount_value REAL NOT NULL DEFAULT 0;
ALTER TABLE panel_prices ADD COLUMN waste_rate_pct REAL NOT NULL DEFAULT 0;
ALTER TABLE panel_prices ADD COLUMN coefficient REAL NOT NULL DEFAULT 1;

-- =========================
--  INDEXES
-- =========================

CREATE INDEX IF NOT EXISTS idx_colors_material ON colors(material_id);
CREATE INDEX IF NOT EXISTS idx_skus_active ON panel_skus(active);
CREATE INDEX IF NOT EXISTS idx_prices_sku_dates ON panel_prices(panel_sku_id, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_order_parts_order ON order_parts(order_id);
CREATE INDEX IF NOT EXISTS idx_plans_order ON plans(order_id);
CREATE INDEX IF NOT EXISTS idx_plan_sheets_plan ON plan_sheets(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_parts_sheet ON plan_parts(plan_sheet_id);