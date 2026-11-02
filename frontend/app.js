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
        el('h2', {}, 'Palavras-chave'),
        chipsDePalavras(t.palavras_chave),
        t.link_pdf && el('p', {}, el('a', { class: 'botao', href: t.link_pdf, target: '_blank', rel: 'noopener' }, 'Abrir PDF')),
      ));
    } catch (erro) {
      app.replaceChildren(voltar, caixaDeErro(erro, erro.status === 404 ? null : () => renderDetalhe(id)));
    }
  }

  // ------------------------------------------------------------------ rotas

  function rotear() {
    const { caminho, parametros } = lerHash();
    const detalhe = caminho.match(/^\/trabalho\/(\d+)$/);
    if (detalhe) {
      renderDetalhe(detalhe[1]);
      return;
    }
    document.title = 'Catálogo de TCCs — IFPB';
    renderLista(parametros);
  }

  window.addEventListener('hashchange', rotear);
  rotear();
})();
