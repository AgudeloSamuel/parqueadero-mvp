from collections.abc import Callable

from app.domain.usuario import Usuario


def autenticar(
    username: str,
    password: str,
    buscar_usuario: Callable[[str], Usuario | None],
    verificar_password: Callable[[str, str], bool],
) -> Usuario | None:
    usuario = buscar_usuario(username)
    if usuario and verificar_password(password, usuario.password_hash):
        return usuario
    return None
