-- ============================================================
-- Cuentas Jessi & Juanse — Esquema de base de datos Supabase
-- Ejecuta este script en: Supabase → SQL Editor → New Query
-- ============================================================

-- Tabla principal de transacciones
CREATE TABLE IF NOT EXISTS transacciones (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    fecha       DATE        NOT NULL DEFAULT CURRENT_DATE,
    persona     TEXT        NOT NULL CHECK (persona IN ('Jessi', 'Juanse', 'Ambos')),
    tipo        TEXT        NOT NULL CHECK (tipo IN ('gasto', 'ingreso')),
    categoria   TEXT        NOT NULL,
    subcategoria TEXT       NOT NULL,
    descripcion TEXT        DEFAULT '',
    monto       NUMERIC(14, 0) NOT NULL CHECK (monto > 0),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para consultas rápidas por mes
CREATE INDEX IF NOT EXISTS idx_trans_fecha ON transacciones(fecha);
CREATE INDEX IF NOT EXISTS idx_trans_tipo  ON transacciones(tipo);

-- Row Level Security: permitir acceso con la clave anon de la app
ALTER TABLE transacciones ENABLE ROW LEVEL SECURITY;

CREATE POLICY "acceso_app" ON transacciones
    FOR ALL USING (true);
