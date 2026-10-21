"""Funcoes compartilhadas de acesso a API do BotCity Maestro (v2).

Este modulo concentra login, montagem de headers, as consultas de
leitura usadas pelo deploy e o cliente generico usado pelo botcity.py.
Manter isso em um lugar so evita que os scripts divirjam no formato dos
headers, que e uma fonte classica de erro 401 dificil de diagnosticar.

A spec publica declara um header "Authorization" em quase toda
operacao. Ele e residuo da geracao automatica e nenhum cliente real o
envia: a autenticacao e feita so pelos headers "token" e
"organization".
"""

import json
import os
import re
import unicodedata

import requests


TIMEOUT = 120
PASTA_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# O config fica fora da pasta da skill para sobreviver a atualizacoes
# dela (reinstalar a skill apagaria um config guardado ali dentro). O
# config.json na pasta da skill continua aceito por compatibilidade.
PASTA_USUARIO = os.path.join(os.path.expanduser('~'), '.botcity')
CAMINHO_CONFIG = os.path.join(PASTA_USUARIO, 'config.json')
CAMINHO_CONFIG_LEGADO = os.path.join(PASTA_SKILL, 'config.json')
VARIAVEL_CONFIG = 'BOTCITY_CONFIG'
PREFIXO_VARIAVEL_CHAVE = 'BOTCITY_KEY_'

# Valor que o setup grava no lugar da chave quando a pessoa prefere
# informa-la por variavel de ambiente ou editando o arquivo.
CHAVE_PENDENTE = 'DEFINA_BOTCITY_KEY_OU_COLE_A_CHAVE_AQUI'

# Mensagens de config ausente comecam com este marcador para que o
# SKILL.md saiba que e hora de rodar o setup de primeiro uso.
MARCADOR_CONFIG_AUSENTE = 'CONFIG_AUSENTE'

SUFIXO_PADRAO = 'c'

# O Maestro limita o tamanho de pagina em 400 mesmo quando se pede
# mais; paginar acima disso so devolve paginas truncadas.
TAMANHO_PAGINA = 400


def localizar_config(caminho=None):
    """Descobre qual arquivo de config deve ser usado.

    A ordem e: caminho explicito, variavel BOTCITY_CONFIG,
    ~/.botcity/config.json e, por ultimo, o config.json legado na
    pasta da skill.

    Args:
        caminho (str): Caminho informado em --config, se houver.

    Returns:
        str: Caminho escolhido (pode nao existir ainda).
    """
    if caminho:
        return os.path.abspath(caminho)

    if os.environ.get(VARIAVEL_CONFIG):
        return os.path.abspath(os.environ[VARIAVEL_CONFIG])

    if (not os.path.isfile(CAMINHO_CONFIG)
            and os.path.isfile(CAMINHO_CONFIG_LEGADO)):
        return CAMINHO_CONFIG_LEGADO

    return CAMINHO_CONFIG


def carregar_config(caminho=None):
    """Carrega o config.json da skill.

    Args:
        caminho (str): Caminho alternativo do config. Se None, segue a
            ordem de localizar_config.

    Returns:
        dict: Configuracao com servidor, ambientes e valores padrao.

    Raises:
        SystemExit: Se o arquivo nao existir, com o marcador
            CONFIG_AUSENTE e a instrucao de como rodar o setup.
    """
    caminho = localizar_config(caminho)

    if not os.path.isfile(caminho):
        raise SystemExit(
            '{0}: config nao encontrado em {1}.\n'
            'Rode o setup de primeiro uso: python {2} criar --servidor '
            'URL --workspace WORKSPACE (ou peca ao Claude "configura a '
            'skill do BotCity").'.format(
                MARCADOR_CONFIG_AUSENTE, caminho,
                os.path.join(PASTA_SKILL, 'scripts', 'configurar.py'))
        )

    with open(caminho, 'r', encoding='utf-8') as arquivo:
        return json.load(arquivo)


