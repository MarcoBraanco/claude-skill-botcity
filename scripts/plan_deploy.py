"""Monta o plano de deploy de um robo no BotCity Maestro.

Este script e somente leitura: ele descobre qual bot do Maestro
corresponde ao projeto, qual versao esta publicada hoje, calcula a
proxima versao e classifica os arquivos do projeto entre "vai no zip",
"fica de fora" e "precisa de decisao humana". Nada e enviado ao
Maestro aqui -- a publicacao fica no run_deploy.py, executado depois
que a pessoa confirmar o plano.

Uso:
    python plan_deploy.py --projeto "C:/Projetos/MeuRobo" \
        [--nome "nome do bot"] [--ambiente PROD] [--bump patch] \
        [--saida plano.json]

    Bot que ainda nao existe no Maestro (primeira versao):
    python plan_deploy.py --projeto "C:/Projetos/MeuRobo" --novo \
        --nome MEU_ROBO [--tecnologia PYTHON] [--comando "python bot.py"]

As opcoes tambem aceitam o nome em ingles (--project, --name, --env,
--new, --technology, --command, --suffix, --output).
"""

import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botcity_api import (  # noqa: E402
    SUFIXO_PADRAO, carregar_config, listar_bots, listar_versoes,
    montar_headers, normalizar, obter_ambiente, obter_release, realizar_login)


PASTAS_EXCLUIDAS = {
    'venv', '.venv', 'env', 'virtualenv', 'site-packages',
    '__pycache__', '.git', '.github', '.gitlab', '.svn', '.hg',
    '.idea', '.vscode', '.vs', 'node_modules', '.pytest_cache',
    '.mypy_cache', '.ruff_cache', 'htmlcov', '.tox', 'dist', 'build',
    '.eggs', 'tests', 'test', 'testes', 'docs', 'doc', 'documentacao',
    'logs', 'log', 'temp', 'tmp', 'output', 'outputs', 'saida',
    'saidas', 'resultado', 'resultados', 'relatorio', 'relatorios',
    'evidencia', 'evidencias', 'backup', 'backups', 'downloads',
    '.claude', '.ipynb_checkpoints', '.versoes',
}

# Pastas que o proprio robo cria enquanto roda e que nao tem nome
# fixo. O caso mais comum e o perfil do navegador do Selenium
# (".chrome-profile-rpa" e variantes): sao milhares de arquivos de
# cache, e o perfil guarda cookies e tokens de sessao de verdade --
# empacotar isso vaza credencial junto com o codigo.
PADROES_PASTA_EXCLUIDA = (
    re.compile(r'(chrome|edge|firefox|browser)[-_ ]?profile'),
    re.compile(r'profile[-_ ]?(rpa|selenium|bot)'),
    re.compile(r'user[-_ ]?data([-_ ]?dir)?$'),
    re.compile(r'(driver|webdriver)[-_ ]?cache'),
    re.compile(r'^\.(wdm|playwright|cache|pytest_cache)$'),
    re.compile(r'ms-playwright'),
)

EXTENSOES_EXCLUIDAS = {
    '.pyc', '.pyo', '.log', '.bak', '.swp', '.tmp', '.orig', '.rej',
    '.zip', '.rar', '.7z', '.tar', '.gz', '.whl', '.egg', '.md',
    '.rst', '.pdf', '.mp4', '.avi', '.mov', '.dll_backup',
    # Metadado do BotCity Studio (caminhos de source/resource do
    # projeto). Serve a IDE, nao ao runner.
    '.botproj',
}

NOMES_EXCLUIDOS = {
    '.gitignore', '.gitattributes', '.dockerignore', '.editorconfig',
    '.flake8', '.pylintrc', 'pytest.ini', 'tox.ini', 'setup.cfg',
    '.ds_store', 'thumbs.db', 'desktop.ini', '.coverage',
}

# Codigo e manifesto de dependencia: o robo nao roda sem isso. Os
# lock files entram junto porque sao parte da resolucao de versoes.
NOMES_SEMPRE_INCLUIDOS = {
    'requirements.txt', 'pyproject.toml', 'setup.py', 'poetry.lock',
    'uv.lock', 'pipfile', 'pipfile.lock',
}

EXTENSOES_SEMPRE_INCLUIDAS = {'.py'}

