from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from rest_framework.authtoken.models import Token

from catalogo.models import Autor, Curso, Orientador, PalavraChave, Trabalho
from catalogo.permissoes import GRUPO_COORDENACAO

CURSOS = [
    ('TSI', 'Tecnologia em Sistemas para Internet'),
    ('RC', 'Tecnologia em Redes de Computadores'),
    ('TEL', 'Tecnologia em Telemática'),
    ('EC', 'Engenharia de Computação'),
]

# (nome, titulação, e-mail, siglas dos cursos em que orienta)
ORIENTADORES = [
    ('Mariana Albuquerque Lins', 'doutor', 'mariana.lins@ifpb.edu.br', ['TSI']),
    ('Ricardo Nóbrega Farias', 'mestre', 'ricardo.farias@ifpb.edu.br', ['TSI', 'EC']),
    ('Helena Cavalcanti Rocha', 'doutor', 'helena.rocha@ifpb.edu.br', ['RC']),
    ('Fábio Medeiros Targino', 'mestre', 'fabio.targino@ifpb.edu.br', ['RC', 'TEL']),
    ('Joana Batista Queiroga', 'doutor', 'joana.queiroga@ifpb.edu.br', ['TEL']),
    ('Paulo Henrique Diniz', 'especialista', 'paulo.diniz@ifpb.edu.br', ['TEL', 'TSI']),
    ('Luciana Formiga Brito', 'doutor', 'luciana.brito@ifpb.edu.br', ['EC']),
    ('André Vasconcelos Leite', 'mestre', 'andre.leite@ifpb.edu.br', ['EC', 'RC']),
]

# (título, sigla do curso, palavras-chave)
TRABALHOS = [
    ('Catálogo digital de TCCs com API REST em Django', 'TSI', ['django', 'api rest', 'python']),
    ('Aplicativo progressivo para agendamento de atendimento na biblioteca', 'TSI', ['pwa', 'javascript', 'acessibilidade']),
    ('Análise de acessibilidade em portais de prefeituras da Paraíba', 'TSI', ['acessibilidade', 'usabilidade', 'governo eletrônico']),
    ('Controle de frequência escolar com leitura de QR Code', 'TSI', ['python', 'django', 'educação']),
    ('Comparativo de desempenho entre React e Vue em aplicações de página única', 'TSI', ['javascript', 'react', 'desempenho']),
    ('Plataforma de doação de alimentos para bancos comunitários', 'TSI', ['django', 'impacto social', 'api rest']),
    ('Gamificação no ensino de lógica de programação', 'TSI', ['gamificação', 'educação', 'javascript']),
    ('Recomendação de disciplinas optativas com aprendizado de máquina', 'TSI', ['aprendizado de máquina', 'python', 'educação']),
    ('Chatbot para atendimento acadêmico com processamento de linguagem natural', 'TSI', ['processamento de linguagem natural', 'python']),
    ('Painel de transparência de gastos públicos municipais', 'TSI', ['dados abertos', 'governo eletrônico', 'visualização de dados']),
    ('Monitoramento de redes com Zabbix em ambiente acadêmico', 'RC', ['monitoramento', 'redes', 'software livre']),
    ('Implantação de IPv6 na rede de um campus do IFPB', 'RC', ['ipv6', 'redes']),
    ('Análise de vulnerabilidades em roteadores domésticos', 'RC', ['segurança da informação', 'redes']),
    ('Detecção de intrusão com aprendizado de máquina em tráfego de rede', 'RC', ['segurança da informação', 'aprendizado de máquina']),
    ('Virtualização de servidores com Proxmox em pequenas empresas', 'RC', ['virtualização', 'software livre']),
    ('Avaliação de desempenho de redes Wi-Fi 6 em salas de aula', 'RC', ['redes sem fio', 'desempenho']),
    ('Orquestração de contêineres com Kubernetes para serviços acadêmicos', 'RC', ['contêineres', 'computação em nuvem']),
    ('Redes definidas por software aplicadas a laboratórios de ensino', 'RC', ['redes', 'educação']),
    ('Sensoriamento da qualidade do ar com Arduino e LoRa', 'TEL', ['internet das coisas', 'lora', 'arduino']),
    ('Irrigação automatizada de hortas comunitárias com ESP32', 'TEL', ['internet das coisas', 'arduino', 'impacto social']),
    ('Rastreamento em tempo real da frota de ônibus universitário', 'TEL', ['internet das coisas', 'visualização de dados']),
    ('Cobertura de sinal 4G na zona rural do Sertão paraibano', 'TEL', ['telecomunicações', 'redes sem fio']),
    ('Alerta de enchentes baseado em sensores de nível', 'TEL', ['internet das coisas', 'lora']),
    ('Requisitos de rede para telemedicina em unidades básicas de saúde', 'TEL', ['telecomunicações', 'desempenho']),
    ('Casa inteligente de baixo custo com software livre', 'TEL', ['internet das coisas', 'software livre', 'arduino']),
    ('Propagação de ondas de rádio em ambientes internos', 'TEL', ['telecomunicações', 'redes sem fio']),
    ('Compilador educacional para uma linguagem de programação em português', 'EC', ['compiladores', 'educação']),
    ('Visão computacional para contagem de veículos em cruzamentos', 'EC', ['visão computacional', 'aprendizado de máquina', 'python']),
    ('Sistema embarcado vestível para monitoramento cardíaco', 'EC', ['sistemas embarcados', 'internet das coisas']),
    ('Paralelização de algoritmos genéticos em GPU', 'EC', ['computação paralela', 'desempenho']),
    ('Reconhecimento de Libras com redes neurais convolucionais', 'EC', ['visão computacional', 'acessibilidade', 'aprendizado de máquina']),
    ('Robô seguidor de linha controlado por lógica fuzzy', 'EC', ['sistemas embarcados', 'robótica']),
    ('Blockchain para rastreabilidade de diplomas', 'EC', ['blockchain', 'segurança da informação']),
    ('Simulação de tráfego urbano com autômatos celulares', 'EC', ['computação paralela', 'visualização de dados']),
    ('Detecção de notícias falsas em português com modelos de linguagem', 'EC', ['processamento de linguagem natural', 'aprendizado de máquina']),
    ('Consumo energético em redes de sensores sem fio', 'EC', ['sistemas embarcados', 'redes sem fio']),
]

