from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .filtros import TrabalhoGestaoFilter
from .models import Autor, Curso, Orientador, PalavraChave, Trabalho
from .permissoes import EhCoordenacao
from .serializers import (
    AutorSerializer,
    CursoSerializer,
    OrientadorSerializer,
    PalavraChaveSerializer,
    TrabalhoGestaoSerializer,
)


class PortaFechadaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, EhCoordenacao]


@extend_schema_view(
    list=extend_schema(summary='Listar todos os trabalhos, em qualquer situação'),
    create=extend_schema(
        summary='Cadastrar trabalho',
        description='`cadastrado_por` é preenchido com o dono do token; o valor enviado é ignorado.',
    ),
    partial_update=extend_schema(
        summary='Alterar parte de um trabalho',
        description='Para publicar, envie `{"situacao": "publicado"}`; exige nota e data de defesa.',
    ),
)
@extend_schema(tags=['Porta fechada — trabalhos'])
class TrabalhoGestaoViewSet(PortaFechadaViewSet):
    queryset = (
        Trabalho.objects.select_related('curso', 'orientador', 'coorientador', 'cadastrado_por')
        .prefetch_related('autores', 'palavras_chave')
    )
    serializer_class = TrabalhoGestaoSerializer
    filterset_class = TrabalhoGestaoFilter
    search_fields = ['titulo', 'resumo', 'autores__nome', 'orientador__nome']
    ordering_fields = ['ano', 'titulo', 'criado_em', 'atualizado_em']

    def perform_create(self, serializer):
        serializer.save(cadastrado_por=self.request.user)


@extend_schema(tags=['Porta fechada — cadastros de apoio'])
class CursoViewSet(PortaFechadaViewSet):
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    search_fields = ['nome', 'sigla']


@extend_schema(tags=['Porta fechada — cadastros de apoio'])
class OrientadorViewSet(PortaFechadaViewSet):
    queryset = Orientador.objects.all()
    serializer_class = OrientadorSerializer
    search_fields = ['nome', 'email']


@extend_schema(tags=['Porta fechada — cadastros de apoio'])
class AutorViewSet(PortaFechadaViewSet):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer
    search_fields = ['nome', 'email']


@extend_schema(tags=['Porta fechada — cadastros de apoio'])
class PalavraChaveViewSet(PortaFechadaViewSet):
    queryset = PalavraChave.objects.all()
    serializer_class = PalavraChaveSerializer
    search_fields = ['termo']