# Arquivos que podem ou nao ser necessarios em execucao. O script
# procura referencias a eles no codigo: com referencia entram no zip,
# sem referencia sobem para revisao humana.
EXTENSOES_REVISAO = {
    '.json', '.ini', '.yaml', '.yml', '.toml', '.cfg', '.txt',
    '.csv', '.xlsx', '.xls', '.xlsm', '.png', '.jpg', '.jpeg',
    '.gif', '.bmp', '.ico', '.docx', '.pptx', '.sql', '.html',
    '.xml', '.pem', '.crt', '.key', '.p12', '.pfx', '.db',
    '.sqlite', '.sqlite3', '.exe', '.dll', '.bat', '.ps1', '.sh',
}

# Marca arquivos que carregam segredo. Isso nao impede a inclusao: se
# o robo usa o arquivo, ele precisa subir junto, senao a execucao
# quebra em producao. A marca serve para o arquivo aparecer nomeado na
# tela de confirmacao, em vez de passar escondido no meio da lista.
# O trecho (^|/) e o que faz um .env em subpasta ser pego -- ancorar
# so no inicio deixaria passar "src/integracao/.env".
PADRAO_SENSIVEL = re.compile(
    r'(senha|password|secret|credential|credencial|token|apikey|'
    r'api[_-]?key|\.pem$|\.key$|\.p12$|\.pfx$|'
    r'(^|/)\.env|(^|/)\.netrc)',
    re.IGNORECASE
)

EXTENSOES_CODIGO = {'.py', '.bat', '.ps1', '.sh', '.cmd'}

ENTRADAS_PROVAVEIS = ('main.py', 'bot.py', '__main__.py', 'run.py',
                      'app.py', 'start.py', 'executar.py')

# Quem usa python-dotenv chama load_dotenv() sem citar o nome do
# arquivo, entao a busca por referencia nunca acha o ".env". Estes
# sinais no codigo valem como prova de que o arquivo e usado.
SINAIS_DOTENV = ('load_dotenv', 'dotenv', 'environ', 'getenv')

LIMITE_AVISO_BYTES = 50 * 1024 * 1024

# Acima disso a fila de revisao deixou de ser uma lista de decisoes e
# virou sintoma de uma pasta inteira escapando da classificacao.
LIMITE_REVISAO = 40

# Abaixo deste score o nome do projeto nao lembra o botId o bastante
# para decidir sozinho.
SCORE_MINIMO = 0.85

# Se o segundo colocado esta a menos que isto do primeiro, os dois sao
# plausiveis. E o caso classico de familia de bots ("ROBO_NFE_1" e
# "ROBO_NFE_2"), em que a pasta so tem o prefixo comum.
DIFERENCA_MINIMA = 0.10

# Versao "bem comportada": numeros separados por ponto, com sufixo de
# letras opcional. Qualquer coisa fora disso (ex.: "1.0EXECUNICA")
# carrega significado que o incremento automatico joga fora.
PADRAO_VERSAO = re.compile(r'^\d+(?:\.\d+)*[A-Za-z]*$')


def parse_argumentos():
    """Le os argumentos de linha de comando.

    Returns:
        argparse.Namespace: Argumentos ja validados.
    """
    parser = argparse.ArgumentParser(
        description='Planeja o deploy de um robo no BotCity Maestro.'
    )
    parser.add_argument('--projeto', '--project', required=True,
                        help='Pasta raiz do projeto do robo.')
    parser.add_argument('--nome', '--name', default=None,
                        help='Nome/botId informado pela pessoa. Se '
                             'omitido, usa o nome da pasta.')
    parser.add_argument('--ambiente', '--env', default=None,
                        help='Ambiente do config.json (padrao: '
                             'ambiente_padrao do config).')
    parser.add_argument('--bump', default='patch',
                        choices=('patch', 'minor', 'major'),
                        help='Parte da versao a incrementar.')
    parser.add_argument('--sufixo', '--suffix', default=None,
                        help='Sufixo da versao (padrao: sufixo_versao '
                             'do config, normalmente "c").')
    parser.add_argument('--novo', '--new', action='store_true',
                        help='Bot que ainda nao existe no Maestro: '
                             'publica a primeira versao com o botId '
                             'de --nome.')
    parser.add_argument('--tecnologia', '--technology', default=None,
                        type=str.upper,
                        choices=('PYTHON', 'JAVA', 'JAVASCRIPT',
                                 'COMMAND'),
                        help='Padrao: a do release atual (ou PYTHON '
                             'em bot novo).')
    parser.add_argument('--comando', '--command', default=None,
                        help='Comando de execucao. Padrao: o do '
                             'release atual ou o ponto de entrada '
                             'encontrado no projeto.')
    parser.add_argument('--saida', '--output', default=None,
                        help='Caminho do plano JSON de saida.')
    parser.add_argument('--config', default=None,
                        help='Caminho alternativo do config.json.')

    return parser.parse_args()


