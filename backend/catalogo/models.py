from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

MIN_AUTORES = 1
MAX_AUTORES = 2


def validar_ano_nao_futuro(ano):
    ano_corrente = timezone.localdate().year
    if ano > ano_corrente:
        raise ValidationError(
            f'O ano não pode ser maior que o ano corrente ({ano_corrente}).',
            code='ano_futuro',
        )


def validar_quantidade_autores(autores):
    """Recebe a lista de autores ainda não salva.

    O relacionamento muitos-para-muitos só existe depois que o trabalho tem
    chave primária, então esta regra não cabe no clean() do model: ela é
    chamada pelo serializer e pelo formulário do admin, que têm a lista em mãos
    antes de salvar.
    """
    quantidade = len(autores)
    if not MIN_AUTORES <= quantidade <= MAX_AUTORES:
        raise ValidationError(
            f'Todo trabalho tem no mínimo {MIN_AUTORES} e no máximo {MAX_AUTORES} autores '
            f'(foram informados {quantidade}).',
            code='quantidade_autores',
        )


class Curso(models.Model):
    nome = models.CharField('nome', max_length=150, unique=True)
    sigla = models.CharField('sigla', max_length=20, unique=True)

    class Meta:
        verbose_name = 'curso'
        verbose_name_plural = 'cursos'
        ordering = ['nome']

    def __str__(self):
        return f'{self.sigla} — {self.nome}'


class Orientador(models.Model):
    class Titulacao(models.TextChoices):
        ESPECIALISTA = 'especialista', 'Especialista'
        MESTRE = 'mestre', 'Mestre'
        DOUTOR = 'doutor', 'Doutor'

    nome = models.CharField('nome', max_length=150)
    titulacao = models.CharField('titulação', max_length=20, choices=Titulacao.choices)
    email = models.EmailField('e-mail institucional', unique=True)

    class Meta:
        verbose_name = 'orientador'
        verbose_name_plural = 'orientadores'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Autor(models.Model):
    nome = models.CharField('nome', max_length=150)
    email = models.EmailField('e-mail', unique=True)

    class Meta:
        verbose_name = 'autor'
        verbose_name_plural = 'autores'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class PalavraChave(models.Model):
    termo = models.CharField('termo', max_length=60, unique=True)

    class Meta:
        verbose_name = 'palavra-chave'
        verbose_name_plural = 'palavras-chave'
        ordering = ['termo']

    def __str__(self):
        return self.termo


class TrabalhoQuerySet(models.QuerySet):
    def publicados(self):
        return self.filter(situacao=Trabalho.Situacao.PUBLICADO)


class Trabalho(models.Model):
    class Situacao(models.TextChoices):
        EM_ANDAMENTO = 'em_andamento', 'Em andamento'
        DEFENDIDO = 'defendido', 'Defendido'
        PUBLICADO = 'publicado', 'Publicado'

    titulo = models.CharField('título', max_length=255)
    resumo = models.TextField('resumo')
    ano = models.PositiveSmallIntegerField(
        'ano', validators=[MinValueValidator(1900), validar_ano_nao_futuro]
    )
    data_defesa = models.DateField('data da defesa', null=True, blank=True)
    nota = models.DecimalField(
        'nota',
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    situacao = models.CharField(
        'situação', max_length=20, choices=Situacao.choices, default=Situacao.EM_ANDAMENTO
    )
    link_pdf = models.URLField('link do arquivo em PDF', blank=True)
    curso = models.ForeignKey(
        Curso, verbose_name='curso', on_delete=models.PROTECT, related_name='trabalhos'
    )
    orientador = models.ForeignKey(
        Orientador,
        verbose_name='orientador',
        on_delete=models.PROTECT,
        related_name='trabalhos_orientados',
    )
    coorientador = models.ForeignKey(
        Orientador,
        verbose_name='coorientador',
        on_delete=models.PROTECT,
        related_name='trabalhos_coorientados',
        null=True,
        blank=True,
    )
    autores = models.ManyToManyField(Autor, verbose_name='autores', related_name='trabalhos')
    palavras_chave = models.ManyToManyField(
        PalavraChave, verbose_name='palavras-chave', related_name='trabalhos', blank=True
    )
    cadastrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='cadastrado por',
        on_delete=models.PROTECT,
        related_name='trabalhos_cadastrados',
        editable=False,
    )
    criado_em = models.DateTimeField('criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('atualizado em', auto_now=True)

    objects = TrabalhoQuerySet.as_manager()

    class Meta:
        verbose_name = 'trabalho'
        verbose_name_plural = 'trabalhos'
        ordering = ['-ano', 'titulo']
        constraints = [
            models.UniqueConstraint(
                fields=['titulo', 'curso', 'ano'],
                name='trabalho_titulo_curso_ano_unico',
                violation_error_message=(
                    'Já existe um trabalho com este título neste curso e neste ano.'
                ),
            ),
        ]

    def __str__(self):
        return f'{self.titulo} ({self.ano})'

    def clean(self):
        super().clean()
        erros = {}
        if self.situacao == self.Situacao.PUBLICADO:
            if self.nota is None:
                erros['nota'] = 'Um trabalho só pode ser publicado se tiver nota.'
            if self.data_defesa is None:
                erros['data_defesa'] = 'Um trabalho só pode ser publicado se tiver data de defesa.'
        if self.coorientador_id and self.coorientador_id == self.orientador_id:
            erros['coorientador'] = 'O coorientador não pode ser o próprio orientador.'
        if erros:
            raise ValidationError(erros)
