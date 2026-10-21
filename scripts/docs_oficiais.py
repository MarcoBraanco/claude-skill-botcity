"""Confere e atualiza a skill a partir da documentacao oficial da BotCity.

Le as paginas oficiais do Maestro SDK (Python) e da Maestro API,
extrai a parte estrutural de cada uma (assinaturas e parametros dos
metodos, trechos de codigo Python dos guias e as operacoes da spec
OpenAPI que a pagina da API embute) e compara com o ultimo retrato
guardado em references/docs_snapshot.json.

O hash e calculado sobre essa estrutura, nao sobre o HTML: mudanca de
menu lateral, rodape ou "What's new" nao conta como mudanca de doc.

Se uma URL deixar de existir, o script procura a pagina no sitemap do
site pelo slug e pelo titulo (h1) e grava a URL nova em
references/fontes_docs.json.

Uso:
    python docs_oficiais.py verificar   (check)   -> 0 igual, 10 mudou,
                                                     2 falha de rede
    python docs_oficiais.py atualizar   (update)  -> grava referencias
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sys
from urllib.parse import urljoin

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botcity_api import PASTA_SKILL  # noqa: E402


PASTA_REFERENCIAS = os.path.join(PASTA_SKILL, 'references')
CAMINHO_FONTES = os.path.join(PASTA_REFERENCIAS, 'fontes_docs.json')
CAMINHO_SNAPSHOT = os.path.join(PASTA_REFERENCIAS, 'docs_snapshot.json')
CAMINHO_SDK_MD = os.path.join(PASTA_REFERENCIAS, 'maestro_sdk.md')
CAMINHO_SPEC = os.path.join(PASTA_REFERENCIAS, 'openapi.json')

TIMEOUT = 60
CABECALHOS = {'User-Agent': 'botcity-skill-docs-check/1.0'}

SAIDA_IGUAL = 0
SAIDA_MUDOU = 10
SAIDA_FALHA = 2

METODOS_HTTP = ('get', 'post', 'put', 'patch', 'delete')

PADRAO_TITULO = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
PADRAO_OBJETO = re.compile(
    r'<h(\d) id="(botcity\.[\w.]+)" class="doc doc-heading">\s*'
    r'(?:<code[^>]*>(.*?)</code>)?', re.S)
PADRAO_CODIGO = re.compile(
    r'<div class="language-(\w+) highlight"><pre>(.*?)</pre>', re.S)
PADRAO_SECAO = re.compile(r'<h([23])[^>]*>(.*?)</h\1>', re.S)
PADRAO_IFRAME = re.compile(r'class="swagger-ui-iframe"[^>]*src="([^"]+)"')
PADRAO_URL_SPEC = re.compile(r'var\s+url\s*=\s*"([^"]+)"')


class FalhaDeRede(Exception):
    """Indica que uma fonte oficial nao pode ser lida."""


# ---------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------


def agora():
    """Devolve o instante atual em ISO 8601 (UTC, sem microssegundos).

    Returns:
        str: Data e hora, ex.: '2026-10-21T13:00:00Z'.
    """
    instante = datetime.datetime.now(datetime.timezone.utc)

    return instante.replace(microsecond=0).isoformat().replace(
        '+00:00', 'Z')


def texto_limpo(fragmento):
    """Remove tags e entidades HTML de um trecho.

    Args:
        fragmento (str): HTML.

    Returns:
        str: Texto puro, com espacos normalizados.
    """
    texto = html.unescape(re.sub(r'<[^>]+>', '', fragmento or ''))

    return re.sub(r'\s+', ' ', texto.replace('¶', '')).strip()


def hash_de(objeto):
    """Calcula o hash estavel de um objeto JSON.

    Args:
        objeto (object): Valor serializavel.

    Returns:
        str: SHA-256 hexadecimal (16 primeiros caracteres).
    """
    bruto = json.dumps(objeto, sort_keys=True, ensure_ascii=False)

    return hashlib.sha256(bruto.encode('utf-8')).hexdigest()[:16]


def ler_json(caminho, padrao=None):
    """Le um JSON do disco, tolerando arquivo ausente.

    Args:
        caminho (str): Caminho do arquivo.
        padrao (object): Valor devolvido se o arquivo nao existir.

    Returns:
        object: Conteudo decodificado ou o padrao.
    """
    if not os.path.isfile(caminho):
        return padrao

    with open(caminho, 'r', encoding='utf-8') as origem:
        return json.load(origem)


def gravar_json(caminho, dados):
    """Grava um JSON legivel em disco.

    Args:
        caminho (str): Caminho de destino.
        dados (object): Conteudo.
    """
    with open(caminho, 'w', encoding='utf-8') as destino:
        json.dump(dados, destino, indent=2, ensure_ascii=False)
        destino.write('\n')


def baixar(url):
    """Baixa uma URL e devolve a resposta.

    Args:
        url (str): Endereco.

    Returns:
        requests.Response: Resposta (qualquer status).

    Raises:
        FalhaDeRede: Se nao houver comunicacao.
    """
    try:
        return requests.get(url, headers=CABECALHOS, timeout=TIMEOUT)
    except requests.RequestException as erro:
        raise FalhaDeRede('{0}: {1}'.format(url, erro))


def titulo_da_pagina(conteudo):
    """Extrai o h1 do artigo principal de uma pagina MkDocs.

    Args:
        conteudo (str): HTML da pagina.

    Returns:
        str: Titulo, ou texto vazio.
    """
    inicio = conteudo.find('<article')
    achado = PADRAO_TITULO.search(conteudo[max(inicio, 0):])

    return texto_limpo(achado.group(1)) if achado else ''


# ---------------------------------------------------------------------
# Localizacao das paginas (com redescoberta pelo sitemap)
# ---------------------------------------------------------------------


def pagina_valida(fonte, resposta):
    """Diz se a resposta e mesmo a pagina esperada.

    Args:
        fonte (dict): Entrada de fontes_docs.json.
        resposta (requests.Response): Resposta obtida.

    Returns:
        bool: True se o status for 200 e o h1 bater com o titulo.
    """
    if resposta.status_code != 200:
        return False

    titulo = titulo_da_pagina(resposta.text).lower()

    return titulo == fonte['titulo'].lower()


def urls_do_sitemap(fontes):
    """Lista as URLs em ingles do sitemap oficial.

    Args:
        fontes (dict): Conteudo de fontes_docs.json.

    Returns:
        list: URLs, sem as traducoes /pt/ e /es/.

    Raises:
        FalhaDeRede: Se o sitemap nao puder ser lido.
    """
    resposta = baixar(fontes['sitemap'])

    if resposta.status_code != 200:
        raise FalhaDeRede('sitemap respondeu HTTP {0}'.format(
            resposta.status_code))

    urls = re.findall(r'<loc>([^<]+)</loc>', resposta.text)

    return [url for url in urls
            if not re.search(r'/(pt|es)/', url[len(fontes['site']):])]


def redescobrir(nome, fonte, fontes):
    """Procura no sitemap a URL nova de uma pagina que mudou de lugar.

    Prioriza URLs de maestro cujo ultimo trecho e o slug esperado e
    confirma pelo titulo (h1) da pagina.

    Args:
        nome (str): Chave da pagina em fontes_docs.json.
        fonte (dict): Entrada da pagina.
        fontes (dict): Conteudo de fontes_docs.json.

    Returns:
        tuple: (url, resposta) da pagina reencontrada, ou (None, None).
    """
    candidatas = []

    for url in urls_do_sitemap(fontes):
        partes = [p for p in url.rstrip('/').split('/') if p]
        if not partes:
            continue
        pontos = 0
        if partes[-1] == fonte['slug']:
            pontos += 2
        if 'maestro' in url:
            pontos += 1
        if 'sdk' in url and fonte['tipo'] != 'swagger':
            pontos += 1
        if 'api' in url and fonte['tipo'] == 'swagger':
            pontos += 1
        if pontos >= 2:
            candidatas.append((pontos, url))

    for _, url in sorted(candidatas, reverse=True)[:15]:
        resposta = baixar(url)
        if pagina_valida(fonte, resposta):
            print('Pagina "{0}" mudou de endereco: {1}'.format(nome, url))
            return url, resposta

    return None, None


def obter_pagina(nome, fonte, fontes):
    """Baixa uma pagina oficial, redescobrindo a URL se preciso.

    Args:
        nome (str): Chave da pagina.
        fonte (dict): Entrada da pagina (a URL pode ser atualizada).
        fontes (dict): Conteudo de fontes_docs.json.

    Returns:
        str: HTML da pagina.

    Raises:
        FalhaDeRede: Se a pagina nao for encontrada nem no sitemap.
    """
    resposta = baixar(fonte['url'])

    if pagina_valida(fonte, resposta):
        return resposta.text

    url, resposta = redescobrir(nome, fonte, fontes)

    if not url:
        raise FalhaDeRede(
            'pagina "{0}" ({1}) nao encontrada, nem pelo sitemap. '
            'Atualize a URL em {2}.'.format(nome, fonte['url'],
                                            CAMINHO_FONTES))

    fonte['url'] = url
    fontes['_alterado'] = True

    return resposta.text


# ---------------------------------------------------------------------
# Extracao da estrutura
# ---------------------------------------------------------------------


def tabela_apos(bloco, rotulo):
    """Le a tabela que vem depois de "<strong>rotulo:</strong>".

    Args:
        bloco (str): HTML do objeto documentado.
        rotulo (str): 'Parameters' ou 'Returns'.

    Returns:
        list: Linhas, cada uma lista de celulas em texto.
    """
    achado = re.search(r'<strong>{0}:</strong></p>\s*<table>(.*?)</table>'
                       .format(rotulo), bloco, re.S)

    if not achado:
        return []

    corpo = achado.group(1).split('<tbody>')[-1]

    return [[texto_limpo(celula) for celula in
             re.findall(r'<td>(.*?)</td>', linha, re.S)]
            for linha in re.findall(r'<tr>(.*?)</tr>', corpo, re.S)]


def extrair_referencia(conteudo):
    """Extrai classes e metodos de uma pagina mkdocstrings.

    Args:
        conteudo (str): HTML da pagina de referencia do SDK.

    Returns:
        dict: {nome_qualificado: {assinatura, resumo, parametros,
            retorno}}.
    """
    achados = list(PADRAO_OBJETO.finditer(conteudo))
    objetos = {}

    for posicao, achado in enumerate(achados):
        fim = (achados[posicao + 1].start() if posicao + 1 < len(achados)
               else len(conteudo))
        bloco = conteudo[achado.end():fim]
        nome = achado.group(2)
        resumo = re.search(r'<p>(.*?)</p>', bloco, re.S)
        parametros = [
            {'nome': linha[0], 'tipo': linha[1],
             'padrao': linha[3] if len(linha) > 3 else '',
             'descricao': linha[2] if len(linha) > 2 else ''}
            for linha in tabela_apos(bloco, 'Parameters') if linha]
        retorno = tabela_apos(bloco, 'Returns')
        assinatura = texto_limpo(achado.group(3))

        if achado.group(1) == '2':
            tipo = 'classe'
        elif '(' in assinatura:
            tipo = 'metodo'
        else:
            tipo = 'propriedade'

        objetos[nome] = {
            'tipo': tipo,
            'assinatura': assinatura,
            'resumo': texto_limpo(resumo.group(1)) if resumo else '',
            'parametros': parametros,
            'retorno': retorno[0][0] if retorno and retorno[0] else '',
        }

    return objetos


def extrair_guia(conteudo):
    """Extrai secoes e trechos Python de uma pagina de guia.

    Args:
        conteudo (str): HTML da pagina.

    Returns:
        list: [{secao, codigo}] na ordem da pagina, so Python.
    """
    inicio = conteudo.find('<article')
    artigo = conteudo[max(inicio, 0):conteudo.find('</article>')]
    marcas = [(m.start(), 'secao', texto_limpo(m.group(2)))
              for m in PADRAO_SECAO.finditer(artigo)]
    marcas += [(m.start(), m.group(1),
                html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip())
               for m in PADRAO_CODIGO.finditer(artigo)]
    secao = ''
    trechos = []

    for _, tipo, valor in sorted(marcas):
        if tipo == 'secao':
            secao = valor
        elif tipo == 'python':
            trechos.append({'secao': secao, 'codigo': valor})

    return trechos


def obter_spec(conteudo_api, fontes):
    """Segue o Swagger embutido na pagina da API ate a spec OpenAPI.

    Args:
        conteudo_api (str): HTML da pagina Full API.
        fontes (dict): Conteudo de fontes_docs.json (spec_url pode ser
            atualizada).

    Returns:
        dict: Spec OpenAPI.

    Raises:
        FalhaDeRede: Se a spec nao puder ser baixada.
    """
    url_spec = fontes.get('spec_url')
    iframe = PADRAO_IFRAME.search(conteudo_api)

    if iframe:
        url_iframe = urljoin(fontes['paginas']['api']['url'],
                             iframe.group(1))
        resposta = baixar(url_iframe)
        achado = PADRAO_URL_SPEC.search(resposta.text)
        if resposta.status_code == 200 and achado:
            if achado.group(1) != url_spec:
                print('A spec oficial mudou de endereco: {0}'.format(
                    achado.group(1)))
                fontes['spec_url'] = achado.group(1)
                fontes['_alterado'] = True
            url_spec = achado.group(1)

    resposta = baixar(url_spec)

    if resposta.status_code != 200:
        raise FalhaDeRede('spec {0} respondeu HTTP {1}'.format(
            url_spec, resposta.status_code))

    return resposta.json()


def normalizar_no(no):
    """Ordena as alternativas oneOf/anyOf/allOf de um no da spec.

    O gerador da spec oficial (springdoc) emite essas listas em ordem
    variavel entre uma publicacao e outra; sem ordenar, toda operacao
    pareceria alterada a cada verificacao.

    Args:
        no (object): No da spec.

    Returns:
        object: Copia normalizada.
    """
    if isinstance(no, dict):
        copia = {chave: normalizar_no(valor) for chave, valor in no.items()}
        for chave in ('oneOf', 'anyOf', 'allOf'):
            if isinstance(copia.get(chave), list):
                copia[chave] = sorted(
                    copia[chave], key=lambda item: json.dumps(
                        item, sort_keys=True))
        return copia

    if isinstance(no, list):
        return [normalizar_no(item) for item in no]

    return no


def operacoes_da_spec(spec):
    """Resume cada operacao da spec em um hash.

    Args:
        spec (dict): Spec OpenAPI.

    Returns:
        dict: {"METODO caminho": hash da operacao}.
    """
    return {'{0} {1}'.format(metodo.upper(), caminho):
            hash_de(normalizar_no(operacao))
            for caminho, item in spec.get('paths', {}).items()
            for metodo, operacao in item.items() if metodo in METODOS_HTTP}


def esquemas_da_spec(spec):
    """Resume cada schema (DTO) da spec em um hash.

    Args:
        spec (dict): Spec OpenAPI.

    Returns:
        dict: {nome do schema: hash}.
    """
    esquemas = (spec.get('components') or {}).get('schemas') or {}

    return {nome: hash_de(normalizar_no(esquema))
            for nome, esquema in esquemas.items()}


def versao_pypi(fontes):
    """Consulta a versao atual do botcity-maestro-sdk no PyPI.

    Args:
        fontes (dict): Conteudo de fontes_docs.json.

    Returns:
        str: Versao, ou None se o PyPI nao responder.
    """
    try:
        resposta = baixar(fontes['pypi'])
        return resposta.json()['info']['version']
    except (FalhaDeRede, ValueError, KeyError):
        return None


def coletar():
    """Le todas as fontes oficiais e monta o retrato atual.

    Returns:
        tuple: (retrato, spec, fontes) onde retrato tem o mesmo
            formato de docs_snapshot.json.

    Raises:
        FalhaDeRede: Se alguma fonte essencial nao puder ser lida.
    """
    fontes = ler_json(CAMINHO_FONTES)
    paginas = {}
    spec = None

    for nome, fonte in fontes['paginas'].items():
        conteudo = obter_pagina(nome, fonte, fontes)

        if fonte['tipo'] == 'referencia':
            estrutura = extrair_referencia(conteudo)
        elif fonte['tipo'] == 'guia':
            estrutura = extrair_guia(conteudo)
        else:
            spec = obter_spec(conteudo, fontes)
            estrutura = {'spec_url': fontes['spec_url']}

        paginas[nome] = {'url': fonte['url'], 'tipo': fonte['tipo'],
                         'hash': hash_de(estrutura),
                         'estrutura': estrutura}

    operacoes = operacoes_da_spec(spec or {})
    retrato = {
        'sdk_versao_pypi': versao_pypi(fontes),
        'paginas': paginas,
        'spec': {'url': fontes.get('spec_url'),
                 'hash': hash_de(operacoes),
                 'operacoes': operacoes,
                 'esquemas': esquemas_da_spec(spec or {})},
    }

    return retrato, spec, fontes


# ---------------------------------------------------------------------
# Comparacao
# ---------------------------------------------------------------------


def chave_de_estrutura(objeto):
    """Resume um metodo documentado para exibir numa diferenca.

    Args:
        objeto (dict): Entrada de extrair_referencia.

    Returns:
        str: Assinatura e os nomes/tipos dos parametros.
    """
    parametros = ', '.join('{0}:{1}'.format(p['nome'], p['tipo'])
                           for p in objeto.get('parametros', []))

    return '{0} [{1}]'.format(objeto.get('assinatura', ''), parametros)


def comparar(anterior, atual):
    """Lista as diferencas entre dois retratos.

    Args:
        anterior (dict): Snapshot gravado (ou vazio).
        atual (dict): Retrato recem coletado.

    Returns:
        list: Linhas legiveis; vazia se nada mudou.
    """
    diferencas = []
    anterior = anterior or {}

    if anterior.get('sdk_versao_pypi') != atual.get('sdk_versao_pypi'):
        diferencas.append('SDK no PyPI: {0} -> {1}'.format(
            anterior.get('sdk_versao_pypi'), atual.get('sdk_versao_pypi')))

    paginas_antes = anterior.get('paginas', {})

    for nome, pagina in atual['paginas'].items():
        antes = paginas_antes.get(nome)
        if not antes:
            diferencas.append('Pagina nova acompanhada: {0}'.format(nome))
            continue
        if antes['hash'] == pagina['hash']:
            continue
        if pagina['tipo'] == 'referencia':
            velho, novo = antes['estrutura'], pagina['estrutura']
            for metodo in sorted(set(novo) - set(velho)):
                diferencas.append('SDK + {0}: {1}'.format(
                    metodo, novo[metodo]['assinatura']))
            for metodo in sorted(set(velho) - set(novo)):
                diferencas.append('SDK - {0} (removido)'.format(metodo))
            for metodo in sorted(set(velho) & set(novo)):
                if velho[metodo] != novo[metodo]:
                    diferencas.append('SDK ~ {0}: {1} -> {2}'.format(
                        metodo, chave_de_estrutura(velho[metodo]),
                        chave_de_estrutura(novo[metodo])))
        elif pagina['tipo'] == 'guia':
            diferencas.append('Guia "{0}" mudou ({1} trechos Python '
                              'agora, {2} antes)'.format(
                                  nome, len(pagina['estrutura']),
                                  len(antes['estrutura'])))
        else:
            diferencas.append('Endereco da spec: {0} -> {1}'.format(
                antes['estrutura'].get('spec_url'),
                pagina['estrutura'].get('spec_url')))

    ops_antes = anterior.get('spec', {}).get('operacoes', {})
    ops_agora = atual['spec']['operacoes']

    if ops_antes != ops_agora:
        novas = sorted(set(ops_agora) - set(ops_antes))
        removidas = sorted(set(ops_antes) - set(ops_agora))
        alteradas = sorted(op for op in set(ops_antes) & set(ops_agora)
                           if ops_antes[op] != ops_agora[op])
        diferencas.append('API: {0} operacoes ({1} antes): {2} novas, {3} '
                          'removidas, {4} alteradas'.format(
                              len(ops_agora), len(ops_antes), len(novas),
                              len(removidas), len(alteradas)))
        diferencas += ['API + ' + op for op in novas]
        diferencas += ['API - ' + op for op in removidas]
        diferencas += ['API ~ ' + op for op in alteradas]

    esquemas_antes = anterior.get('spec', {}).get('esquemas')
    esquemas_agora = atual['spec'].get('esquemas', {})

    if esquemas_antes is not None and esquemas_antes != esquemas_agora:
        for nome in sorted(set(esquemas_antes) | set(esquemas_agora)):
            if esquemas_antes.get(nome) != esquemas_agora.get(nome):
                marca = ('+' if nome not in esquemas_antes else
                         '-' if nome not in esquemas_agora else '~')
                diferencas.append('Schema {0} {1}'.format(marca, nome))

    return diferencas


# ---------------------------------------------------------------------
# Geracao das referencias
# ---------------------------------------------------------------------


def gerar_sdk_md(retrato):
    """Monta o references/maestro_sdk.md a partir do retrato.

    Args:
        retrato (dict): Retrato coletado.

    Returns:
        str: Conteudo Markdown.
    """
    paginas = retrato['paginas']
    referencia = paginas['sdk_python']['estrutura']
    linhas = [
        '# BotCity Maestro SDK (Python) - referencia',
        '',
        'Gerado por `scripts/docs_oficiais.py atualizar` a partir da '
        'documentacao oficial em {0}. Nao edite a mao.'.format(agora()),
        '',
        '- Pacote: `botcity-maestro-sdk` (PyPI: {0})'.format(
            retrato.get('sdk_versao_pypi') or '?'),
        '- Fonte: {0}'.format(paginas['sdk_python']['url']),
        '',
    ]
    for nome, objeto in referencia.items():
        if objeto['tipo'] == 'classe':
            linhas += ['## `{0}`'.format(objeto['assinatura'] or nome), '']
            if objeto['resumo']:
                linhas += [objeto['resumo'], '']
            continue
        if objeto['tipo'] == 'propriedade':
            linhas += ['- propriedade `{0}`: {1}'.format(
                objeto['assinatura'], objeto['resumo']), '']
            continue
        linhas += ['### `{0}`'.format(objeto['assinatura']), '']
        if objeto['resumo']:
            linhas += [objeto['resumo'], '']
        if objeto['parametros']:
            linhas += ['| Parametro | Tipo | Padrao | Descricao |',
                       '|---|---|---|---|']
            for parametro in objeto['parametros']:
                linhas.append('| `{0}` | {1} | {2} | {3} |'.format(
                    parametro['nome'], parametro['tipo'],
                    parametro['padrao'],
                    parametro['descricao'].replace('|', '/')))
            linhas.append('')
        if objeto['retorno']:
            linhas += ['Retorna: `{0}`'.format(objeto['retorno']), '']

    linhas += ['---', '', '# Guias oficiais (trechos Python)', '']

    for nome, pagina in paginas.items():
        if pagina['tipo'] != 'guia':
            continue
        linhas += ['## {0}'.format(nome), '', 'Fonte: ' + pagina['url'], '']
        for trecho in pagina['estrutura']:
            linhas += ['**{0}**'.format(trecho['secao']), '', '```python',
                       trecho['codigo'], '```', '']

    return '\n'.join(linhas)


def snapshot_atual():
    """Le o snapshot gravado.

    Returns:
        dict: Conteudo de docs_snapshot.json, ou vazio.
    """
    return ler_json(CAMINHO_SNAPSHOT, {})


def atualizar(retrato, spec, fontes):
    """Grava spec, indice, maestro_sdk.md, fontes e snapshot.

    Args:
        retrato (dict): Retrato coletado.
        spec (dict): Spec OpenAPI oficial.
        fontes (dict): Fontes (com URLs possivelmente atualizadas).
    """
    from botcity import gerar_indice

    with open(CAMINHO_SPEC, 'w', encoding='utf-8') as destino:
        json.dump(spec, destino, ensure_ascii=False, separators=(',', ':'))

    gerar_indice()

    with open(CAMINHO_SDK_MD, 'w', encoding='utf-8') as destino:
        destino.write(gerar_sdk_md(retrato))

    fontes.pop('_alterado', None)
    gravar_json(CAMINHO_FONTES, fontes)

    retrato['atualizado_em'] = agora()
    retrato['verificado_em'] = retrato['atualizado_em']
    gravar_json(CAMINHO_SNAPSHOT, retrato)


def verificar(atualizar_se_mudou=False):
    """Compara a doc oficial com o snapshot e opcionalmente atualiza.

    Args:
        atualizar_se_mudou (bool): Se True grava as referencias novas
            quando houver diferenca.

    Returns:
        tuple: (codigo, diferencas) com codigo SAIDA_IGUAL, SAIDA_MUDOU
            ou SAIDA_FALHA.
    """
    try:
        retrato, spec, fontes = coletar()
    except FalhaDeRede as erro:
        return SAIDA_FALHA, ['Falha ao ler a documentacao oficial: '
                             '{0}'.format(erro)]

    anterior = snapshot_atual()

    if not anterior.get('spec') and os.path.isfile(CAMINHO_SPEC):
        # Sem retrato anterior, a referencia e a spec que veio com a
        # skill; assim a primeira verificacao ja mostra o que mudou.
        local = ler_json(CAMINHO_SPEC, {})
        anterior['spec'] = {'operacoes': operacoes_da_spec(local),
                            'esquemas': esquemas_da_spec(local)}

    diferencas = comparar(anterior, retrato)

    if not diferencas:
        anterior['verificado_em'] = agora()
        gravar_json(CAMINHO_SNAPSHOT, anterior)
        if fontes.pop('_alterado', None):
            gravar_json(CAMINHO_FONTES, fontes)
        return SAIDA_IGUAL, []

    if atualizar_se_mudou:
        atualizar(retrato, spec, fontes)

    return SAIDA_MUDOU, diferencas


def cmd_verificar(args):
    """Executa o subcomando verificar.

    Args:
        args (argparse.Namespace): Argumentos.

    Returns:
        int: Codigo de saida.
    """
    codigo, diferencas = verificar(atualizar_se_mudou=False)

    if codigo == SAIDA_IGUAL:
        print('Documentacao oficial sem mudancas desde {0}.'.format(
            snapshot_atual().get('atualizado_em', '?')))
    else:
        if codigo == SAIDA_MUDOU:
            print('A documentacao oficial MUDOU desde {0}:'.format(
                snapshot_atual().get('atualizado_em', 'o ultimo retrato')))
        for linha in diferencas[:args.limite]:
            print('  ' + linha)
        if len(diferencas) > args.limite:
            print('  ... e mais {0}.'.format(len(diferencas) - args.limite))
        if codigo == SAIDA_MUDOU:
            print('Rode "docs_oficiais.py atualizar" para atualizar as '
                  'referencias da skill.')

    return codigo


def cmd_atualizar(args):
    """Executa o subcomando atualizar.

    Args:
        args (argparse.Namespace): Argumentos.

    Returns:
        int: Codigo de saida.
    """
    codigo, diferencas = verificar(atualizar_se_mudou=True)

    if codigo == SAIDA_FALHA:
        print(diferencas[0])
    elif codigo == SAIDA_IGUAL:
        print('Nada a atualizar: a documentacao oficial nao mudou.')
    else:
        print('Referencias atualizadas ({0} diferenca(s)):'.format(
            len(diferencas)))
        for linha in diferencas[:args.limite]:
            print('  ' + linha)
        print('Gravados: openapi.json, endpoints.md, maestro_sdk.md e '
              'docs_snapshot.json em {0}.'.format(PASTA_REFERENCIAS))

    return codigo


def main(argv=None):
    """Interpreta a linha de comando.

    Args:
        argv (list): Argumentos; se None usa sys.argv.
    """
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description='Confere e atualiza a skill com a doc oficial.')
    sub = parser.add_subparsers(dest='comando', metavar='comando')
    sub.required = True

    for nome, aliases, funcao, ajuda in (
            ('verificar', ['check'], cmd_verificar,
             'Compara a doc oficial com o ultimo retrato.'),
            ('atualizar', ['update'], cmd_atualizar,
             'Atualiza as referencias se a doc mudou.')):
        p = sub.add_parser(nome, aliases=aliases, help=ajuda)
        p.add_argument('--limite', '--limit', type=int, default=60)
        p.set_defaults(funcao=funcao)

    args = parser.parse_args(argv)
    sys.exit(args.funcao(args))


if __name__ == '__main__':
    main()
