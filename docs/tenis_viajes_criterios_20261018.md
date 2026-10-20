# Viajes entre torneos: criterios de investigacion

Fecha de revision: 2026-10-18. Alcance: tenis no comercial, sin modificar modelos congelados.

## Decision

Medir transiciones entre ediciones de torneos. No generar una nueva exposicion de viaje por cada partido ni por cambios de pista dentro de una misma competicion. Las distancias cortas entre torneos siguen siendo observaciones validas; distancia pequena no acredita transporte por carretera. Una transicion observada entre sedes no demuestra itinerario directo: puede haber regreso a casa u otra escala.

Conservar por separado distancia geodesica, desplazamiento horario firmado, direccion geografica, intervalo entre ultima participacion conocida y debut, altitud de destino y cambio de altitud. Mantener procedencia, precision, momento de disponibilidad y valores desconocidos. La eliminacion en individuales no acredita salida si siguen dobles u otra participacion.

## Herramientas contrastadas

- OpenRouteService estima ruta y duracion segun red/perfil. No mide el trayecto ni trafico vivido por el atleta. El servicio alojado requiere credenciales y tiene cuotas: no asumir como vigente el antiguo anuncio de 2.000 consultas diarias. La pagina oficial redirige a HeiGIT y no expuso sus cuotas en la consulta realizada. Verificar plan antes de activar llamadas. https://openrouteservice.org/plans/ y https://openrouteservice.org/restrictions/
- OSRM puede alojarse localmente, condicionado por recursos y datos. El servidor publico es una demostracion con politica y sin garantia de acceso; no es un servicio ilimitado. https://github.com/Project-OSRM/osrm-backend/wiki/Api-usage-policy
- Amadeus Flight Offers Search devuelve ofertas de itinerarios y duraciones previstas. No identifica el vuelo tomado por un jugador ni reconstruye por si solo viajes historicos. Pruebas usan datos limitados/cacheados; franquicias dependen de API/entorno y el exceso en produccion puede facturarse. No contratar ni integrar como dependencia necesaria por ahora. https://admin.developers.amadeus.com/self-service/apis-docs/guides/developer-guides/faq/ y https://github.com/amadeus4dev/developer-guides/blob/master/docs/resources/flights.md
- Arcascope/circadian implementa Forger99, Jewett99 y otros modelos con estado inicial y exposicion luminosa como entradas. Permite simulaciones condicionadas a supuestos; no determina dias exactos de recuperacion individual a partir de sedes solamente. https://github.com/Arcascope/circadian
- El consenso distingue fatiga de viaje de jet lag, reconoce variacion individual y limitaciones de evidencia. No respalda los coeficientes del score aportado. https://pmc.ncbi.nlm.nih.gov/articles/PMC8279034/ y https://bjsm.bmj.com/content/55/7/356

## Formula propuesta: no promover al modelo

La aproximacion distancia/800 + 2,5 horas es una hipotesis operacional, no una formula ATP/NBA validada por las fuentes revisadas. No representa escalas, aeropuertos elegidos, esperas, traslados ni viento. Si se explora, etiquetar tiempo hipotetico, parametrizar supuestos y comparar escenarios; no llamarlo duracion real.

El score con pesos 0,4/1,8/1,2, factor Este 1,5 y umbral critico 10 carece de calibracion presentada. El argumento km_distancia ni se utiliza. La documentacion cita 800 m pero la funcion introduce efecto para cualquier ascenso positivo; un cambio de 1.000 a 1.800 m recibe el mismo valor que uno de 0 a 800 m. La contribucion de vuelo persiste indefinidamente aunque aumente el descanso. No aplicar penalizaciones manuales a probabilidades ni interpretar este score como diagnostico.

## Contrato para la implementacion posterior

1. Completar georreferenciacion de 27 recintos y registrar elevaciones solo de puntos aceptados. La cobertura confirmada sigue siendo 102/228 encuentros con coordenadas y elevacion; 228/228 tienen sede identificada.
2. Construir transiciones por jugador y edicion con historial suficiente. Etiquetar ultima participacion conocida, eliminacion confirmada o cierre de participacion; no confundir esos estados.
3. Calcular diferencias de UTC con zonas IANA y fecha/DST explicitos, comparando ambos offsets en un mismo instante de referencia. Separar signo de diferencia horaria y direccion geografica, especialmente alrededor de la linea de fecha.
4. Usar horas reales solo con evidencia y disponibilidad anterior a la decision. Si solo hay fechas o intervalos, devolver cotas/incertidumbre. Intervalo salida-debut no es tiempo desde llegada ni descanso efectivo.
5. Transporte como candidato con regla configurable y confianza. Distancia corta no acredita carretera, especialmente entre islas; distancia larga no acredita un vuelo concreto. Consultas de rutas opcionales, cacheadas por par/perfil/version.
6. Probar variables separadas e interacciones regularizadas: desplazamiento horario por tiempo disponible, direccion, altitud de destino y cambio de altitud. Datos y transformaciones solo disponibles antes del pronostico. No usar vuelos actuales como evidencia de itinerarios historicos.
7. Comparar base frente a base+viajes en muestra comun, validacion temporal, log-loss/Brier/calibracion y ablaciones; mantener holdout intacto. Modelos circadianos solo como escenarios experimentales si faltan luz, sueno o llegada observados.

Esta revision es documental. No se instalaron librerias ni se realizaron llamadas a servicios de rutas/vuelos ni cambios de probabilidades. Georreferenciacion pendiente permanece abierta.
