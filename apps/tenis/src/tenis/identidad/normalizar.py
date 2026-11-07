"""Normalización de nombres de jugador para comparar fuentes. Puro, sin base.

Reglas: sin tildes, minúsculas; guion y apóstrofo se pegan («Auger-Aliassime» = «Auger Aliassime», «O'Connell» =
«OConnell»); otros signos fuera; partículas («de», «van»…) se pegan a la palabra siguiente («De Minaur» = «Deminaur»).
Nunca se compara difuso: las claves son exactas, y el cruce entre circuitos se hace fuera de aquí.
"""
import re
import unicodedata

PARTICULAS = frozenset({"de", "da", "do", "dos", "das", "del", "della", "di", "du", "van", "von", "der", "den",
                        "la", "le", "al", "el", "bin", "ben"})
_APELLIDO_INICIAL = re.compile(r"^\s*(.*?[^\s.])\s+([^\W\d_])\.?\s*$")   # «Alcaraz C.» o «Carreño Busta R.»


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def tokens(nombre: str) -> list[str]:
    """Palabras normalizadas, con las partículas pegadas a la palabra siguiente."""
    s = sin_tildes(nombre or "").lower()
    s = re.sub(r"['`’\-]", "", s)          # guion y apóstrofo: se pegan
    s = re.sub(r"[^a-z ]+", " ", s)             # resto de signos y cifras fuera
    salida, pendiente = [], ""
    for t in s.split():
        if t in PARTICULAS and salida:
            pendiente += t
        else:
            salida.append(pendiente + t)
            pendiente = ""
    if pendiente:
        salida.append(pendiente)
    return salida


def nombre_clave(nombre: str) -> str:
    """Clave completa e insensible al orden («Alcaraz Carlos» = «Carlos Alcaraz»). Para igualdad exacta."""
    return " ".join(sorted(tokens(nombre)))


def claves_apellido(nombre: str) -> frozenset:
    """Pares (apellido, inicial) para buscar candidatos, en orden «Nombre Apellido» o «Apellido I.».

    «Carlos Alcaraz» → (alcaraz, c); «Alcaraz C.» → (alcaraz, c); «Juan Carlos Ferrero» → (carlosferrero, j) y
    (ferrero, j). El orden «Apellido Nombre» completo NO genera claves: se resuelve con `nombre_clave` (igualdad
    exacta sin importar el orden). Así «Carlos Alcantara» nunca comparte clave con «Carlos Alcaraz».
    """
    m = _APELLIDO_INICIAL.match(nombre or "")
    if m:
        apellido = "".join(tokens(m.group(1)))
        return frozenset({(apellido, m.group(2).lower())}) if apellido else frozenset()
    t = tokens(nombre)
    if len(t) < 2:
        return frozenset()
    return frozenset(("".join(t[k:]), t[0][0]) for k in range(1, len(t)))