def pasta_descartavel(nome):
    """Diz se uma pasta deve ser podada da varredura.

    Args:
        nome (str): Nome da pasta, sem caminho.

    Returns:
        bool: True se a pasta nao deve entrar no pacote.
    """
    minusculo = nome.lower()

    if minusculo in PASTAS_EXCLUIDAS:
        return True

    return any(padrao.search(minusculo)
               for padrao in PADROES_PASTA_EXCLUIDA)


def coletar_codigo(raiz):
    """Le o conteudo dos arquivos de codigo do projeto.

    O texto concatenado e usado para descobrir se um arquivo de apoio
    (imagem, planilha, .ini) e realmente usado pelo robo.

    Args:
        raiz (str): Pasta raiz do projeto.

    Returns:
        str: Conteudo de todos os arquivos de codigo, em minusculas.
    """
    partes = []

    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = [s for s in subpastas
                        if not pasta_descartavel(s)]

        for arquivo in arquivos:
            if os.path.splitext(arquivo)[1].lower() in EXTENSOES_CODIGO:
                caminho = os.path.join(pasta, arquivo)
                try:
                    with open(caminho, 'r', encoding='utf-8',
                              errors='ignore') as origem:
                        partes.append(origem.read())
                except OSError:
                    continue

    return '\n'.join(partes).lower()


def usa_dotenv(codigo):
    """Diz se o codigo carrega variaveis de um arquivo .env.

    Args:
        codigo (str): Conteudo concatenado do codigo, em minusculas.

    Returns:
        bool: True se houver sinal de uso de python-dotenv.
    """
    return any(sinal in codigo for sinal in SINAIS_DOTENV)


def esta_referenciado(caminho_relativo, codigo):
    """Verifica se um arquivo aparece citado no codigo do robo.

    Procura tanto pelo nome completo quanto pelo nome sem extensao,
    porque e comum o codigo montar o caminho com os.path.join ou
    referenciar imagens pelo rotulo do recurso.

    Args:
        caminho_relativo (str): Caminho do arquivo dentro do projeto.
        codigo (str): Conteudo concatenado do codigo, em minusculas.

    Returns:
        bool: True se houver alguma mencao ao arquivo.
    """
    nome = os.path.basename(caminho_relativo).lower()
    sem_extensao = os.path.splitext(nome)[0]
    pasta = os.path.dirname(caminho_relativo).replace('\\', '/')

    if nome.startswith('.env'):
        return usa_dotenv(codigo)

    if nome and nome in codigo:
        return True

    if len(sem_extensao) >= 4 and sem_extensao in codigo:
        return True

    if pasta and pasta.lower() in codigo:
        return True

    return False


