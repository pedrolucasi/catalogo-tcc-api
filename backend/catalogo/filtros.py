import django_filters

from .models import Trabalho


class TrabalhoPublicoFilter(django_filters.FilterSet):
    ano = django_filters.NumberFilter(field_name='ano', label='Ano da defesa, ex.: 2023.')
    curso = django_filters.CharFilter(
        field_name='curso__sigla',
        lookup_expr='iexact',
        label='Sigla do curso, sem diferenciar maiúsculas, ex.: TSI.',
    )
    palavra_chave = django_filters.CharFilter(
        field_name='palavras_chave__termo',
        lookup_expr='iexact',
        label='Termo exato de uma palavra-chave, sem diferenciar maiúsculas, ex.: django.',
    )

    class Meta:
        model = Trabalho
        fields = ['ano', 'curso', 'palavra_chave']


class TrabalhoGestaoFilter(django_filters.FilterSet):
    class Meta:
        model = Trabalho
        fields = ['situacao', 'curso', 'orientador', 'ano']
