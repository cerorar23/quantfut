"""Genera el hash de ADMIN_CONSOLE_PASSWORD_HASH sin guardar la clave en disco."""
import getpass
import hashlib
import secrets


def main() -> None:
    password = getpass.getpass("Contraseña nueva para el panel: ")
    confirmation = getpass.getpass("Repite la contraseña: ")
    if len(password) < 16 or password != confirmation:
        raise SystemExit("Las claves deben coincidir y tener al menos 16 caracteres")
    if not password.isascii():
        raise SystemExit("Usa caracteres ASCII para compatibilidad con HTTP Basic")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    print(f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}")


if __name__ == "__main__":
    main()
