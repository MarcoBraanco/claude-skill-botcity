"""Setup de primeiro uso da skill do BotCity Maestro.

Cria e mantem o config.json (por padrao em ~/.botcity/config.json),
confere se cada ambiente tem chave e testa o login. A chave de acesso
nunca e impressa: o caminho recomendado e defini-la na variavel
BOTCITY_KEY_<AMBIENTE> ou edita-la direto no arquivo, sem passar pela
conversa. Quem preferir pode informa-la com --chave.

Uso:
    python configurar.py status
    python configurar.py criar --servidor URL --workspace W [opcoes]
    python configurar.py chave PROD
    python configurar.py testar [--ambiente PROD]
    python configurar.py migrar

Todos os subcomandos tem nome em ingles: status, init, key, test,
migrate.
"""

import argparse
import getpass
import json
import os
import shutil
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botcity_api import (  # noqa: E402
    CAMINHO_CONFIG, CAMINHO_CONFIG_LEGADO, CHAVE_PENDENTE,
    PREFIXO_VARIAVEL_CHAVE, SUFIXO_PADRAO, ClienteMaestro, chave_do_ambiente,
    detalhar_erro, localizar_config)


def ler_config_existente(caminho):
    """Le o config se ele existir, sem exigir que exista.

    Args:
        caminho (str): Caminho do config.

    Returns:
        dict: Config carregado, ou dicionario vazio.
    """
    if not os.path.isfile(caminho):
        return {}

    with open(caminho, 'r', encoding='utf-8') as origem:
        return json.load(origem)


def gravar_config(caminho, config):
    """Grava o config em disco, criando a pasta se preciso.

    Args:
        caminho (str): Caminho de destino.
        config (dict): Conteudo a gravar.
    """
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)

    with open(caminho, 'w', encoding='utf-8') as destino:
        json.dump(config, destino, indent=2, ensure_ascii=False)
        destino.write('\n')


def cmd_status(args):
    """Mostra onde esta o config e o estado de cada ambiente.

    Args:
        args (argparse.Namespace): Argumentos (usa --config).
    """
    caminho = localizar_config(args.config)
    config = ler_config_existente(caminho)

    if not config:
        print('CONFIG_AUSENTE: nenhum config em {0}.\nRode: configurar.py '
              'criar --servidor URL --workspace WORKSPACE\nOs dados ficam no '
              'Maestro, menu "Ambiente do desenvolvedor" (Workspace, Login '
              'e Chave).'.format(caminho))
        return

    print('Config:          {0}'.format(caminho))
    if caminho == CAMINHO_CONFIG_LEGADO:
        print('                 (local legado, dentro da skill; rode '
              '"migrar" para mover para {0})'.format(CAMINHO_CONFIG))
    print('Servidor:        {0}'.format(config.get('servidor')))
    print('Ambiente padrao: {0}'.format(config.get('ambiente_padrao')))
    print('Repositorio:     {0}'.format(config.get('repositorio_padrao')))
    print('Sufixo versao:   "{0}"'.format(
        config.get('sufixo_versao', SUFIXO_PADRAO)))
    print('Downloads:       {0}'.format(config.get('pasta_downloads')))
    print('Raizes projetos: {0}'.format(
        ', '.join(config.get('raizes_projetos') or []) or '-'))
    print('\nAmbientes:')

    for nome, ambiente in sorted((config.get('ambientes') or {}).items()):
        _, origem = chave_do_ambiente(nome, ambiente)
        estado = {
            'variavel': 'chave OK (variavel {0}{1})'.format(
                PREFIXO_VARIAVEL_CHAVE, nome),
            'arquivo': 'chave OK (no arquivo)',
        }.get(origem, 'SEM CHAVE - defina {0}{1} ou edite o arquivo'
              .format(PREFIXO_VARIAVEL_CHAVE, nome))
        print('  {0:6} workspace={1:25} {2}'.format(
            nome, ambiente.get('workspace') or '?', estado))


