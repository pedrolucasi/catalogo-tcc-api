(function () {
  'use strict';

  const API = window.CONFIG.API_BASE;
  const TAMANHO_PAGINA = 10;
  const ESPERA_DIGITACAO_MS = 400;
  const TEMPO_LIMITE_MS = 10000;
  const FILTROS = ['search', 'ano', 'curso', 'palavra_chave', 'ordering', 'page'];

  const app = document.getElementById('app');
  document.getElementById('link-docs').href = window.CONFIG.DOCS_URL;

  let opcoesDeFiltro = null;
  let requisicaoAtual = null;
  let ultimaListaHash = '#/';

  // ---------------------------------------------------------------- utilidades

  function el(tag, atributos, ...filhos) {
    const no = document.createElement(tag);
    for (const [chave, valor] of Object.entries(atributos || {})) {
      if (valor === null || valor === undefined || valor === false) continue;
      if (chave.startsWith('on')) no.addEventListener(chave.slice(2), valor);
      else if (chave === 'class') no.className = valor;
      else no.setAttribute(chave, valor === true ? '' : valor);
    }
    for (const filho of filhos.flat()) {
      if (filho === null || filho === undefined || filho === false) continue;
      no.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
    }
    return no;
  }

  class ErroApi extends Error {
    constructor(status, detalhe, retryAfter) {
      super(detalhe || `Erro ${status}`);
      this.status = status;
      this.retryAfter = retryAfter;
    }
  }

  async function apiGet(caminho, parametros, sinal) {
    const url = new URL(API + caminho);
    for (const [chave, valor] of Object.entries(parametros || {})) {
      if (valor !== '' && valor !== null && valor !== undefined) url.searchParams.set(chave, valor);
    }
    const limite = AbortSignal.timeout(TEMPO_LIMITE_MS);
    let resposta;
    try {
      resposta = await fetch(url, {
        signal: sinal ? AbortSignal.any([sinal, limite]) : limite,
        headers: { Accept: 'application/json' },
      });
    } catch (erro) {
      if (erro.name === 'AbortError') throw erro;
      throw new ErroApi(0, 'Sem conexão com a API.');
    }
    if (!resposta.ok) {
      let detalhe = '';
      try { detalhe = (await resposta.json()).detail || ''; } catch (_) { /* corpo não é JSON */ }
      throw new ErroApi(resposta.status, detalhe, resposta.headers.get('Retry-After'));
    }
    return resposta.json();
  }

  function lerHash() {
    const [caminho, consulta = ''] = location.hash.replace(/^#/, '').split('?');
    return { caminho: caminho || '/', parametros: Object.fromEntries(new URLSearchParams(consulta)) };
  }

  function hashDaLista(parametros) {
    const consulta = new URLSearchParams();
    for (const chave of FILTROS) {
      if (parametros[chave]) consulta.set(chave, parametros[chave]);
    }
    const texto = consulta.toString();
    return texto ? `#/?${texto}` : '#/';
  }

  function irParaLista(alteracoes) {
    const atuais = lerHash().parametros;
    const novos = { ...atuais, ...alteracoes };
    if (!('page' in alteracoes)) delete novos.page;
    location.hash = hashDaLista(novos);
  }

  function formatarData(iso) {
    if (!iso) return null;
    const [ano, mes, dia] = iso.split('-');
    return `${dia}/${mes}/${ano}`;
  }

  function juntarNomes(nomes) {
    if (nomes.length <= 1) return nomes.join('');
    return `${nomes.slice(0, -1).join(', ')} e ${nomes[nomes.length - 1]}`;
  }

  // -------------------------------------------------------- mensagens de estado

  function caixaDeErro(erro, aoTentarDeNovo) {
    let titulo = 'Algo deu errado';
    let texto = `A API respondeu com erro ${erro.status}. Tente de novo em instantes.`;
    if (erro.status === 0) {
      titulo = 'Não foi possível falar com a API';
      texto = 'O servidor do catálogo não respondeu. Verifique se ele está no ar e tente de novo.';
    } else if (erro.status === 429) {
      titulo = 'Muitas consultas em pouco tempo';
      texto = `A API pública limita o número de consultas por minuto. Aguarde ${erro.retryAfter || 'alguns'} segundos e tente de novo.`;
    } else if (erro.status === 404) {
      titulo = 'Não encontrado';
      texto = 'Este trabalho não existe ou ainda não está publicado.';
    }
    return el('section', { class: 'estado estado--erro', role: 'alert' },
      el('h2', {}, titulo),
      el('p', {}, texto),
      aoTentarDeNovo && el('button', { type: 'button', class: 'botao', onclick: aoTentarDeNovo }, 'Tentar de novo'),
    );
  }

  function caixaVazia(parametros) {
    const partes = [];
    if (parametros.search) partes.push(`“${parametros.search}”`);
    if (parametros.ano) partes.push(`ano ${parametros.ano}`);
    if (parametros.curso) partes.push(`curso ${parametros.curso}`);
    if (parametros.palavra_chave) partes.push(`palavra-chave “${parametros.palavra_chave}”`);
    return el('section', { class: 'estado' },
      el('h2', {}, 'Nenhum trabalho encontrado'),
      el('p', {}, partes.length
        ? `Não há trabalhos publicados para ${juntarNomes(partes)}. Tente outros termos ou remova algum filtro.`
        : 'Ainda não há trabalhos publicados no catálogo.'),
      partes.length > 0 && el('button', { type: 'button', class: 'botao', onclick: () => { location.hash = '#/'; } }, 'Limpar filtros'),
    );
  }

  function carregando() {
    return el('p', { class: 'carregando' }, 'Carregando…');
  }

  // -------------------------------------------------------------------- lista

  function montarEstruturaDaLista() {
    const busca = el('input', {
      type: 'search', id: 'f-search', name: 'search', class: 'campo',
      placeholder: 'Título, resumo, autor ou orientador', autocomplete: 'off',
    });
    let temporizador;
    busca.addEventListener('input', () => {
      clearTimeout(temporizador);
      temporizador = setTimeout(() => irParaLista({ search: busca.value.trim() }), ESPERA_DIGITACAO_MS);
    });

    const selecao = (id, rotulo, opcoes) => {
      const campo = el('select', { id: `f-${id}`, name: id, class: 'campo' },
        el('option', { value: '' }, rotulo), opcoes);
      campo.addEventListener('change', () => irParaLista({ [id]: campo.value }));
      return campo;
    };

    const formulario = el('form', { id: 'filtros', class: 'filtros', onsubmit: (evento) => {
      evento.preventDefault();
      clearTimeout(temporizador);
      irParaLista({ search: busca.value.trim() });
    } },
      el('label', { class: 'filtros__busca' }, el('span', { class: 'rotulo' }, 'Buscar'), busca),
      el('label', {}, el('span', { class: 'rotulo' }, 'Ano'), selecao('ano', 'Todos os anos', [])),
      el('label', {}, el('span', { class: 'rotulo' }, 'Curso'), selecao('curso', 'Todos os cursos', [])),
      el('label', {}, el('span', { class: 'rotulo' }, 'Ordenar por'), selecao('ordering', 'Mais recentes', [
        el('option', { value: 'ano' }, 'Mais antigos'),
        el('option', { value: 'titulo' }, 'Título (A–Z)'),
        el('option', { value: '-titulo' }, 'Título (Z–A)'),
      ])),
    );

    app.replaceChildren(
      formulario,
      el('div', { id: 'filtro-ativo' }),
      el('div', { id: 'resultados' }),
    );
    carregarOpcoesDeFiltro();
  }

  async function carregarOpcoesDeFiltro() {
    if (!opcoesDeFiltro) {
      try {
        opcoesDeFiltro = await apiGet('/estatisticas/');
      } catch (_) {
        return; // os selects ficam só com "Todos"; o erro principal aparece na lista
      }
    }
    const ano = document.getElementById('f-ano');
    const curso = document.getElementById('f-curso');
    if (!ano || !curso) return;
    if (ano.options.length === 1) {
      [...opcoesDeFiltro.por_ano].reverse().forEach((linha) => {
        ano.append(el('option', { value: linha.ano }, `${linha.ano} (${linha.total})`));
      });
    }
    if (curso.options.length === 1) {
      opcoesDeFiltro.por_curso.forEach((linha) => {
        curso.append(el('option', { value: linha.sigla }, `${linha.nome} (${linha.total})`));
      });
    }
    sincronizarFormulario(lerHash().parametros);
  }

  function sincronizarFormulario(parametros) {
    const busca = document.getElementById('f-search');
    if (busca && document.activeElement !== busca) busca.value = parametros.search || '';
    for (const id of ['ano', 'curso', 'ordering']) {
      const campo = document.getElementById(`f-${id}`);
      if (campo) campo.value = parametros[id] || '';
    }
    const ativo = document.getElementById('filtro-ativo');
    ativo.replaceChildren();
    if (parametros.palavra_chave) {
      ativo.append(el('p', { class: 'filtro-ativo' }, 'Palavra-chave: ',
        el('button', { type: 'button', class: 'chip chip--ativo', title: 'Remover filtro',
          onclick: () => irParaLista({ palavra_chave: '' }) }, `${parametros.palavra_chave} ✕`)));
    }
  }

  function chipsDePalavras(palavras) {
    return el('ul', { class: 'chips' }, palavras.map((termo) => el('li', {},
      el('a', { class: 'chip', href: hashDaLista({ palavra_chave: termo }) }, termo))));
  }

  function cartao(trabalho) {
    return el('article', { class: 'cartao' },
      el('h2', { class: 'cartao__titulo' }, el('a', { href: `#/trabalho/${trabalho.id}` }, trabalho.titulo)),
      el('p', { class: 'cartao__meta' }, `${trabalho.ano} · ${trabalho.curso.sigla} — ${trabalho.curso.nome}`),
      el('p', {}, el('strong', {}, trabalho.autores.length > 1 ? 'Autores: ' : 'Autor: '), juntarNomes(trabalho.autores)),
      el('p', {}, el('strong', {}, 'Orientação: '), trabalho.orientador),
      chipsDePalavras(trabalho.palavras_chave),
    );
  }

  function paginacao(dados, paginaAtual) {
    const totalPaginas = Math.max(1, Math.ceil(dados.count / TAMANHO_PAGINA));
    if (totalPaginas === 1) return null;
    return el('nav', { class: 'paginacao', 'aria-label': 'Paginação' },
      el('button', { type: 'button', class: 'botao', disabled: !dados.previous,
        onclick: () => irParaLista({ page: paginaAtual - 1 > 1 ? String(paginaAtual - 1) : '' }) }, '← Anterior'),
      el('span', {}, `Página ${paginaAtual} de ${totalPaginas}`),
      el('button', { type: 'button', class: 'botao', disabled: !dados.next,
        onclick: () => irParaLista({ page: String(paginaAtual + 1) }) }, 'Próxima →'),
    );
  }

  async function renderLista(parametros) {
    ultimaListaHash = hashDaLista(parametros);
    if (!document.getElementById('filtros')) montarEstruturaDaLista();
    sincronizarFormulario(parametros);

    const resultados = document.getElementById('resultados');
    resultados.replaceChildren(carregando());

    if (requisicaoAtual) requisicaoAtual.abort();
    const controle = new AbortController();
    requisicaoAtual = controle;

    const pagina = Number(parametros.page) || 1;
    try {
      const dados = await apiGet('/trabalhos/', {
        search: parametros.search,
        ano: parametros.ano,
        curso: parametros.curso,
        palavra_chave: parametros.palavra_chave,
        ordering: parametros.ordering,
        page: pagina > 1 ? pagina : '',
        tamanho: TAMANHO_PAGINA,
      }, controle.signal);

      if (dados.count === 0) {
        resultados.replaceChildren(caixaVazia(parametros));
        return;
      }
      resultados.replaceChildren(...[
        el('p', { class: 'contagem' }, dados.count === 1 ? '1 trabalho encontrado' : `${dados.count} trabalhos encontrados`),
        el('div', { class: 'lista' }, dados.results.map(cartao)),
        paginacao(dados, pagina),
      ].filter(Boolean));
      if (!opcoesDeFiltro) carregarOpcoesDeFiltro();
    } catch (erro) {
      if (erro.name === 'AbortError') return;
      if (erro.status === 404 && pagina > 1) {
        irParaLista({ page: '' });
        return;
      }
      resultados.replaceChildren(caixaDeErro(erro, () => renderLista(parametros)));
    }
  }

  // ------------------------------------------------------------------ detalhe

  function linha(rotulo, valor) {
    if (!valor) return null;
    return [el('dt', {}, rotulo), el('dd', {}, valor)];
  }

  function nomeComTitulacao(pessoa) {
    return pessoa ? `${pessoa.nome} (${pessoa.titulacao})` : null;
  }

  async function renderDetalhe(id) {
    if (requisicaoAtual) requisicaoAtual.abort();
    const voltar = el('a', { href: ultimaListaHash, class: 'voltar' }, '← Voltar à lista');
    app.replaceChildren(voltar, carregando());
    try {
      const t = await apiGet(`/trabalhos/${encodeURIComponent(id)}/`);
      document.title = `${t.titulo} — Catálogo de TCCs`;
      app.replaceChildren(voltar, el('article', { class: 'detalhe' },
        el('p', { class: 'cartao__meta' }, `${t.curso.nome} · ${t.ano}`),
        el('h1', {}, t.titulo),
        el('dl', { class: 'ficha' },
          linha(t.autores.length > 1 ? 'Autores' : 'Autor', juntarNomes(t.autores)),
          linha('Orientador', nomeComTitulacao(t.orientador)),
          linha('Coorientador', nomeComTitulacao(t.coorientador)),
          linha('Ano', String(t.ano)),
          linha('Defesa', formatarData(t.data_defesa)),
          linha('Curso', `${t.curso.nome} (${t.curso.sigla})`),
        ),
        el('h2', {}, 'Resumo'),
        el('p', { class: 'resumo' }, t.resumo),
        t.palavras_chave.length > 0 && [el('h2', {}, 'Palavras-chave'), chipsDePalavras(t.palavras_chave)],
        t.link_pdf && el('p', {}, el('a', { class: 'botao', href: t.link_pdf, target: '_blank', rel: 'noopener' }, 'Abrir PDF')),
      ));
    } catch (erro) {
      app.replaceChildren(voltar, caixaDeErro(erro, erro.status === 404 ? null : () => renderDetalhe(id)));
    }
  }

  // ------------------------------------------------------------ porta fechada
  //
  // Desafio B: login e cadastro de trabalho. O token fica no sessionStorage:
  // sobrevive a um recarregamento, some quando a aba é fechada e não passa para
  // outras abas. A justificativa da escolha está no README.

  const API_GESTAO = window.CONFIG.API_GESTAO;
  const CHAVE_SESSAO = 'catalogo.coordenacao';

  let sessaoAtual = lerSessao();
  let avisoDeEntrada = '';

  function lerSessao() {
    try { return JSON.parse(sessionStorage.getItem(CHAVE_SESSAO)); } catch (_) { return null; }
  }

  function salvarSessao(dados) {
    sessaoAtual = dados;
    try { sessionStorage.setItem(CHAVE_SESSAO, JSON.stringify(dados)); } catch (_) { /* sem armazenamento: vale até recarregar */ }
    atualizarNav();
  }

  function encerrarSessao() {
    sessaoAtual = null;
    try { sessionStorage.removeItem(CHAVE_SESSAO); } catch (_) { /* nada a apagar */ }
    atualizarNav();
  }

  // `token: null` envia a requisição sem token (é o caso do login: um token
  // velho no cabeçalho faria o DRF recusar o pedido antes de olhar a senha).
  async function apiGestao(metodo, caminho, { corpo, token = sessaoAtual && sessaoAtual.token } = {}) {
    const cabecalhos = { Accept: 'application/json' };
    if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json';
    if (token) cabecalhos.Authorization = `Token ${token}`;
    let resposta;
    try {
      resposta = await fetch(caminho.startsWith('http') ? caminho : API_GESTAO + caminho, {
        method: metodo,
        headers: cabecalhos,
        body: corpo === undefined ? undefined : JSON.stringify(corpo),
        signal: AbortSignal.timeout(TEMPO_LIMITE_MS),
      });
    } catch (_) {
      throw new ErroApi(0, 'Sem conexão com a API.');
    }
    let dados = null;
    try { dados = await resposta.json(); } catch (_) { /* corpo vazio ou não JSON */ }
    if (!resposta.ok) {
      const erro = new ErroApi(resposta.status, dados && dados.detail);
      erro.dados = dados;
      throw erro;
    }
    return dados;
  }

  async function todasAsPaginas(caminho) {
    let dados = await apiGestao('GET', `${caminho}?tamanho=50`);
    const itens = [...dados.results];
    while (dados.next) {
      dados = await apiGestao('GET', dados.next);
      itens.push(...dados.results);
    }
    return itens;
  }

  // Token recusado (401) ou conta fora da coordenação (403): volta ao login.
  function sessaoRecusada(erro) {
    if (erro.status !== 401 && erro.status !== 403) return false;
    encerrarSessao();
    avisoDeEntrada = erro.status === 401
      ? 'Sua sessão não é mais válida. Entre de novo.'
      : 'Esta conta não pertence à coordenação.';
    location.hash = '#/entrar';
    return true;
  }

  function atualizarNav() {
    const nav = document.getElementById('nav-coordenacao');
    if (!sessaoAtual) {
      nav.replaceChildren(el('a', { href: '#/entrar', class: 'topo__link' }, 'Área da coordenação'));
      return;
    }
    nav.replaceChildren(
      el('span', { class: 'topo__usuario' }, sessaoAtual.usuario),
      el('a', { href: '#/cadastrar', class: 'topo__link' }, 'Cadastrar trabalho'),
      el('button', { type: 'button', class: 'topo__link', onclick: () => {
        encerrarSessao();
        location.hash = '#/';
      } }, 'Sair'),
    );
  }

  function renderEntrar() {
    if (sessaoAtual) {
      location.hash = '#/cadastrar';
      return;
    }
    document.title = 'Entrar — Catálogo de TCCs';
    const usuario = el('input', { class: 'campo', name: 'username', autocomplete: 'username' });
    const senha = el('input', { class: 'campo', name: 'password', type: 'password', autocomplete: 'current-password' });
    const erro = el('p', { class: 'aviso aviso--erro', role: 'alert', hidden: !avisoDeEntrada }, avisoDeEntrada);
    const botao = el('button', { type: 'submit', class: 'botao' }, 'Entrar');
    avisoDeEntrada = '';

    const mostrarErro = (texto) => { erro.textContent = texto; erro.hidden = false; };

    app.replaceChildren(el('form', { class: 'formulario formulario--estreito', novalidate: true, onsubmit: async (evento) => {
      evento.preventDefault();
      erro.hidden = true;
      botao.disabled = true;
      const nome = usuario.value.trim();
      try {
        const { token } = await apiGestao('POST', '/token/', {
          corpo: { username: nome, password: senha.value },
          token: null,
        });
        // O token é devolvido para qualquer conta; só a coordenação usa a porta
        // fechada. Uma consulta barata confirma isso antes de guardar o token.
        await apiGestao('GET', '/cursos/?tamanho=1', { token });
        salvarSessao({ token, usuario: nome });
        location.hash = '#/cadastrar';
      } catch (e) {
        if (e.status === 0) mostrarErro('Não foi possível falar com a API. Verifique se ela está no ar.');
        else if (e.status === 400) mostrarErro('Usuário ou senha incorretos.');
        else if (e.status === 403) mostrarErro('Esta conta não pertence à coordenação.');
        else mostrarErro(`A API respondeu com erro ${e.status}.`);
      } finally {
        senha.value = '';
        botao.disabled = false;
      }
    } },
      el('h1', {}, 'Área da coordenação'),
      el('p', { class: 'cartao__meta' }, 'Entre com a conta da coordenação para cadastrar trabalhos.'),
      erro,
      el('label', { class: 'formulario__campo' }, el('span', { class: 'rotulo' }, 'Usuário'), usuario),
      el('label', { class: 'formulario__campo' }, el('span', { class: 'rotulo' }, 'Senha'), senha),
      el('p', {}, botao),
    ));
    usuario.focus();
  }

  async function renderCadastrar() {
    if (!sessaoAtual) {
      location.hash = '#/entrar';
      return;
    }
    document.title = 'Cadastrar trabalho — Catálogo de TCCs';
    app.replaceChildren(carregando());
    let apoio;
    try {
      const [cursos, orientadores, autores, palavras] = await Promise.all(
        ['/cursos/', '/orientadores/', '/autores/', '/palavras-chave/'].map(todasAsPaginas),
      );
      apoio = { cursos, orientadores, autores, palavras };
    } catch (erro) {
      if (sessaoRecusada(erro)) return;
      if (lerHash().caminho === '/cadastrar') app.replaceChildren(caixaDeErro(erro, renderCadastrar));
      return;
    }
    if (lerHash().caminho !== '/cadastrar') return; // o usuário saiu da tela enquanto carregava
    app.replaceChildren(formularioDeTrabalho(apoio));
  }

  function formularioDeTrabalho({ cursos, orientadores, autores, palavras }) {
    const opcoes = (lista, texto) => lista.map((item) => el('option', { value: item.id }, texto(item)));
    const selecao = (nome, vazia, lista, texto, multiplo) => el('select',
      { class: 'campo', name: nome, multiple: multiplo, size: multiplo ? 8 : null },
      vazia && el('option', { value: '' }, vazia), opcoes(lista, texto));
    const campo = (nome, rotulo, controle, dica, largo) => el('label',
      { class: largo ? 'formulario__campo formulario__campo--largo' : 'formulario__campo' },
      el('span', { class: 'rotulo' }, rotulo),
      controle,
      dica && el('span', { class: 'dica' }, dica),
      el('span', { class: 'erro-campo', 'data-erro': nome }));

    const geral = el('div', { class: 'aviso aviso--erro', role: 'alert', hidden: true });
    const botao = el('button', { type: 'submit', class: 'botao' }, 'Cadastrar');

    // Sem validação no navegador (novalidate e nenhum `required`): quem decide é
    // a API, e as mensagens que aparecem embaixo de cada campo são as dela.
    const form = el('form', { class: 'formulario', novalidate: true, onsubmit: async (evento) => {
      evento.preventDefault();
      geral.hidden = true;
      form.querySelectorAll('[data-erro]').forEach((alvo) => { alvo.textContent = ''; });
      botao.disabled = true;
      try {
        const trabalho = await apiGestao('POST', '/trabalhos/', { corpo: lerFormulario(form) });
        app.replaceChildren(cadastroConcluido(trabalho));
      } catch (erro) {
        if (sessaoRecusada(erro)) return;
        mostrarErrosDoCadastro(form, geral, erro);
      } finally {
        botao.disabled = false;
      }
    } },
      el('h1', {}, 'Cadastrar trabalho'),
      el('p', { class: 'cartao__meta' }, `Quem cadastrou fica registrado pelo token: ${sessaoAtual.usuario}.`),
      geral,
      el('div', { class: 'formulario__grade' },
        campo('titulo', 'Título', el('input', { class: 'campo', name: 'titulo' }), null, true),
        campo('resumo', 'Resumo', el('textarea', { class: 'campo', name: 'resumo', rows: 6 }), null, true),
        campo('ano', 'Ano', el('input', { class: 'campo', name: 'ano', type: 'number', value: new Date().getFullYear() })),
        campo('situacao', 'Situação', el('select', { class: 'campo', name: 'situacao' },
          el('option', { value: 'em_andamento' }, 'Em andamento'),
          el('option', { value: 'defendido' }, 'Defendido'),
          el('option', { value: 'publicado' }, 'Publicado'))),
        campo('data_defesa', 'Data da defesa', el('input', { class: 'campo', name: 'data_defesa', type: 'date' })),
        campo('nota', 'Nota', el('input', { class: 'campo', name: 'nota', type: 'number', step: '0.01', min: 0, max: 10 })),
        campo('curso', 'Curso', selecao('curso', 'Selecione…', cursos, (c) => `${c.sigla} — ${c.nome}`)),
        campo('link_pdf', 'Link do PDF', el('input', { class: 'campo', name: 'link_pdf', type: 'url', placeholder: 'https://' })),
        campo('orientador', 'Orientador', selecao('orientador', 'Selecione…', orientadores, (o) => o.nome)),
        campo('coorientador', 'Coorientador', selecao('coorientador', 'Nenhum', orientadores, (o) => o.nome)),
        campo('autores', 'Autores', selecao('autores', null, autores, (a) => a.nome, true),
          'Um ou dois. Segure Ctrl (⌘ no Mac) para escolher mais de um.'),
        campo('palavras_chave', 'Palavras-chave', selecao('palavras_chave', null, palavras, (p) => p.termo, true),
          'Opcional. Segure Ctrl (⌘ no Mac) para escolher várias.'),
      ),
      el('p', {}, botao),
    );
    return form;
  }

  function lerFormulario(form) {
    const valor = (nome) => form.elements[nome].value.trim();
    const numero = (nome) => (valor(nome) === '' ? null : Number(valor(nome)));
    const varios = (nome) => [...form.elements[nome].selectedOptions].map((opcao) => Number(opcao.value));
    // `cadastrado_por` não é enviado: a API o tira do token.
    return {
      titulo: valor('titulo'),
      resumo: valor('resumo'),
      ano: numero('ano'),
      situacao: valor('situacao'),
      data_defesa: valor('data_defesa') || null,
      nota: valor('nota') || null,
      link_pdf: valor('link_pdf'),
      curso: numero('curso'),
      orientador: numero('orientador'),
      coorientador: numero('coorientador'),
      autores: varios('autores'),
      palavras_chave: varios('palavras_chave'),
    };
  }

  function mostrarErrosDoCadastro(form, geral, erro) {
    const semCampo = [];
    if (erro.status === 400 && erro.dados && typeof erro.dados === 'object') {
      for (const [nome, mensagens] of Object.entries(erro.dados)) {
        const texto = [].concat(mensagens).join(' ');
        const alvo = form.querySelector(`[data-erro="${nome}"]`);
        if (alvo) alvo.textContent = texto;
        else semCampo.push(texto);
      }
    } else if (erro.status === 0) {
      semCampo.push('Não foi possível falar com a API. Verifique se ela está no ar e tente de novo.');
    } else {
      semCampo.push(`A API respondeu com erro ${erro.status}.${erro.message ? ` ${erro.message}` : ''}`);
    }
    if (semCampo.length) {
      geral.textContent = semCampo.join(' ');
      geral.hidden = false;
    }
    const primeiro = geral.hidden ? form.querySelector('[data-erro]:not(:empty)') : geral;
    if (primeiro) primeiro.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function cadastroConcluido(trabalho) {
    const publicado = trabalho.situacao === 'publicado';
    return el('section', { class: 'estado estado--ok' },
      el('h2', {}, 'Trabalho cadastrado'),
      el('p', {}, `“${trabalho.titulo}” foi gravado com o número ${trabalho.id}, cadastrado por ${trabalho.cadastrado_por}.`),
      el('p', {}, publicado
        ? 'Como está publicado, ele já aparece na porta aberta.'
        : 'Como não está publicado, ele só aparece na porta aberta quando a situação mudar para “publicado”.'),
      el('p', { class: 'acoes' },
        publicado && el('a', { class: 'botao', href: `#/trabalho/${trabalho.id}` }, 'Ver na porta aberta'),
        el('button', { type: 'button', class: 'botao botao--secundario', onclick: renderCadastrar }, 'Cadastrar outro'),
      ),
    );
  }

  // ------------------------------------------------------------------ rotas

  function rotear() {
    const { caminho, parametros } = lerHash();
    if (caminho === '/entrar' || caminho === '/cadastrar') {
      if (requisicaoAtual) requisicaoAtual.abort();
      if (caminho === '/entrar') renderEntrar();
      else renderCadastrar();
      return;
    }
    const detalhe = caminho.match(/^\/trabalho\/(\d+)$/);
    if (detalhe) {
      renderDetalhe(detalhe[1]);
      return;
    }
    document.title = 'Catálogo de TCCs — IFPB';
    renderLista(parametros);
  }

  window.addEventListener('hashchange', rotear);
  atualizarNav();
  rotear();
})();
