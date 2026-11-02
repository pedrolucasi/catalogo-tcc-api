from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def tratador_de_excecoes(exc, context):
    """Traduz a exclusão bloqueada por PROTECT em 409 com JSON, em vez de erro 500."""
    if isinstance(exc, ProtectedError):
        dependentes = sorted({str(obj) for obj in exc.protected_objects})[:5]
        return Response(
            {
                'detail': 'Este registro não pode ser excluído porque outros dependem dele.',
                'dependentes': dependentes,
            },
            status=status.HTTP_409_CONFLICT,
        )
    return exception_handler(exc, context)