def cmd_criar(args):
    """Cria o config ou acrescenta/atualiza um ambiente nele.

    Args:
        args (argparse.Namespace): Dados do servidor e do ambiente.

    Raises:
        SystemExit: Se faltar servidor ou workspace.
    """
    caminho = localizar_config(args.config)

    if caminho == CAMINHO_CONFIG_LEGADO:
        caminho = CAMINHO_CONFIG

    config = ler_config_existente(caminho)
    novo = not config
    ambiente = args.ambiente.upper()

    if args.servidor:
        config['servidor'] = args.servidor.rstrip('/')
    elif not config.get('servidor'):
        raise SystemExit('Informe --servidor (ex.: '
                         'https://SEU-WORKSPACE.botcity.dev).')

    config.setdefault('ambiente_padrao', ambiente)
    if args.padrao:
        config['ambiente_padrao'] = ambiente

    for chave, valor in (('repositorio_padrao', args.repositorio),
                         ('sufixo_versao', args.sufixo),
                         ('pasta_downloads', args.pasta_downloads)):
        if valor is not None:
            config[chave] = valor

    config.setdefault('repositorio_padrao', 'DEFAULT')
    config.setdefault('sufixo_versao', SUFIXO_PADRAO)
    config.setdefault('pasta_downloads',
                      os.path.join(os.path.expanduser('~'), 'BotCity'))

    if args.raiz_projetos:
        config['raizes_projetos'] = args.raiz_projetos
    config.setdefault('raizes_projetos', [])

    ambientes = config.setdefault('ambientes', {})
    atual = ambientes.get(ambiente, {})
    atual['workspace'] = args.workspace or atual.get('workspace')

    if not atual['workspace']:
        raise SystemExit('Informe --workspace.')

    if args.chave:
        atual['chave'] = args.chave
    else:
        atual.setdefault('chave', CHAVE_PENDENTE)

    ambientes[ambiente] = atual
    gravar_config(caminho, config)

    print('Config {0} em {1} (ambiente {2}, workspace {3}).'.format(
        'criado' if novo else 'atualizado', caminho, ambiente,
        atual['workspace']))

    _, origem = chave_do_ambiente(ambiente, atual)
    if not origem:
        print('Falta a chave de acesso do ambiente {0}. Opcoes:\n'
              '  1. (recomendado) defina a variavel de ambiente '
              '{1}{0};\n'
              '  2. edite {2} e troque "{3}" pela chave;\n'
              '  3. rode no seu terminal: python configurar.py chave {0}.'
              .format(ambiente, PREFIXO_VARIAVEL_CHAVE, caminho,
                      CHAVE_PENDENTE))

    if novo:
        print('Sufixo de versao: "{0}". Ele marca no Maestro as versoes '
              'publicadas pelo Claude (1.0.3 -> 1.0.4{0}). Para mudar: '
              'criar --sufixo "" (sem sufixo) ou outro texto.'.format(
                  config['sufixo_versao']))


def cmd_chave(args):
    """Pede a chave de um ambiente sem eco e grava no config.

    So funciona em terminal interativo, para que a chave nao passe
    pela conversa.

    Args:
        args (argparse.Namespace): Ambiente.

    Raises:
        SystemExit: Se o ambiente nao existir, sem terminal
            interativo ou sem chave digitada.
    """
    caminho = localizar_config(args.config)
    config = ler_config_existente(caminho)
    ambiente = args.ambiente.upper()

    if ambiente not in (config.get('ambientes') or {}):
        raise SystemExit('Ambiente {0} nao existe. Rode "criar" antes.'
                         .format(ambiente))

    if not sys.stdin.isatty():
        raise SystemExit(
            'Este comando precisa de um terminal interativo. Rode-o no '
            'seu proprio terminal, defina a variavel {0}{1} ou edite '
            '{2}.'.format(PREFIXO_VARIAVEL_CHAVE, ambiente, caminho))

    chave = getpass.getpass('Chave de acesso do ambiente {0} (nao '
                            'aparece na tela): '.format(ambiente)).strip()

    if not chave:
        raise SystemExit('Nenhuma chave informada. Nada mudou.')

    config['ambientes'][ambiente]['chave'] = chave
    gravar_config(caminho, config)
    print('Chave do ambiente {0} gravada em {1}.'.format(ambiente, caminho))