def chave_do_ambiente(nome_ambiente, ambiente):
    """Devolve a chave de acesso de um ambiente e de onde ela veio.

    A variavel BOTCITY_KEY_<AMBIENTE> tem prioridade sobre o campo
    "chave" do config, para que a chave nunca precise ficar em disco.

    Args:
        nome_ambiente (str): Nome do ambiente, ex.: 'PROD'.
        ambiente (dict): Dados do ambiente no config.

    Returns:
        tuple: (chave, origem) com origem 'variavel', 'arquivo' ou
            None quando nao ha chave definida.
    """
    variavel = PREFIXO_VARIAVEL_CHAVE + nome_ambiente.upper()

    if os.environ.get(variavel):
        return os.environ[variavel], 'variavel'

    chave = (ambiente or {}).get('chave')

    if chave and chave != CHAVE_PENDENTE and 'COLE_AQUI' not in chave:
        return chave, 'arquivo'

    return None, None


def obter_ambiente(config, nome_ambiente):
    """Recupera os dados de um ambiente declarado no config.

    Args:
        config (dict): Configuracao ja carregada.
        nome_ambiente (str): Nome do ambiente, ex.: 'PROD'.

    Returns:
        dict: Dados do ambiente (workspace e chave ja resolvida).

    Raises:
        SystemExit: Se o ambiente nao existir no config ou nao tiver
            chave definida.
    """
    ambientes = config.get('ambientes', {})
    ambiente = ambientes.get(nome_ambiente.upper())

    if not ambiente:
        raise SystemExit(
            'Ambiente "{0}" nao existe no config.json. '
            'Ambientes disponiveis: {1}.'.format(
                nome_ambiente, ', '.join(sorted(ambientes)) or 'nenhum'
            )
        )

    chave, _ = chave_do_ambiente(nome_ambiente, ambiente)

    if not chave:
        raise SystemExit(
            '{0}: o ambiente {1} nao tem chave de acesso. Defina a '
            'variavel {2}{1} ou preencha "chave" em {3} (veja: '
            'configurar.py status).'.format(
                MARCADOR_CONFIG_AUSENTE, nome_ambiente.upper(),
                PREFIXO_VARIAVEL_CHAVE, localizar_config()))

    resolvido = dict(ambiente)
    resolvido['chave'] = chave

    return resolvido


def realizar_login(servidor, workspace, chave):
    """Autentica no Maestro e devolve o token de acesso.

    Args:
        servidor (str): URL base do Maestro, sem barra final.
        workspace (str): Label do workspace/organizacao.
        chave (str): Chave de acesso do workspace.

    Returns:
        tuple: (token, organizacao) devolvidos pelo Maestro.

    Raises:
        RuntimeError: Se a resposta nao trouxer accessToken.
    """
    url = '{0}/api/v2/workspace/login'.format(servidor.rstrip('/'))
    payload = {'login': workspace, 'key': chave}

    resposta = requests.post(url, json=payload, timeout=TIMEOUT)
    resposta.raise_for_status()

    dados = resposta.json()
    token = dados.get('accessToken')

    if not token:
        raise RuntimeError('Login sem accessToken na resposta.')

    return token, dados.get('organizationLabel', workspace)


def montar_headers(token, organizacao, json_body=True):
    """Monta os headers exigidos pela API do Maestro.

    Args:
        token (str): Token de acesso obtido no login.
        organizacao (str): Label da organizacao.
        json_body (bool): Se True inclui Content-Type application/json.
            Deve ser False no upload multipart, porque o requests
            precisa definir o boundary sozinho.

    Returns:
        dict: Headers prontos para uso nas requisicoes.
    """
    headers = {'token': token, 'organization': organizacao}

    if json_body:
        headers['Content-Type'] = 'application/json'

    return headers


