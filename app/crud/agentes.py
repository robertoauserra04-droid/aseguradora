import bcrypt
from app.config.database import query


def listar() -> list:
    r = query(
        """SELECT id, nombre, email, telefono_interno, rol, activo,
                  conversaciones_asignadas, conversaciones_cerradas, tasa_cierre, created_at
           FROM agentes
           WHERE email != 'sistema@carguill.com'
           ORDER BY created_at DESC"""
    )
    return r.rows


def crear(nombre: str, email: str, password: str,
          telefono_interno: str = None, rol: str = "vendedor") -> dict:
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    r = query(
        """INSERT INTO agentes (nombre, email, contrasena, telefono_interno, rol, activo)
           VALUES (%s, %s, %s, %s, %s, true)
           RETURNING id, nombre, email, telefono_interno, rol, activo, created_at""",
        [nombre, email.lower(), password_hash, telefono_interno, rol],
    )
    return r.rows[0]


def actualizar(agente_id: str, datos: dict) -> dict | None:
    nombre = datos.get("nombre")
    email = datos.get("email")
    telefono_interno = datos.get("telefono_interno")
    rol = datos.get("rol")
    r = query(
        """UPDATE agentes
           SET nombre = COALESCE(%s, nombre),
               email  = COALESCE(%s, email),
               telefono_interno = COALESCE(%s, telefono_interno),
               rol    = COALESCE(%s, rol)
           WHERE id = %s AND email != 'sistema@carguill.com'
           RETURNING id, nombre, email, telefono_interno, rol, activo""",
        [nombre, email.lower() if email else None, telefono_interno, rol, agente_id],
    )
    return r.rows[0] if r.rows else None


def cambiar_password(agente_id: str, nueva_password: str) -> bool:
    password_hash = bcrypt.hashpw(nueva_password.encode(), bcrypt.gensalt()).decode()
    r = query(
        "UPDATE agentes SET contrasena = %s WHERE id = %s RETURNING id",
        [password_hash, agente_id],
    )
    return len(r.rows) > 0


def desactivar(agente_id: str) -> bool:
    r = query(
        "UPDATE agentes SET activo = false WHERE id = %s AND email != 'sistema@carguill.com' RETURNING id",
        [agente_id],
    )
    return len(r.rows) > 0


def buscar_por_email(email: str) -> dict | None:
    r = query(
        "SELECT id, nombre, email, rol, contrasena, activo FROM agentes WHERE email = %s",
        [email.lower()],
    )
    return r.rows[0] if r.rows else None