def classificar_arquivos(raiz):
    """Separa os arquivos do projeto entre incluir, revisar e excluir.

    A regra de fundo e "so vai o que o robo precisa para rodar".
    Codigo e dependencias entram sempre; lixo de ambiente, saidas e
    documentacao saem sempre; o meio-termo (planilhas, imagens,
    arquivos de configuracao) entra se o codigo citar, e vira pendencia
    de revisao se ninguem citar.

    Args:
        raiz (str): Pasta raiz do projeto.

    Returns:
        tuple: (incluir, revisar, excluidos, total_bytes) onde incluir
            e uma lista de caminhos relativos, revisar uma lista de
            dicionarios e excluidos um resumo por motivo.
    """
    codigo = coletar_codigo(raiz)
    incluir = []
    revisar = []
    excluidos = {}
    total = 0

    for pasta, subpastas, arquivos in os.walk(raiz):
        podadas = [s for s in subpastas if pasta_descartavel(s)]
        subpastas[:] = [s for s in subpastas
                        if not pasta_descartavel(s)]

        for podada in podadas:
            chave = 'pasta {0}/'.format(podada)
            excluidos[chave] = excluidos.get(chave, 0) + 1

        for arquivo in arquivos:
            caminho = os.path.join(pasta, arquivo)
            relativo = os.path.relpath(caminho, raiz).replace('\\', '/')
            nome = arquivo.lower()
            extensao = os.path.splitext(nome)[1]

            sensivel = bool(PADRAO_SENSIVEL.search(relativo))

            # A exclusao por nome vem antes da inclusao por extensao
            # de proposito: eslint.config.js e jest.config.js sao .js,
            # mas servem ao desenvolvimento, nao a execucao.
            if nome in NOMES_EXCLUIDOS or extensao in EXTENSOES_EXCLUIDAS:
                chave = extensao or nome
                excluidos[chave] = excluidos.get(chave, 0) + 1
                continue

            if nome.startswith('readme') or nome.startswith('license'):
                excluidos['documentacao'] = (
                    excluidos.get('documentacao', 0) + 1)
                continue

            if (nome in NOMES_SEMPRE_INCLUIDOS
                    or extensao in EXTENSOES_SEMPRE_INCLUIDAS):
                incluir.append(relativo)
                total += tamanho(caminho)
                continue

            if extensao in EXTENSOES_REVISAO or sensivel:
                if esta_referenciado(relativo, codigo):
                    incluir.append(relativo)
                    total += tamanho(caminho)
                else:
                    revisar.append({
                        'caminho': relativo,
                        'tamanho_bytes': tamanho(caminho),
                        'referenciado_no_codigo': esta_referenciado(
                            relativo, codigo),
                        'sensivel': sensivel,
                    })
                continue

            revisar.append({
                'caminho': relativo,
                'tamanho_bytes': tamanho(caminho),
                'referenciado_no_codigo': esta_referenciado(
                    relativo, codigo),
                'sensivel': sensivel,
            })

    resumo = [{'motivo': chave, 'quantidade': valor}
              for chave, valor in sorted(excluidos.items())]

    return sorted(incluir), revisar, resumo, total


def tamanho(caminho):
    """Devolve o tamanho de um arquivo em bytes, tolerando erro.

    Args:
        caminho (str): Caminho completo do arquivo.

    Returns:
        int: Tamanho em bytes, ou 0 se nao for possivel ler.
    """
    try:
        return os.path.getsize(caminho)
    except OSError:
        return 0


def candidatos_de_nome(raiz, nome_informado):
    """Reune os nomes que podem identificar o robo no Maestro.

    Args:
        raiz (str): Pasta raiz do projeto.
        nome_informado (str): Nome passado pela pessoa, se houver.

    Returns:
        list: Nomes candidatos, do mais confiavel para o menos.
    """
    candidatos = []

    if nome_informado:
        candidatos.append(nome_informado)

    candidatos.append(os.path.basename(os.path.abspath(raiz)))

    for arquivo in ('bot.json', 'botcity.json', '.botcity.json'):
        caminho = os.path.join(raiz, arquivo)
        if os.path.isfile(caminho):
            try:
                with open(caminho, 'r', encoding='utf-8') as origem:
                    dados = json.load(origem)
                for chave in ('botId', 'bot_id', 'id', 'name'):
                    if dados.get(chave):
                        candidatos.append(str(dados[chave]))
            except (OSError, ValueError):
                continue

    padrao = re.compile(
        r'(?:bot_?id|activity_?label|automation_?label)\s*[=:]\s*'
        r'[\'"]([^\'"]+)[\'"]',
        re.IGNORECASE
    )

    for pasta, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = [s for s in subpastas
                        if not pasta_descartavel(s)]
        for arquivo in arquivos:
            if not arquivo.lower().endswith('.py'):
                continue
            try:
                with open(os.path.join(pasta, arquivo), 'r',
                          encoding='utf-8', errors='ignore') as origem:
                    for achado in padrao.findall(origem.read()):
                        candidatos.append(achado)
            except OSError:
                continue

    vistos = []
    for item in candidatos:
        if item and item not in vistos:
            vistos.append(item)

    return vistos


