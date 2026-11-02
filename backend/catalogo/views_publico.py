from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.versioning import URLPathVersioning
from rest_framework.views import APIView

from .filtros import TrabalhoPublicoFilter
from .models import Curso, Orientador, Trabalho
from .serializers import TrabalhoPublicoDetalheSerializer, TrabalhoPublicoListaSerializer

TOP_ORIENTADORES = 5

RESPOSTA_429 = OpenApiResponse(
    description=(
        'Limite de 30 requisições por minuto por IP excedido. O corpo traz `detail` com a '
        'espera em segundos, e o cabeçalho `Retry-After` traz o mesmo número.'
    )
)


class PortaAbertaMixin:
    """Configuração comum a tudo que é público.

    Sem autenticação nenhuma: mesmo quem envia um token é tratado como anônimo
    aqui, porque a porta aberta não deve se comportar diferente conforme quem
    pergunta. Por isso o limite de uso vale para todos os clientes.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    versioning_class = URLPathVersioning


@extend_schema_view(
    list=extend_schema(
        summary='Listar trabalhos publicados',
        description=(
            'Lista paginada (10 por página, até 50 com `tamanho`) dos TCCs **publicados**. '
            'Trabalhos em andamento ou defendidos sem autorização de divulgação nunca aparecem.\n\n'
            'Cada item traz curso, orientador e autores por nome.\n\n'
            '`search` procura no título, no resumo, no nome dos autores e no nome do orientador. '
            'Os filtros `ano`, `curso` e `palavra_chave` combinam entre si e com a busca. '
            '`ordering` aceita `ano`, `-ano`, `titulo` e `-titulo` (padrão: `-ano,titulo`).'
        ),
        responses={200: TrabalhoPublicoListaSerializer(many=True), 429: RESPOSTA_429},
        tags=['Porta aberta'],
    ),
    retrieve=extend_schema(
        summary='Detalhar um trabalho publicado',
        description=(
            'Ficha completa de um TCC publicado, com resumo e palavras-chave. '
            'Um trabalho que não está publicado responde 404, mesmo que o identificador exista.'
        ),
        responses={
            200: TrabalhoPublicoDetalheSerializer,
            404: OpenApiResponse(description='Trabalho inexistente ou não publicado.'),
            429: RESPOSTA_429,
        },
        tags=['Porta aberta'],
    ),
)
class TrabalhoPublicoViewSet(PortaAbertaMixin, viewsets.ReadOnlyModelViewSet):
    queryset = (
        Trabalho.objects.publicados()
        .select_related('curso', 'orientador', 'coorientador')
        .prefetch_related('autores', 'palavras_chave')
    )
    filterset_class = TrabalhoPublicoFilter
    search_fields = ['titulo', 'resumo', 'autores__nome', 'orientador__nome']
    ordering_fields = ['ano', 'titulo']
    ordering = ['-ano', 'titulo']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TrabalhoPublicoDetalheSerializer
        return TrabalhoPublicoListaSerializer


class EstatisticasView(PortaAbertaMixin, APIView):
    @extend_schema(
        summary='Estatísticas do acervo publicado',
        description=(
            'Números do acervo, calculados pelo banco a cada requisição, considerando apenas '
            'trabalhos publicados: total geral, trabalhos por ano, trabalhos por curso '
            f'e os {TOP_ORIENTADORES} orientadores com mais trabalhos publicados.'
        ),
        responses={
            200: inline_serializer(
                name='Estatisticas',
                fields={
                    'total': serializers.IntegerField(),
                    'por_ano': inline_serializer(
                        name='EstatisticaAno',
                        fields={'ano': serializers.IntegerField(), 'total': serializers.IntegerField()},
                        many=True,
                    ),
                    'por_curso': inline_serializer(
                        name='EstatisticaCurso',
                        fields={
                            'sigla': serializers.CharField(),
                            'nome': serializers.CharField(),
                            'total': serializers.IntegerField(),
                        },
                        many=True,
                    ),
                    'top_orientadores': inline_serializer(
                        name='EstatisticaOrientador',
                        fields={'nome': serializers.CharField(), 'total': serializers.IntegerField()},
                        many=True,
                    ),
                },
            ),
            429: RESPOSTA_429,
        },
        tags=['Porta aberta'],
    )
    def get(self, request, *args, **kwargs):
        publicados = Trabalho.objects.publicados()
        so_publicados = Q(trabalhos__situacao=Trabalho.Situacao.PUBLICADO)
        orientou_publicado = Q(trabalhos_orientados__situacao=Trabalho.Situacao.PUBLICADO)

        por_ano = (
            publicados.order_by().values('ano').annotate(total=Count('id')).order_by('ano')
        )
        por_curso = (
            Curso.objects.annotate(total=Count('trabalhos', filter=so_publicados))
            .values('sigla', 'nome', 'total')
            .order_by('-total', 'sigla')
        )
        top_orientadores = (
            Orientador.objects.annotate(total=Count('trabalhos_orientados', filter=orientou_publicado))
            .filter(total__gt=0)
            .values('nome', 'total')
            .order_by('-total', 'nome')[:TOP_ORIENTADORES]
        )
        return Response(
            {
                'total': publicados.count(),
                'por_ano': list(por_ano),
                'por_curso': list(por_curso),
                'top_orientadores': list(top_orientadores),
            }
        )
