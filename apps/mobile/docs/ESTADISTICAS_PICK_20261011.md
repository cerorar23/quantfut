# Estadísticas dentro del pick — 11/10/2026

Adaptación de las seis capturas del usuario al detalle real del partido. El
selector Pronósticos / Estadísticas / H2H conserva el mismo partido y los
permisos de la API. Los gráficos usan la respuesta de `/mobile/v1/matches/{id}`.

Implementado:

- Cabecera con escudos y nombres reales, fecha/hora local, marcador confirmado
  o cuenta atrás hasta el inicio programado.
- Pestañas con subrayado verde, sin partir el texto de Estadísticas.
- Resumen 1X2 con tres segmentos y las probabilidades existentes del modelo.
- Pronóstico publicado y cuota solo cuando el servidor autoriza su lectura.
  La comparación histórica no genera un consejo de apuesta adicional.
- Promedio histórico de goles: valores positivos registrados, claramente
  diferenciados de una proyección de goles. No copiar los valores negativos
  de goles esperados de la referencia.
- Forma de cada equipo con G/E/P, resultados recientes primero y detalle de
  fecha, rival y marcador en cada etiqueta.
- Radar superpuesto morado/verde con las métricas disponibles de ambos equipos.
  Basta con tres ejes completos y algún valor positivo; no depende de que exista
  xG. Las métricas faltantes no se convierten en cero.
- Comparación por barras: goles, remates, remates a puerta, córners, portería a
  cero, ambos marcan, más de 2,5 y xG histórico. Se muestran valores originales
  y una escala relativa, no supuestas probabilidades de ganar derivadas de ellos.
- Clasificación real, puntos y partidos. Mejores triunfos en casa/fuera y rachas
  se calculan únicamente de los resultados recientes disponibles, con su muestra
  visible; no se anuncian como récords de toda la temporada.
- Cara a cara dentro de Estadísticas, con equipos en el orden local/visitante
  de cada encuentro y goles correctamente orientados. Respeta el interruptor H2H.

La cobertura de remates/córners/xG puede ser menor que el número de partidos
del promedio. Un radar más grande no equivale a más probabilidad de victoria.
Si faltan probabilidades se muestran guiones, no porcentajes simulados.

## Recursos de GitHub

Se revisó [fl_chart](https://github.com/imaNNeo/fl_chart), ya incluido en el
proyecto como `^1.2.0`, y su
[documentación de RadarChart](https://github.com/imaNNeo/fl_chart/blob/main/repo_files/documentations/radar_chart.md).
El nuevo radar usa `RadarChart`, dos series, bordes poligonales, rellenos
transparentes y etiquetas propias del proyecto. No se copiaron conjuntos de
datos del ejemplo. Las barras se dibujan con widgets de Flutter a partir de los
valores del servidor. No se agregó otra dependencia.

## Información que aún falta

- Eventos históricos por minuto para el gráfico de momento de goles.
- Parámetros y distribución Poisson / marcadores probables entregados por el
  modelo para este detalle, con origen y fecha.
- Disciplina agregada y récords de la temporada completa, con muestra definida.
- Encuestas de aficionados: votos reales, almacenamiento y prevención de votos
  duplicados. No se añadieron votos ni porcentajes ilustrativos.

Los dos primeros bloques muestran explícitamente su falta de datos. Los otros
dos requieren una ampliación del contrato y no se sustituyen por números ficticios.
Estas ampliaciones quedan en el backlog. El registro inicial con Firebase
permanece solo en el plan, sin implementación, conforme a la instrucción anterior.

## Comprobación

Pruebas de navegación y de datos ausentes, más una respuesta pública real
guardada exclusivamente como fixture en `test/fixtures/match_statistics_real.json`.
La prueba confirma que el radar tiene seis ejes cuando ambos xG son nulos y
que la normalización conserva la relación de goles 0,9 / 1,1. Las capturas
de revisión están en `docs/validation/real_mobile_20261011/stats_real_*.png`.
La app en ejecución consulta el servidor; nunca carga ese fixture.