FORA_DE_PUBLICACAO = {
    3: Trabalho.Situacao.DEFENDIDO,
    9: Trabalho.Situacao.EM_ANDAMENTO,
    15: Trabalho.Situacao.DEFENDIDO,
    20: Trabalho.Situacao.EM_ANDAMENTO,
    26: Trabalho.Situacao.DEFENDIDO,
    31: Trabalho.Situacao.EM_ANDAMENTO,
    34: Trabalho.Situacao.DEFENDIDO,
}

ANOS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

NOMES = [
    'Ana', 'Bruno', 'Camila', 'Diego', 'Eduarda', 'Felipe', 'Gabriela', 'Heitor', 'Isabela',
    'João', 'Larissa', 'Marcos', 'Natália', 'Otávio', 'Patrícia', 'Rafael', 'Sofia', 'Tiago',
    'Vitória', 'Wesley', 'Yasmin', 'Lucas', 'Beatriz', 'Mateus', 'Letícia', 'Gustavo',
]
SOBRENOMES = [
    'Silva', 'Souza', 'Oliveira', 'Pereira', 'Lima', 'Araújo', 'Costa', 'Barbosa', 'Ribeiro',
    'Cavalcante', 'Medeiros', 'Dantas', 'Nóbrega', 'Fernandes', 'Gomes', 'Freitas', 'Macedo',
]

COORDENACAO = [
    ('coord.ana', 'Ana', 'Coordenadora', 'ana.coord@ifpb.edu.br', '3f6c0e1b9a8d4c7e2f5a1b0c9d8e7f6a5b4c3d2e'),
    ('coord.bruno', 'Bruno', 'Coordenador', 'bruno.coord@ifpb.edu.br', '7a1e4c2b9d0f3e6a8c5b1d4e7f0a2c9b6e3d8f1a'),
]
SENHA_COORDENACAO = 'Coord@2026'


def resumo_para(titulo, palavras):
    temas = ', '.join(palavras[:-1]) + (f' e {palavras[-1]}' if len(palavras) > 1 else palavras[0])
    return (
        f'Este trabalho trata de {titulo[0].lower() + titulo[1:]}. '
        f'A pesquisa parte de um problema observado na comunidade atendida pelo IFPB e '
        f'investiga como {temas} podem contribuir para resolvê-lo. '
        'Foi feito um levantamento bibliográfico, seguido do desenvolvimento de um protótipo '
        'e de uma avaliação com usuários reais. Os resultados indicam ganhos mensuráveis em '
        'relação à situação anterior e apontam limitações que orientam trabalhos futuros.'
    )


