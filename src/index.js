require('dotenv').config();
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const path = require('path');

const healthRouter = require('./routes/health');
const webhookRouter = require('./routes/webhook');
const conversacionesRouter = require('./routes/conversaciones');
const dashboardRouter = require('./routes/dashboard');
const { errorHandler } = require('./middleware/errorHandler');
const { iniciarJobs } = require('./services/jobsService');
const { runMigrations } = require('./db/migrate');
const { runSeed } = require('./db/seed');
const authRouter  = require('./routes/auth');
const adminRouter = require('./routes/admin');
const botRouter   = require('./routes/bot');

const app = express();
const PORT = process.env.PORT || 3000;

// Seguridad básica
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors());

// Archivos estáticos (frontend)
app.use(express.static(path.join(__dirname, '..', 'public')));

// Body parsing para rutas de API (el webhook tiene su propio parser con rawBody)
app.use('/api', express.json());

// Rutas
app.use('/api', healthRouter);
app.use('/api', authRouter);
app.use('/api', adminRouter);
app.use('/api', conversacionesRouter);
app.use('/api', dashboardRouter);
app.use('/api', botRouter);
app.use('/', webhookRouter); // El webhook tiene su propio express.json()

// Error handler
app.use(errorHandler);

// Arrancar: primero migraciones, luego servidor
async function start() {
  await runMigrations();
  await runSeed();
  app.listen(PORT, () => {
    console.log(`Servidor Carguill corriendo en puerto ${PORT}`);
    iniciarJobs();
  });
}

start();

module.exports = app;