def listar_bots(servidor, headers):
    """Lista os bots do workspace, um item por botId.

    O Maestro devolve aqui apenas a versao em release de cada bot. Para
    enxergar todas as versoes cadastradas use listar_versoes.

    Args:
        servidor (str): URL base do Maestro.
        headers (dict): Headers de autenticacao.

    Returns:
        list: Lista de DeployDTO (a versao em release de cada bot).
    """
    url = '{0}/api/v2/bot'.format(servidor.rstrip('/'))
    resposta = requests.get(url, headers=headers, timeout=TIMEOUT)
    resposta.raise_for_status()

    dados = resposta.json()

    return dados if isinstance(dados, list) else []


def listar_versoes(servidor, headers, bot_id):
    """Lista todas as versoes cadastradas de um bot.

    Args:
        servidor (str): URL base do Maestro.
        headers (dict): Headers de autenticacao.
        bot_id (str): ID do bot no Maestro.

    Returns:
        list: DeployDTO de cada versao, da mais recente para a mais
            antiga.
    """
    url = '{0}/api/v2/bot/pagination'.format(servidor.rstrip('/'))
    versoes = []
    pagina = 0

    while True:
        resposta = requests.get(
            url, headers=headers, timeout=TIMEOUT,
            params={'botId': bot_id, 'page': pagina,
                    'size': TAMANHO_PAGINA, 'sort': 'lastUpdate,desc'})
        resposta.raise_for_status()
        dados = resposta.json()
        versoes.extend(item for item in dados.get('content', [])
                       if item.get('botId') == bot_id)

        if dados.get('last', True):
            return versoes

        pagina += 1


def obter_release(servidor, headers, bot_id, repositorio='DEFAULT'):
    """Consulta a versao publicada (released) de um bot.

    Args:
        servidor (str): URL base do Maestro.
        headers (dict): Headers de autenticacao.
        bot_id (str): ID do bot no Maestro.
        repositorio (str): Label do repositorio.

    Returns:
        dict: DeployDTO da versao publicada, ou None se nao houver.
    """
    url = '{0}/api/v2/bot/{1}'.format(servidor.rstrip('/'), bot_id)
    resposta = requests.get(url, headers=headers,
                            params={'repository': repositorio},
                            timeout=TIMEOUT)

    if resposta.status_code == 404:
        return None

    resposta.raise_for_status()

    dados = resposta.json()

    return dados or None


def detalhar_erro(erro):
    """Extrai a mensagem util de um erro HTTP do Maestro.

    Args:
        erro (requests.HTTPError): Excecao capturada.

    Returns:
        str: Mensagem legivel com status e corpo da resposta.
    """
    resposta = getattr(erro, 'response', None)

    if resposta is None:
        return str(erro)

    corpo = (resposta.text or '').strip()

    return 'HTTP {0}: {1}'.format(resposta.status_code, corpo[:500])


def normalizar(texto):
    """Reduz um texto a letras e numeros minusculos, sem acento.

    Serve para comparar o nome da pasta do projeto com o botId do
    Maestro, que costumam diferir em acento, espaco, hifen e caixa.

    Args:
        texto (str): Texto original.

    Returns:
        str: Texto normalizado.
    """
    if not texto:
        return ''

    sem_acento = unicodedata.normalize('NFKD', str(texto))
    sem_acento = sem_acento.encode('ascii', 'ignore').decode('ascii')

    return re.sub(r'[^a-z0-9]+', '', sem_acento.lower())


def normalizar_caminho(caminho):
    """Converte o caminho informado no path absoluto da API.

    Aceita "task/1", "api/v2/task/1" ou "/api/v2/task/1". Tambem
    desfaz a conversao automatica do Git Bash, que transforma
    "/api/v2/..." em "C:/Program Files/Git/api/v2/...".

    Args:
        caminho (str): Caminho como digitado.

    Returns:
        str: Caminho comecando com "/api/" ou "/private/".
    """
    caminho = caminho.strip().replace('\\', '/')

    for prefixo in ('/api/', '/private/'):
        posicao = caminho.find(prefixo)
        if posicao > 0 and ':' in caminho[:posicao]:
            caminho = caminho[posicao:]

    caminho = '/' + caminho.lstrip('/')

    if not (caminho.startswith('/api/')
            or caminho.startswith('/private/')):
        caminho = '/api/v2' + caminho

    return caminho


