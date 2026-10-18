// Acceso con Google (Firebase Auth, SDK web). Solo obtiene el ID token: el servidor lo verifica
// y abre la misma sesión de cookie que el acceso con correo (/app/v1/firebase/web-session).
// La configuración pública la sirve el backend (/app/v1/firebase/web-config); nada va en el repo.
const SDK = 'https://www.gstatic.com/firebasejs/11.10.0';
let loaded = null;

async function load(config) {
  loaded ??= Promise.all([import(`${SDK}/firebase-app.js`), import(`${SDK}/firebase-auth.js`)])
    .then(([app, auth]) => {
      const { consentVersion, ...options } = config;
      return { auth: auth.getAuth(app.initializeApp(options)), api: auth };
    });
  return loaded;
}

/** Abre la ventana de Google y devuelve el ID token de Firebase. */
export async function googleIdToken(config) {
  const { auth, api } = await load(config);
  const provider = new api.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: 'select_account' });
  try {
    const result = await api.signInWithPopup(auth, provider);
    const token = await result.user.getIdToken();
    // La sesión del servidor es la única; Firebase no guarda estado propio en la página.
    await api.signOut(auth);
    return token;
  } catch (error) {
    if (error?.code === 'auth/popup-closed-by-user' || error?.code === 'auth/cancelled-popup-request') return null;
    if (error?.code === 'auth/popup-blocked') throw new Error('El navegador bloqueó la ventana de Google. Permite las ventanas emergentes e inténtalo de nuevo.');
    throw new Error('No se pudo iniciar sesión con Google. Inténtalo de nuevo.');
  }
}
