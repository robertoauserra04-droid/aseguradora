const fs = require('fs');
const path = require('path');
const db = require('../config/database');

async function runMigrations() {
  try {
    const schemaPath = path.join(__dirname, 'schema.sql');
    const sql = fs.readFileSync(schemaPath, 'utf8');
    await db.query(sql);
    console.log('[DB] Tablas verificadas/creadas correctamente');
  } catch (err) {
    console.error('[DB] Error ejecutando migraciones:', err);
    throw err;
  }
}

module.exports = { runMigrations };
