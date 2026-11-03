import json

from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import Autor, Curso, Orientador, Trabalho

LISTA = '/api/publico/v1/trabalhos/'
ESTATISTICAS = '/api/publico/v1/estatisticas/'
GESTAO = '/api/gestao/trabalhos/'
TOKEN_ANA = '3f6c0e1b9a8d4c7e2f5a1b0c9d8e7f6a5b4c3d2e'


class BaseCatalogo(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_catalogo', stdout=open('NUL' if __import__('os').name == 'nt' else '/dev/null', 'w'))

    def setUp(self):
        cache.clear()

    def todos_os_itens(self, url=LISTA):
        itens = []
        while url:
            resposta = self.client.get(url, {'tamanho': 50} if url == LISTA else None)
            itens += resposta.data['results']
            url = resposta.data['next']
        return itens


class PortaAbertaTests(BaseCatalogo):
    def test_01_02_10_lista_paginada_com_nomes(self):
        resposta = self.client.get(LISTA)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(set(resposta.data), {'count', 'next', 'previous', 'results'})
        self.assertEqual(len(resposta.data['results']), 10)
        item = resposta.data['results'][0]
        self.assertIsInstance(item['curso']['nome'], str)
        self.assertIsInstance(item['orientador'], str)
        self.assertTrue(all(isinstance(nome, str) for nome in item['autores']))

    def test_03_04_sem_nota_nem_email(self):
        corpo = json.dumps([self.client.get(LISTA).json(), self.client.get(f'{LISTA}{self.publicado().pk}/').json()])
        self.assertNotIn('nota', corpo)
        self.assertNotIn('email', corpo)
        self.assertNotIn('@', corpo)

    def test_05_lista_so_tem_publicados(self):
        ids = {item['id'] for item in self.todos_os_itens()}
        self.assertEqual(ids, set(Trabalho.objects.publicados().values_list('pk', flat=True)))

    def test_06_detalhe_de_nao_publicado_e_404(self):
        for trabalho in Trabalho.objects.exclude(situacao=Trabalho.Situacao.PUBLICADO):
            self.assertEqual(self.client.get(f'{LISTA}{trabalho.pk}/').status_code, 404)

    def test_detalhe_traz_resumo_e_palavras_chave(self):
        dados = self.client.get(f'{LISTA}{self.publicado().pk}/').data
        self.assertTrue(dados['resumo'])
        self.assertTrue(dados['palavras_chave'])

    def test_07_busca_por_titulo(self):
        dados = self.client.get(LISTA, {'search': 'Zabbix'}).data
        self.assertEqual(dados['count'], 1)

    def test_08_busca_por_orientador(self):
        dados = self.client.get(LISTA, {'search': 'Queiroga', 'tamanho': 50}).data
        self.assertGreater(dados['count'], 0)
        esperado = Trabalho.objects.publicados().filter(orientador__nome__icontains='Queiroga').count()
        self.assertEqual(dados['count'], esperado)

    def test_busca_por_autor_nao_duplica(self):
        autor = Autor.objects.filter(trabalhos__situacao='publicado').first()
        dados = self.client.get(LISTA, {'search': autor.nome}).data
        ids = [item['id'] for item in dados['results']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 0)

    def test_09_filtro_por_ano_e_curso(self):
        trabalho = self.publicado()
        dados = self.client.get(LISTA, {'ano': trabalho.ano, 'curso': trabalho.curso.sigla.lower()}).data
        self.assertGreater(dados['count'], 0)
        for item in dados['results']:
            self.assertEqual(item['ano'], trabalho.ano)
            self.assertEqual(item['curso']['sigla'], trabalho.curso.sigla)

    def test_filtro_por_palavra_chave_com_busca(self):
        dados = self.client.get(LISTA, {'palavra_chave': 'internet das coisas', 'search': 'arduino'}).data
        self.assertGreater(dados['count'], 0)
        for item in dados['results']:
            self.assertIn('internet das coisas', item['palavras_chave'])

    def test_ordenacao_por_titulo(self):
        titulos = [item['titulo'] for item in self.client.get(LISTA, {'ordering': 'titulo', 'tamanho': 50}).data['results']]
        self.assertEqual(titulos, sorted(titulos))

    def test_11_estatisticas(self):
        dados = self.client.get(ESTATISTICAS).data
        self.assertEqual(dados['total'], Trabalho.objects.publicados().count())
        self.assertEqual(sum(linha['total'] for linha in dados['por_ano']), dados['total'])
        self.assertEqual(sum(linha['total'] for linha in dados['por_curso']), dados['total'])
        self.assertTrue(dados['top_orientadores'])

    def test_lista_nao_cresce_em_consultas(self):
        with self.assertNumQueries(4):
            self.client.get(LISTA, {'tamanho': 50})

    def publicado(self):
        return Trabalho.objects.publicados().first()


class PortaFechadaTests(BaseCatalogo):
    def autenticar(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {TOKEN_ANA}')

    def payload(self, **extra):
        dados = {
            'titulo': 'Um trabalho novo',
            'resumo': 'Resumo do trabalho novo.',
            'ano': 2025,
            'curso': Curso.objects.get(sigla='TSI').pk,
            'orientador': Orientador.objects.first().pk,
            'autores': [Autor.objects.first().pk],
            'situacao': 'em_andamento',
        }
        dados.update(extra)
        return dados

    def test_12_post_sem_token_e_401(self):
        self.assertEqual(self.client.post(GESTAO, self.payload(), format='json').status_code, 401)

    def test_13_obter_token(self):
        resposta = self.client.post('/api/gestao/token/', {'username': 'coord.ana', 'password': 'Coord@2026'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data['token'], TOKEN_ANA)

    def test_14_19_post_com_token_ignora_cadastrado_por(self):
        self.autenticar()
        resposta = self.client.post(GESTAO, self.payload(cadastrado_por='coord.bruno'), format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data['cadastrado_por'], 'coord.ana')
        self.assertEqual(Trabalho.objects.get(pk=resposta.data['id']).cadastrado_por.username, 'coord.ana')

    def test_15_publicar_sem_nota_e_400(self):
        self.autenticar()
        trabalho = Trabalho.objects.filter(situacao='em_andamento').first()
        resposta = self.client.patch(f'{GESTAO}{trabalho.pk}/', {'situacao': 'publicado'}, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('nota', resposta.json())
        self.assertIn('data_defesa', resposta.json())

    def test_16_ano_futuro_e_400(self):
        self.autenticar()
        resposta = self.client.post(GESTAO, self.payload(ano=2999), format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('ano', resposta.json())

    def test_17_sem_autor_e_400(self):
        self.autenticar()
        for autores in ([], None):
            dados = self.payload(autores=autores)
            if autores is None:
                del dados['autores']
            resposta = self.client.post(GESTAO, dados, format='json')
            self.assertEqual(resposta.status_code, 400)
            self.assertIn('autores', resposta.json())

    def test_tres_autores_e_400(self):
        self.autenticar()
        resposta = self.client.post(GESTAO, self.payload(autores=list(Autor.objects.values_list('pk', flat=True)[:3])), format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('autores', resposta.json())

    def test_18_titulo_repetido_no_mesmo_curso_e_ano_e_400(self):
        self.autenticar()
        existente = Trabalho.objects.first()
        resposta = self.client.post(
            GESTAO,
            self.payload(titulo=existente.titulo, ano=existente.ano, curso=existente.curso_id),
            format='json',
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('non_field_errors', resposta.json())

    def test_20_publicar_faz_aparecer_na_porta_aberta(self):
        self.autenticar()
        trabalho = Trabalho.objects.filter(situacao='defendido').first()
        self.assertEqual(self.client.get(f'{LISTA}{trabalho.pk}/').status_code, 404)
        resposta = self.client.patch(f'{GESTAO}{trabalho.pk}/', {'situacao': 'publicado'}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.client.credentials()
        self.assertEqual(self.client.get(f'{LISTA}{trabalho.pk}/').status_code, 200)

    def test_cadastros_de_apoio(self):
        self.autenticar()
        for rota, dados in [
            ('cursos', {'nome': 'Gestão da TI', 'sigla': 'GTI'}),
            ('orientadores', {'nome': 'Fulano', 'titulacao': 'mestre', 'email': 'fulano@ifpb.edu.br'}),
            ('autores', {'nome': 'Beltrano', 'email': 'beltrano@academico.ifpb.edu.br'}),
            ('palavras-chave', {'termo': 'rad'}),
        ]:
            resposta = self.client.post(f'/api/gestao/{rota}/', dados, format='json')
            self.assertEqual(resposta.status_code, 201, resposta.data)
            pk = resposta.data['id']
            self.assertEqual(self.client.delete(f'/api/gestao/{rota}/{pk}/').status_code, 204)

    def test_excluir_curso_em_uso_e_409(self):
        self.autenticar()
        curso = Curso.objects.first()
        self.assertEqual(self.client.delete(f'/api/gestao/cursos/{curso.pk}/').status_code, 409)


class LimitesEDocumentacaoTests(BaseCatalogo):
    def test_21_acima_do_limite_e_429(self):
        for _ in range(30):
            self.assertEqual(self.client.get(ESTATISTICAS).status_code, 200)
        resposta = self.client.get(ESTATISTICAS)
        self.assertEqual(resposta.status_code, 429)
        self.assertIn('Retry-After', resposta.headers)

    def test_21_front_end_consegue_ler_o_retry_after(self):
        # O front-end roda em outra origem: sem expor o cabeçalho pelo CORS, o
        # navegador o esconde e a tela não sabe quantos segundos pedir de espera.
        origem = {'HTTP_ORIGIN': 'http://localhost:5500'}
        for _ in range(30):
            self.client.get(ESTATISTICAS, **origem)
        resposta = self.client.get(ESTATISTICAS, **origem)
        self.assertEqual(resposta.status_code, 429)
        self.assertIn('retry-after', resposta.headers['Access-Control-Expose-Headers'].lower())

    def test_22_23_documentacao_e_schema(self):
        self.assertEqual(self.client.get('/api/docs/').status_code, 200)
        resposta = self.client.get('/api/schema/', HTTP_ACCEPT='application/vnd.oai.openapi+json')
        self.assertEqual(resposta.status_code, 200)
        schema = json.loads(resposta.content)
        operacao = schema['paths']['/api/publico/v1/trabalhos/']['get']
        self.assertTrue(operacao['description'])
        self.assertIn('/api/gestao/trabalhos/', schema['paths'])


class VersionamentoTests(BaseCatalogo):
    """Desafio A: a v2 renomeia `resumo` para `resumo_pt` e a v1 continua intacta."""

    def detalhe(self, versao):
        pk = Trabalho.objects.publicados().first().pk
        resposta = self.client.get(f'/api/publico/{versao}/trabalhos/{pk}/')
        self.assertEqual(resposta.status_code, 200)
        return resposta.data

    def test_v1_continua_com_resumo(self):
        dados = self.detalhe('v1')
        self.assertIn('resumo', dados)
        self.assertNotIn('resumo_pt', dados)

    def test_v2_troca_resumo_por_resumo_pt_e_mantem_o_resto(self):
        v1, v2 = self.detalhe('v1'), self.detalhe('v2')
        self.assertNotIn('resumo', v2)
        self.assertEqual(v2['resumo_pt'], v1['resumo'])
        self.assertEqual(set(v2) - {'resumo_pt'}, set(v1) - {'resumo'})

    def test_v2_tem_as_mesmas_regras_da_porta_aberta(self):
        nao_publicado = Trabalho.objects.exclude(situacao=Trabalho.Situacao.PUBLICADO).first()
        self.assertEqual(self.client.get(f'/api/publico/v2/trabalhos/{nao_publicado.pk}/').status_code, 404)
        self.assertEqual(self.client.get('/api/publico/v2/trabalhos/').status_code, 200)
        self.assertEqual(self.client.get('/api/publico/v2/estatisticas/').status_code, 200)

    def test_versao_inexistente_e_404(self):
        self.assertEqual(self.client.get('/api/publico/v3/trabalhos/').status_code, 404)

    def test_schema_de_cada_versao(self):
        def campos_do_detalhe(versao):
            resposta = self.client.get(
                f'/api/schema/?version={versao}', HTTP_ACCEPT='application/vnd.oai.openapi+json'
            )
            schema = json.loads(resposta.content)
            operacao = schema['paths'][f'/api/publico/{versao}/trabalhos/{{id}}/']['get']
            ref = operacao['responses']['200']['content']['application/json']['schema']['$ref']
            return set(schema['components']['schemas'][ref.rsplit('/', 1)[1]]['properties'])

        self.assertIn('resumo', campos_do_detalhe('v1'))
        self.assertIn('resumo_pt', campos_do_detalhe('v2'))
        self.assertNotIn('resumo', campos_do_detalhe('v2'))
