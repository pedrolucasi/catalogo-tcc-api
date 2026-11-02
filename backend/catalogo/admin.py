from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Autor, Curso, Orientador, PalavraChave, Trabalho, validar_quantidade_autores


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['sigla', 'nome']
    search_fields = ['nome', 'sigla']


@admin.register(Orientador)
class OrientadorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'titulacao', 'email']
    list_filter = ['titulacao']
    search_fields = ['nome', 'email']


@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email']
    search_fields = ['nome', 'email']


@admin.register(PalavraChave)
class PalavraChaveAdmin(admin.ModelAdmin):
    search_fields = ['termo']


class TrabalhoAdminForm(forms.ModelForm):
    class Meta:
        model = Trabalho
        fields = '__all__'

    def clean_autores(self):
        autores = self.cleaned_data.get('autores') or []
        try:
            validar_quantidade_autores(list(autores))
        except ValidationError as erro:
            raise forms.ValidationError(erro.messages)
        return autores


@admin.register(Trabalho)
class TrabalhoAdmin(admin.ModelAdmin):
    form = TrabalhoAdminForm
    list_display = ['titulo', 'ano', 'curso', 'orientador', 'situacao', 'cadastrado_por']
    list_filter = ['situacao', 'curso', 'ano']
    search_fields = ['titulo', 'resumo', 'autores__nome', 'orientador__nome']
    filter_horizontal = ['autores', 'palavras_chave']
    readonly_fields = ['cadastrado_por', 'criado_em', 'atualizado_em']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.cadastrado_por = request.user
        super().save_model(request, obj, form, change)