class ClienteMaestro:
    """Cliente autenticado para qualquer endpoint do Maestro.

    Faz login uma vez, guarda servidor e headers e refaz o login
    automaticamente se o token expirar no meio da execucao.
    """

    def __init__(self, nome_ambiente=None, caminho_config=None):
        """Carrega o config e autentica no ambiente escolhido.

        Args:
            nome_ambiente (str): Ambiente do config (ex.: 'PROD'). Se
                None, usa "ambiente_padrao" do config.
            caminho_config (str): Caminho alternativo do config.json.
        """
        self.config = carregar_config(caminho_config)
        self.nome_ambiente = (nome_ambiente
                              or self.config.get('ambiente_padrao')
                              or 'PROD').upper()
        self.ambiente = obter_ambiente(self.config, self.nome_ambiente)
        self.servidor = self.config['servidor'].rstrip('/')
        self.repositorio = self.config.get('repositorio_padrao',
                                           'DEFAULT')
        self.token = None
        self.organizacao = None
        self.autenticar()

    def autenticar(self):
        """Faz (ou refaz) o login e guarda token e organizacao."""
        self.token, self.organizacao = realizar_login(
            self.servidor, self.ambiente['workspace'],
            self.ambiente['chave'])

    def headers(self, json_body=True):
        """Devolve os headers de autenticacao atuais.

        Args:
            json_body (bool): Se True inclui Content-Type JSON.

        Returns:
            dict: Headers prontos para a requisicao.
        """
        return montar_headers(self.token, self.organizacao, json_body)

    def url(self, caminho):
        """Monta a URL completa de um caminho da API.

        Args:
            caminho (str): Caminho em qualquer formato aceito por
                normalizar_caminho.

        Returns:
            str: URL absoluta.
        """
        return self.servidor + normalizar_caminho(caminho)

    def requisitar(self, metodo, caminho, query=None, corpo=None,
                   arquivos=None, saida=None):
        """Executa uma chamada a API e devolve a resposta tratada.

        Args:
            metodo (str): Verbo HTTP.
            caminho (str): Caminho do endpoint.
            query (dict): Parametros de query. Listas viram parametro
                repetido (?a=1&a=2), que e o formato do Spring.
            corpo (object): Corpo JSON, ou None.
            arquivos (dict): {campo: caminho_local} para upload
                multipart. Quando informado, o corpo e ignorado.
            saida (str): Se informado, grava a resposta binaria neste
                arquivo em vez de interpreta-la.

        Returns:
            object: JSON decodificado, texto puro, None (resposta
                vazia) ou {'arquivo', 'bytes'} quando ha saida.

        Raises:
            requests.HTTPError: Se o Maestro responder com erro.
        """
        for tentativa in (1, 2):
            resposta = self._enviar(metodo, caminho, query, corpo,
                                    arquivos, saida)
            if resposta.status_code == 401 and tentativa == 1:
                self.autenticar()
                continue
            break

        resposta.raise_for_status()

        if saida:
            return self._gravar(resposta, saida)

        if not resposta.content:
            return None

        try:
            return resposta.json()
        except ValueError:
            return resposta.text

    def _enviar(self, metodo, caminho, query, corpo, arquivos, saida):
        """Monta e dispara a requisicao HTTP.

        Args:
            metodo (str): Verbo HTTP.
            caminho (str): Caminho do endpoint.
            query (dict): Parametros de query.
            corpo (object): Corpo JSON.
            arquivos (dict): Uploads multipart {campo: caminho}.
            saida (str): Destino do download, se houver.

        Returns:
            requests.Response: Resposta crua.
        """
        argumentos = {'params': query, 'timeout': TIMEOUT,
                      'stream': bool(saida)}

        if arquivos:
            abertos = {
                campo: (os.path.basename(local), open(local, 'rb'))
                for campo, local in arquivos.items()
            }
            try:
                return requests.request(
                    metodo.upper(), self.url(caminho),
                    headers=self.headers(json_body=False),
                    files=abertos, **argumentos)
            finally:
                for _, manipulador in abertos.values():
                    manipulador.close()

        if corpo is not None:
            argumentos['data'] = json.dumps(corpo).encode('utf-8')

        return requests.request(
            metodo.upper(), self.url(caminho),
            headers=self.headers(json_body=corpo is not None),
            **argumentos)

    @staticmethod
    def _gravar(resposta, saida):
        """Grava o corpo de uma resposta em disco, em blocos.

        Args:
            resposta (requests.Response): Resposta em modo stream.
            saida (str): Caminho do arquivo de destino.

        Returns:
            dict: {'arquivo': caminho absoluto, 'bytes': tamanho}.
        """
        pasta = os.path.dirname(os.path.abspath(saida))
        os.makedirs(pasta, exist_ok=True)
        total = 0

        with open(saida, 'wb') as destino:
            for bloco in resposta.iter_content(chunk_size=1024 * 256):
                destino.write(bloco)
                total += len(bloco)

        return {'arquivo': os.path.abspath(saida), 'bytes': total}

    def paginar(self, caminho, query=None, limite=None):
        """Percorre um endpoint paginado e junta o "content".

        Args:
            caminho (str): Caminho do endpoint paginado.
            query (dict): Filtros adicionais.
            limite (int): Maximo de itens a devolver. None = todos.

        Returns:
            list: Itens de todas as paginas lidas.
        """
        query = dict(query or {})
        query['size'] = min(limite or TAMANHO_PAGINA, TAMANHO_PAGINA)
        itens = []
        pagina = 0

        while True:
            query['page'] = pagina
            dados = self.requisitar('GET', caminho, query=query)

            if not isinstance(dados, dict) or 'content' not in dados:
                return dados if isinstance(dados, list) else itens

            itens.extend(dados['content'])

            if limite and len(itens) >= limite:
                return itens[:limite]

            if dados.get('last', True):
                return itens

            pagina += 1

    def listar_bots(self):
        """Lista os bots do workspace (versao em release de cada um).

        Returns:
            list: DeployDTO por botId.
        """
        return listar_bots(self.servidor, self.headers())

    def listar_versoes(self, bot_id):
        """Lista todas as versoes cadastradas de um bot.

        Args:
            bot_id (str): ID do bot.

        Returns:
            list: DeployDTO de cada versao.
        """
        return listar_versoes(self.servidor, self.headers(), bot_id)

    def obter_release(self, bot_id):
        """Consulta a versao em release de um bot.

        Args:
            bot_id (str): ID do bot.

        Returns:
            dict: DeployDTO da versao em release, ou None.
        """
        return obter_release(self.servidor, self.headers(), bot_id,
                             self.repositorio)

    def baixar_pacote(self, bot_id, versao, destino):
        """Baixa o pacote (.zip) de uma versao do bot.

        O Maestro encontra o arquivo pelo nome "<botId>.zip"; com
        "bot.zip" costuma responder 404. Os outros nomes ficam como
        reserva para pacotes enviados com nome diferente.

        Args:
            bot_id (str): ID do bot.
            versao (str): Versao a baixar.
            destino (str): Caminho do arquivo local a gravar.

        Returns:
            dict: {'arquivo', 'bytes'} do pacote baixado.

        Raises:
            requests.HTTPError: Se nenhum nome de arquivo funcionar.
        """
        caminho = '/api/v2/bot/{0}/version/{1}/download'.format(
            bot_id, versao)
        nomes = ('{0}.zip'.format(bot_id), 'bot.zip',
                 '{0}_{1}.zip'.format(bot_id, versao))
        ultimo_erro = None

        for nome in nomes:
            try:
                return self.requisitar('GET', caminho,
                                       query={'fileName': nome},
                                       saida=destino)
            except requests.HTTPError as erro:
                resposta = erro.response
                if resposta is None or resposta.status_code != 404:
                    raise
                ultimo_erro = erro

        raise ultimo_erro
