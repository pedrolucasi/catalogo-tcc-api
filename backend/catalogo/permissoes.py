from rest_framework.permissions import BasePermission

GRUPO_COORDENACAO = 'coordenacao'


class EhCoordenacao(BasePermission):
    message = 'Apenas contas da coordenação podem usar a porta fechada.'

    def has_permission(self, request, view):
        usuario = request.user
        if not (usuario and usuario.is_authenticated):
            return False
        return usuario.is_superuser or usuario.groups.filter(name=GRUPO_COORDENACAO).exists()
