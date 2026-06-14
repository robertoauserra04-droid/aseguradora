from datetime import datetime, timedelta
from app.config.database import query

CONVERSACIONES_PRUEBA = [
    {"nombre": "Carlos Méndez Ruiz",      "telefono": "+528112345601", "tipo": "vida",    "estado": "inicio",              "prioridad": "normal",   "requiere": False,
     "mensajes": [{"autor": "cliente", "contenido": "Hola, quiero información sobre seguros de vida", "horas": 5}]},
    {"nombre": "María González López",    "telefono": "+528112345602", "tipo": "medical",  "estado": "inicio",              "prioridad": "alta",     "requiere": False,
     "mensajes": [
         {"autor": "cliente", "contenido": "Buenos días, me interesa un seguro de gastos médicos para mi familia", "horas": 10},
         {"autor": "agente",  "contenido": "¡Hola María! Con gusto te ayudo. ¿Cuántas personas incluiría la póliza?", "horas": 9},
         {"autor": "cliente", "contenido": "Somos 4: mi esposo, yo y 2 hijos de 8 y 12 años", "horas": 8},
         {"autor": "agente",  "contenido": "Perfecto, ¿tienen alguna condición preexistente?", "horas": 7},
         {"autor": "cliente", "contenido": "No ninguna, estamos todos sanos", "horas": 6},
     ]},
    {"nombre": "Roberto Salinas",         "telefono": "+528112345603", "tipo": "auto",     "estado": "cotizacion",          "prioridad": "normal",   "requiere": False,
     "mensajes": [
         {"autor": "cliente", "contenido": "Necesito asegurar mi carro, es un Nissan Versa 2022", "horas": 24},
         {"autor": "agente",  "contenido": "Claro Roberto, ¿tiene algún siniestro previo?", "horas": 23},
         {"autor": "cliente", "contenido": "No, es mi primer seguro", "horas": 22},
         {"autor": "agente",  "contenido": "Excelente, ya estoy cotizando con GNP, Qualitas y AXA. Te mando resultados pronto", "horas": 21},
     ]},
    {"nombre": "Alejandra Torres",        "telefono": "+528112345604", "tipo": "vida",     "estado": "cotizacion",          "prioridad": "alta",     "requiere": True,
     "mensajes": [
         {"autor": "cliente", "contenido": "Me interesa un seguro de vida, tengo 35 años", "horas": 48},
         {"autor": "agente",  "contenido": "Hola Alejandra, tengo una excelente propuesta para ti", "horas": 36},
         {"autor": "cliente", "contenido": "¿Cuánto tiempo tengo para decidir?", "horas": 3},
     ]},
    {"nombre": "Fernando Ibarra Castillo","telefono": "+528112345605", "tipo": "auto",     "estado": "tramite_oficina",     "prioridad": "critica",  "requiere": True,
     "mensajes": [
         {"autor": "cliente", "contenido": "Ya revisé las cotizaciones, me convence la de Qualitas", "horas": 72},
         {"autor": "agente",  "contenido": "¡Perfecto Fernando! ¿Procedemos con el pago?", "horas": 71},
         {"autor": "cliente", "contenido": "Ok ya los tengo, ¿a dónde los mando?", "horas": 2},
     ]},
    {"nombre": "Lucía Ramírez Vega",      "telefono": "+528112345606", "tipo": "medical",  "estado": "entrega",             "prioridad": "alta",     "requiere": False,
     "mensajes": [
         {"autor": "cliente", "contenido": "Ya firmé los documentos que me mandaron", "horas": 96},
         {"autor": "agente",  "contenido": "Perfecto Lucía, ya los recibimos. Solo falta el pago de la primera prima", "horas": 94},
     ]},
    {"nombre": "Jorge Pérez Hernández",   "telefono": "+528112345607", "tipo": "vida",     "estado": "vigente",             "prioridad": "baja",     "requiere": False,
     "mensajes": [
         {"autor": "sistema", "contenido": "Póliza emitida exitosamente. Vigencia del 15/01/2026 al 15/01/2027", "horas": 120},
     ]},
    {"nombre": "Carmen Ortiz Morales",    "telefono": "+528112345608", "tipo": "viaje",    "estado": "inicio",              "prioridad": "normal",   "requiere": False,
     "mensajes": [
         {"autor": "cliente", "contenido": "Hola, voy a viajar a Europa en julio, ¿tienen seguro de viaje?", "horas": 2},
     ]},
    {"nombre": "Miguel Ángel Fuentes",    "telefono": "+528112345609", "tipo": "auto",     "estado": "servicio",            "prioridad": "alta",     "requiere": True,
     "mensajes": [
         {"autor": "cliente", "contenido": "Necesito reportar un siniestro, choqué ayer", "horas": 1},
         {"autor": "agente",  "contenido": "Miguel, ¿hubo lesionados? ¿Cuál es la ubicación del vehículo?", "horas": 1},
     ]},
    {"nombre": "Isabel Contreras",        "telefono": "+528112345610", "tipo": "medical",  "estado": "renovacion",          "prioridad": "alta",     "requiere": False,
     "mensajes": [
         {"autor": "sistema", "contenido": "Tu póliza vence en 25 días. Contáctanos para renovarla", "horas": 48},
         {"autor": "cliente", "contenido": "Sí quiero renovar, ¿el precio sube?", "horas": 47},
     ]},
]