def casar_bot(candidatos, bots):
    """Ordena os bots do Maestro por semelhanca com os candidatos.

    Args:
        candidatos (list): Nomes candidatos extraidos do projeto.
        bots (list): DeployDTO devolvidos pelo Maestro.

    Returns:
        list: Dicionarios {bot_id, score, casou_com}, do melhor para o
            pior, com um item por botId distinto.
    """
    ids = sorted({bot.get('botId') for bot in bots if bot.get('botId')})
    resultados = []

    for bot_id in ids:
        alvo = normalizar(bot_id)
        melhor = 0.0
        origem = ''

        for posicao, candidato in enumerate(candidatos):
            base = normalizar(candidato)
            if not base or not alvo:
                continue

            if base == alvo:
                score = 1.0
            elif base in alvo or alvo in base:
                score = 0.9
            else:
                score = difflib.SequenceMatcher(None, base, alvo).ratio()

            score -= posicao * 0.02

            if score > melhor:
                melhor = score
                origem = candidato

        resultados.append({'bot_id': bot_id,
                           'score': round(melhor, 3),
                           'casou_com': origem})

    return sorted(resultados, key=lambda item: item['score'],
                  reverse=True)


def avaliar_match(ranking):
    """Decide se o bot escolhido precisa de confirmacao humana.

    Errar o bot aqui publica o pacote de um robo por cima de outro, em
    producao. Como o custo do erro e alto e o custo de perguntar e
    baixo, qualquer duvida vira pergunta.

    Args:
        ranking (list): Candidatos ordenados por score.

    Returns:
        tuple: (precisa_confirmar, motivo). O motivo e vazio quando o
            match e seguro.
    """
    melhor = ranking[0]

    if melhor['score'] < SCORE_MINIMO:
        return True, (
            'O nome do projeto nao bate bem com nenhum botId (melhor '
            'score: {0}). Confirme qual e o bot antes de publicar.'
        ).format(melhor['score'])

    if len(ranking) > 1:
        diferenca = melhor['score'] - ranking[1]['score']
        if diferenca < DIFERENCA_MINIMA:
            return True, (
                '"{0}" e "{1}" sao candidatos igualmente plausiveis '
                '(scores {2} e {3}). Confirme qual e o bot certo.'
            ).format(melhor['bot_id'], ranking[1]['bot_id'],
                     melhor['score'], ranking[1]['score'])

    return False, ''


def proxima_versao(versao_atual, bump, sufixo, existentes):
    """Calcula a proxima versao a publicar.

    Parte da versao publicada hoje, descarta qualquer sufixo de letras,
    incrementa o trecho pedido e recoloca o sufixo. Se a versao
    resultante ja existir no Maestro, continua incrementando o patch
    ate achar uma livre -- reaproveitar um numero ja usado sobrescreve
    um pacote antigo, o que nao e o que se espera de um deploy novo.

    Args:
        versao_atual (str): Versao publicada hoje, ex.: '1.0.3'.
        bump (str): 'patch', 'minor' ou 'major'.
        sufixo (str): Sufixo a acrescentar, ex.: 'c'.
        existentes (set): Versoes ja cadastradas para o bot.

    Returns:
        str: Nova versao, ex.: '1.0.4c'.
    """
    achado = re.match(r'^(\d+(?:\.\d+)*)', versao_atual or '')
    partes = [int(p) for p in achado.group(1).split('.')] if achado \
        else [1, 0, 0]

    while len(partes) < 3:
        partes.append(0)

    if bump == 'major':
        partes = [partes[0] + 1, 0, 0]
    elif bump == 'minor':
        partes = [partes[0], partes[1] + 1, 0]
    else:
        partes = [partes[0], partes[1], partes[2] + 1]

    candidata = '{0}{1}'.format('.'.join(str(p) for p in partes), sufixo)

    while candidata in existentes:
        partes[2] += 1
        candidata = '{0}{1}'.format(
            '.'.join(str(p) for p in partes), sufixo)

    return candidata


def descobrir_comando(raiz, comando_atual):
    """Define o comando de execucao do bot.

    Args:
        raiz (str): Pasta raiz do projeto.
        comando_atual (str): Comando do deploy publicado hoje.

    Returns:
        str: Comando a usar na nova versao, ou None.
    """
    if comando_atual:
        return comando_atual

    for entrada in ENTRADAS_PROVAVEIS:
        if os.path.isfile(os.path.join(raiz, entrada)):
            return 'python {0}'.format(entrada)

    return None


