import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Autor, Curso, Orientador, PalavraChave, Trabalho, validar_quantidade_autores

# ---------------------------------------------------------------------------
# Porta aberta
#
# Contrato público: só o que interessa a quem consulta um acervo. Nota, e-mails,
# situação, quem cadastrou e datas de controle nunca aparecem aqui. Estes
# serializers são somente leitura e não herdam dos da gestão, para que um campo
# novo no model ou na gestão não vaze para a porta aberta por acidente.
# ---------------------------------------------------------------------------


class CursoPublicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = ['nome', 'sigla']
        read_only_fields = fields


class OrientadorPublicoSerializer(serializers.ModelSerializer):
    titulacao = serializers.CharField(source='get_titulacao_display', read_only=True)

    class Meta:
        model = Orientador
        fields = ['nome', 'titulacao']
        read_only_fields = fields


class TrabalhoPublicoListaSerializer(serializers.ModelSerializer):
    curso = CursoPublicoSerializer(read_only=True)
    orientador = serializers.CharField(source='orientador.nome', read_only=True)
    autores = serializers.SlugRelatedField(many=True, read_only=True, slug_field='nome')
    palavras_chave = serializers.SlugRelatedField(many=True, read_only=True, slug_field='termo')

    class Meta:
        model = Trabalho
        fields = ['id', 'titulo', 'ano', 'curso', 'orientador', 'autores', 'palavras_chave']
        read_only_fields = fields


class TrabalhoPublicoDetalheSerializer(serializers.ModelSerializer):
    curso = CursoPublicoSerializer(read_only=True)
    orientador = OrientadorPublicoSerializer(read_only=True)
    coorientador = OrientadorPublicoSerializer(read_only=True, allow_null=True)
    autores = serializers.SlugRelatedField(many=True, read_only=True, slug_field='nome')
    palavras_chave = serializers.SlugRelatedField(many=True, read_only=True, slug_field='termo')

    class Meta:
        model = Trabalho
        fields = [
            'id',
            'titulo',
            'resumo',
            'ano',
            'data_defesa',
            'curso',
            'orientador',
            'coorientador',
            'autores',
            'palavras_chave',
            'link_pdf',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Porta fechada
# ---------------------------------------------------------------------------


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = ['id', 'nome', 'sigla']


class OrientadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orientador
        fields = ['id', 'nome', 'titulacao', 'email']


class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = ['id', 'nome', 'email']


class PalavraChaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = PalavraChave
        fields = ['id', 'termo']


class TrabalhoGestaoSerializer(serializers.ModelSerializer):
    autores = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Autor.objects.all(), allow_empty=True
    )
    cadastrado_por = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Trabalho
        fields = [
            'id',
            'titulo',
            'resumo',
            'ano',
            'data_defesa',
            'nota',
            'situacao',
            'link_pdf',
            'curso',
            'orientador',
            'coorientador',
            'autores',
            'palavras_chave',
            'cadastrado_por',
            'criado_em',
            'atualizado_em',
        ]
        read_only_fields = ['cadastrado_por', 'criado_em', 'atualizado_em']

    def validate_autores(self, autores):
        try:
            validar_quantidade_autores(autores)
        except DjangoValidationError as erro:
            raise serializers.ValidationError(erro.messages)
        return autores

    def validate(self, attrs):
        # As regras que olham mais de um campo vivem em Trabalho.clean(). Num
        # PATCH só chegam os campos alterados, então a checagem é feita sobre
        # uma cópia do registro atual com as alterações aplicadas.
        trabalho = copy.copy(self.instance) if self.instance else Trabalho()
        for campo, valor in attrs.items():
            if campo not in ('autores', 'palavras_chave'):
                setattr(trabalho, campo, valor)
        try:
            trabalho.clean()
        except DjangoValidationError as erro:
            raise serializers.ValidationError(erro.message_dict)
        return attrs