def _insertar_datos() -> None:
    for c in CONVERSACIONES_PRUEBA:
        ahora = datetime.utcnow()
        ultimo_msg = ahora - timedelta(hours=c["mensajes"][-1]["horas"]) if c["mensajes"] else ahora

        r = query(
            """INSERT INTO conversaciones
                 (cliente_nombre, cliente_telefono, cliente_whatsapp_id, tipo_seguro, estado,
                  prioridad, requiere_respuesta, activo, created_at, updated_at, ultimo_mensaje_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, true, NOW(), NOW(), %s)
               RETURNING id""",
            [c["nombre"], c["telefono"], c["telefono"], c["tipo"], c["estado"],
             c["prioridad"], c["requiere"], ultimo_msg],
        )
        conv_id = str(r.rows[0]["id"])

        for msg in c["mensajes"]:
            ts = ahora - timedelta(hours=msg["horas"])
            query(
                """INSERT INTO mensajes
                     (conversacion_id, autor, nombre_autor, contenido, tipo_mensaje, timestamp_mensaje)
                   VALUES (%s, %s, %s, %s, 'text', %s)""",
                [conv_id, msg["autor"], msg["autor"].capitalize(), msg["contenido"], ts],
            )


def limpiar_datos() -> None:
    # Solo borra datos de las conversaciones de PRUEBA (teléfonos +52811234560x),
    # nunca de clientes reales. El ON DELETE CASCADE del schema limpia las tablas
    # hijas (mensajes, notas, cotizaciones, historial) al borrar la conversación.
    query("DELETE FROM conversaciones WHERE cliente_telefono LIKE '+52811234560%'")
    # Clientes de prueba (sus pólizas caen por ON DELETE CASCADE)
    query("DELETE FROM clientes WHERE telefono LIKE '+52811234570%'")


# Clientes demo con varias pólizas cada uno (teléfonos +52811234570x = datos de prueba)
CLIENTES_PRUEBA = [
    {"nombre": "Patricia Guzmán Salas", "telefono": "+528112345701", "email": "patricia@example.com", "rfc": "GUSP850312AB1",
     "polizas": [
         {"ramo": "auto",    "aseguradora": "Qualitas", "numero": "AUT-10231", "prima": 12500, "comision_pct": 12, "venc_dias": 20},
         {"ramo": "vida",    "aseguradora": "Metlife",  "numero": "VID-55012", "prima": 8400,  "comision_pct": 25, "venc_dias": 200},
     ]},
    {"nombre": "Eduardo Lozano Pérez", "telefono": "+528112345702", "email": "eduardo@example.com", "rfc": "LOPE900720CD2",
     "polizas": [
         {"ramo": "medical", "aseguradora": "GNP",      "numero": "GMM-77820", "prima": 32000, "comision_pct": 15, "venc_dias": 45},
         {"ramo": "auto",    "aseguradora": "AXA",       "numero": "AUT-22198", "prima": 15800, "comision_pct": 12, "venc_dias": 90},
     ]},
    {"nombre": "Sofía Márquez Ríos", "telefono": "+528112345703", "email": "sofia@example.com", "rfc": "MARS880101EF3",
     "polizas": [
         {"ramo": "daño",    "aseguradora": "Seguros Monterrey", "numero": "DAN-30441", "prima": 21000, "comision_pct": 18, "venc_dias": 12},
     ]},
]


def _insertar_clientes() -> None:
    from datetime import date, timedelta
    hoy = date.today()
    for c in CLIENTES_PRUEBA:
        r = query(
            """INSERT INTO clientes (nombre, telefono, email, rfc)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (telefono) DO NOTHING
               RETURNING id""",
            [c["nombre"], c["telefono"], c["email"], c["rfc"]],
        )
        if not r.rows:
            continue
        cliente_id = str(r.rows[0]["id"])
        for p in c["polizas"]:
            venc = hoy + timedelta(days=p["venc_dias"])
            inicio = venc - timedelta(days=365)
            comision = round(p["prima"] * p["comision_pct"] / 100, 2)
            query(
                """INSERT INTO polizas
                     (cliente_id, numero_poliza, ramo, aseguradora, estado,
                      fecha_inicio, fecha_vencimiento, prima, comision_pct, comision_monto)
                   VALUES (%s, %s, %s, %s, 'vigente', %s, %s, %s, %s, %s)""",
                [cliente_id, p["numero"], p["ramo"], p["aseguradora"],
                 inicio, venc, p["prima"], p["comision_pct"], comision],
            )


def run_seed() -> None:
    r = query("SELECT COUNT(*) as cnt FROM conversaciones")
    if int(r.rows[0]["cnt"]) == 0:
        try:
            _insertar_datos()
            _insertar_clientes()
            print(f"[Seed] {len(CONVERSACIONES_PRUEBA)} conversaciones y {len(CLIENTES_PRUEBA)} clientes insertados")
        except Exception as e:
            print(f"[Seed] Error al insertar datos: {e}")


def run_seed_force() -> None:
    limpiar_datos()
    _insertar_datos()
    _insertar_clientes()
    print(f"[Seed] {len(CONVERSACIONES_PRUEBA)} conversaciones y {len(CLIENTES_PRUEBA)} clientes recargados")