def gravar_plano(plano, saida=None):
    """Grava o plano em JSON e imprime o mesmo conteudo.

    Args:
        plano (dict): Plano de deploy.
        saida (str): Caminho de destino; padrao .botcity_plano.json na
            raiz do projeto.
    """
    saida = saida or os.path.join(plano['projeto'], '.botcity_plano.json')

    with open(saida, 'w', encoding='utf-8') as destino:
        json.dump(plano, destino, indent=2, ensure_ascii=False)

    print(json.dumps(plano, indent=2, ensure_ascii=False))
    print('\nPlano gravado em: {0}'.format(saida))


def planejar_bot_novo(args, raiz, servidor, ambiente, repositorio, sufixo,
                      bots):
    """Monta o plano da primeira versao de um bot inexistente.

    Sempre exige confirmacao: criar bot com nome errado deixa um bot
    orfao no Maestro, e o nome nao vem de nenhum cadastro existente.

    Args:
        args (argparse.Namespace): Argumentos (usa nome, tecnologia,
            comando e saida).
        raiz (str): Pasta do projeto.
        servidor (str): URL do Maestro.
        ambiente (dict): Dados do ambiente.
        repositorio (str): Repositorio de destino.
        sufixo (str): Sufixo de versao.
        bots (list): Bots existentes no workspace.

    Raises:
        SystemExit: Sem --nome, ou se o botId ja existir.
    """
    if not args.nome:
        raise SystemExit('Com --novo, informe o botId em --nome.')

    parecidos = [bot.get('botId') for bot in bots
                 if normalizar(bot.get('botId')) == normalizar(args.nome)]

    if parecidos:
        raise SystemExit(
            'Ja existe bot "{0}" no workspace. Rode sem --novo para '
            'publicar uma versao nova dele.'.format(parecidos[0]))

    incluir, revisar, excluidos, total = classificar_arquivos(raiz)
    plano = {
        'ambiente': args.ambiente,
        'servidor': servidor,
        'workspace': ambiente['workspace'],
        'projeto': raiz,
        'bot_id': args.nome,
        'novo': True,
        'confianca_match': None,
        'casou_com': None,
        'precisa_confirmar_bot': True,
        'motivo_confirmacao': (
            'Bot novo: o botId "{0}" sera criado no Maestro. Confirme o '
            'nome antes de publicar.'.format(args.nome)),
        'outros_candidatos': casar_bot([args.nome], bots)[:3],
        'repositorio': repositorio,
        'tecnologia': args.tecnologia or 'PYTHON',
        'comando': args.comando or descobrir_comando(raiz, None),
        'versao_atual': None,
        'versao_nova': '1.0.0{0}'.format(sufixo),
        'versao_atual_fora_do_padrao': False,
        'versoes_existentes': [],
        'arquivos': incluir,
        'sensiveis_incluidos': [caminho for caminho in incluir
                                if PADRAO_SENSIVEL.search(caminho)],
        'revisar': sorted(revisar, key=lambda i: i['caminho']),
        'excluidos_resumo': excluidos,
        'tamanho_estimado_bytes': total,
    }

    gravar_plano(plano, args.saida)
    print('\nATENCAO - bot novo: confirme o botId "{0}", a tecnologia '
          '{1} e o comando "{2}" antes de publicar. Depois do deploy, '
          'crie a automacao que usa este bot (criar-automacao).'.format(
              plano['bot_id'], plano['tecnologia'], plano['comando']))


