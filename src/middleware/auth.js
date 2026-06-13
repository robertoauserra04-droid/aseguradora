const jwt = require('jsonwebtoken');

function authenticateAgent(req, res, next) {
  const authHeader = req.headers.authorization;
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Token requerido' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'carguill_secret_dev');
    req.agente = decoded;
    next();
  } catch {
    res.status(401).json({ error: 'Token inválido o expirado' });
  }
}

function requireAdmin(req, res, next) {
  if (req.agente?.rol !== 'admin') {
    return res.status(403).json({ error: 'Se requiere rol de administrador' });
  }
  next();
}

function requireSupervisor(req, res, next) {
  if (!['admin', 'supervisor'].includes(req.agente?.rol)) {
    return res.status(403).json({ error: 'Se requiere rol de supervisor o administrador' });
  }
  next();
}

module.exports = { authenticateAgent, requireAdmin, requireSupervisor };
