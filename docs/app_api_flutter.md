# API de clientes para la web y la app Flutter

`/app/v1` en el mismo FastAPI (`src/qf/api/cuentas.py`). Requiere
`ACCOUNTS_ENABLED=1` y `db/043_cuentas.sql` aplicado.

## Reglas que no cambian

- La app **no lleva secretos**. Nada de `SERVICE_TOKEN` ni `ADMIN_TOKEN`
  en el binario: se extraen. Cada persona se autentica con su cuenta.
- Qué picks ve cada uno lo decide el servidor (`subscriptions`). La app no
  oculta nada: lo que no le corresponde no llega.
- El pago nunca se confirma desde la app. El acceso solo lo concede el panel
  o el webhook del procesador (pendiente de elegir).

## Rutas

| Método | Ruta | Auth | Respuesta |
| --- | --- | --- | --- |
| POST | `/auth/register` | — | `TokensOut` (201). 409 si el correo ya existe, 422 si es inválido o la contraseña no tiene 10–128 caracteres |
| POST | `/auth/login` | — | `TokensOut`. 401 credenciales, 403 cuenta suspendida, 429 demasiados intentos |
| POST | `/auth/refresh` | — | `TokensOut` nuevo. El refresh anterior deja de valer |
| POST | `/auth/logout` | Bearer | 204 |
| POST | `/auth/verify/resend` | Bearer | 202 (`enviado` / `ya_verificado`); 503 `correo_no_configurado` |
| POST | `/auth/verify/confirm` | — | `{token}` → 204; 400 `token_invalido` |
| POST | `/auth/password/forgot` | — | `{email}` → 202 siempre (no revela si existe la cuenta) |
| POST | `/auth/password/reset` | — | `{token, password}` → 204, cierra todas las sesiones; 400 `token_invalido` |
| GET | `/me` | Bearer | cuenta, `plus` y suscripción vigente |
| GET | `/plans` | — | planes a la venta (precio en céntimos) |
| GET | `/picks?limit&offset` | Bearer | `plus`, `publicacion_activa` y picks (solo `free` sin Plus) |
| GET | `/openapi.json` | — | esquema OpenAPI solo de estas rutas |

Errores: `{"detail": {"code": "...", "message": "..."}}`. Decide por
`code`; `message` es para mostrar.

## Correo (Proton Mail)

Al registrarse se envía un enlace de verificación (48 h) y «olvidé mi
contraseña» envía uno de restablecimiento (60 min). Los enlaces abren
`/cuenta/verificar` y `/cuenta/restablecer` en el navegador, así que sirven
igual desde la app; abrirlos no gasta el token, solo el botón de la página.
Si más adelante la app usa deep links, puede leer el `token` del enlace y
llamar a `/auth/verify/confirm` o `/auth/password/reset`.

## Tokens

- `access_token`: opaco, 15 minutos (`expires_in` en segundos). Va en
  `Authorization: Bearer <token>`.
- `refresh_token`: opaco, 30 días, **se rota en cada uso**. Guarda siempre
  el último que devuelve `/auth/refresh`.
- Ante un 401 en una ruta con Bearer: llama una vez a `/auth/refresh` y
  repite la petición. Si el refresh devuelve 401 (`refresh_invalido` o
  `refresh_reusado`), manda al usuario al login.
- `refresh_reusado` significa que alguien presentó un refresh ya usado: la
  sesión se revoca entera. Pasa si dos peticiones refrescan a la vez con el
  mismo token, así que serializa el refresh en la app (un solo refresh en
  vuelo; las demás peticiones esperan su resultado).

En Flutter: `flutter_secure_storage` para el refresh (Keychain / Keystore),
el access solo en memoria, e interceptor de `dio` con un `Completer`
compartido para el refresh único.

## Generar el cliente Dart

```bash
npx @openapitools/openapi-generator-cli generate -i https://pronosticosdeportivos.pro/app/v1/openapi.json -g dart-dio -o quantfut_api
```

En local, cambia la URL por `http://localhost:8000/app/v1/openapi.json`.
