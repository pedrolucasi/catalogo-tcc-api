# Catálogo de TCCs com API pública

Atividade de laboratório de Rapid Application Development (RAD) — Tecnólogo em Sistemas para Internet, IFPB.

Catálogo de trabalhos de conclusão de curso com duas portas sobre os mesmos models:

- **Porta aberta** (`/api/publico/v1/`): leitura, sem conta e sem senha, só trabalhos publicados.
- **Porta fechada** (`/api/gestao/`): escrita para a coordenação, autenticada por token.

O Django não devolve nenhuma página própria: só JSON, mais as páginas que o DRF e o drf-spectacular geram (API navegável e documentação) e o admin.

## Integrantes

- Pedro Lucas Silva Batista
- Suetone Carneiro de Andrade Neto

## Estrutura

```
backend/    projeto Django (config/ + app catalogo/), migrations, requirements.txt e db.sqlite3 com os dados de teste
frontend/   cliente web em HTML, CSS e JavaScript puro, servido à parte
```

## Como subir

### Back-end (porta 8000)

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

Linux/macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

O `db.sqlite3` já vem com os dados de teste. Para recriá-los do zero (apaga o catálogo e recria as contas e os tokens abaixo):

```bash
python manage.py popular_catalogo
```

Testes automatizados (cobrem os critérios de aceitação 1 a 23 e a `v2` do Desafio A):

```bash
python manage.py test catalogo
```

### Front-end (porta 5500)

**Tecnologia:** HTML, CSS e JavaScript puro (sem framework, sem etapa de build), consumindo a API com `fetch`.

Com o back-end no ar, em outro terminal:

```bash
cd frontend
python -m http.server 5500
```

Abra <http://localhost:5500>. O endereço da API fica em `frontend/config.js`.

O CORS do Django autoriza apenas as origens `http://localhost:5500` e `http://127.0.0.1:5500`.

## Contas da coordenação

| Usuário | Senha | Token |
|---|---|---|
| `coord.ana` | `Coord@2026` | `3f6c0e1b9a8d4c7e2f5a1b0c9d8e7f6a5b4c3d2e` |
| `coord.bruno` | `Coord@2026` | `7a1e4c2b9d0f3e6a8c5b1d4e7f0a2c9b6e3d8f1a` |

As duas contas estão no grupo `coordenacao` (exigido pela porta fechada) e são `staff`, então também entram no admin em <http://127.0.0.1:8000/admin/>.

Use o token no cabeçalho `Authorization: Token <chave>`, com a palavra `Token` antes da chave.

## Endpoints

Documentação navegável: <http://127.0.0.1:8000/api/docs/> (Swagger UI) e <http://127.0.0.1:8000/api/redoc/>. Elas mostram a `v1`; a `v2` da porta aberta fica em <http://127.0.0.1:8000/api/docs/?version=v2> (veja o Desafio A).
Schema OpenAPI: <http://127.0.0.1:8000/api/schema/>.

### Porta aberta — sem autenticação, limitada a 30 requisições por minuto por IP

| Método | Endereço | Descrição |
|---|---|---|
| GET | `/api/publico/v1/trabalhos/` | Lista paginada dos trabalhos publicados |
| GET | `/api/publico/v1/trabalhos/{id}/` | Detalhe de um trabalho publicado; 404 se não estiver publicado |
| GET | `/api/publico/v1/estatisticas/` | Totais por ano, por curso e os 5 orientadores com mais trabalhos publicados |

Parâmetros da lista, todos combináveis:

| Parâmetro | Exemplo | Efeito |
|---|---|---|
| `search` | `?search=zabbix` | Procura no título, no resumo, no nome dos autores e no nome do orientador |
| `ano` | `?ano=2024` | Ano exato |
| `curso` | `?curso=TSI` | Sigla do curso, sem diferenciar maiúsculas |
| `palavra_chave` | `?palavra_chave=django` | Termo da palavra-chave, sem diferenciar maiúsculas |
| `ordering` | `?ordering=titulo` | `ano`, `-ano`, `titulo` ou `-titulo`; o padrão é `-ano,titulo` |
| `page` / `tamanho` | `?page=2&tamanho=20` | Página e itens por página (padrão 10, máximo 50) |

### Porta fechada — `Authorization: Token <chave>`

| Método | Endereço | Descrição |
|---|---|---|
| POST | `/api/gestao/token/` | Troca `username` e `password` pelo token |
| GET, POST | `/api/gestao/trabalhos/` | Lista todos os trabalhos (qualquer situação) e cadastra |
| GET, PUT, PATCH, DELETE | `/api/gestao/trabalhos/{id}/` | Consulta, altera (inclusive a situação) e exclui |
| GET, POST | `/api/gestao/cursos/`, `/orientadores/`, `/autores/`, `/palavras-chave/` | Cadastros de apoio |
| GET, PUT, PATCH, DELETE | `/api/gestao/<recurso>/{id}/` | Idem, por registro |

