-- Schema PostgreSQL - Seguros Carguill
-- Ejecutar: psql $DATABASE_URL -f src/db/schema.sql

-- Extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================
-- TABLA: agentes
-- =============================================
CREATE TABLE IF NOT EXISTS agentes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  nombre VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  telefono_interno VARCHAR(50),

  rol VARCHAR(50) NOT NULL DEFAULT 'vendedor', -- vendedor, supervisor, admin
  activo BOOLEAN DEFAULT true,

  -- Stats
  conversaciones_asignadas INT DEFAULT 0,
  conversaciones_cerradas INT DEFAULT 0,
  tasa_cierre DECIMAL(5, 2) DEFAULT 0,

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agentes_rol ON agentes(rol);
CREATE INDEX IF NOT EXISTS idx_agentes_activo ON agentes(activo);

-- =============================================
-- TABLA: conversaciones
-- =============================================
CREATE TABLE IF NOT EXISTS conversaciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Cliente
  cliente_nombre VARCHAR(255) NOT NULL DEFAULT 'Cliente',
  cliente_telefono VARCHAR(20) NOT NULL UNIQUE,
  cliente_whatsapp_id VARCHAR(50) NOT NULL UNIQUE,
  cliente_email VARCHAR(255),

  -- Seguro
  tipo_seguro VARCHAR(50), -- vida, medical, auto, daño, viaje, null
  aseguradora_ofrecida TEXT[] DEFAULT '{}',

  -- Estado
  estado VARCHAR(50) NOT NULL DEFAULT 'prospectiva',
  estado_anterior VARCHAR(50),
  fecha_cambio_estado TIMESTAMP,
  motivo_cambio_estado TEXT,

  -- Asignación
  agente_asignado UUID REFERENCES agentes(id),
  agente_nombre VARCHAR(255),

  -- Urgencia
  requiere_respuesta BOOLEAN DEFAULT false,
  prioridad VARCHAR(20) DEFAULT 'normal', -- baja, normal, alta, critica
  dias_en_estado INT DEFAULT 0,

  -- Póliza
  numero_poliza VARCHAR(100),
  fecha_inicio_poliza DATE,
  fecha_vencimiento_poliza DATE,
  prima_poliza DECIMAL(10, 2),
  estado_poliza VARCHAR(50),

  -- Metadata
  activo BOOLEAN DEFAULT true,
  tags TEXT[] DEFAULT '{}',

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  ultimo_mensaje_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversaciones_estado ON conversaciones(estado);
CREATE INDEX IF NOT EXISTS idx_conversaciones_agente ON conversaciones(agente_asignado);
CREATE INDEX IF NOT EXISTS idx_conversaciones_telefono ON conversaciones(cliente_telefono);
CREATE INDEX IF NOT EXISTS idx_conversaciones_tipo_seguro ON conversaciones(tipo_seguro);
CREATE INDEX IF NOT EXISTS idx_conversaciones_requiere_respuesta ON conversaciones(requiere_respuesta);

-- =============================================
-- TABLA: mensajes
-- =============================================
CREATE TABLE IF NOT EXISTS mensajes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversacion_id UUID NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,

  -- Contenido
  autor VARCHAR(50), -- cliente, agente, bot, sistema
  nombre_autor VARCHAR(255),
  contenido TEXT NOT NULL,
  tipo_mensaje VARCHAR(50) DEFAULT 'text',

  -- WhatsApp
  whatsapp_message_id VARCHAR(100) UNIQUE,

  -- Metadata
  timestamp_mensaje TIMESTAMP NOT NULL,
  leido BOOLEAN DEFAULT false,

  -- Análisis automático
  palabras_clave TEXT[],
  sentimiento VARCHAR(20), -- positivo, negativo, neutro
  requiere_respuesta BOOLEAN DEFAULT false,

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion ON mensajes(conversacion_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_whatsapp_id ON mensajes(whatsapp_message_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_timestamp ON mensajes(timestamp_mensaje);

-- =============================================
-- TABLA: cambios_estado_historico
-- =============================================
CREATE TABLE IF NOT EXISTS cambios_estado_historico (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversacion_id UUID NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,

  estado_anterior VARCHAR(50),
  estado_nuevo VARCHAR(50) NOT NULL,
  realizado_por VARCHAR(50) DEFAULT 'sistema',
  nombre_quien_realizo VARCHAR(255),
  motivo TEXT,

  timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cambios_conversacion ON cambios_estado_historico(conversacion_id);

-- =============================================
-- TABLA: notas_internas
-- =============================================
CREATE TABLE IF NOT EXISTS notas_internas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversacion_id UUID NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,

  agente_id UUID REFERENCES agentes(id),
  agente_nombre VARCHAR(255),

  contenido TEXT NOT NULL,
  visible_para_agentes BOOLEAN DEFAULT true,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notas_conversacion ON notas_internas(conversacion_id);

-- =============================================
-- TABLA: cotizaciones
-- =============================================
CREATE TABLE IF NOT EXISTS cotizaciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversacion_id UUID NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,

  aseguradora VARCHAR(100) NOT NULL,
  prima DECIMAL(10, 2),
  moneda VARCHAR(10) DEFAULT 'MXN',
  cobertura TEXT,

  estado VARCHAR(50) DEFAULT 'cotizando', -- cotizando, enviada, aceptada, rechazada
  fecha_cotizacion TIMESTAMP DEFAULT NOW(),
  fecha_vencimiento TIMESTAMP,

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cotizaciones_conversacion ON cotizaciones(conversacion_id);
CREATE INDEX IF NOT EXISTS idx_cotizaciones_aseguradora ON cotizaciones(aseguradora);

-- =============================================
-- TABLA: idempotencia_webhooks
-- =============================================
CREATE TABLE IF NOT EXISTS idempotencia_webhooks (
  idempotency_key VARCHAR(100) PRIMARY KEY,
  event_type VARCHAR(100),
  processed_at TIMESTAMP DEFAULT NOW()
);

-- Limpiar registros de idempotencia viejos (más de 7 días)
CREATE INDEX IF NOT EXISTS idx_idempotencia_processed ON idempotencia_webhooks(processed_at);

-- =============================================
-- Agente por defecto (sistema)
-- =============================================
INSERT INTO agentes (nombre, email, rol)
VALUES ('Sistema', 'sistema@carguill.com', 'admin')
ON CONFLICT (email) DO NOTHING;

-- =============================================
-- TABLA: bot_config (singleton de configuración del bot)
-- =============================================
CREATE TABLE IF NOT EXISTS bot_config (
  id SERIAL PRIMARY KEY,
  instrucciones TEXT NOT NULL DEFAULT '',
  activo_global BOOLEAN DEFAULT true,
  contexto JSONB DEFAULT '{}',
  updated_at TIMESTAMP DEFAULT NOW()
);
ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS contexto JSONB DEFAULT '{}';
INSERT INTO bot_config (instrucciones, activo_global)
VALUES ('Eres el asistente virtual de Seguros Carguill. Responde en español formal y amable. Solo habla de seguros y citas. Si el cliente quiere una cita, ofrece horarios disponibles.', true)
ON CONFLICT DO NOTHING;

-- =============================================
-- TABLA: bot_faq (base de conocimiento Q&A)
-- =============================================
CREATE TABLE IF NOT EXISTS bot_faq (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pregunta TEXT NOT NULL,
  respuesta TEXT NOT NULL,
  activo BOOLEAN DEFAULT true,
  orden INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Campo bot_activo por conversación
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS bot_activo BOOLEAN DEFAULT true;