class Command(BaseCommand):
    help = 'Apaga e recria os dados de teste do catálogo e as contas da coordenação.'

    @transaction.atomic
    def handle(self, *args, **options):
        Trabalho.objects.all().delete()
        Autor.objects.all().delete()
        PalavraChave.objects.all().delete()
        Orientador.objects.all().delete()
        Curso.objects.all().delete()
        if connection.vendor == 'sqlite':
            tabelas = [m._meta.db_table for m in (Trabalho, Autor, PalavraChave, Orientador, Curso)]
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM sqlite_sequence WHERE name IN ({', '.join(['%s'] * len(tabelas))})",
                    tabelas,
                )

        usuarios = self.criar_coordenacao()

        cursos = {sigla: Curso.objects.create(sigla=sigla, nome=nome) for sigla, nome in CURSOS}

        orientadores_por_curso = {sigla: [] for sigla in cursos}
        for nome, titulacao, email, siglas in ORIENTADORES:
            orientador = Orientador.objects.create(nome=nome, titulacao=titulacao, email=email)
            for sigla in siglas:
                orientadores_por_curso[sigla].append(orientador)

        termos = sorted({termo for _, _, palavras in TRABALHOS for termo in palavras})
        palavras = {termo: PalavraChave.objects.create(termo=termo) for termo in termos}

        proximo_autor = 0

        def novo_autor():
            nonlocal proximo_autor
            i = proximo_autor
            proximo_autor += 1
            meio = (i * 7) % len(SOBRENOMES)
            fim = (i * 3 + 5) % len(SOBRENOMES)
            if fim == meio:
                fim = (fim + 1) % len(SOBRENOMES)
            nome = f'{NOMES[i % len(NOMES)]} {SOBRENOMES[meio]} {SOBRENOMES[fim]}'
            email = f'aluno{i + 1:03d}@academico.ifpb.edu.br'
            return Autor.objects.create(nome=nome, email=email)

        for i, (titulo, sigla, termos_do_trabalho) in enumerate(TRABALHOS):
            situacao = FORA_DE_PUBLICACAO.get(i, Trabalho.Situacao.PUBLICADO)
            opcoes = orientadores_por_curso[sigla]
            orientador = opcoes[(i // 2) % len(opcoes)]
            coorientador = opcoes[(i // 2 + 1) % len(opcoes)] if i % 4 == 0 else None

            if situacao == Trabalho.Situacao.EM_ANDAMENTO:
                ano, data_defesa, nota = 2026, None, None
            else:
                ano = ANOS[(i * 3) % len(ANOS)]
                data_defesa = date(ano, 6 if i % 2 else 12, 5 + i % 20)
                nota = Decimal(70 + (i * 37) % 30) / 10

            trabalho = Trabalho(
                titulo=titulo,
                resumo=resumo_para(titulo, termos_do_trabalho),
                ano=ano,
                data_defesa=data_defesa,
                nota=nota,
                situacao=situacao,
                link_pdf=f'https://repositorio.ifpb.edu.br/tcc/{i + 1:03d}.pdf',
                curso=cursos[sigla],
                orientador=orientador,
                coorientador=coorientador,
                cadastrado_por=usuarios[i % len(usuarios)],
            )
            trabalho.full_clean()
            trabalho.save()
            autores = [novo_autor()]
            if i % 5 == 1:
                autores.append(novo_autor())
            trabalho.autores.set(autores)
            trabalho.palavras_chave.set(palavras[termo] for termo in termos_do_trabalho)

        publicados = Trabalho.objects.publicados().count()
        self.stdout.write(
            self.style.SUCCESS(
                f'{Curso.objects.count()} cursos, {Orientador.objects.count()} orientadores, '
                f'{Autor.objects.count()} autores, {PalavraChave.objects.count()} palavras-chave, '
                f'{Trabalho.objects.count()} trabalhos ({publicados} publicados).'
            )
        )
        for usuario in usuarios:
            self.stdout.write(f'{usuario.username} / {SENHA_COORDENACAO} / token {usuario.auth_token.key}')

    def criar_coordenacao(self):
        grupo, _ = Group.objects.get_or_create(name=GRUPO_COORDENACAO)
        grupo.permissions.set(Permission.objects.filter(content_type__app_label='catalogo'))

        usuarios = []
        for username, nome, sobrenome, email, chave in COORDENACAO:
            usuario, _ = User.objects.get_or_create(username=username)
            usuario.first_name = nome
            usuario.last_name = sobrenome
            usuario.email = email
            usuario.is_staff = True
            usuario.set_password(SENHA_COORDENACAO)
            usuario.save()
            usuario.groups.add(grupo)
            Token.objects.filter(user=usuario).delete()
            Token.objects.create(user=usuario, key=chave)
            usuarios.append(usuario)
        return usuarios