Exemplos com curl:

```bash
# token
curl -X POST http://127.0.0.1:8000/api/gestao/token/ -d "username=coord.ana&password=Coord@2026"

# cadastrar (cadastrado_por vem do token; se for enviado no JSON, é ignorado)
curl -X POST http://127.0.0.1:8000/api/gestao/trabalhos/ \
  -H "Authorization: Token 3f6c0e1b9a8d4c7e2f5a1b0c9d8e7f6a5b4c3d2e" \
  -H "Content-Type: application/json" \
  -d '{"titulo": "Novo TCC", "resumo": "...", "ano": 2025, "curso": 1, "orientador": 1, "autores": [1]}'

# publicar (o trabalho 4 está "defendido" nos dados de teste)
curl -X PATCH http://127.0.0.1:8000/api/gestao/trabalhos/4/ \
  -H "Authorization: Token 3f6c0e1b9a8d4c7e2f5a1b0c9d8e7f6a5b4c3d2e" \
  -H "Content-Type: application/json" \
  -d '{"situacao": "publicado"}'
```

Os identificadores de curso, orientador e autor podem ser consultados em `GET /api/gestao/cursos/` etc.

## As três decisões da porta aberta

### 1. O que a porta aberta expõe

**Quais registros:** só trabalhos com situação `publicado`. O recorte está no **queryset** (`Trabalho.objects.publicados()`), não no serializer. Assim, um trabalho em andamento ou defendido sem autorização não entra na lista, não entra na busca, não conta nas estatísticas e responde **404** no detalhe, mesmo quando o identificador é informado diretamente: para a porta aberta, ele não existe.

**Quais campos:**

| Lista | Detalhe |
|---|---|
| `id`, `titulo`, `ano`, `curso` (`nome`, `sigla`), `orientador` (nome), `autores` (nomes), `palavras_chave` (termos) | tudo da lista, mais `resumo`, `data_defesa`, `orientador` e `coorientador` (`nome`, `titulacao`) e `link_pdf` |

**O que ficou de fora, e por quê:**

- **`nota`**: é a avaliação da banca, um dado da vida acadêmica do aluno. Não ajuda ninguém a saber se um tema já foi trabalhado.
- **E-mails de autores e orientadores**: são dados pessoais. Numa porta sem autenticação, expô-los transformaria o catálogo numa lista de e-mails para spam. Quem quiser contato pode procurar pelo nome nos canais oficiais do instituto.
- **`situacao`**: na porta aberta, ela é sempre `publicado`. Expor o campo seria uma promessa a mais sem informação nenhuma.
- **`cadastrado_por`, `criado_em`, `atualizado_em`**: são controle interno da coordenação e não dizem nada sobre o trabalho.
- **Identificadores numéricos de curso, orientador e autor**: são detalhe do banco. O consumidor recebe nomes, e a sigla do curso, que é um identificador público e é o que o filtro `curso` aceita. Assim, renumerar registros não quebra ninguém. O `id` do trabalho fica, porque é o endereço do detalhe e precisa ser estável.

Os serializers da porta aberta (`TrabalhoPublicoListaSerializer` e `TrabalhoPublicoDetalheSerializer`) são classes próprias, somente leitura, e não herdam do serializer da gestão. Um campo novo no model ou na gestão só aparece na porta aberta se alguém o acrescentar ali de propósito.

### 2. Por quanto tempo prometemos: versão no endereço

- **Porta aberta: com versão no endereço**, `/api/publico/v1/`, via `URLPathVersioning` do DRF (`ALLOWED_VERSIONS = ['v1', 'v2']`; a `v2` é o Desafio A, mais abaixo).
- **Porta fechada: sem versão**, `/api/gestao/`.

As respostas são diferentes porque os consumidores são diferentes.

A porta aberta tem consumidores que **não conhecemos e não podemos avisar**, como o aluno de outro campus com o painel. Para eles, a versão no endereço é um contrato: dentro de `v1`, o formato só muda de forma **aditiva**. Campos novos podem aparecer, mas nenhum campo existente muda de nome, de tipo ou de formato, e nenhum desaparece. Quando algo precisar mudar de verdade (por exemplo, `resumo` virar `resumo_pt` porque entra um resumo em inglês), a mudança vai para `/api/publico/v2/`. A `v1` continua no ar, servida pelos mesmos models, por um período de transição anunciado (pelo menos um semestre letivo) antes de ser desligada. Quem já consome a `v1` continua funcionando sem precisar saber que a `v2` existe.

