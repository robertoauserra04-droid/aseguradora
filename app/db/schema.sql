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
  -- Sin UNIQUE: un mismo cliente puede tener varias conversaciones (casos), p.ej. un caso
  -- cerrado en el historial + uno nuevo abierto al volver a escribir.
  cliente_telefono VARCHAR(20) NOT NULL,
  cliente_whatsapp_id VARCHAR(50) NOT NULL,
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
  ultimo_mensaje_at TIMESTAMP,
  closed_at TIMESTAMP -- NULL = abierta; al cerrar el caso se congela aquí
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
  activo_global BOOLEAN DEFAULT false,
  contexto JSONB DEFAULT '{}',
  updated_at TIMESTAMP DEFAULT NOW()
);
ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS contexto JSONB DEFAULT '{}';
INSERT INTO bot_config (id, instrucciones, activo_global)
VALUES (1, '', false)
ON CONFLICT (id) DO NOTHING;
-- Limpiar filas duplicadas que se hayan creado (dejar solo id=1)
DELETE FROM bot_config WHERE id <> 1;

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

-- bot_activo por conversación: true por defecto (el global activo_global es el control maestro)
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS bot_activo BOOLEAN DEFAULT true;

-- Contraseña para login de agentes (bcrypt hash)
ALTER TABLE agentes ADD COLUMN IF NOT EXISTS contrasena TEXT;

-- =============================================
-- TABLA: clientes (entidad reutilizable; 1 cliente -> N pólizas)
-- =============================================
CREATE TABLE IF NOT EXISTS clientes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre VARCHAR(255) NOT NULL DEFAULT 'Cliente',
  telefono VARCHAR(20) UNIQUE,
  email VARCHAR(255),
  rfc VARCHAR(13),
  fecha_nacimiento DATE,
  direccion TEXT,
  notas TEXT,
  agente_asignado UUID REFERENCES agentes(id),
  activo BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes(telefono);

-- =============================================
-- TABLA: polizas
-- =============================================
CREATE TABLE IF NOT EXISTS polizas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  conversacion_id UUID REFERENCES conversaciones(id) ON DELETE SET NULL, -- origen opcional

  numero_poliza VARCHAR(100),
  ramo VARCHAR(50) NOT NULL,            -- vida, medical, auto, daño, viaje, mascotas
  aseguradora VARCHAR(100) NOT NULL,
  estado VARCHAR(30) DEFAULT 'vigente', -- vigente, vencida, cancelada, en_tramite

  fecha_inicio DATE,
  fecha_vencimiento DATE,
  suma_asegurada DECIMAL(14, 2),
  prima DECIMAL(12, 2),
  moneda VARCHAR(10) DEFAULT 'MXN',
  forma_pago VARCHAR(20) DEFAULT 'anual', -- anual, semestral, trimestral, mensual

  -- Comisión del broker (ingreso)
  comision_pct DECIMAL(5, 2) DEFAULT 0,
  comision_monto DECIMAL(12, 2),          -- se calcula prima*pct/100 si viene null

  notas TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_polizas_cliente ON polizas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_polizas_vencimiento ON polizas(fecha_vencimiento);
CREATE INDEX IF NOT EXISTS idx_polizas_estado ON polizas(estado);

-- Enlace opcional de conversación -> cliente
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS cliente_id UUID REFERENCES clientes(id);

-- Pólizas: tipo (ramo) y aseguradora opcionales (se pueden capturar después)
ALTER TABLE polizas ALTER COLUMN ramo DROP NOT NULL;
ALTER TABLE polizas ALTER COLUMN aseguradora DROP NOT NULL;

-- Conversaciones: varios tipos de seguro por persona. tipo_seguro queda como el
-- "principal" (primer tipo) para compatibilidad con kanban/filtros/bot/calendario.
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS tipos_seguro TEXT[] DEFAULT '{}';
UPDATE conversaciones SET tipos_seguro = ARRAY[tipo_seguro]
  WHERE tipo_seguro IS NOT NULL AND (tipos_seguro IS NULL OR tipos_seguro = '{}');

-- =============================================
-- TABLA: etapas (fases del kanban, editables)
-- =============================================
CREATE TABLE IF NOT EXISTS etapas (
  key VARCHAR(50) PRIMARY KEY,
  label VARCHAR(100) NOT NULL,
  color VARCHAR(20) NOT NULL DEFAULT '#3B82F6',
  orden INT NOT NULL DEFAULT 0,
  es_cerrada BOOLEAN DEFAULT false,
  activo BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- TABLA: citas (agendadas por el bot o manual; se ven en el calendario del panel)
-- =============================================
CREATE TABLE IF NOT EXISTS citas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversacion_id UUID REFERENCES conversaciones(id) ON DELETE SET NULL,
  cliente_id UUID REFERENCES clientes(id) ON DELETE SET NULL,
  titulo VARCHAR(200),
  motivo TEXT,
  inicio TIMESTAMP NOT NULL,
  fin TIMESTAMP,
  estado VARCHAR(30) DEFAULT 'agendada',
  google_event_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_citas_inicio ON citas(inicio);

-- =============================================
-- TABLA: bot_numeros_excluidos
-- Números donde el bot NUNCA responde (ej. número personal del dueño,
-- contactos que se atienden manualmente, proveedores, etc.)
-- =============================================
CREATE TABLE IF NOT EXISTS bot_numeros_excluidos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  numero VARCHAR(20) NOT NULL UNIQUE,
  motivo VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bot_excluidos_numero ON bot_numeros_excluidos(numero);

-- =============================================
-- Cierre de conversaciones por caso (closed_at) y varias conversaciones por teléfono
-- =============================================
-- Una conversación cerrada deja de aparecer en el tablero pero sigue en la lista/historial.
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP;
-- Permitir varias conversaciones (casos) por mismo teléfono: quitar los UNIQUE heredados.
ALTER TABLE conversaciones DROP CONSTRAINT IF EXISTS conversaciones_cliente_telefono_key;
ALTER TABLE conversaciones DROP CONSTRAINT IF EXISTS conversaciones_cliente_whatsapp_id_key;
CREATE INDEX IF NOT EXISTS idx_conversaciones_closed_at ON conversaciones(closed_at);
CREATE INDEX IF NOT EXISTS idx_conversaciones_whatsapp_id ON conversaciones(cliente_whatsapp_id);

-- =============================================
-- Feature: pausa automática del bot cuando el agente responde
-- =============================================
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS bot_auto_pausado BOOLEAN DEFAULT false;
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS agente_respondio_at TIMESTAMP;

-- Feature: rastrear quién envió el último mensaje (para badges 'ya se respondió')
ALTER TABLE conversaciones ADD COLUMN IF NOT EXISTS ultimo_autor VARCHAR(20);

-- =============================================
-- Feature: notificaciones WhatsApp por cambio de fase
-- =============================================
CREATE TABLE IF NOT EXISTS notificaciones_etapa (
  etapa_key VARCHAR(50) PRIMARY KEY REFERENCES etapas(key) ON DELETE CASCADE,
  mensaje_template TEXT NOT NULL,
  activo BOOLEAN DEFAULT true
);

-- =============================================
-- Feature: Google Drive como base de conocimiento del bot
-- =============================================
ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS drive_folder_id TEXT;
ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS calendar_id TEXT;
ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS whatsapp_template_notif TEXT DEFAULT 'actualizacion_fase';

CREATE TABLE IF NOT EXISTS documentos_drive (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_id TEXT NOT NULL UNIQUE,
  nombre TEXT,
  mime_type TEXT,
  contenido_texto TEXT,
  actualizado_at TIMESTAMP DEFAULT NOW()
);