def cmd_testar(args):
    """Faz login no ambiente e mostra o resultado.

    Args:
        args (argparse.Namespace): Ambiente opcional.

    Raises:
        SystemExit: Se o login ou a comunicacao falharem.
    """
    try:
        cliente = ClienteMaestro(args.ambiente, args.config)
        bots = cliente.listar_bots()
    except requests.HTTPError as erro:
        raise SystemExit('Login falhou: {0}. Confira servidor, workspace '
                         'e chave.'.format(detalhar_erro(erro)))
    except requests.RequestException as erro:
        raise SystemExit('Sem comunicacao com o servidor: {0}'.format(erro))

    print('Login OK no ambiente {0}: organizacao {1}, {2} bot(s) no '
          'workspace.'.format(cliente.nome_ambiente, cliente.organizacao,
                              len(bots)))


def cmd_migrar(args):
    """Move o config legado (pasta da skill) para ~/.botcity.

    Args:
        args (argparse.Namespace): Argumentos gerais.

    Raises:
        SystemExit: Se ja existir config no destino.
    """
    if not os.path.isfile(CAMINHO_CONFIG_LEGADO):
        print('Nao ha config legado em {0}.'.format(CAMINHO_CONFIG_LEGADO))
        return

    if os.path.isfile(CAMINHO_CONFIG):
        raise SystemExit('Ja existe {0}. Nada foi movido; apague um dos '
                         'dois manualmente.'.format(CAMINHO_CONFIG))

    os.makedirs(os.path.dirname(CAMINHO_CONFIG), exist_ok=True)
    shutil.move(CAMINHO_CONFIG_LEGADO, CAMINHO_CONFIG)
    print('Config movido para {0}.'.format(CAMINHO_CONFIG))


def montar_parser():
    """Monta o parser com os subcomandos em portugues e ingles.

    Returns:
        argparse.ArgumentParser: Parser pronto.
    """
    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument('--config', default=argparse.SUPPRESS,
                       help='Caminho alternativo do config.json.')

    parser = argparse.ArgumentParser(
        description='Setup da skill do BotCity Maestro.', parents=[comum])
    parser.set_defaults(config=None)
    sub = parser.add_subparsers(dest='comando', metavar='comando')
    sub.required = True

    p = sub.add_parser('status', parents=[comum],
                       help='Mostra o config e as chaves (sem valores).')
    p.set_defaults(funcao=cmd_status)

    p = sub.add_parser('criar', aliases=['init'], parents=[comum],
                       help='Cria o config ou adiciona um ambiente.')
    p.add_argument('--servidor', '--server')
    p.add_argument('--workspace')
    p.add_argument('--ambiente', '--env', default='PROD')
    p.add_argument('--chave', '--key',
                   help='Opcional: a chave fica no historico do chat.')
    p.add_argument('--padrao', '--default', action='store_true',
                   help='Torna este o ambiente padrao.')
    p.add_argument('--repositorio', '--repository')
    p.add_argument('--sufixo', '--suffix')
    p.add_argument('--pasta-downloads', '--downloads-dir')
    p.add_argument('--raiz-projetos', '--projects-root', action='append')
    p.set_defaults(funcao=cmd_criar)

    p = sub.add_parser('chave', aliases=['key'], parents=[comum],
                       help='Pede a chave sem eco (terminal interativo).')
    p.add_argument('ambiente')
    p.set_defaults(funcao=cmd_chave)

    p = sub.add_parser('testar', aliases=['test'], parents=[comum],
                       help='Testa o login.')
    p.add_argument('--ambiente', '--env', default=None)
    p.set_defaults(funcao=cmd_testar)

    p = sub.add_parser('migrar', aliases=['migrate'], parents=[comum],
                       help='Move o config legado para ~/.botcity.')
    p.set_defaults(funcao=cmd_migrar)

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
    args.funcao(args)


if __name__ == '__main__':
    main()
