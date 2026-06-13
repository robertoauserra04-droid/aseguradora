// Detección de tipo de seguro y datos del cliente sin llamar a OpenAI

const SEGUROS_KEYWORDS = {
  vida: ['vida', 'seguro de vida', 'fallecimiento', 'muerte', 'beneficiario', 'ahorro', 'plan de ahorro'],
  medical: [
    'médico', 'medico', 'salud', 'gastos médicos', 'gastos medicos',
    'hospital', 'hospitalización', 'hospitalizacion', 'enfermedad',
    'consulta médica', 'doctor', 'seguro de salud', 'gmm',
  ],
  auto: [
    'auto', 'carro', 'coche', 'vehículo', 'vehiculo', 'automóvil', 'automovil',
    'flota', 'camioneta', 'pickup', 'moto', 'motocicleta', 'seguro de auto',
  ],
  daño: [
    'daño', 'daños', 'dano', 'casa', 'hogar', 'negocio', 'empresa',
    'propiedad', 'incendio', 'robo', 'responsabilidad civil',
  ],
  viaje: ['viaje', 'viajar', 'viajero', 'turista', 'vuelo', 'vacaciones', 'continental assist'],
  mascotas: ['mascota', 'perro', 'gato', 'veterinario', 'animal'],
};

function detectarTipoSeguro(texto) {
  if (!texto) return null;
  const lower = texto.toLowerCase();
  for (const [tipo, keywords] of Object.entries(SEGUROS_KEYWORDS)) {
    if (keywords.some(kw => lower.includes(kw))) return tipo;
  }
  return null;
}

// Detecta si el cliente quiere hablar con un humano
function quiereAsesorHumano(texto) {
  if (!texto) return false;
  const lower = texto.toLowerCase();
  const triggers = [
    'hablar con', 'hablar a', 'comunicar con', 'asesor', 'agente',
    'persona', 'humano', 'representante', 'ejecutivo', 'llamar',
  ];
  return triggers.some(t => lower.includes(t));
}

module.exports = { detectarTipoSeguro, quiereAsesorHumano };