def main():
    """Executa o planejamento e grava o plano em JSON."""
    args = parse_argumentos()
    raiz = os.path.abspath(args.projeto)

    if not os.path.isdir(raiz):
        raise SystemExit('Projeto nao encontrado: {0}'.format(raiz))

    config = carregar_config(args.config)
    servidor = config['servidor'].rstrip('/')
    repositorio = config.get('repositorio_padrao', 'DEFAULT')
    args.ambiente = (args.ambiente or config.get('ambiente_padrao')
                     or 'PROD').upper()
    sufixo = args.sufixo if args.sufixo is not None \
        else config.get('sufixo_versao', SUFIXO_PADRAO)
    ambiente = obter_ambiente(config, args.ambiente)

    token, organizacao = realizar_login(servidor,
                                        ambiente['workspace'],
                                        ambiente['chave'])
    headers = montar_headers(token, organizacao)
    bots = listar_bots(servidor, headers)

    if args.novo:
        planejar_bot_novo(args, raiz, servidor, ambiente, repositorio,
                          sufixo, bots)
        return

    candidatos = candidatos_de_nome(raiz, args.nome)
    ranking = casar_bot(candidatos, bots)

    if not ranking:
        raise SystemExit(
            'Nenhum bot cadastrado no workspace {0}.'.format(
                ambiente['workspace']))

    escolhido = ranking[0]
    bot_id = escolhido['bot_id']
    precisa_confirmar, motivo = avaliar_match(ranking)

    # GET /api/v2/bot so traz a versao em release de cada bot; as
    # versoes antigas, que nao podem ser reaproveitadas, so aparecem
    # na listagem paginada.
    versoes = {item.get('version') for item in
               listar_versoes(servidor, headers, bot_id)
               if item.get('version')}

    release = obter_release(servidor, headers, bot_id, repositorio)

    if not release:
        raise SystemExit(
            'O bot "{0}" nao tem versao publicada no repositorio {1} '
            'do ambiente {2}. Se o bot ainda nao existe, rode de novo '
            'com --novo --nome "<botId>".'.format(
                bot_id, repositorio, args.ambiente.upper()))

    versao_atual = release.get('version') or ''
    versao_nova = proxima_versao(versao_atual, args.bump, sufixo,
                                 versoes)

    incluir, revisar, excluidos, total = classificar_arquivos(raiz)

    plano = {
        'ambiente': args.ambiente.upper(),
        'servidor': servidor,
        'workspace': ambiente['workspace'],
        'projeto': raiz,
        'bot_id': bot_id,
        'confianca_match': escolhido['score'],
        'casou_com': escolhido['casou_com'],
        'precisa_confirmar_bot': precisa_confirmar,
        'motivo_confirmacao': motivo,
        'outros_candidatos': ranking[1:4],
        'repositorio': release.get('repositoryLabel') or repositorio,
        'novo': False,
        'tecnologia': (args.tecnologia or release.get('technology')
                       or 'PYTHON'),
        'comando': args.comando or descobrir_comando(
            raiz, release.get('command')),
        'versao_atual': versao_atual,
        'versao_nova': versao_nova,
        'versao_atual_fora_do_padrao': not bool(
            PADRAO_VERSAO.match(versao_atual)),
        'versoes_existentes': sorted(versoes),
        'arquivos': incluir,
        'sensiveis_incluidos': [caminho for caminho in incluir
                                if PADRAO_SENSIVEL.search(caminho)],
        'revisar': sorted(revisar, key=lambda i: i['caminho']),
        'excluidos_resumo': excluidos,
        'tamanho_estimado_bytes': total,
    }

    gravar_plano(plano, args.saida)

    if precisa_confirmar:
        print('\nATENCAO - identificacao do bot incerta: {0}\n'
              'Pergunte antes de publicar, ou refaca o plano com '
              '--nome "<botId exato>".'.format(motivo))

    if plano['sensiveis_incluidos']:
        print('\nO pacote leva arquivo com segredo (o robo usa em '
              'execucao): {0}.\nCite na confirmacao para a pessoa '
              'saber o que esta subindo.'.format(
                  ', '.join(plano['sensiveis_incluidos'])))

    if plano['versao_atual_fora_do_padrao']:
        print('\nATENCAO - a versao publicada hoje e "{0}", que nao '
              'segue o padrao numerico. A proposta "{1}" descarta o '
              'texto do nome; confirme com a pessoa se e isso mesmo.'
              .format(versao_atual, versao_nova))

    if len(revisar) > LIMITE_REVISAO:
        print('\nATENCAO - {0} arquivos caíram na revisao. Isso quase '
              'sempre e uma pasta inteira de runtime vazando (perfil '
              'de navegador, cache, downloads), nao algo para triar um '
              'a um. Olhe as pastas de topo em "revisar" e confirme se '
              'nao ha uma delas que deveria sair inteira.'.format(
                  len(revisar)))

    if total > LIMITE_AVISO_BYTES:
        print('AVISO: pacote estimado em {0:.1f} MB. Confira se nao '
              'sobrou arquivo pesado desnecessario.'.format(
                  total / 1024 / 1024))


if __name__ == '__main__':
    main()
