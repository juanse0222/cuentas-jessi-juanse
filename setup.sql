-- ============================================================
-- Cuentas Jessi & Juanse — Esquema de base de datos Supabase
-- Ejecuta este script en: Supabase → SQL Editor → New Query
-- ============================================================

-- Tabla principal de transacciones
CREATE TABLE IF NOT EXISTS transacciones (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    fecha       DATE        NOT NULL DEFAULT CURRENT_DATE,
    mes_presupuestal DATE   NOT NULL DEFAULT CURRENT_DATE,
    persona     TEXT        NOT NULL CHECK (persona IN ('Jessi', 'Juanse', 'Ambos')),
    tipo        TEXT        NOT NULL CHECK (tipo IN ('gasto', 'ingreso')),
    categoria   TEXT        NOT NULL,
    subcategoria TEXT       NOT NULL,
    descripcion TEXT        DEFAULT '',
    monto       NUMERIC(14, 0) NOT NULL CHECK (monto > 0),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Por si la tabla ya existía sin esta columna (caso de este proyecto)
ALTER TABLE transacciones ADD COLUMN IF NOT EXISTS mes_presupuestal DATE NOT NULL DEFAULT CURRENT_DATE;

-- Índices para consultas rápidas por mes
CREATE INDEX IF NOT EXISTS idx_trans_fecha ON transacciones(fecha);
CREATE INDEX IF NOT EXISTS idx_trans_tipo  ON transacciones(tipo);
CREATE INDEX IF NOT EXISTS idx_trans_mes   ON transacciones(mes_presupuestal);

-- Row Level Security: permitir acceso con la clave anon de la app
ALTER TABLE transacciones ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "acceso_app" ON transacciones;
CREATE POLICY "acceso_app" ON transacciones
    FOR ALL USING (true);

-- Tabla de lista de gastos / compras planificadas (pestaña "🛒 Lista")
CREATE TABLE IF NOT EXISTS items_lista (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    mes_presupuestal DATE   NOT NULL DEFAULT CURRENT_DATE,
    nombre      TEXT        NOT NULL,
    categoria   TEXT        NOT NULL,
    subcategoria TEXT       NOT NULL,
    precio      NUMERIC(14, 0) NOT NULL DEFAULT 0,
    cantidad    INTEGER     NOT NULL DEFAULT 1,
    pagado      BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_items_mes ON items_lista(mes_presupuestal);

ALTER TABLE items_lista ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "acceso_app" ON items_lista;
CREATE POLICY "acceso_app" ON items_lista
    FOR ALL USING (true);

-- Historial de importaciones (pestaña "🗂️ Historial Importaciones")
CREATE TABLE IF NOT EXISTS importaciones_log (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    fecha_hora    TIMESTAMPTZ DEFAULT NOW(),
    realizado_por TEXT        NOT NULL,
    fuente        TEXT        NOT NULL,
    reconocidos   INTEGER     NOT NULL DEFAULT 0,
    omitidos      INTEGER     NOT NULL DEFAULT 0,
    detalle       TEXT        DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_importaciones_fecha ON importaciones_log(fecha_hora);

ALTER TABLE importaciones_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "acceso_app" ON importaciones_log;
CREATE POLICY "acceso_app" ON importaciones_log
    FOR ALL USING (true);
