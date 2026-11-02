from django.urls import include, path, re_path
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.routers import DefaultRouter, SimpleRouter

from . import views_gestao, views_publico

publico = SimpleRouter()
publico.register('trabalhos', views_publico.TrabalhoPublicoViewSet, basename='publico-trabalho')

gestao = DefaultRouter()
gestao.register('trabalhos', views_gestao.TrabalhoGestaoViewSet, basename='gestao-trabalho')
gestao.register('cursos', views_gestao.CursoViewSet, basename='gestao-curso')
gestao.register('orientadores', views_gestao.OrientadorViewSet, basename='gestao-orientador')
gestao.register('autores', views_gestao.AutorViewSet, basename='gestao-autor')
gestao.register('palavras-chave', views_gestao.PalavraChaveViewSet, basename='gestao-palavra-chave')

ObterToken = extend_schema_view(
    post=extend_schema(
        summary='Obter token da coordenação',
        description='Troca usuário e senha por um token. Use-o em `Authorization: Token <chave>`.',
        tags=['Porta fechada — autenticação'],
    )
)(ObtainAuthToken)

urlpatterns = [
    re_path(
        r'^publico/(?P<version>v1)/',
        include(
            [
                *publico.urls,
                path(
                    'estatisticas/',
                    views_publico.EstatisticasView.as_view(),
                    name='publico-estatisticas',
                ),
            ]
        ),
    ),
    path('gestao/token/', ObterToken.as_view(), name='gestao-token'),
    path('gestao/', include(gestao.urls)),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
