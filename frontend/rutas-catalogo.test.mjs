import test from 'node:test';
import assert from 'node:assert/strict';
import { DEPORTES_RESPALDO, normalizarDeportes, deportesNavegacion, nombreDeporte, urlCatalogo } from './rutas.js';

const dep = (id, orden, extra = {}) => ({
  id, orden, estado: 'on', nombre: { es: id.toUpperCase(), en: `${id}-en`, pt: `${id}-pt` }, slug: { es: id, en: id, pt: id }, ...extra,
});
const ids = lista => lista.map(d => d.id);

test('con la copia incrustada la navegación es la de hoy: Fútbol, NBA, Tenis en español en todos los idiomas', () => {
  for (const lang of ['es', 'en', 'pt']) {
    assert.deepEqual(deportesNavegacion(null, lang).map(d => [d.id, d.label, d.slug]),
      [['futbol', 'Fútbol', 'futbol'], ['nba', 'NBA', 'nba'], ['tenis', 'Tenis', 'tenis']]);
  }
  assert.deepEqual(ids(DEPORTES_RESPALDO), ['futbol', 'nba', 'tenis']);
});

test('con deportes válidos: solo los que manda el servidor, en el orden de `orden` y con nombre[idioma]', () => {
  const cat = normalizarDeportes({ contrato: 1, deportes: [dep('tenis', 3), dep('futbol', 1), dep('beisbol', 2)] });
  assert.deepEqual(ids(cat), ['futbol', 'beisbol', 'tenis']);
  assert.deepEqual(deportesNavegacion(cat, 'en').map(d => d.label), ['futbol-en', 'beisbol-en', 'tenis-en']);
  assert.ok(!ids(deportesNavegacion(cat, 'es')).includes('nba'));    // el servidor no lo manda → fuera
  const sinOrden = normalizarDeportes({ deportes: [dep('nba', undefined), dep('futbol', 1)] });
  assert.deepEqual(ids(sinOrden), ['futbol', 'nba']);               // sin `orden` va al final
});

test('el nombre cae a es cuando falta el idioma', () => {
  const cat = normalizarDeportes({ deportes: [dep('nba', 1, { nombre: { es: 'Baloncesto' } })] });
  assert.equal(nombreDeporte(cat[0], 'pt'), 'Baloncesto');
  assert.equal(deportesNavegacion(cat, 'en')[0].label, 'Baloncesto');
  assert.equal(nombreDeporte({ id: 'nba', nombre: {} }, 'en'), 'NBA');   // y a la copia incrustada si no hay ninguno
});

test('un deporte en preview no entra en la navegación pero sigue en el catálogo', () => {
  const cat = normalizarDeportes({ deportes: [dep('futbol', 1), dep('nba', 2, { estado: 'preview' }), dep('tenis', 3)] });
  assert.deepEqual(ids(cat), ['futbol', 'nba', 'tenis']);            // alcanzable por URL (fijarDeportes lo recibe)
  assert.deepEqual(ids(deportesNavegacion(cat)), ['futbol', 'tenis']);
  const solo = normalizarDeportes({ deportes: [dep('nba', 1, { estado: 'preview' })] });
  assert.deepEqual(ids(deportesNavegacion(solo)), ['nba']);          // nunca una navegación vacía
});

test('respuesta inválida o sin deportes → null: quien llama conserva lo que tiene', () => {
  for (const mala of [null, undefined, 'x', 3, {}, { contrato: 0 }, { deportes: null }, { deportes: {} }, { deportes: [] }, { deportes: [null, 1, 'a'] },
    { deportes: [{ id: 'NBA', estado: 'on', slug: { es: 'nba' } }] },
    { deportes: [{ id: 'nba', estado: 'off', slug: { es: 'nba' } }] },
    { deportes: [{ id: 'nba', estado: 'on', slug: { es: '../x' } }] },
    { deportes: [{ id: 'nba', estado: 'on' }] }])
    assert.equal(normalizarDeportes(mala), null, JSON.stringify(mala));
});

test('se descartan solo las entradas inválidas y los repetidos; un slug en/pt malo cae al es', () => {
  const cat = normalizarDeportes({ deportes: [dep('futbol', 1), { id: 'x', estado: 'on' }, dep('futbol', 2), dep('nba', 3, { slug: { es: 'nba', en: 'Bad Slug', pt: 'nba-pt' } })] });
  assert.deepEqual(ids(cat), ['futbol', 'nba']);
  assert.deepEqual(cat[1].slug, { es: 'nba', en: 'nba', pt: 'nba-pt' });
});

test('con un deporte de slug distinto, la navegación apunta a su slug por idioma', () => {
  const cat = normalizarDeportes({ deportes: [dep('nba', 1, { slug: { es: 'baloncesto', en: 'basketball', pt: 'basquete' } })] });
  assert.deepEqual(deportesNavegacion(cat, 'en').map(d => d.slug), ['basketball']);
  assert.deepEqual(deportesNavegacion(cat, 'pt').map(d => d.slug), ['basquete']);
  assert.deepEqual(deportesNavegacion(cat, 'es').map(d => d.slug), ['baloncesto']);
});

test('la URL del catálogo pide contrato 1 como cliente web y solo con idiomas conocidos', () => {
  assert.equal(urlCatalogo('pt'), '/cliente/v1/config?cliente=web&contrato=1&lang=pt');
  assert.equal(urlCatalogo('xx'), '/cliente/v1/config?cliente=web&contrato=1&lang=es');
});
