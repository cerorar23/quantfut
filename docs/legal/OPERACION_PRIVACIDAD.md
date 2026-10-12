# Atención de privacidad de QuantFut

Titular y responsable de atención: **Saptain LTD**, a través del buzón confirmado
**admin@pronosticosdeportivos.pro**. Revisarlo diariamente; no se configura aquí
un envío de correo a terceros ni un borrado automático de cuentas.

1. Registrar fecha de recepción, derecho solicitado, cuenta y plazo aplicable
   en un registro privado. Acusar recibo y verificar identidad proporcionalmente
   desde el correo de la cuenta; nunca pedir contraseñas o códigos de Google.
2. Resolver acceso/corrección/portabilidad con los datos de esa cuenta, excluyendo
   secretos, contraseñas, tokens y datos de terceros. Un mes bajo RGPD; si hace
   falta ampliación legal, comunicar motivos en el primer mes. Aplicar un plazo
   menor si la ley correspondiente lo exige; informar vías de recurso.
3. Para cierre verificado: suspender la cuenta en el panel para impedir acceso;
   revocar sus sesiones, retirar sus dispositivos/colas y preferencias Firebase.
   Coordinar la cancelación de suscripciones mediante revocación, sin alterar
   el historial de suscripciones ni el registro de auditoría inmutable.
4. Borrar la identidad Google/Firebase en la consola Authentication con una
   cuenta administradora y retirar el vínculo local. El servidor tiene solo
   lectura de Authentication y envío FCM; no tiene permiso de borrar identidades.
   Verificar ambos sistemas: borrar solo Firebase no borra la cuenta comercial.
5. Inventariar datos personales de cuenta, correos, referidos, sesiones y
   recompensas. Eliminar o anonimizar los que no tengan motivo de conservación;
   restringir lo que sea necesario por ley o reclamación y documentar el motivo
   y su fecha de revisión. Las restricciones de inmutabilidad no se deshabilitan:
   cualquier anonimización necesaria del ledger exige un procedimiento revisado
   para sus campos personales. No prometer eliminación integral ya ejecutada.
6. Registrar el resultado y comunicarlo. Guardar las instrucciones de borrado
   necesarias para reaplicarlas antes de abrir al público una restauración.
   La revocación/suspensión en el servidor protege también sesiones Firebase
   ya emitidas porque cada petición comprueba la cuenta local activa.

## Conservación operativa

- Analytics: usuarios/eventos **2 meses**, reinicio por actividad desactivado.
  Cambio guardado en la propiedad 558571758. Google aplica a las 24 h y depura
  mensualmente; no afecta informes agregados estándar.
- Avisos caducados y cola: retiro diario al cumplir 30 días desde caducidad.
- Dispositivos sin actualización: token retirado a los 90 días. El cliente
  vuelve a registrar su dispositivo al reanudar cuando tiene permiso.
- Copias comerciales nuevas: privadas (carpeta 0700, archivos 0600), cada día,
  rotación de 30 días en `/home/qf/.local/share/quantfut/commercial-backups`.
  No incluyen historias deportivas ni NBA. No sustituyen un respaldo completo
  ni una copia fuera del VPS. Restaurar sobre la base completa correspondiente,
  con una validación previa y reaplicación de solicitudes de borrado.
- Copias manuales de despliegues anteriores: inventariar y revisar por motivo
  de recuperación, obligación o reclamación; no se han eliminado archivos
  anteriores de otras sesiones. No están incluidos en el ciclo periódico.
- Registros comerciales: conservar según la obligación legal o prescripción
  concreta documentada para cada categoría/caso. No inventar un plazo universal
  de 5 o 10 años para todos los países.

## Revisión territorial

Publicar estos textos permite informar sobre la aplicación; no acredita una
licencia ni cumplimiento general en todos los mercados previstos. Antes del
lanzamiento comercial de cada país, revisar con asesoría habilitada contenido
de pronósticos, consumo, pagos, representación EEE/Reino Unido y garantías de
transferencias. Documentar contratos/DPA de Contabo/Google/Proton; aceptar un
contrato nuevo corresponde al titular, no se ha firmado en su nombre.
Pagos y proveedores de ofertas continúan desactivados.
