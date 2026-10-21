"""CLI do BotCity Maestro: atalhos do dia a dia e acesso a toda a API.

Os atalhos cobrem bots e releases (inclusive baixar e descompactar um
release), automacoes, tarefas, runners, agendamentos, credenciais,
datapools, logs, erros, alertas e arquivos de resultado. Para o resto,
"endpoints" e "describe" consultam a spec local e "call" chama qualquer
endpoint.

O deploy de uma versao nova continua nos scripts plan_deploy.py e
run_deploy.py, que tem o fluxo de revisao e confirmacao proprio.

Uso:
    python botcity.py [--ambiente QA] [--json] <comando> [opcoes]
    python botcity.py --help
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botcity_api import (  # noqa: E402
    PASTA_SKILL, ClienteMaestro, carregar_config, detalhar_erro, normalizar,
    normalizar_caminho)
from plan_deploy import avaliar_match, casar_bot  # noqa: E402


PASTA_REFERENCIAS = os.path.join(PASTA_SKILL, 'references')
CAMINHO_SPEC = os.path.join(PASTA_REFERENCIAS, 'openapi.json')
CAMINHO_EXTRAS = os.path.join(PASTA_REFERENCIAS, 'endpoints_extras.json')
CAMINHO_INDICE = os.path.join(PASTA_REFERENCIAS, 'endpoints.md')

METODOS_HTTP = ('get', 'post', 'put', 'patch', 'delete')

# Headers que a spec lista mas que o cliente ja resolve sozinho; nao
# faz sentido mostra-los no describe.
HEADERS_IGNORADOS = {'organization', 'authorization'}

# Contadores que o GET do datapool devolve mas que nao fazem parte do
# objeto de configuracao reenviado no POST.
CAMPOS_ESTATISTICA_DATAPOOL = {
    'avgDone', 'countCanceled', 'countDone', 'countError',
    'countPending', 'countProcessing', 'countTimeout',
}

LARGURA_MAXIMA_CELULA = 70

TIPOS_CAMPO_DATAPOOL = ('TEXT', 'INTEGER', 'DOUBLE')

TIPOS_PARAMETRO_AUTOMACAO = (
    'TEXT', 'INTEGER', 'DOUBLE', 'DATE', 'SINGLE_OPTION', 'MULTI_OPTION',
    'FILE', 'CREDENTIAL_SINGLE', 'CREDENTIAL_MULTIPLE',
)

TECNOLOGIAS = ('JAVA', 'PYTHON', 'JAVASCRIPT', 'COMMAND')

# Nome em ingles de cada subcomando. O nome em portugues e o
# principal; o alias permite pedir "tasks" em vez de "tarefas".
ALIASES_COMANDOS = {
    'baixar': ('download',),
    'atualizar-bot': ('update-bot',),
    'apagar-versao': ('delete-version',),
    'automacoes': ('automations',),
    'automacao': ('automation',),
    'editar-automacao': ('edit-automation',),
    'prioridade': ('priority',),
    'exportar-automacao': ('export-automation',),
    'criar-automacao': ('create-automation',),
    'tarefas': ('tasks',),
    'tarefa': ('task',),
    'criar-tarefa': ('create-task',),
    'finalizar-tarefa': ('finish-task',),
    'reiniciar-tarefa': ('restart-task',),
    'interromper-tarefa': ('interrupt-task',),
    'duplicar-tarefa': ('duplicate-task',),
    'diagnosticar': ('diagnose',),
    'analisar': ('insights', 'analyze'),
    'agendamentos': ('schedules',),
    'agendamento': ('schedule',),
    'ativar-agendamento': ('enable-schedule',),
    'desativar-agendamento': ('disable-schedule',),
    'criar-agendamento': ('create-schedule',),
    'apagar-agendamento': ('delete-schedule',),
    'credenciais': ('credentials',),
    'credencial': ('credential',),
    'credencial-chave': ('credential-key',),
    'criar-credencial': ('create-credential',),
    'remover-chave': ('remove-key',),
    'apagar-credencial': ('delete-credential',),
    'ativar-datapool': ('enable-datapool',),
    'desativar-datapool': ('disable-datapool',),
    'criar-datapool': ('create-datapool',),
    'apagar-datapool': ('delete-datapool',),
    'erros': ('errors',),
    'erro': ('error',),
    'alertas': ('alerts',),
    'artefatos': ('artifacts', 'result-files'),
    'baixar-artefato': ('download-artifact',),
    'describe': ('descrever',),
    'call': ('chamar',),
    'indice': ('index',),
}

# Metricas do painel do Maestro (API v3) usadas pelo comando analisar.
METRICAS_ANALISE = (
    ('por_estado', '/api/v3/tasks/count-by-state'),
    ('execucoes', '/api/v3/tasks/count-executions'),
    ('sucesso_itens', '/api/v3/tasks/success-rate'),
    ('falhas_consecutivas', '/api/v3/tasks/count-consecutive-failures'),
    ('falhas_por_automacao', '/api/v3/tasks/count-failed-by-automation'),
    ('erros_por_automacao', '/api/v3/errors/count-by-automation'),
)


# ---------------------------------------------------------------------
# Utilitarios de entrada e saida
# ---------------------------------------------------------------------


def mostrar(dados):
    """Imprime um valor como JSON legivel.

    Args:
        dados (object): Valor a imprimir.
    """
    if isinstance(dados, str):
        print(dados)
        return

    print(json.dumps(dados, indent=2, ensure_ascii=False, default=str))


def valor_de(item, chave):
    """Extrai um valor de um dicionario por chave, caminho ou funcao.

    Args:
        item (dict): Registro de origem.
        chave (object): Nome do campo, caminho com pontos
            ("metrics.cpuUsagePercentage") ou funcao que recebe o item.

    Returns:
        object: Valor encontrado, ou None.
    """
    if callable(chave):
        return chave(item)

    atual = item
    for parte in chave.split('.'):
        if not isinstance(atual, dict):
            return None
        atual = atual.get(parte)

    return atual


def como_texto(valor):
    """Converte um valor em texto curto para uma celula de tabela.

    Args:
        valor (object): Valor original.

    Returns:
        str: Texto em uma linha, truncado se for longo.
    """
    if valor is None:
        return ''

    if isinstance(valor, float):
        valor = round(valor, 1)

    if isinstance(valor, (list, dict)):
        valor = json.dumps(valor, ensure_ascii=False)

    texto = re.sub(r'\s+', ' ', str(valor)).strip()

    if len(texto) > LARGURA_MAXIMA_CELULA:
        texto = texto[:LARGURA_MAXIMA_CELULA - 3] + '...'

    return texto


def data_curta(valor):
    """Reduz uma data ISO a "AAAA-MM-DD HH:MM".

    Args:
        valor (str): Data em ISO 8601.

    Returns:
        str: Data resumida, ou texto vazio.
    """
    if not valor:
        return ''

    return str(valor)[:16].replace('T', ' ')


def tabela(itens, colunas, args):
    """Imprime uma lista de registros como tabela de texto.

    Com --json imprime os registros crus em vez da tabela.

    Args:
        itens (list): Registros a exibir.
        colunas (list): Pares (titulo, chave) passados a valor_de.
        args (argparse.Namespace): Argumentos (usa a flag json).
    """
    if getattr(args, 'json', False):
        mostrar(itens)
        return

    titulos = [titulo for titulo, _ in colunas]
    linhas = [[como_texto(valor_de(item, chave)) for _, chave in colunas]
              for item in itens]
    larguras = [max([len(titulo)] + [len(linha[pos]) for linha in linhas])
                for pos, titulo in enumerate(titulos)]

    def formatar(celulas):
        """Alinha as celulas de uma linha.

        Args:
            celulas (list): Textos da linha.

        Returns:
            str: Linha formatada.
        """
        return '  '.join(celula.ljust(larguras[pos])
                         for pos, celula in enumerate(celulas)).rstrip()

    print(formatar(titulos))
    print(formatar(['-' * largura for largura in larguras]))
    for linha in linhas:
        print(formatar(linha))
    print('-- {0} item(ns)'.format(len(itens)))


def interpretar_valor(bruto):
    """Interpreta um valor digitado como JSON quando possivel.

    "10" vira 10, "true" vira True, '{"a": 1}' vira dict; qualquer
    outra coisa continua texto.

    Args:
        bruto (str): Valor como digitado.

    Returns:
        object: Valor convertido.
    """
    try:
        return json.loads(bruto)
    except ValueError:
        return bruto


def ler_pares(pares, interpretar=False):
    """Converte uma lista "chave=valor" em dicionario.

    Chaves repetidas viram lista, que e como a API recebe filtros
    multiplos (?states=A&states=B).

    Args:
        pares (list): Itens no formato "chave=valor".
        interpretar (bool): Se True converte valores com
            interpretar_valor.

    Returns:
        dict: Pares convertidos.

    Raises:
        SystemExit: Se algum item nao tiver "=".
    """
    resultado = {}

    for par in pares or []:
        if '=' not in par:
            raise SystemExit(
                'Use o formato chave=valor (recebido: "{0}").'.format(par))

        chave, valor = par.split('=', 1)
        valor = interpretar_valor(valor) if interpretar else valor

        if chave in resultado:
            anterior = resultado[chave]
            if not isinstance(anterior, list):
                anterior = [anterior]
            resultado[chave] = anterior + [valor]
        else:
            resultado[chave] = valor

    return resultado


def ler_corpo(bruto):
    """Le o corpo JSON informado em linha, arquivo ou stdin.

    Args:
        bruto (str): JSON literal, "@arquivo" ou "@-" para stdin.

    Returns:
        object: Corpo decodificado, ou None se nada foi informado.

    Raises:
        SystemExit: Se o conteudo nao for JSON valido.
    """
    if bruto is None:
        return None

    if bruto == '@-':
        texto = sys.stdin.read()
    elif bruto.startswith('@'):
        with open(bruto[1:], 'r', encoding='utf-8') as origem:
            texto = origem.read()
    else:
        texto = bruto

    try:
        return json.loads(texto)
    except ValueError as erro:
        raise SystemExit('Corpo nao e JSON valido: {0}'.format(erro))


def nome_seguro(texto):
    """Troca caracteres problematicos em nome de arquivo por "_".

    Args:
        texto (str): Texto original.

    Returns:
        str: Texto seguro para nome de arquivo ou pasta.
    """
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', str(texto))


def exigir_confirmacao(args, descricao, impacto=None):
    """Interrompe a execucao se a operacao nao veio com --yes.

    Sem --yes, mostra o que vai mudar ou ser apagado (o "impacto",
    lido do Maestro antes de qualquer escrita) com o marcador
    CONFIRMACAO_NECESSARIA, para a pessoa decidir vendo o objeto real.

    Args:
        args (argparse.Namespace): Argumentos com a flag yes.
        descricao (str): O que seria feito, para a mensagem.
        impacto (list): Linhas descrevendo o que muda/e apagado.

    Raises:
        SystemExit: Se --yes nao foi informado.
    """
    if getattr(args, 'yes', False):
        return

    linhas = ['CONFIRMACAO_NECESSARIA: {0}.'.format(descricao)]

    if impacto:
        linhas.append('O que vai mudar:')
        linhas += ['  ' + linha for linha in impacto]

    linhas.append('Nada foi alterado. Mostre isto a pessoa e, so depois '
                  'do ok dela, repita com --yes.')

    raise SystemExit('\n'.join(linhas))


def consultar_alvo(cliente, caminho, rotulo):
    """Le o objeto que vai ser apagado, falhando se ele nao existir.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        caminho (str): Endpoint GET do objeto.
        rotulo (str): Nome do objeto, para a mensagem.

    Returns:
        object: Objeto como veio da API.

    Raises:
        SystemExit: Se o objeto nao existir (404).
    """
    try:
        return cliente.requisitar('GET', caminho)
    except requests.HTTPError as erro:
        if erro.response is not None and erro.response.status_code == 404:
            raise SystemExit('{0} nao existe no ambiente {1}; nada foi '
                             'apagado.'.format(rotulo, cliente.nome_ambiente))
        raise


def linhas_de(objeto, campos):
    """Descreve campos de um objeto, uma linha por campo preenchido.

    Args:
        objeto (dict): Objeto da API.
        campos (list): Pares (rotulo, chave) aceitos por valor_de.

    Returns:
        list: Linhas "rotulo: valor".
    """
    linhas = []

    for rotulo, chave in campos:
        valor = valor_de(objeto or {}, chave)
        if valor not in (None, '', [], {}):
            linhas.append('{0}: {1}'.format(rotulo, como_texto(valor)))

    return linhas


def mascarar_segredos(cofre):
    """Devolve uma copia do cofre com os valores das chaves ocultos.

    Args:
        cofre (dict): CredentialDTO como veio da API.

    Returns:
        dict: Copia com cada "value" trocado por "****".
    """
    copia = dict(cofre)
    copia['secrets'] = [
        {'key': segredo.get('key'), 'value': '****'}
        for segredo in (cofre.get('secrets') or [])
    ]

    return copia


# ---------------------------------------------------------------------
# Bots e releases
# ---------------------------------------------------------------------


def resolver_bot(cliente, nome):
    """Descobre o botId exato a partir do nome informado.

    Aceita o botId exato, o botId com diferenca de caixa/acento ou um
    trecho do nome. Se mais de um bot for plausivel, para e lista os
    candidatos: agir no bot errado aqui pode mexer na automacao de
    outra pessoa.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        nome (str): Nome ou trecho do botId.

    Returns:
        str: botId exato.

    Raises:
        SystemExit: Se nenhum bot casar ou se o nome for ambiguo.
    """
    bots = cliente.listar_bots()
    ids = {bot.get('botId') for bot in bots if bot.get('botId')}

    if nome in ids:
        return nome

    for bot_id in ids:
        if normalizar(bot_id) == normalizar(nome):
            return bot_id

    if cliente.listar_versoes(nome):
        return nome

    ranking = casar_bot([nome], bots)

    if not ranking:
        raise SystemExit('Nenhum bot cadastrado no workspace.')

    precisa_confirmar, motivo = avaliar_match(ranking)

    if precisa_confirmar:
        candidatos = '\n'.join(
            '  {0}  (score {1})'.format(item['bot_id'], item['score'])
            for item in ranking[:8])
        raise SystemExit(
            'Nao da para saber com seguranca qual bot e "{0}". {1}\n'
            'Candidatos:\n{2}\nRepita com o botId exato.'.format(
                nome, motivo, candidatos))

    return ranking[0]['bot_id']


def cmd_bots(cliente, args):
    """Lista os bots do workspace com a versao em release.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Filtro opcional --busca.
    """
    bots = cliente.listar_bots()

    if args.busca:
        alvo = normalizar(args.busca)
        bots = [bot for bot in bots
                if alvo in normalizar(bot.get('botId'))]

    bots.sort(key=lambda bot: bot.get('botId') or '')
    tabela(bots, [('botId', 'botId'), ('release', 'version'),
                  ('tecnologia', 'technology'),
                  ('atualizado', lambda b: data_curta(b.get('lastUpdate'))),
                  ('comando', 'command')], args)


def cmd_bot(cliente, args):
    """Mostra todas as versoes de um bot e qual esta em release.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Nome do bot.
    """
    bot_id = resolver_bot(cliente, args.bot)
    release = cliente.obter_release(bot_id) or {}
    versoes = cliente.listar_versoes(bot_id)

    if getattr(args, 'json', False):
        mostrar({'botId': bot_id, 'release': release, 'versoes': versoes})
        return

    print('Bot:      {0}'.format(bot_id))
    print('Release:  {0}'.format(release.get('version') or '(nenhuma)'))
    print('Comando:  {0}'.format(release.get('command') or ''))
    print('Tecnol.:  {0}\n'.format(release.get('technology') or ''))

    em_release = release.get('version')
    tabela(versoes, [
        ('versao', 'version'),
        ('', lambda v: 'RELEASE' if v.get('version') == em_release
         else ''),
        ('criada', lambda v: data_curta(v.get('lastUpdate'))),
        ('tecnologia', 'technology'),
        ('comando', 'command'),
    ], args)


def extrair_pacote(arquivo, pasta):
    """Descompacta um pacote .zip/.jar/.tar.gz em uma pasta.

    Antes de extrair confere se nenhum membro aponta para fora da
    pasta de destino ("zip slip"), o que permitiria a um pacote
    sobrescrever arquivos arbitrarios da maquina.

    Args:
        arquivo (str): Caminho do pacote baixado.
        pasta (str): Pasta de destino.

    Returns:
        int: Quantidade de arquivos extraidos.

    Raises:
        SystemExit: Se o pacote nao for zip nem tar, ou se tiver
            membro fora da pasta de destino.
    """
    raiz = os.path.realpath(pasta)

    def dentro_da_pasta(nome):
        """Diz se um membro do pacote cai dentro da pasta destino.

        Args:
            nome (str): Caminho do membro dentro do pacote.

        Returns:
            bool: True se o caminho final fica dentro da pasta.
        """
        alvo = os.path.realpath(os.path.join(raiz, nome))
        return alvo == raiz or alvo.startswith(raiz + os.sep)

    if zipfile.is_zipfile(arquivo):
        with zipfile.ZipFile(arquivo) as pacote:
            membros = pacote.infolist()
            invalidos = [m.filename for m in membros
                         if not dentro_da_pasta(m.filename)]
            if invalidos:
                raise SystemExit(
                    'Pacote com caminho fora da pasta de destino: '
                    '{0}. Nada foi extraido.'.format(invalidos[:5]))
            os.makedirs(raiz, exist_ok=True)
            pacote.extractall(raiz)
            return sum(1 for m in membros if not m.is_dir())

    if tarfile.is_tarfile(arquivo):
        with tarfile.open(arquivo) as pacote:
            membros = pacote.getmembers()
            invalidos = [m.name for m in membros
                         if not dentro_da_pasta(m.name)]
            if invalidos:
                raise SystemExit(
                    'Pacote com caminho fora da pasta de destino: '
                    '{0}. Nada foi extraido.'.format(invalidos[:5]))
            os.makedirs(raiz, exist_ok=True)
            if hasattr(tarfile, 'data_filter'):
                pacote.extractall(raiz, filter='data')
            else:
                pacote.extractall(raiz)
            return sum(1 for m in membros if m.isfile())

    raise SystemExit(
        'O arquivo baixado nao e .zip nem .tar: {0}'.format(arquivo))


def cmd_baixar(cliente, args):
    """Baixa o pacote de uma versao do bot e descompacta.

    Sem --versao usa a versao em release. O destino padrao e
    "<pasta_downloads>/<botId>_<versao>". Uma pasta que ja tem
    arquivos nunca e apagada: sem --sobrescrever o comando recusa.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Bot, versao e opcoes de destino.
    """
    bot_id = resolver_bot(cliente, args.bot)
    versao = args.versao

    if not versao:
        release = cliente.obter_release(bot_id)
        if not release:
            raise SystemExit(
                'O bot {0} nao tem versao em release. Informe a versao '
                'com --versao (veja as versoes com: bot {0}).'.format(
                    bot_id))
        versao = release.get('version')

    base = cliente.config.get('pasta_downloads') or os.getcwd()
    nome = '{0}_{1}'.format(nome_seguro(bot_id), nome_seguro(versao))

    if args.sem_extrair:
        destino_zip = os.path.abspath(
            args.destino or os.path.join(base, nome + '.zip'))
        if os.path.exists(destino_zip) and not args.sobrescrever:
            raise SystemExit(
                'O arquivo {0} ja existe. Nada foi baixado. Use '
                '--sobrescrever ou --destino.'.format(destino_zip))
        info = cliente.baixar_pacote(bot_id, versao, destino_zip)
        print('Pacote da versao {0} do bot {1} salvo em {2} '
              '({3:.2f} MB).'.format(versao, bot_id, info['arquivo'],
                                     info['bytes'] / 1024 / 1024))
        return

    pasta = os.path.abspath(args.destino or os.path.join(base, nome))

    if os.path.isdir(pasta) and os.listdir(pasta) \
            and not args.sobrescrever:
        raise SystemExit(
            'A pasta {0} ja existe e tem arquivos. Nada foi baixado. '
            'Use --sobrescrever para extrair por cima (nada e apagado) '
            'ou --destino para outra pasta.'.format(pasta))

    temporaria = tempfile.mkdtemp(prefix='botcity_')

    try:
        arquivo = os.path.join(temporaria, nome + '.zip')
        info = cliente.baixar_pacote(bot_id, versao, arquivo)
        total = extrair_pacote(arquivo, pasta)

        if args.manter_zip:
            shutil.copy2(arquivo, pasta.rstrip('\\/') + '.zip')
    finally:
        shutil.rmtree(temporaria, ignore_errors=True)

    print('Versao {0} do bot {1} baixada e descompactada em {2} '
          '({3} arquivos, pacote de {4:.2f} MB).'.format(
              versao, bot_id, pasta, total,
              info['bytes'] / 1024 / 1024))


def cmd_release(cliente, args):
    """Publica uma versao ja existente (inclusive rollback).

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Bot, versao e flag --yes.
    """
    bot_id = resolver_bot(cliente, args.bot)
    versoes = {item.get('version')
               for item in cliente.listar_versoes(bot_id)}

    if args.versao not in versoes:
        raise SystemExit(
            'A versao {0} nao existe para o bot {1}. Versoes: {2}.'
            .format(args.versao, bot_id,
                    ', '.join(sorted(v for v in versoes if v))))

    atual = cliente.obter_release(bot_id) or {}

    if atual.get('version') == args.versao:
        print('A versao {0} ja e a versao em release do bot {1}.'
              .format(args.versao, bot_id))
        return

    exigir_confirmacao(args, 'publicar a versao {0} do bot {1} no '
                             'lugar da {2} ({3})'.format(
                                 args.versao, bot_id,
                                 atual.get('version') or 'nenhuma',
                                 cliente.nome_ambiente))

    corpo = {
        'organization': cliente.organizacao,
        'botId': bot_id,
        'version': args.versao,
        'repositoryLabel': (atual.get('repositoryLabel')
                            or cliente.repositorio),
    }
    cliente.requisitar('POST', '/api/v2/bot/release', corpo=corpo)

    print('Bot {0} ({1}): release trocado de {2} para {3}.'.format(
        bot_id, cliente.nome_ambiente, atual.get('version') or 'nenhuma',
        args.versao))


def cmd_atualizar_bot(cliente, args):
    """Altera comando ou tecnologia de uma versao do bot.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Bot, versao e campos novos.
    """
    bot_id = resolver_bot(cliente, args.bot)
    caminho = '/api/v2/bot/{0}/version/{1}'.format(bot_id, args.versao)
    deploy = cliente.requisitar('GET', caminho)

    if args.comando is not None:
        deploy['command'] = args.comando or None
    if args.tecnologia:
        deploy['technology'] = args.tecnologia.upper()

    if args.dry_run:
        mostrar({'POST': '/api/v2/bot/update', 'corpo': deploy})
        return

    mostrar(cliente.requisitar('POST', '/api/v2/bot/update',
                               corpo=deploy))


def cmd_apagar_versao(cliente, args):
    """Apaga uma versao do bot que nao esteja em release.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Bot, versao e flag --yes.
    """
    bot_id = resolver_bot(cliente, args.bot)
    atual = cliente.obter_release(bot_id) or {}

    if atual.get('version') == args.versao:
        raise SystemExit(
            'A versao {0} e a versao em release do bot {1}; apagar '
            'deixaria os runners sem pacote. Publique outra versao '
            'antes.'.format(args.versao, bot_id))

    caminho = '/api/v2/bot/{0}/version/{1}'.format(bot_id, args.versao)
    versao = consultar_alvo(cliente, caminho, 'A versao {0} do bot {1}'
                            .format(args.versao, bot_id))
    restantes = sorted(v.get('version') for v in
                       cliente.listar_versoes(bot_id)
                       if v.get('version') not in (None, args.versao))
    impacto = ['APAGA a versao {0} do bot {1} e o pacote dela.'.format(
        args.versao, bot_id)]
    impacto += linhas_de(versao, [
        ('Tecnologia', 'technology'), ('Comando', 'command'),
        ('Arquivo', 'file'), ('Atualizada', 'lastUpdate')])
    impacto += [
        'Continua em release: {0}'.format(atual.get('version') or
                                          '(nenhuma)'),
        'Versoes que ficam ({0}): {1}'.format(
            len(restantes), ', '.join(restantes[-10:]) or '(nenhuma)'),
    ]

    exigir_confirmacao(args, 'apagar a versao {0} do bot {1} ({2})'
                       .format(args.versao, bot_id,
                               cliente.nome_ambiente), impacto)

    cliente.requisitar('DELETE', caminho)
    print('Versao {0} do bot {1} apagada ({2}).'.format(
        args.versao, bot_id, cliente.nome_ambiente))


# ---------------------------------------------------------------------
# Automacoes
# ---------------------------------------------------------------------


def cmd_automacoes(cliente, args):
    """Lista automacoes, opcionalmente filtradas por texto.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Filtro --busca.
    """
    query = {'sort': 'label,asc'}

    if args.busca:
        query['automation'] = args.busca

    itens = cliente.paginar('/api/v2/activity/pagination', query)
    tabela(itens, [('label', 'label'), ('nome', 'name'),
                   ('tecnologia', 'technology'), ('prior.', 'priority'),
                   ('timeout', 'timeout'), ('estado', 'state')], args)


def cmd_automacao(cliente, args):
    """Mostra o cadastro completo de uma automacao.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label da automacao.
    """
    mostrar(cliente.requisitar(
        'GET', '/api/v2/activity/{0}'.format(args.label)))


def cmd_editar_automacao(cliente, args):
    """Altera campos de uma automacao via PATCH.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label e pares --set campo=valor.
    """
    campos = ler_pares(args.set, interpretar=True)

    if not campos:
        raise SystemExit('Informe ao menos um --set campo=valor.')

    caminho = '/api/v2/activity/{0}'.format(args.label)

    if args.dry_run:
        mostrar({'PATCH': caminho, 'corpo': campos})
        return

    mostrar(cliente.requisitar('PATCH', caminho, corpo=campos))


def cmd_prioridade(cliente, args):
    """Altera a prioridade de uma automacao.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label e prioridade (0 a 10).
    """
    mostrar(cliente.requisitar(
        'PUT', '/api/v2/activity/{0}/priority/{1}'.format(
            args.label, args.prioridade)))


def cmd_exportar_automacao(cliente, args):
    """Exporta o cadastro de uma automacao para um arquivo JSON.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label e caminho de saida.
    """
    saida = args.saida or '{0}.json'.format(nome_seguro(args.label))
    info = cliente.requisitar(
        'GET', '/api/v2/activity/{0}/export'.format(args.label),
        saida=saida)
    print('Automacao {0} exportada em {1}.'.format(
        args.label, info['arquivo']))


# ---------------------------------------------------------------------
# Tarefas
# ---------------------------------------------------------------------


def cmd_tarefas(cliente, args):
    """Lista tarefas recentes com filtros.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Estado, automacao, runner, dias e
            limite.
    """
    query = {'days': args.dias, 'sort': 'dateCreation,desc'}

    if args.estado:
        query['states'] = [estado.upper() for estado in args.estado]
    if args.automacao:
        query['activityLabel'] = args.automacao
    if args.runner:
        query['machineId'] = args.runner

    itens = cliente.paginar('/api/v2/task', query, args.limite)
    tabela(itens, [('id', 'id'), ('automacao', 'activityLabel'),
                   ('estado', 'state'), ('final', 'finishStatus'),
                   ('runner', 'machineId'),
                   ('criada', lambda t: data_curta(t.get('dateCreation'))),
                   ('usuario', 'userCreationName')], args)


def cmd_tarefa(cliente, args):
    """Mostra os detalhes de uma tarefa.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID da tarefa.
    """
    mostrar(cliente.requisitar('GET', '/api/v2/task/{0}'.format(args.id)))


def cmd_criar_tarefa(cliente, args):
    """Enfileira uma nova execucao de uma automacao.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label, parametros e opcoes.
    """
    corpo = {
        'activityLabel': args.label,
        'parameters': ler_pares(args.parametro, interpretar=True),
        'test': args.teste,
        'priority': args.prioridade,
    }

    if args.min_execucao:
        corpo['minExecutionDate'] = args.min_execucao

    if args.dry_run:
        mostrar({'POST': '/api/v2/task', 'corpo': corpo})
        return

    tarefa = cliente.requisitar('POST', '/api/v2/task', corpo=corpo)
    print('Tarefa {0} criada para {1} (estado {2}).'.format(
        tarefa.get('id'), args.label, tarefa.get('state')))


def cmd_finalizar_tarefa(cliente, args):
    """Encerra uma tarefa com o status informado.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID, status, mensagem e itens.
    """
    corpo = {'state': 'FINISHED', 'finishStatus': args.status.upper()}

    if args.mensagem:
        corpo['finishMessage'] = args.mensagem

    if args.itens:
        try:
            total, ok, falha = (int(p) for p in args.itens.split(','))
        except ValueError:
            raise SystemExit('Use --itens total,processados,falhas '
                             '(ex.: 100,95,5).')
        if total != ok + falha:
            raise SystemExit(
                'O total ({0}) precisa ser processados + falhas ({1}). '
                'O servidor aceita valor inconsistente, mas ele suja o '
                'Insights.'.format(total, ok + falha))
        corpo.update({'totalItems': total, 'processedItems': ok,
                      'failedItems': falha})

    tarefa = cliente.requisitar(
        'POST', '/api/v2/task/{0}'.format(args.id), corpo=corpo)
    print('Tarefa {0} finalizada: {1} / {2}.'.format(
        args.id, (tarefa or {}).get('state', 'FINISHED'),
        (tarefa or {}).get('finishStatus', corpo['finishStatus'])))


def cmd_reiniciar_tarefa(cliente, args):
    """Recoloca uma tarefa na fila (estado START).

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID da tarefa.
    """
    cliente.requisitar('POST', '/api/v2/task/{0}'.format(args.id),
                       corpo={'state': 'START'})
    print('Tarefa {0} recolocada na fila.'.format(args.id))


def cmd_interromper_tarefa(cliente, args):
    """Pede a interrupcao (cooperativa) de uma tarefa.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID da tarefa.
    """
    cliente.requisitar('POST', '/api/v2/task/{0}'.format(args.id),
                       corpo={'interrupted': True})
    print('Interrupcao solicitada para a tarefa {0}. O bot so para se '
          'consultar a flag "interrupted"; se nao parar, use '
          'finalizar-tarefa.'.format(args.id))


def cmd_duplicar_tarefa(cliente, args):
    """Cria uma tarefa nova com os mesmos parametros de outra.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID da tarefa original.
    """
    tarefa = cliente.requisitar(
        'POST', '/api/v2/task/{0}/duplicate'.format(args.id))
    print('Tarefa {0} criada a partir da {1}.'.format(
        (tarefa or {}).get('id'), args.id))


# ---------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------


def cmd_runners(cliente, args):
    """Lista os runners (maquinas) do workspace.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Argumentos gerais.
    """
    itens = cliente.requisitar('GET', '/api/v2/machine/') or []
    itens.sort(key=lambda m: m.get('idMachine') or '')
    tabela(itens, [('id', 'idMachine'), ('nome', 'name'),
                   ('tipo', 'type'),
                   ('online', 'isOnline'), ('status', 'status'),
                   ('heartbeat',
                    lambda m: data_curta(m.get('lastHeartbeat'))),
                   ('cpu%', 'metrics.cpuUsagePercentage'),
                   ('mem%', 'metrics.memoryUsagePercentage'),
                   ('runner', 'metrics.runnerVersion')], args)


def cmd_runner(cliente, args):
    """Mostra um runner e, se pedido, baixa screenshot e log.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID e destinos de screenshot/log.
    """
    mostrar(cliente.requisitar(
        'GET', '/api/v2/machine/{0}'.format(args.id)))

    if args.screenshot:
        info = cliente.requisitar(
            'GET', '/api/v2/machine/screenshot/{0}'.format(args.id),
            saida=args.screenshot)
        print('Screenshot salvo em {0}.'.format(info['arquivo']))

    if args.log:
        info = cliente.requisitar(
            'GET', '/api/v2/machine/log/{0}'.format(args.id),
            saida=args.log)
        print('Log salvo em {0}.'.format(info['arquivo']))


# ---------------------------------------------------------------------
# Agendamentos
# ---------------------------------------------------------------------


def cmd_agendamentos(cliente, args):
    """Lista agendamentos, opcionalmente filtrados por texto.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Filtro --busca.
    """
    query = {}

    if args.busca:
        query['likeAutomationOrScheduleName'] = args.busca

    itens = cliente.paginar('/api/v2/scheduling', query)
    tabela(itens, [('id', 'id'), ('automacao', 'activityLabel'),
                   ('nome', 'scheduleName'), ('cron', 'cron'),
                   ('ativo', 'active'), ('prior.', 'priority')], args)


def cmd_agendamento(cliente, args):
    """Mostra um agendamento.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID do agendamento.
    """
    mostrar(cliente.requisitar(
        'GET', '/api/v2/scheduling/{0}'.format(args.id)))


def alternar_agendamento(cliente, args, ativo):
    """Ativa ou desativa um agendamento reenviando o objeto inteiro.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID e flag --dry-run.
        ativo (bool): Estado desejado.
    """
    caminho = '/api/v2/scheduling/{0}'.format(args.id)
    agendamento = cliente.requisitar('GET', caminho)

    if agendamento.get('active') is ativo:
        print('O agendamento {0} ja esta {1}.'.format(
            args.id, 'ativo' if ativo else 'inativo'))
        return

    agendamento['active'] = ativo

    if args.dry_run:
        mostrar({'POST': caminho, 'corpo': agendamento})
        return

    cliente.requisitar('POST', caminho, corpo=agendamento)
    print('Agendamento {0} ({1}, cron "{2}") {3}.'.format(
        args.id, agendamento.get('activityLabel'),
        agendamento.get('cron'), 'ativado' if ativo else 'desativado'))


def cmd_ativar_agendamento(cliente, args):
    """Ativa um agendamento.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID do agendamento.
    """
    alternar_agendamento(cliente, args, True)


def cmd_desativar_agendamento(cliente, args):
    """Desativa um agendamento.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID do agendamento.
    """
    alternar_agendamento(cliente, args, False)


# ---------------------------------------------------------------------
# Credenciais
# ---------------------------------------------------------------------


def cmd_credenciais(cliente, args):
    """Lista os cofres de credenciais, so com o nome das chaves.

    A listagem da API devolve os valores em texto puro; eles nunca
    sao impressos aqui, nem com --json.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Filtro --busca.
    """
    cofres = cliente.requisitar('GET', '/api/v2/credential') or []

    if args.busca:
        alvo = normalizar(args.busca)
        cofres = [c for c in cofres if alvo in normalizar(c.get('label'))]

    cofres = sorted((mascarar_segredos(c) for c in cofres),
                    key=lambda c: c.get('label') or '')
    tabela(cofres, [
        ('label', 'label'), ('repositorio', 'repositoryLabel'),
        ('chaves', lambda c: ', '.join(
            s['key'] or '' for s in c['secrets'])),
        ('atualizado', lambda c: data_curta(c.get('lastUpdate'))),
    ], args)


def cmd_credencial(cliente, args):
    """Mostra um cofre de credenciais, com valores mascarados.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label e flag --mostrar.
    """
    cofre = cliente.requisitar(
        'GET', '/api/v2/credential/{0}'.format(args.label))
    mostrar(cofre if args.mostrar else mascarar_segredos(cofre))


def cmd_credencial_chave(cliente, args):
    """Cria ou atualiza uma chave dentro de um cofre existente.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label, chave e valor.
    """
    cliente.requisitar(
        'POST', '/api/v2/credential/{0}/key'.format(args.label),
        corpo={'key': args.chave, 'value': args.valor})
    print('Chave "{0}" gravada no cofre {1} ({2}).'.format(
        args.chave, args.label, cliente.nome_ambiente))


# ---------------------------------------------------------------------
# Datapool
# ---------------------------------------------------------------------


def cmd_datapools(cliente, args):
    """Lista as filas (datapools) com os contadores por estado.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Filtro --busca.
    """
    filas = cliente.paginar('/api/v2/datapool')

    if args.busca:
        alvo = normalizar(args.busca)
        filas = [f for f in filas
                 if alvo in normalizar(f.get('label'))
                 or alvo in normalizar(f.get('name'))]

    filas.sort(key=lambda f: f.get('label') or '')
    tabela(filas, [('label', 'label'), ('ativa', 'active'),
                   ('pend.', 'countPending'),
                   ('process.', 'countProcessing'),
                   ('erro', 'countError'), ('feito', 'countDone'),
                   ('automacao', 'defaultActivity')], args)


def cmd_datapool(cliente, args):
    """Mostra a configuracao e o resumo de uma fila.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label da fila.
    """
    caminho = '/api/v2/datapool/{0}'.format(args.label)
    mostrar({'configuracao': cliente.requisitar('GET', caminho),
             'resumo': cliente.requisitar('GET', caminho + '/summary')})


def cmd_datapool_push(cliente, args):
    """Insere um item em uma fila.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label, valores e prioridade.
    """
    valores = ler_pares(args.valor)

    if not valores:
        raise SystemExit('Informe ao menos um -v campo=valor.')

    corpo = {'priority': args.prioridade, 'values': valores}
    caminho = '/api/v2/datapool/{0}/push'.format(args.label)

    if args.dry_run:
        mostrar({'POST': caminho, 'corpo': corpo})
        return

    mostrar(cliente.requisitar('POST', caminho, corpo=corpo))


def alternar_datapool(cliente, args, ativo):
    """Ativa ou desativa uma fila reenviando o objeto inteiro.

    O GET devolve a automacao padrao como "defaultActivity", mas o
    POST espera "defaultAutomation"; sem a traducao a fila perderia a
    automacao vinculada.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label e flag --dry-run.
        ativo (bool): Estado desejado.
    """
    caminho = '/api/v2/datapool/{0}'.format(args.label)
    fila = cliente.requisitar('GET', caminho)

    if fila.get('active') is ativo:
        print('A fila {0} ja esta {1}.'.format(
            args.label, 'ativa' if ativo else 'inativa'))
        return

    corpo = {chave: valor for chave, valor in fila.items()
             if chave not in CAMPOS_ESTATISTICA_DATAPOOL}

    if 'defaultAutomation' not in corpo:
        corpo['defaultAutomation'] = corpo.get('defaultActivity')

    corpo['active'] = ativo

    if args.dry_run:
        mostrar({'POST': caminho, 'corpo': corpo})
        return

    cliente.requisitar('POST', caminho, corpo=corpo)
    print('Fila {0} {1}.'.format(
        args.label, 'ativada' if ativo else 'desativada'))


def cmd_ativar_datapool(cliente, args):
    """Ativa uma fila.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label da fila.
    """
    alternar_datapool(cliente, args, True)


def cmd_desativar_datapool(cliente, args):
    """Desativa uma fila.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label da fila.
    """
    alternar_datapool(cliente, args, False)


# ---------------------------------------------------------------------
# Diagnostico: erros, alertas, logs e arquivos de resultado
# ---------------------------------------------------------------------


def cmd_erros(cliente, args):
    """Lista erros registrados pelas automacoes.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Automacao, tarefa, dias e limite.
    """
    query = {'days': args.dias, 'sort': 'dateCreation,desc'}

    if args.automacao:
        query['automations'] = [args.automacao]
    if args.tarefa:
        query['taskId'] = args.tarefa

    itens = cliente.paginar('/api/v2/error', query, args.limite)
    tabela(itens, [('id', 'id'), ('automacao', 'automationLabel'),
                   ('tarefa', 'taskId'), ('tipo', 'type'),
                   ('mensagem', 'message'),
                   ('data', lambda e: data_curta(e.get('dateCreation')))],
           args)


def cmd_erro(cliente, args):
    """Mostra um erro com stack trace e, se pedido, o screenshot.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID e destino do screenshot.
    """
    mostrar(cliente.requisitar('GET', '/api/v2/error/{0}'.format(args.id)))

    if args.screenshot:
        info = cliente.requisitar(
            'GET', '/api/v2/error/{0}/screenshot'.format(args.id),
            saida=args.screenshot)
        print('Screenshot salvo em {0}.'.format(info['arquivo']))


def cmd_alertas(cliente, args):
    """Lista alertas emitidos pelas automacoes.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Automacao, tipo, tarefa, dias e
            limite.
    """
    query = {'days': args.dias, 'sort': 'date,desc'}

    if args.automacao:
        query['activityLabel'] = args.automacao
    if args.tipo:
        query['type'] = args.tipo.upper()
    if args.tarefa:
        query['taskId'] = args.tarefa

    itens = cliente.paginar('/api/v2/alerts', query, args.limite)
    tabela(itens, [('data', lambda a: data_curta(a.get('date'))),
                   ('tipo', 'type'), ('automacao', 'activityLabel'),
                   ('tarefa', 'taskId'), ('titulo', 'title'),
                   ('mensagem', 'message')], args)


def cmd_logs(cliente, args):
    """Lista os logs de execucao ou as entradas de um log.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label opcional, dias e limite.
    """
    if not args.label:
        itens = cliente.paginar('/api/v2/log')
        itens.sort(key=lambda log: log.get('label') or '')
        tabela(itens, [('label', 'label'),
                       ('colunas', lambda log: ', '.join(
                           c.get('name') or '' for c in
                           (log.get('columns') or []))),
                       ('criado',
                        lambda log: data_curta(log.get('dateCreation')))],
               args)
        return

    caminho = '/api/v2/log/{0}'.format(args.label)
    cabecalho = cliente.requisitar('GET', caminho) or {}
    entradas = cliente.requisitar(
        'GET', caminho + '/entry-list', query={'days': args.dias}) or []

    if isinstance(entradas, dict):
        entradas = entradas.get('content', [])

    entradas = entradas[:args.limite]
    colunas = [(c.get('name') or c.get('label'),
                'columns.' + c.get('label'))
               for c in (cabecalho.get('columns') or [])]
    tabela(entradas,
           [('data', lambda e: data_curta(e.get('dateCreation')))]
           + colunas, args)


def cmd_artefatos(cliente, args):
    """Lista arquivos de resultado gerados pelas automacoes.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Tarefa, automacao, dias e limite.
    """
    query = {'days': args.dias, 'sort': 'dateCreation,desc'}

    if args.tarefa:
        query['taskId'] = args.tarefa
    if args.automacao:
        query['automation'] = args.automacao

    itens = cliente.paginar('/api/v2/artifact', query, args.limite)
    tabela(itens, [('id', 'id'), ('tarefa', 'taskId'),
                   ('automacao', 'activityLabel'),
                   ('arquivo', 'fileName'), ('tipo', 'type'),
                   ('data', lambda a: data_curta(a.get('dateCreation')))],
           args)


def cmd_baixar_artefato(cliente, args):
    """Baixa um arquivo de resultado.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID e destino.
    """
    caminho = '/api/v2/artifact/{0}'.format(args.id)
    registro = cliente.requisitar('GET', caminho) or {}
    nome = registro.get('fileName') or registro.get('name') \
        or 'artefato_{0}'.format(args.id)
    destino = args.destino or nome

    if os.path.isdir(destino):
        destino = os.path.join(destino, nome)

    info = cliente.requisitar('GET', caminho + '/file', saida=destino)
    print('Arquivo {0} salvo em {1} ({2} bytes).'.format(
        nome, info['arquivo'], info['bytes']))


# ---------------------------------------------------------------------
# Criacao de credenciais, filas, agendamentos e automacoes
# ---------------------------------------------------------------------


def cmd_criar_credencial(cliente, args):
    """Cria um cofre de credenciais com uma ou mais chaves.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label, segredos e flags.
    """
    segredos = ler_pares(args.segredo)

    if not segredos:
        raise SystemExit('Informe ao menos um -s chave=valor.')

    corpo = {
        'label': args.label,
        'organizationLabel': cliente.organizacao,
        'repositoryLabel': args.repositorio or cliente.repositorio,
        'secrets': [{'key': chave, 'value': valor}
                    for chave, valor in segredos.items()],
    }

    if args.dry_run:
        mostrar({'POST': '/api/v2/credential',
                 'corpo': mascarar_segredos(corpo)})
        return

    exigir_confirmacao(args, 'criar o cofre {0} com as chaves {1} ({2})'
                       .format(args.label, ', '.join(segredos),
                               cliente.nome_ambiente))
    cliente.requisitar('POST', '/api/v2/credential', corpo=corpo)
    print('Cofre {0} criado com as chaves: {1} ({2}).'.format(
        args.label, ', '.join(segredos), cliente.nome_ambiente))


def cmd_remover_chave(cliente, args):
    """Remove uma chave de um cofre reenviando a lista inteira.

    A API nao tem remocao de chave individual: o POST no cofre
    substitui todos os segredos, entao a chave sai por omissao.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label, chave e flags.
    """
    caminho = '/api/v2/credential/{0}'.format(args.label)
    cofre = cliente.requisitar('GET', caminho)
    segredos = cofre.get('secrets') or []
    restantes = [s for s in segredos if s.get('key') != args.chave]

    if len(restantes) == len(segredos):
        raise SystemExit('A chave "{0}" nao existe no cofre {1}.'.format(
            args.chave, args.label))

    cofre['secrets'] = restantes

    if args.dry_run:
        mostrar({'POST': caminho, 'corpo': mascarar_segredos(cofre)})
        return

    impacto = [
        'REMOVE a chave "{0}" do cofre {1} (o valor e perdido).'.format(
            args.chave, args.label),
        'Chaves hoje:  {0}'.format(', '.join(
            s.get('key') or '' for s in segredos)),
        'Chaves depois: {0}'.format(', '.join(
            s.get('key') or '' for s in restantes) or '(nenhuma)'),
        'Robos que leem "{0}/{1}" passam a falhar.'.format(
            args.label, args.chave),
    ]
    exigir_confirmacao(args, 'remover a chave {0} do cofre {1} ({2})'
                       .format(args.chave, args.label,
                               cliente.nome_ambiente), impacto)
    cliente.requisitar('POST', caminho, corpo=cofre)
    print('Chave "{0}" removida do cofre {1}.'.format(
        args.chave, args.label))


def cmd_apagar_credencial(cliente, args):
    """Apaga um cofre de credenciais inteiro.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label e flag --yes.
    """
    caminho = '/api/v2/credential/{0}'.format(args.label)
    cofre = consultar_alvo(cliente, caminho,
                           'O cofre {0}'.format(args.label))
    chaves = [s.get('key') or '' for s in (cofre.get('secrets') or [])]
    impacto = ['APAGA o cofre {0} inteiro, com {1} chave(s): {2}'.format(
        args.label, len(chaves), ', '.join(chaves) or '(nenhuma)')]
    impacto += linhas_de(cofre, [('Repositorio', 'repositoryLabel'),
                                 ('Atualizado', 'lastUpdate')])
    impacto.append('Os valores sao perdidos e os robos que leem este '
                   'cofre passam a falhar.')

    exigir_confirmacao(args, 'apagar o cofre {0} inteiro ({1})'.format(
        args.label, cliente.nome_ambiente), impacto)
    cliente.requisitar('DELETE', caminho)
    print('Cofre {0} apagado ({1}).'.format(args.label,
                                            cliente.nome_ambiente))


def ler_campos_datapool(campos):
    """Converte "nome:TIPO[:id][:exibir]" no schema de uma fila.

    Args:
        campos (list): Itens como digitados em --campo.

    Returns:
        list: Campos do schema no formato da API.

    Raises:
        SystemExit: Se algum tipo for invalido.
    """
    schema = []

    for item in campos or []:
        partes = item.split(':')
        tipo = (partes[1] if len(partes) > 1 else 'TEXT').upper()
        marcas = {parte.lower() for parte in partes[2:]}

        if tipo not in TIPOS_CAMPO_DATAPOOL:
            raise SystemExit('Tipo "{0}" invalido em "{1}". Use: {2}.'
                             .format(tipo, item,
                                     ', '.join(TIPOS_CAMPO_DATAPOOL)))

        schema.append({
            'label': partes[0],
            'type': tipo,
            'uniqueId': bool(marcas & {'id', 'unico', 'unique'}),
            'displayValue': bool(marcas & {'exibir', 'display'}),
        })

    return schema


def cmd_criar_datapool(cliente, args):
    """Cria uma fila (datapool).

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label, campos e configuracoes.
    """
    schema = ler_campos_datapool(args.campo)

    if not schema:
        raise SystemExit('Informe ao menos um --campo nome:TIPO '
                         '(ex.: --campo cpf:TEXT:id:exibir).')

    corpo = {
        'label': args.label,
        'name': args.nome or args.label,
        'defaultAutomation': args.automacao,
        'consumptionPolicy': args.politica,
        'schema': schema,
        'trigger': args.gatilho,
        'autoRetry': args.max_tentativas > 0,
        'maxAutoRetry': args.max_tentativas,
        'abortOnError': args.max_erros > 0,
        'maxErrorsBeforeInactive': args.max_erros,
        'enableProcessingTime': bool(args.tempo_item),
        'itemMaxProcessingTime': args.tempo_item or 0,
        'active': True,
        'repositoryLabel': args.repositorio or cliente.repositorio,
    }

    if args.dry_run:
        mostrar({'POST': '/api/v2/datapool', 'corpo': corpo})
        return

    exigir_confirmacao(args, 'criar a fila {0} ({1})'.format(
        args.label, cliente.nome_ambiente))
    cliente.requisitar('POST', '/api/v2/datapool', corpo=corpo)
    print('Fila {0} criada com os campos: {1}.'.format(
        args.label, ', '.join(c['label'] for c in schema)))


def cmd_apagar_datapool(cliente, args):
    """Apaga uma fila e seus itens.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label e flag --yes.
    """
    caminho = '/api/v2/datapool/{0}'.format(args.label)
    fila = consultar_alvo(cliente, caminho, 'A fila {0}'.format(args.label))
    contagem = {campo[5:].lower(): fila.get(campo) or 0
                for campo in sorted(CAMPOS_ESTATISTICA_DATAPOOL)
                if campo.startswith('count')}
    impacto = ['APAGA a fila {0} e TODOS os {1} itens dela.'.format(
        args.label, sum(contagem.values()))]
    impacto.append('Itens por estado: ' + ', '.join(
        '{0}={1}'.format(estado, total)
        for estado, total in contagem.items()))
    impacto += linhas_de(fila, [
        ('Nome', 'name'), ('Ativa', 'active'),
        ('Automacao padrao', 'defaultActivity'),
        ('Campos', lambda f: ', '.join(
            c.get('label') or '' for c in (f.get('schema') or [])))])

    if contagem.get('pending') or contagem.get('processing'):
        impacto.append('ATENCAO: ha itens pendentes/em processamento que '
                       'nao serao executados.')

    exigir_confirmacao(args, 'apagar a fila {0} e todos os itens ({1})'
                       .format(args.label, cliente.nome_ambiente), impacto)
    cliente.requisitar('DELETE', caminho)
    print('Fila {0} apagada ({1}).'.format(args.label,
                                           cliente.nome_ambiente))


def cmd_criar_agendamento(cliente, args):
    """Cria um agendamento, validando o cron antes.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Automacao, cron e opcoes.
    """
    # O corpo e um mapa com "cronExpression" (com "cron" o servidor
    # responde 400) e a resposta e um booleano puro. Cron invalido
    # volta como HTTP 400 com corpo "false".
    try:
        validacao = cliente.requisitar(
            'POST', '/api/v2/scheduling/validate-cron',
            corpo={'cronExpression': args.cron})
    except requests.HTTPError as erro:
        if (erro.response is None
                or erro.response.text.strip().lower() != 'false'):
            raise
        validacao = False

    if validacao is not True and str(validacao).lower() != 'true':
        raise SystemExit('Cron invalido: "{0}". Use 6 campos com segundos '
                         '(ex.: "0 30 8 * * MON-FRI" ou "0 0 12 ? * '
                         'MON-FRI"). Nada foi criado.'.format(args.cron))

    corpo = {
        'activityLabel': args.label,
        'organizationLabel': cliente.organizacao,
        'repositoryLabel': args.repositorio or cliente.repositorio,
        'active': not args.inativo,
        'priority': args.prioridade,
        'cron': args.cron,
        'parameters': ler_pares(args.parametro, interpretar=True),
    }

    if args.nome:
        corpo['scheduleName'] = args.nome

    if args.dry_run:
        mostrar({'POST': '/api/v2/scheduling', 'corpo': corpo,
                 'validacao_cron': validacao})
        return

    exigir_confirmacao(args, 'criar agendamento "{0}" para {1} ({2})'
                       .format(args.cron, args.label,
                               cliente.nome_ambiente))
    criado = cliente.requisitar('POST', '/api/v2/scheduling', corpo=corpo)
    print('Agendamento {0} criado para {1} (cron "{2}", {3}).'.format(
        (criado or {}).get('id'), args.label, args.cron,
        'inativo' if args.inativo else 'ativo'))


def cmd_apagar_agendamento(cliente, args):
    """Apaga um agendamento.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID e flag --yes.
    """
    caminho = '/api/v2/scheduling/{0}'.format(args.id)
    agendamento = consultar_alvo(cliente, caminho,
                                 'O agendamento {0}'.format(args.id))
    impacto = ['APAGA o agendamento {0}; a automacao deixa de rodar '
               'nesse horario.'.format(args.id)]
    impacto += linhas_de(agendamento, [
        ('Automacao', 'activityLabel'), ('Nome', 'scheduleName'),
        ('Cron', 'cron'), ('Ativo', 'active'),
        ('Parametros', 'parameters')])
    impacto.append('Para so pausar, use desativar-agendamento.')

    exigir_confirmacao(args, 'apagar o agendamento {0} ({1})'.format(
        args.id, cliente.nome_ambiente), impacto)
    cliente.requisitar('DELETE', caminho)
    print('Agendamento {0} ({1}) apagado.'.format(
        args.id, agendamento.get('activityLabel')))


def ler_parametros_automacao(itens):
    """Converte "label:TIPO[:obrigatorio]" em parametros de automacao.

    Args:
        itens (list): Itens como digitados em --param-automacao.

    Returns:
        list: Parametros no formato da API.

    Raises:
        SystemExit: Se algum tipo for invalido.
    """
    parametros = []

    for item in itens or []:
        partes = item.split(':')
        tipo = (partes[1] if len(partes) > 1 else 'TEXT').upper()

        if tipo not in TIPOS_PARAMETRO_AUTOMACAO:
            raise SystemExit('Tipo "{0}" invalido em "{1}". Use: {2}.'
                             .format(tipo, item,
                                     ', '.join(TIPOS_PARAMETRO_AUTOMACAO)))

        parametros.append({
            'label': partes[0], 'name': partes[0], 'type': tipo,
            'required': any(p.lower() in ('obrigatorio', 'required')
                            for p in partes[2:]),
        })

    return parametros


def cmd_criar_automacao(cliente, args):
    """Cria uma automacao a partir de flags e/ou de um corpo JSON.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Label, nome, tecnologia e opcoes.
    """
    corpo = ler_corpo(args.body) or {}
    corpo.setdefault('label', args.label)
    corpo.setdefault('name', args.nome or args.label)
    corpo.setdefault('description', args.descricao or corpo['name'])
    corpo.setdefault('technology', args.tecnologia)
    corpo.setdefault('repositoryLabel',
                     args.repositorio or cliente.repositorio)
    corpo.setdefault('priority', args.prioridade)

    if args.timeout is not None:
        corpo['timeout'] = args.timeout
    if args.runner:
        corpo['machines'] = args.runner
    if args.param_automacao:
        corpo['parameters'] = ler_parametros_automacao(args.param_automacao)

    if args.dry_run:
        mostrar({'POST': '/api/v2/activity', 'corpo': corpo})
        return

    criada = cliente.requisitar('POST', '/api/v2/activity', corpo=corpo)
    print('Automacao {0} criada (tecnologia {1}, estado {2}).'.format(
        (criada or {}).get('label', corpo['label']), corpo['technology'],
        (criada or {}).get('state', '?')))


# ---------------------------------------------------------------------
# Analise do workspace e diagnostico de tarefa
# ---------------------------------------------------------------------


def janela_utc(dias):
    """Monta o intervalo [agora - dias, agora] em ISO 8601 UTC.

    Args:
        dias (int): Tamanho da janela em dias.

    Returns:
        dict: {'startDate', 'endDate'} prontos para a query.
    """
    fim = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0)
    inicio = fim - datetime.timedelta(days=dias)
    formato = '%Y-%m-%dT%H:%M:%SZ'

    return {'startDate': inicio.strftime(formato),
            'endDate': fim.strftime(formato)}


def consultar_metrica(cliente, caminho, query):
    """Chama um endpoint de metrica sem derrubar a analise inteira.

    Workspaces antigos ou on-premise podem nao ter os endpoints v3;
    nesse caso a metrica aparece como indisponivel.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        caminho (str): Endpoint.
        query (dict): Filtros.

    Returns:
        object: Resposta, ou {'indisponivel': motivo}.
    """
    try:
        resposta = cliente.requisitar('GET', caminho, query=query)
    except requests.HTTPError as erro:
        return {'indisponivel': detalhar_erro(erro)}

    return resposta if isinstance(resposta, dict) else {'valor': resposta}


def cmd_analisar(cliente, args):
    """Resume a saude das automacoes numa janela de dias.

    Junta contagem por estado, execucoes, taxa de sucesso por item,
    falhas consecutivas, falhas por automacao e erros por automacao.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): Dias, automacoes, repositorio e top.
    """
    query = janela_utc(args.dias)

    if args.automacao:
        query['automations'] = args.automacao
    if args.repositorio:
        query['repository'] = args.repositorio

    metricas = {nome: consultar_metrica(cliente, caminho, query)
                for nome, caminho in METRICAS_ANALISE}

    if getattr(args, 'json', False):
        mostrar({'janela': query, 'metricas': metricas})
        return

    print('Janela: {0} a {1} (UTC){2}\n'.format(
        query['startDate'], query['endDate'],
        ' | automacoes: ' + ', '.join(args.automacao)
        if args.automacao else ''))

    estados = metricas['por_estado']
    if 'indisponivel' in estados:
        print('Tarefas por estado: indisponivel ({0})'.format(
            estados['indisponivel']))
    else:
        print('Tarefas por estado: ' + '  '.join(
            '{0}={1}'.format(k, v) for k, v in estados.items()))

    execucoes = metricas['execucoes']
    print('Execucoes: {0}'.format(
        execucoes.get('count', execucoes.get('indisponivel'))))

    sucesso = metricas['sucesso_itens']
    if 'indisponivel' not in sucesso:
        print('Itens: {0} com sucesso de {1} processados ({2}%)'.format(
            sucesso.get('itemsSuccess'), sucesso.get('itemsProcessed'),
            sucesso.get('differencePercentage')))

    for chave, titulo in (('falhas_consecutivas', 'Falhas consecutivas'),
                          ('falhas_por_automacao', 'Tarefas com falha'),
                          ('erros_por_automacao', 'Erros registrados')):
        dados = metricas[chave]
        print('\n{0} (total {1}):'.format(
            titulo, dados.get('total', dados.get('indisponivel'))))
        for item in (dados.get('items') or [])[:args.top]:
            print('  {0:>6}  {1}'.format(item.get('value'),
                                         item.get('automationLabel')))

    piores = sorted(
        (item for item in (sucesso.get('items') or [])
         if item.get('itemsProcessed')
         and item.get('itemsSuccess') != item.get('itemsProcessed')),
        key=lambda item: item['itemsSuccess'] / item['itemsProcessed'])

    if piores:
        print('\nMenor taxa de sucesso por item:')
        for item in piores[:args.top]:
            print('  {0:>6.1f}%  {1}  ({2}/{3})'.format(
                100.0 * item['itemsSuccess'] / item['itemsProcessed'],
                item.get('automationLabel'), item['itemsSuccess'],
                item['itemsProcessed']))


def cmd_diagnosticar(cliente, args):
    """Junta tudo o que explica o resultado de uma tarefa.

    Mostra a tarefa, os erros, alertas e arquivos ligados a ela, o
    estado do runner e o historico recente da mesma automacao.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        args (argparse.Namespace): ID da tarefa e dias de historico.
    """
    tarefa = cliente.requisitar('GET', '/api/v2/task/{0}'.format(args.id))
    automacao = tarefa.get('activityLabel')
    filtro = {'taskId': args.id, 'days': args.dias}
    relatorio = {
        'tarefa': tarefa,
        'erros': cliente.paginar('/api/v2/error', filtro, 20),
        'alertas': cliente.paginar('/api/v2/alerts', filtro, 20),
        'artefatos': cliente.paginar('/api/v2/artifact', filtro, 20),
        'historico': cliente.paginar(
            '/api/v2/task', {'activityLabel': automacao,
                             'days': args.dias,
                             'sort': 'dateCreation,desc'}, 10),
        'runner': None,
    }

    if tarefa.get('machineId'):
        try:
            relatorio['runner'] = cliente.requisitar(
                'GET', '/api/v2/machine/{0}'.format(tarefa['machineId']))
        except requests.HTTPError as erro:
            relatorio['runner'] = {'indisponivel': detalhar_erro(erro)}

    if getattr(args, 'json', False):
        mostrar(relatorio)
        return

    print('Tarefa {0} - {1}'.format(args.id, automacao))
    for rotulo, chave in (('Estado', 'state'), ('Final', 'finishStatus'),
                          ('Mensagem', 'finishMessage'),
                          ('Runner', 'machineId'),
                          ('Criada', 'dateCreation'),
                          ('Inicio', 'dateStartRunning'),
                          ('Atualizada', 'dateLastModified'),
                          ('Itens', lambda t: '{0} total, {1} ok, {2} falha'
                           .format(t.get('totalItems'),
                                   t.get('processedItems'),
                                   t.get('failedItems'))),
                          ('Interrompida', 'interrupted'),
                          ('Parametros', 'parameters')):
        print('  {0:12} {1}'.format(rotulo, como_texto(
            valor_de(tarefa, chave))))

    runner = relatorio['runner'] or {}
    if runner:
        print('  {0:12} online={1} status={2} heartbeat={3}'.format(
            'Runner agora', runner.get('isOnline'), runner.get('status'),
            data_curta(runner.get('lastHeartbeat'))))

    print('\nErros ({0}):'.format(len(relatorio['erros'])))
    for erro in relatorio['erros']:
        print('  #{0} {1}: {2}'.format(erro.get('id'), erro.get('type'),
                                       como_texto(erro.get('message'))))

    print('\nAlertas ({0}):'.format(len(relatorio['alertas'])))
    for alerta in relatorio['alertas']:
        print('  {0} {1}: {2}'.format(alerta.get('type'),
                                      alerta.get('title'),
                                      como_texto(alerta.get('message'))))

    print('\nArquivos ({0}):'.format(len(relatorio['artefatos'])))
    for artefato in relatorio['artefatos']:
        print('  #{0} {1}'.format(artefato.get('id'),
                                  artefato.get('fileName')))

    print('\nUltimas tarefas de {0}:'.format(automacao))
    for item in relatorio['historico']:
        print('  {0:>8}  {1:9} {2:20} {3}'.format(
            item.get('id'), item.get('state') or '',
            item.get('finishStatus') or '',
            data_curta(item.get('dateCreation'))))

    if relatorio['erros']:
        print('\nStack trace e screenshot: erro <id> [--screenshot ARQ].')


# ---------------------------------------------------------------------
# Spec local e chamada generica
# ---------------------------------------------------------------------


def carregar_spec():
    """Carrega a spec publica somada aos endpoints fora dela.

    Returns:
        tuple: (spec, notas) onde spec e um OpenAPI com os paths
            combinados e notas e o dicionario "METODO caminho" ->
            lista de observacoes curadas (descricao, exemplo).
    """
    with open(CAMINHO_SPEC, 'r', encoding='utf-8') as origem:
        spec = json.load(origem)

    notas = {}

    if os.path.isfile(CAMINHO_EXTRAS):
        with open(CAMINHO_EXTRAS, 'r', encoding='utf-8') as origem:
            extras = json.load(origem)
        # A spec oficial prevalece: os extras so preenchem operacoes que
        # ela nao tem (as notas curadas valem para todas).
        for caminho, operacoes in extras.get('paths', {}).items():
            item = spec['paths'].setdefault(caminho, {})
            for metodo, operacao in operacoes.items():
                item.setdefault(metodo, operacao)
        notas = extras.get('x-notas', {})

    return spec, notas


def iterar_operacoes(spec):
    """Percorre as operacoes da spec.

    Args:
        spec (dict): Spec OpenAPI.

    Yields:
        tuple: (METODO, caminho, operacao).
    """
    for caminho, item in sorted(spec['paths'].items()):
        for metodo in METODOS_HTTP:
            if metodo in item:
                yield metodo.upper(), caminho, item[metodo]


def resolver_ref(spec, no, profundidade=0):
    """Substitui recursivamente os "$ref" de um no da spec.

    Args:
        spec (dict): Spec OpenAPI.
        no (object): No a resolver.
        profundidade (int): Nivel atual, para evitar ciclo infinito.

    Returns:
        object: No sem referencias.
    """
    if isinstance(no, dict):
        if '$ref' in no and profundidade < 12:
            alvo = spec
            for parte in no['$ref'].lstrip('#/').split('/'):
                alvo = alvo[parte]
            return resolver_ref(spec, alvo, profundidade + 1)
        return {chave: resolver_ref(spec, valor, profundidade)
                for chave, valor in no.items()}

    if isinstance(no, list):
        return [resolver_ref(spec, item, profundidade) for item in no]

    return no


def tipo_do_schema(schema):
    """Resume o tipo de um schema em texto.

    Args:
        schema (dict): Schema ja resolvido.

    Returns:
        str: Ex.: "string", "integer<int32>", "array<string>".
    """
    tipo = schema.get('type') or 'object'

    if tipo == 'array':
        return 'array<{0}>'.format(
            tipo_do_schema(schema.get('items') or {}))

    if schema.get('format'):
        return '{0}<{1}>'.format(tipo, schema['format'])

    return tipo


def descrever_schema(schema, linhas, recuo, nivel, nivel_maximo):
    """Gera linhas de texto descrevendo os campos de um schema.

    Args:
        schema (dict): Schema ja resolvido.
        linhas (list): Lista onde as linhas sao acrescentadas.
        recuo (str): Prefixo de indentacao.
        nivel (int): Nivel atual.
        nivel_maximo (int): Nivel maximo a detalhar.
    """
    for variante in ('oneOf', 'anyOf'):
        if variante in schema:
            for numero, opcao in enumerate(schema[variante], 1):
                linhas.append('{0}({1} opcao {2})'.format(
                    recuo, variante, numero))
                descrever_schema(opcao, linhas, recuo + '  ', nivel,
                                 nivel_maximo)
            return

    if schema.get('type') == 'array' and 'properties' not in schema:
        schema = schema.get('items') or {}

    obrigatorios = set(schema.get('required') or [])

    for nome, campo in (schema.get('properties') or {}).items():
        extras = []
        if nome in obrigatorios:
            extras.append('OBRIGATORIO')
        enum = campo.get('enum') or (campo.get('items') or {}).get('enum')
        if enum:
            extras.append('enum=' + ','.join(str(e) for e in enum))
        linhas.append('{0}{1} ({2}){3}'.format(
            recuo, nome, tipo_do_schema(campo),
            ' [' + '; '.join(extras) + ']' if extras else ''))

        interno = campo.get('items') if campo.get('type') == 'array' \
            else campo
        if (interno or {}).get('properties') and nivel < nivel_maximo:
            descrever_schema(interno, linhas, recuo + '    ', nivel + 1,
                             nivel_maximo)


def achar_operacao(spec, metodo, caminho):
    """Localiza uma operacao pelo metodo e caminho (aceita IDs reais).

    Args:
        spec (dict): Spec OpenAPI.
        metodo (str): Verbo HTTP.
        caminho (str): Caminho literal ou com valores
            (ex.: "/api/v2/task/123").

    Returns:
        tuple: (caminho_modelo, operacao).

    Raises:
        SystemExit: Se a operacao nao existir na spec.
    """
    metodo = metodo.lower()
    caminho = normalizar_caminho(caminho)
    item = spec['paths'].get(caminho)

    if item and metodo in item:
        return caminho, item[metodo]

    candidatos = []
    for modelo, item in spec['paths'].items():
        padrao = '^' + re.sub(r'\{[^}]+\}', r'[^/]+', modelo) + '/?$'
        if metodo in item and re.match(padrao, caminho):
            candidatos.append((modelo.count('{'), modelo, item[metodo]))

    if candidatos:
        _, modelo, operacao = sorted(candidatos)[0]
        return modelo, operacao

    raise SystemExit('Operacao nao encontrada: {0} {1}. Procure com o '
                     'comando endpoints.'.format(metodo.upper(), caminho))


def cmd_endpoints(cliente, args):
    """Procura endpoints na spec local por palavras.

    Args:
        cliente (ClienteMaestro): Nao usado (comando offline).
        args (argparse.Namespace): Termos e filtro de metodo.
    """
    spec, notas = carregar_spec()
    termos = [normalizar(termo) for termo in args.termos]
    total = 0

    for metodo, caminho, operacao in iterar_operacoes(spec):
        if args.metodo and metodo != args.metodo.upper():
            continue

        nomes = [n['nome'] for n in
                 notas.get('{0} {1}'.format(metodo, caminho), [])]
        resumo = ' / '.join(nomes) or operacao.get('summary') \
            or operacao.get('operationId') or ''
        texto = normalizar(' '.join([
            metodo, caminho, resumo, ' '.join(operacao.get('tags') or []),
            operacao.get('operationId') or '']))

        if all(termo in texto for termo in termos):
            marcas = ''
            if operacao.get('deprecated'):
                marcas += ' [DEPRECATED]'
            if operacao.get('x-fora-da-spec'):
                marcas += ' [fora da spec]'
            print('{0:6} {1}  | {2}{3}'.format(metodo, caminho, resumo,
                                               marcas))
            total += 1

    print('-- {0} operacao(oes)'.format(total))


def cmd_describe(cliente, args):
    """Descreve parametros, corpo e observacoes de uma operacao.

    Args:
        cliente (ClienteMaestro): Nao usado (comando offline).
        args (argparse.Namespace): Metodo, caminho e profundidade.
    """
    spec, notas = carregar_spec()
    modelo, operacao = achar_operacao(spec, args.metodo, args.caminho)
    operacao = resolver_ref(spec, operacao)
    metodo = args.metodo.upper()
    linhas = ['{0} {1}'.format(metodo, modelo),
              'operationId: {0}'.format(operacao.get('operationId', '-'))]

    if operacao.get('deprecated'):
        linhas.append('DEPRECATED na propria spec.')
    if operacao.get('x-fora-da-spec'):
        linhas.append('Fora do OpenAPI publico (mapeado do SDK/uso).')

    parametros = [p for p in operacao.get('parameters') or []
                  if p.get('name', '').lower() not in HEADERS_IGNORADOS]

    if parametros:
        linhas.append('\nParametros:')

    for parametro in parametros:
        schema = parametro.get('schema') or {}
        local = parametro.get('in')
        if local == 'query' and schema.get('properties'):
            linhas.append('  [query, campos de {0}]'.format(
                parametro.get('name')))
            descrever_schema(schema, linhas, '    ', 0, 0)
            continue
        linhas.append('  [{0}] {1} ({2}){3}{4}'.format(
            local, parametro.get('name'), tipo_do_schema(schema),
            ' OBRIGATORIO' if parametro.get('required') else '',
            ': ' + parametro['description']
            if parametro.get('description') else ''))

    for tipo, conteudo in ((operacao.get('requestBody') or {})
                           .get('content') or {}).items():
        schema = conteudo.get('schema') or {}
        campos = schema.get('properties') or {}
        if campos.get('file', {}).get('format') == 'binary' \
                or schema.get('format') == 'byte':
            linhas.append('\nCorpo: upload multipart/form-data -> use '
                          'call ... --arquivo file=<caminho>')
            continue
        if schema:
            linhas.append('\nCorpo ({0}):'.format(tipo))
            descrever_schema(schema, linhas, '  ', 0, args.profundidade)

    if args.resposta:
        sucesso = (operacao.get('responses') or {}).get('200') or {}
        for conteudo in (sucesso.get('content') or {}).values():
            linhas.append('\nResposta 200:')
            descrever_schema(conteudo.get('schema') or {}, linhas, '  ',
                             0, args.profundidade)

    for nota in notas.get('{0} {1}'.format(metodo, modelo), []):
        linhas.append('\n== {0} =='.format(nota['nome']))
        if nota.get('descricao'):
            linhas.append(nota['descricao'])
        for observacao in nota.get('observacoes', []):
            linhas.append('* ' + observacao)
        if nota.get('query_sugerida'):
            linhas.append('Query sugerida: ' + json.dumps(
                nota['query_sugerida'], ensure_ascii=False))
        if 'exemplo' in nota:
            linhas.append('Exemplo de corpo:')
            linhas.append(json.dumps(nota['exemplo'], indent=2,
                                     ensure_ascii=False))

    print('\n'.join(linhas))


def resumir_objeto(objeto, limite=12):
    """Resume um objeto da API em poucas linhas legiveis.

    Args:
        objeto (object): Resposta da API.
        limite (int): Maximo de campos mostrados.

    Returns:
        list: Linhas "campo: valor".
    """
    if isinstance(objeto, list):
        return ['{0} registro(s)'.format(len(objeto))]

    if not isinstance(objeto, dict):
        return [como_texto(objeto)]

    linhas = ['{0}: {1}'.format(chave, como_texto(valor))
              for chave, valor in objeto.items()
              if valor not in (None, '', [], {})]

    return linhas[:limite]


def impacto_de_exclusao(cliente, caminho, corpo):
    """Le o que um DELETE generico (ou /task/bulk) vai apagar.

    Args:
        cliente (ClienteMaestro): Cliente autenticado.
        caminho (str): Endpoint normalizado.
        corpo (object): Corpo da requisicao (ids no /task/bulk).

    Returns:
        list: Linhas descrevendo o que sera apagado.

    Raises:
        SystemExit: Se o objeto nao existir (404).
    """
    if caminho.rstrip('/').endswith('/task/bulk'):
        ids = (corpo or {}).get('labels') or []
        impacto = ['APAGA {0} tarefa(s):'.format(len(ids))]
        for id_tarefa in ids[:20]:
            try:
                tarefa = cliente.requisitar(
                    'GET', '/api/v2/task/{0}'.format(id_tarefa))
                impacto.append('  {0}  {1}  {2}/{3}  {4}'.format(
                    id_tarefa, tarefa.get('activityLabel'),
                    tarefa.get('state'), tarefa.get('finishStatus') or '-',
                    data_curta(tarefa.get('dateCreation'))))
            except requests.HTTPError as erro:
                impacto.append('  {0}  (nao lida: {1})'.format(
                    id_tarefa, detalhar_erro(erro)[:60]))
        if len(ids) > 20:
            impacto.append('  ... e mais {0}.'.format(len(ids) - 20))
        return impacto

    try:
        objeto = cliente.requisitar('GET', caminho)
    except requests.HTTPError as erro:
        resposta = erro.response
        if resposta is not None and resposta.status_code == 404:
            raise SystemExit('{0} nao existe no ambiente {1}; nada foi '
                             'apagado.'.format(caminho,
                                               cliente.nome_ambiente))
        return ['APAGA {0}.'.format(caminho),
                '(nao foi possivel ler o objeto antes: {0}; confira '
                'com describe/endpoints)'.format(detalhar_erro(erro)[:80])]

    if '/credential/' in caminho:
        if isinstance(objeto, dict) and 'secrets' in objeto:
            objeto = mascarar_segredos(objeto)
        elif '/key/' in caminho:
            objeto = '(valor da chave oculto)'

    return ['APAGA {0}:'.format(caminho)] + [
        '  ' + linha for linha in resumir_objeto(objeto)]


def cmd_call(cliente, args):
    """Chama qualquer endpoint da API.

    DELETE e exclusao em lote exigem --yes. Com --dry-run mostra o que
    seria enviado sem tocar no Maestro.

    Args:
        cliente (ClienteMaestro): Cliente autenticado (None no
            dry-run).
        args (argparse.Namespace): Metodo, caminho, query, corpo,
            arquivos e opcoes.
    """
    metodo = args.metodo.upper()
    caminho = normalizar_caminho(args.caminho)
    query = ler_pares(args.query)
    corpo = ler_corpo(args.body)
    arquivos = ler_pares(args.arquivo)

    if args.dry_run:
        servidor = carregar_config()['servidor'].rstrip('/')
        mostrar({'metodo': metodo, 'url': servidor + caminho,
                 'query': query, 'corpo': corpo, 'arquivos': arquivos})
        return

    destrutivo = metodo == 'DELETE' or caminho.rstrip('/').endswith(
        '/task/bulk')

    if destrutivo and not args.yes:
        exigir_confirmacao(args, '{0} {1} ({2})'.format(
            metodo, caminho, cliente.nome_ambiente),
            impacto_de_exclusao(cliente, caminho, corpo))

    if args.todas and metodo == 'GET':
        mostrar(cliente.paginar(caminho, query, args.limite))
        return

    mostrar(cliente.requisitar(metodo, caminho, query=query or None,
                               corpo=corpo, arquivos=arquivos or None,
                               saida=args.saida))


def cmd_indice(cliente, args):
    """Regenera o references/endpoints.md a partir da spec local.

    Args:
        cliente (ClienteMaestro): Nao usado (comando offline).
        args (argparse.Namespace): Argumentos gerais.
    """
    total = gerar_indice()
    print('Indice com {0} operacoes gravado em {1}.'.format(
        total, CAMINHO_INDICE))


def gerar_indice():
    """Grava o references/endpoints.md a partir da spec local.

    Returns:
        int: Quantidade de operacoes no indice.
    """
    spec, notas = carregar_spec()
    grupos = {}

    for metodo, caminho, operacao in iterar_operacoes(spec):
        tag = (operacao.get('tags') or ['outros'])[0]
        nomes = [n['nome'] for n in
                 notas.get('{0} {1}'.format(metodo, caminho), [])]
        resumo = ' / '.join(nomes) or operacao.get('operationId') or ''
        if operacao.get('deprecated'):
            resumo += ' **(deprecated)**'
        if operacao.get('x-fora-da-spec'):
            resumo += ' *(fora da spec)*'
        grupos.setdefault(tag, []).append((caminho, metodo, resumo))

    linhas = ['# BotCity Maestro - indice de endpoints', '',
              'Gerado por `botcity.py indice` a partir de '
              '`openapi.json` + `endpoints_extras.json`. Detalhes de '
              'cada um: `botcity.py describe METODO caminho`.', '']
    total = 0

    for tag in sorted(grupos):
        linhas += ['## ' + tag, '', '| Metodo | Caminho | Resumo |',
                   '|---|---|---|']
        for caminho, metodo, resumo in sorted(grupos[tag]):
            linhas.append('| {0} | `{1}` | {2} |'.format(
                metodo, caminho, resumo))
            total += 1
        linhas.append('')

    with open(CAMINHO_INDICE, 'w', encoding='utf-8') as destino:
        destino.write('\n'.join(linhas))

    return total


# ---------------------------------------------------------------------
# Linha de comando
# ---------------------------------------------------------------------


def montar_parser():
    """Monta o parser de argumentos com todos os subcomandos.

    Cada subcomando e cada opcao aceitam o nome em portugues e em
    ingles (ex.: "tarefas" ou "tasks", "--dias" ou "--days").

    Returns:
        argparse.ArgumentParser: Parser pronto.
    """
    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument('--ambiente', '--env', default=argparse.SUPPRESS,
                       help='Ambiente do config.json (padrao: '
                            'ambiente_padrao, normalmente PROD).')
    comum.add_argument('--json', action='store_true',
                       default=argparse.SUPPRESS,
                       help='Imprime o JSON cru em vez da tabela.')

    parser = argparse.ArgumentParser(
        description='BotCity Maestro: atalhos e acesso a toda a API. '
                    'Comandos e opcoes aceitam portugues ou ingles.',
        parents=[comum])
    sub = parser.add_subparsers(dest='comando', metavar='comando')
    sub.required = True

    def novo(nome, ajuda, funcao, login=True):
        """Registra um subcomando com o alias em ingles, se houver.

        Args:
            nome (str): Nome do subcomando em portugues.
            ajuda (str): Texto de ajuda.
            funcao (callable): Funcao que executa o comando.
            login (bool): Se o comando precisa autenticar.

        Returns:
            argparse.ArgumentParser: Parser do subcomando.
        """
        aliases = list(ALIASES_COMANDOS.get(nome, ()))
        p = sub.add_parser(nome, help=ajuda, parents=[comum],
                           aliases=aliases)
        p.set_defaults(funcao=funcao, login=login)
        return p

    def busca(p):
        """Acrescenta o filtro --busca/--search.

        Args:
            p (argparse.ArgumentParser): Parser do subcomando.
        """
        p.add_argument('--busca', '--search')

    def janela(p, dias=7, limite=50):
        """Acrescenta --dias/--days e --limite/--limit.

        Args:
            p (argparse.ArgumentParser): Parser do subcomando.
            dias (int): Valor padrao de dias.
            limite (int): Valor padrao de limite.
        """
        p.add_argument('--dias', '--days', type=int, default=dias)
        p.add_argument('--limite', '--limit', type=int, default=limite)

    def flag(p, *nomes, **opcoes):
        """Acrescenta uma flag booleana.

        Args:
            p (argparse.ArgumentParser): Parser do subcomando.
            *nomes (str): Nomes da flag.
            **opcoes: Outras opcoes do add_argument.
        """
        p.add_argument(*nomes, action='store_true', **opcoes)

    def repositorio(p):
        """Acrescenta --repositorio/--repository.

        Args:
            p (argparse.ArgumentParser): Parser do subcomando.
        """
        p.add_argument('--repositorio', '--repository',
                       help='Padrao: repositorio_padrao do config.')

    # Bots e releases -------------------------------------------------

    busca(novo('bots', 'Lista bots com a versao em release.', cmd_bots))

    novo('bot', 'Versoes de um bot e qual esta em release.',
         cmd_bot).add_argument('bot')

    p = novo('baixar', 'Baixa e descompacta um release.', cmd_baixar)
    p.add_argument('bot')
    p.add_argument('--versao', '--version',
                   help='Padrao: versao em release.')
    p.add_argument('--destino', '--dest',
                   help='Pasta (ou .zip com --sem-extrair).')
    flag(p, '--sem-extrair', '--no-extract', help='So salva o .zip.')
    flag(p, '--manter-zip', '--keep-zip',
         help='Guarda o .zip ao lado da pasta extraida.')
    flag(p, '--sobrescrever', '--overwrite',
         help='Extrai por cima de pasta existente.')

    p = novo('release', 'Publica uma versao existente (rollback).',
             cmd_release)
    p.add_argument('bot')
    p.add_argument('versao')
    flag(p, '--yes')

    p = novo('atualizar-bot', 'Altera comando/tecnologia de uma versao.',
             cmd_atualizar_bot)
    p.add_argument('bot')
    p.add_argument('versao')
    p.add_argument('--comando', '--command', help='Use "" para limpar.')
    p.add_argument('--tecnologia', '--technology', choices=TECNOLOGIAS,
                   type=str.upper)
    flag(p, '--dry-run')

    p = novo('apagar-versao', 'Apaga uma versao fora de release.',
             cmd_apagar_versao)
    p.add_argument('bot')
    p.add_argument('versao')
    flag(p, '--yes')

    # Automacoes ------------------------------------------------------

    busca(novo('automacoes', 'Lista automacoes.', cmd_automacoes))

    novo('automacao', 'Cadastro de uma automacao.',
         cmd_automacao).add_argument('label')

    p = novo('editar-automacao', 'Altera campos de uma automacao.',
             cmd_editar_automacao)
    p.add_argument('label')
    p.add_argument('--set', action='append', metavar='CAMPO=VALOR')
    flag(p, '--dry-run')

    p = novo('prioridade', 'Altera a prioridade de uma automacao.',
             cmd_prioridade)
    p.add_argument('label')
    p.add_argument('prioridade', type=int)

    p = novo('exportar-automacao', 'Exporta o cadastro em JSON.',
             cmd_exportar_automacao)
    p.add_argument('label')
    p.add_argument('--saida', '--output')

    p = novo('criar-automacao', 'Cria uma automacao.', cmd_criar_automacao)
    p.add_argument('label')
    p.add_argument('--nome', '--name')
    p.add_argument('--descricao', '--description')
    p.add_argument('--tecnologia', '--technology', choices=TECNOLOGIAS,
                   type=str.upper, default='PYTHON')
    p.add_argument('--runner', action='append',
                   help='Runner (machineId) habilitado. Repetivel.')
    p.add_argument('--timeout', type=int, help='Minutos.')
    p.add_argument('--prioridade', '--priority', type=int, default=0)
    p.add_argument('--param-automacao', '--automation-param',
                   action='append', metavar='LABEL:TIPO[:obrigatorio]')
    p.add_argument('--body', help='JSON base, @arquivo ou @-.')
    repositorio(p)
    flag(p, '--dry-run')

    # Tarefas ---------------------------------------------------------

    p = novo('tarefas', 'Lista tarefas.', cmd_tarefas)
    p.add_argument('--estado', '--state', action='append',
                   help='START, RUNNING, TIMEOUT, FINISHED, CANCELED. '
                        'Repetivel.')
    p.add_argument('--automacao', '--automation',
                   help='activityLabel exato.')
    p.add_argument('--runner')
    janela(p)

    novo('tarefa', 'Detalhes de uma tarefa.', cmd_tarefa).add_argument('id')

    p = novo('criar-tarefa', 'Enfileira uma execucao.', cmd_criar_tarefa)
    p.add_argument('label')
    p.add_argument('-p', '--parametro', '--param', action='append',
                   metavar='CHAVE=VALOR')
    flag(p, '--teste', '--test')
    p.add_argument('--prioridade', '--priority', type=int, default=0)
    p.add_argument('--min-execucao', '--min-execution',
                   help='ISO 8601 em UTC.')
    flag(p, '--dry-run')

    p = novo('finalizar-tarefa', 'Encerra uma tarefa.',
             cmd_finalizar_tarefa)
    p.add_argument('id')
    p.add_argument('--status', required=True, type=str.upper,
                   choices=('SUCCESS', 'FAILED', 'PARTIALLY_COMPLETED'))
    p.add_argument('--mensagem', '--message')
    p.add_argument('--itens', '--items', metavar='TOTAL,OK,FALHA')

    for nome, funcao, ajuda in (
            ('reiniciar-tarefa', cmd_reiniciar_tarefa,
             'Recoloca a tarefa na fila.'),
            ('interromper-tarefa', cmd_interromper_tarefa,
             'Pede a interrupcao da tarefa.'),
            ('duplicar-tarefa', cmd_duplicar_tarefa,
             'Cria tarefa igual a outra.')):
        novo(nome, ajuda, funcao).add_argument('id')

    p = novo('diagnosticar', 'Tarefa + erros + alertas + runner + '
                             'historico.', cmd_diagnosticar)
    p.add_argument('id')
    p.add_argument('--dias', '--days', type=int, default=30)

    p = novo('analisar', 'Saude das automacoes (metricas do painel).',
             cmd_analisar)
    p.add_argument('--dias', '--days', type=int, default=7)
    p.add_argument('--automacao', '--automation', action='append',
                   help='Label da automacao. Repetivel.')
    p.add_argument('--top', type=int, default=10)
    repositorio(p)

    # Runners ---------------------------------------------------------

    novo('runners', 'Lista runners.', cmd_runners)

    p = novo('runner', 'Detalhes de um runner.', cmd_runner)
    p.add_argument('id')
    p.add_argument('--screenshot', metavar='ARQUIVO')
    p.add_argument('--log', metavar='ARQUIVO')

    # Agendamentos ----------------------------------------------------

    busca(novo('agendamentos', 'Lista agendamentos.', cmd_agendamentos))

    novo('agendamento', 'Detalhes de um agendamento.',
         cmd_agendamento).add_argument('id')

    for nome, funcao in (('ativar-agendamento', cmd_ativar_agendamento),
                         ('desativar-agendamento',
                          cmd_desativar_agendamento)):
        p = novo(nome, nome.replace('-', ' ').capitalize() + '.', funcao)
        p.add_argument('id')
        flag(p, '--dry-run')

    p = novo('criar-agendamento', 'Cria um agendamento (valida o cron).',
             cmd_criar_agendamento)
    p.add_argument('label', help='Label da automacao.')
    p.add_argument('--cron', required=True,
                   help='6 campos com segundos: "0 30 8 * * MON-FRI".')
    p.add_argument('-p', '--parametro', '--param', action='append',
                   metavar='CHAVE=VALOR')
    p.add_argument('--nome', '--name')
    p.add_argument('--prioridade', '--priority', type=int, default=0)
    flag(p, '--inativo', '--inactive', help='Cria desativado.')
    repositorio(p)
    flag(p, '--dry-run')
    flag(p, '--yes')

    p = novo('apagar-agendamento', 'Apaga um agendamento.',
             cmd_apagar_agendamento)
    p.add_argument('id')
    flag(p, '--yes')

    # Credenciais -----------------------------------------------------

    busca(novo('credenciais', 'Lista cofres (sem valores).',
               cmd_credenciais))

    p = novo('credencial', 'Mostra um cofre (valores mascarados).',
             cmd_credencial)
    p.add_argument('label')
    flag(p, '--mostrar', '--show', help='Exibe os valores reais.')

    p = novo('credencial-chave', 'Cria/atualiza uma chave do cofre.',
             cmd_credencial_chave)
    p.add_argument('label')
    p.add_argument('chave')
    p.add_argument('valor')

    p = novo('criar-credencial', 'Cria um cofre de credenciais.',
             cmd_criar_credencial)
    p.add_argument('label')
    p.add_argument('-s', '--segredo', '--secret', action='append',
                   metavar='CHAVE=VALOR')
    repositorio(p)
    flag(p, '--dry-run')
    flag(p, '--yes')

    p = novo('remover-chave', 'Remove uma chave de um cofre.',
             cmd_remover_chave)
    p.add_argument('label')
    p.add_argument('chave')
    flag(p, '--dry-run')
    flag(p, '--yes')

    p = novo('apagar-credencial', 'Apaga um cofre inteiro.',
             cmd_apagar_credencial)
    p.add_argument('label')
    flag(p, '--yes')

    # Datapool --------------------------------------------------------

    busca(novo('datapools', 'Lista filas.', cmd_datapools))

    novo('datapool', 'Configuracao e resumo de uma fila.',
         cmd_datapool).add_argument('label')

    p = novo('datapool-push', 'Insere item na fila.', cmd_datapool_push)
    p.add_argument('label')
    p.add_argument('-v', '--valor', '--value', action='append',
                   metavar='CAMPO=VALOR')
    p.add_argument('--prioridade', '--priority', type=int, default=0)
    flag(p, '--dry-run')

    for nome, funcao in (('ativar-datapool', cmd_ativar_datapool),
                         ('desativar-datapool', cmd_desativar_datapool)):
        p = novo(nome, nome.replace('-', ' ').capitalize() + '.', funcao)
        p.add_argument('label')
        flag(p, '--dry-run')

    p = novo('criar-datapool', 'Cria uma fila.', cmd_criar_datapool)
    p.add_argument('label')
    p.add_argument('--campo', '--field', action='append',
                   metavar='NOME:TIPO[:id][:exibir]',
                   help='TIPO: TEXT, INTEGER ou DOUBLE. Repetivel.')
    p.add_argument('--nome', '--name')
    p.add_argument('--automacao', '--automation',
                   help='Automacao padrao da fila.')
    p.add_argument('--politica', '--policy', choices=('FIFO', 'LIFO'),
                   type=str.upper, default='FIFO')
    p.add_argument('--gatilho', '--trigger', type=str.upper,
                   choices=('NEVER', 'ALWAYS', 'NO_TASK_ACTIVE'),
                   default='NEVER')
    p.add_argument('--max-tentativas', '--max-retries', type=int,
                   default=0, help='Reprocessamento automatico (0 = nao).')
    p.add_argument('--max-erros', '--max-errors', type=int, default=0,
                   help='Desativa a fila apos N erros (0 = nunca).')
    p.add_argument('--tempo-item', '--item-timeout', type=int,
                   help='Minutos ate o item virar TIMEOUT.')
    repositorio(p)
    flag(p, '--dry-run')
    flag(p, '--yes')

    p = novo('apagar-datapool', 'Apaga uma fila e os itens.',
             cmd_apagar_datapool)
    p.add_argument('label')
    flag(p, '--yes')

    # Diagnostico -----------------------------------------------------

    p = novo('erros', 'Lista erros.', cmd_erros)
    p.add_argument('--automacao', '--automation')
    p.add_argument('--tarefa', '--task')
    janela(p)

    p = novo('erro', 'Detalhes de um erro.', cmd_erro)
    p.add_argument('id')
    p.add_argument('--screenshot', metavar='ARQUIVO')

    p = novo('alertas', 'Lista alertas.', cmd_alertas)
    p.add_argument('--automacao', '--automation')
    p.add_argument('--tipo', '--type', choices=('INFO', 'WARN', 'ERROR'),
                   type=str.upper)
    p.add_argument('--tarefa', '--task')
    janela(p)

    p = novo('logs', 'Lista logs ou entradas de um log.', cmd_logs)
    p.add_argument('label', nargs='?')
    janela(p, limite=100)

    p = novo('artefatos', 'Lista arquivos de resultado.', cmd_artefatos)
    p.add_argument('--tarefa', '--task')
    p.add_argument('--automacao', '--automation')
    janela(p)

    p = novo('baixar-artefato', 'Baixa um arquivo de resultado.',
             cmd_baixar_artefato)
    p.add_argument('id')
    p.add_argument('--destino', '--dest')

    # Spec local e chamada generica -----------------------------------

    p = novo('endpoints', 'Procura endpoints na spec local.',
             cmd_endpoints, login=False)
    p.add_argument('termos', nargs='*')
    p.add_argument('--metodo', '--method')

    p = novo('describe', 'Detalha um endpoint.', cmd_describe,
             login=False)
    p.add_argument('metodo')
    p.add_argument('caminho')
    p.add_argument('--profundidade', '--depth', type=int, default=1)
    flag(p, '--resposta', '--response',
         help='Mostra tambem o schema da resposta.')

    p = novo('call', 'Chama qualquer endpoint.', cmd_call)
    p.add_argument('metodo')
    p.add_argument('caminho')
    p.add_argument('-q', '--query', action='append',
                   metavar='CHAVE=VALOR')
    p.add_argument('--body', help='JSON, @arquivo ou @- (stdin).')
    p.add_argument('--arquivo', '--file', action='append',
                   metavar='CAMPO=CAMINHO', help='Upload multipart.')
    p.add_argument('--saida', '--output',
                   help='Grava a resposta (binaria) aqui.')
    flag(p, '--todas', '--all', help='Percorre todas as paginas (GET).')
    p.add_argument('--limite', '--limit', type=int)
    flag(p, '--dry-run')
    flag(p, '--yes')

    novo('indice', 'Regenera references/endpoints.md.', cmd_indice,
         login=False)

    return parser


def main(argv=None):
    """Interpreta a linha de comando e executa o subcomando.

    Args:
        argv (list): Argumentos; se None usa sys.argv.
    """
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8', errors='replace')

    args = montar_parser().parse_args(argv)
    sem_login = not args.login or (
        args.funcao is cmd_call and args.dry_run)

    try:
        cliente = None if sem_login else ClienteMaestro(
            getattr(args, 'ambiente', None))
        args.funcao(cliente, args)
    except requests.HTTPError as erro:
        raise SystemExit(detalhar_erro(erro))
    except requests.RequestException as erro:
        raise SystemExit('Falha de comunicacao com o Maestro: {0}'
                         .format(erro))


if __name__ == '__main__':
    main()