A porta fechada tem consumidores **conhecidos e poucos**: a coordenação e as ferramentas que nós mesmos mantemos. Uma mudança ali é combinada antes e sobe junto com quem a consome. Versionar a gestão obrigaria a manter serializers e rotas duplicados para clientes que podemos simplesmente atualizar: pagaríamos o custo do versionamento sem o benefício.

### 3. O que segura o uso: limite de requisições

Sem login, não há quem bloquear, então a porta aberta limita o volume:

- **Limite:** **30 requisições por minuto por IP**, somando todos os endpoints públicos (`AnonRateThrottle`, escopo `anon`).
- **Vale para todo cliente da porta aberta.** As views públicas não fazem autenticação nenhuma (`authentication_classes = []`), então quem mandar um token também é tratado como anônimo ali. A porta aberta se comporta igual para todos.
- **Por que 30:** uma pessoa navegando pelo front-end faz de uma a duas requisições por ação (a busca espera o usuário parar de digitar antes de chamar a API), e 30 por minuto sobra para isso. Um script que dispara em laço esbarra no limite em segundos. O número também é baixo o bastante para ser demonstrado na prática.
- **O que o cliente recebe ao passar do limite:** `HTTP 429 Too Many Requests`, com o cabeçalho `Retry-After` dizendo quantos segundos esperar e corpo JSON:

  ```json
  {"detail": "Pedido foi suprimido. Espera-se que esteja diponível em 59 segundos."}
  ```

  O front-end mostra essa espera ao usuário em vez de uma tela vazia.
- A porta fechada não tem limite, porque cada requisição ali já é de uma conta conhecida da coordenação.

Para ver o 429 (PowerShell):

```powershell
1..31 | % { curl.exe -s -o NUL -w "%{http_code} " http://127.0.0.1:8000/api/publico/v1/estatisticas/ }
```

Em bash: `for i in $(seq 31); do curl -s -o /dev/null -w "%{http_code} " http://127.0.0.1:8000/api/publico/v1/estatisticas/; done`

O contador fica no cache padrão do Django (memória do processo), o que basta para um único servidor. Com vários processos, seria preciso apontar `CACHES` para um cache compartilhado.

## Desafio A: a promessa quebrada, de propósito

A porta aberta tem uma `v2`, em `/api/publico/v2/`, em que o campo `resumo` do detalhe passa a se chamar `resumo_pt`, como no cenário da seção 4. A `v1` continua no ar, intacta, e as duas são servidas pelos mesmos models: o banco tem um único campo `resumo`, e cada versão o publica com o nome que prometeu.

| | `v1` | `v2` |
|---|---|---|
| Lista e estatísticas | iguais | iguais |
| Detalhe | `resumo` | `resumo_pt` |
| Regras (só publicados, 404, limite de uso) | iguais | iguais |
| Documentação | <http://127.0.0.1:8000/api/docs/> | <http://127.0.0.1:8000/api/docs/?version=v2> |

O front-end continua na `v1` de propósito: ele faz o papel do painel do aluno de outro campus, que não sabe que a `v2` existe e segue funcionando.

### Quanto código foi duplicado

**Nenhuma linha duplicada.** Foram cerca de 12 linhas novas de código:

- **8 linhas:** o `TrabalhoPublicoDetalheV2Serializer`, que herda do detalhe da `v1` e só troca `resumo` por `resumo_pt`.
- **2 linhas:** o `get_serializer_class()` do ViewSet escolhe esse serializer quando `request.version == 'v2'`.
- **1 linha:** a rota aceita `v1|v2`.
- **1 linha:** `ALLOWED_VERSIONS` em `settings.py`.

Os testes de que a `v1` não mudou e de que a `v2` segue as mesmas regras ficam em `VersionamentoTests`.

Saiu barato porque a mudança é só um nome na borda, e o resto da cadeia (queryset, filtros, busca, paginação, limite) é o mesmo. Mesmo assim, já cobrou três preços:

1. **A documentação perdeu detalhe.** Para o drf-spectacular gerar um formato de resposta por versão, o detalhe deixou de declarar as respostas 404 e 429 de forma estruturada (declarar qualquer código impede que ele leia o 200 do serializer). Elas passaram a ser descritas em texto.
2. **Cada versão nova multiplica o que precisa ser testado.** Toda regra da porta aberta agora vale em dois endereços.
3. **A herança só funciona enquanto a v1 só cresce.** Ela funciona porque a `v1` só muda de forma aditiva: um campo novo no detalhe da `v1` aparece também na `v2`, o que é aceitável. Se a mudança fosse mais funda (por exemplo, a `v2` com outro formato de data em todos os campos, outros nomes de filtro ou o resumo em inglês saindo de um campo novo no model), a herança deixaria de servir. Viriam serializers, filtros e talvez views paralelas, e esse número cresceria rápido. É por isso que versionar dói: o custo não está na `v2`, está em manter a `v1` viva enquanto ela existir.

