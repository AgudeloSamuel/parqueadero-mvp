from argparse import ArgumentParser
from getpass import getpass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.usuario import Rol
from app.infrastructure.db import UsuarioDB, motor_db
from app.infrastructure.seguridad import hash_password


def main() -> None:
    parser = ArgumentParser(description="Crea un usuario local del parqueadero.")
    parser.add_argument("username")
    parser.add_argument("rol", type=Rol, choices=list(Rol))
    args = parser.parse_args()
    if not args.username.strip() or len(args.username) > 100:
        parser.error("El usuario debe tener entre 1 y 100 caracteres.")
    password = getpass("Contraseña: ")
    if password != getpass("Repite la contraseña: "):
        parser.error("Las contraseñas no coinciden.")
    try:
        password_hash = hash_password(password)
    except ValueError as error:
        parser.error(str(error))
    try:
        with Session(motor_db()) as sesion, sesion.begin():
            sesion.add(
                UsuarioDB(username=args.username, password_hash=password_hash, rol=args.rol)
            )
    except IntegrityError:
        parser.error("El nombre de usuario ya existe.")
    print(f"Usuario {args.username} creado con rol {args.rol}.")


if __name__ == "__main__":
    main()