## ViewSet com router e APIView: qual ficou em cada um, e por quê

- **ViewSet + router:**
  - `TrabalhoPublicoViewSet` (`ReadOnlyModelViewSet`): a porta aberta de trabalhos é um recurso clássico de lista e detalhe sobre um queryset, com filtro, busca, ordenação e paginação. O ViewSet entrega tudo isso declarativamente, e o router gera as duas rotas.
  - `TrabalhoGestaoViewSet`, `CursoViewSet`, `OrientadorViewSet`, `AutorViewSet` e `PalavraChaveViewSet` (`ModelViewSet`): são CRUDs completos e uniformes. Escrever cinco vezes as mesmas cinco operações à mão seria código repetido sem ganho.
- **APIView:**
  - `EstatisticasView`: não é um recurso nem corresponde a um model. Não tem lista, detalhe, criação nem identificador. É um único `GET` que monta uma resposta a partir de três agregações (`Count` com `GROUP BY` no banco). Num ViewSet, ele precisaria de queryset e serializer artificiais. A `APIView` deixa explícito que é uma consulta pontual. Os números são sempre calculados na hora, nenhum fica guardado em campo.

## Onde ficam as validações

Todas ficam no model ou no serializer, nunca na view, e valem para qualquer porta que grave dados (API e admin):

| Regra | Onde | Por quê ali |
|---|---|---|
| Ano não maior que o corrente | validador `validar_ano_nao_futuro` no campo `ano` do model | Olha um campo só. O `ModelSerializer` e o admin herdam o validador automaticamente |
| Só publica com nota e data de defesa | `Trabalho.clean()`, chamado pelo `validate()` do serializer | Olha a combinação de três campos. Num `PATCH` só chega o campo alterado, então o serializer aplica as alterações sobre uma cópia do registro atual antes de chamar o `clean()` |
| De 1 a 2 autores | `validar_quantidade_autores`, chamada pelo `validate_autores()` do serializer e pelo formulário do admin | Um relacionamento muitos-para-muitos só existe **depois** que o trabalho é salvo, então não dá para checá-lo no `clean()` do model. A regra roda sobre a lista recebida, antes de salvar |
| Título único por curso e ano | `UniqueConstraint` no model, com mensagem própria | O banco garante a regra, e o DRF gera o validador correspondente no serializer, que responde 400 antes de chegar ao banco |

Todos os erros voltam como **400 com JSON** indicando o campo, por exemplo:

```json
{"nota": ["Um trabalho só pode ser publicado se tiver nota."],
 "data_defesa": ["Um trabalho só pode ser publicado se tiver data de defesa."]}
```

Excluir um curso, orientador ou autor que ainda tem trabalhos devolve **409 com JSON** (o model usa `PROTECT`), em vez de erro 500.

## Dados de teste

Gerados pelo comando `popular_catalogo` e já gravados no `db.sqlite3`:

- 4 cursos, 8 orientadores, 43 autores e 36 palavras-chave, reaproveitadas entre trabalhos;
- 36 trabalhos de 2019 a 2026; 29 publicados (de 2019 a 2025) e 7 fora de publicação (3 em andamento e 4 defendidos sem autorização), que provam o 404 do detalhe;
- 7 trabalhos com dois autores;
- 2 contas da coordenação com token (tabela acima).

## Front-end

- A tela inicial lista os trabalhos da API, com paginação ("Anterior"/"Próxima").
- A busca é enviada ao servidor (`search`) 400 ms depois que o usuário para de digitar, para não gastar o limite de uso a cada tecla.
- Filtros por ano, curso e palavra-chave (clicando numa palavra-chave), mais ordenação. Tudo é filtrado no servidor, e as opções de ano e curso vêm de `/estatisticas/`.
- O detalhe mostra resumo, autores, orientador, coorientador, ano, data de defesa e palavras-chave.
- Estados vazio e de erro: busca sem resultado mostra uma mensagem e um botão para limpar os filtros; API fora do ar (ou sem resposta em 10 s), 404 e 429 têm mensagens próprias e botão para tentar de novo.
- O front-end não guarda cópia de dados. Com o Django desligado, a tela mostra apenas o erro.
- O estado da busca fica no endereço (`#/?search=...&curso=TSI`), então recarregar a página ou compartilhar o link mantém a busca.
