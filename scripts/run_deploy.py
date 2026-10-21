"""Empacota e publica uma nova versao do robo no BotCity Maestro.

Recebe o plano gerado pelo plan_deploy.py (ja revisado e confirmado),
monta o .zip apenas com os arquivos listados em "arquivos" e executa a
sequencia deploy -> upload -> release.

A lista "revisar" do plano e ignorada de proposito: se um arquivo de
la deve ir junto, ele precisa ter sido movido para "arquivos" durante
a revisao. Assim o pacote publicado e sempre exatamente o que a pessoa
aprovou na tela de confirmacao.

Uso:
    python run_deploy.py plano.json [--somente-zip]
    python run_deploy.py plan.json [--zip-only]
"""

import argparse
import json
import os
import re
import sys
import tempfile
import zipfile

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botcity_api import (  # noqa: E402
    TIMEOUT, carregar_config, detalhar_erro, montar_headers, obter_ambiente,
    realizar_login)


def parse_argumentos():
    """Le os argumentos de linha de comando.

    Returns:
        argparse.Namespace: Argumentos ja validados.
    """
    parser = argparse.ArgumentParser(
        description='Publica uma nova versao do robo no Maestro.'
    )
    parser.add_argument('plano', help='Caminho do plano JSON.')
    parser.add_argument('--somente-zip', '--zip-only', action='store_true',
                        help='Apenas monta o .zip e mostra o caminho, '
                             'sem enviar nada ao Maestro.')
    parser.add_argument('--config', default=None,
                        help='Caminho alternativo do config.json.')

    return parser.parse_args()


def carregar_plano(caminho):
    """Carrega e valida o plano de deploy.

    Args:
        caminho (str): Caminho do arquivo JSON do plano.

    Returns:
        dict: Plano carregado.

    Raises:
        SystemExit: Se faltar algum campo obrigatorio.
    """
    if not os.path.isfile(caminho):
        raise SystemExit('Plano nao encontrado: {0}'.format(caminho))

    with open(caminho, 'r', encoding='utf-8') as origem:
        plano = json.load(origem)

    obrigatorios = ('projeto', 'bot_id', 'versao_nova', 'arquivos',
                    'ambiente', 'tecnologia')
    faltando = [c for c in obrigatorios if not plano.get(c)]

    if faltando:
        raise SystemExit(
            'Plano incompleto, faltam os campos: {0}'.format(
                ', '.join(faltando)))

    return plano


def montar_zip(plano):
    """Gera o pacote .zip com os arquivos aprovados no plano.

    Args:
        plano (dict): Plano de deploy ja revisado.

    Returns:
        str: Caminho do .zip gerado.

    Raises:
        SystemExit: Se algum arquivo listado nao existir mais.
    """
    raiz = plano['projeto']
    nome = '{0}_{1}.zip'.format(
        re.sub(r'[^A-Za-z0-9_.-]+', '_', plano['bot_id']),
        re.sub(r'[^A-Za-z0-9_.-]+', '_', plano['versao_nova'])
    )
    pasta = os.path.join(tempfile.gettempdir(), 'botcity_deploy')
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, nome)

    ausentes = [rel for rel in plano['arquivos']
                if not os.path.isfile(os.path.join(raiz, rel))]

    if ausentes:
        raise SystemExit(
            'Arquivos do plano nao existem mais no projeto: '
            '{0}'.format(', '.join(ausentes[:10])))

    with zipfile.ZipFile(destino, 'w',
                         compression=zipfile.ZIP_DEFLATED) as pacote:
        for relativo in plano['arquivos']:
            pacote.write(os.path.join(raiz, relativo), relativo)

    return destino


def criar_deploy(servidor, headers, plano, organizacao):
    """Cria o registro da nova versao do bot no Maestro.

    Args:
        servidor (str): URL base do Maestro.
        headers (dict): Headers de autenticacao.
        plano (dict): Plano de deploy.
        organizacao (str): Label da organizacao.

    Returns:
        dict: DeployDTO devolvido pelo Maestro.
    """
    url = '{0}/api/v2/bot'.format(servidor)
    payload = {
        'organization': organizacao,
        'botId': plano['bot_id'],
        'version': plano['versao_nova'],
        'technology': plano['tecnologia'],
        'command': plano.get('comando'),
        'repositoryLabel': plano.get('repositorio', 'DEFAULT'),
    }

    resposta = requests.post(url, headers=headers, json=payload,
                             timeout=TIMEOUT)
    resposta.raise_for_status()

    try:
        return resposta.json()
    except ValueError:
        return {}


def enviar_pacote(servidor, headers, plano, caminho_zip):
    """Envia o .zip para a versao recem-criada.

    Args:
        servidor (str): URL base do Maestro.
        headers (dict): Headers de autenticacao sem Content-Type.
        plano (dict): Plano de deploy.
        caminho_zip (str): Caminho do pacote a enviar.

    Returns:
        None
    """
    url = '{0}/api/v2/bot/upload/{1}/version/{2}'.format(
        servidor, plano['bot_id'], plano['versao_nova'])

    with open(caminho_zip, 'rb') as pacote:
        arquivos = {'file': (os.path.basename(caminho_zip), pacote,
                             'application/zip')}
        resposta = requests.post(url, headers=headers, files=arquivos,
                                 timeout=TIMEOUT)

    resposta.raise_for_status()


def publicar_release(servidor, headers, plano, organizacao):
    """Marca a nova versao como a versao em uso pelos runners.

    Args:
        servidor (str): URL base do Maestro.
        headers (dict): Headers de autenticacao.
        plano (dict): Plano de deploy.
        organizacao (str): Label da organizacao.

    Returns:
        None
    """
    url = '{0}/api/v2/bot/release'.format(servidor)
    payload = {
        'organization': organizacao,
        'botId': plano['bot_id'],
        'version': plano['versao_nova'],
        'repositoryLabel': plano.get('repositorio', 'DEFAULT'),
    }

    resposta = requests.post(url, headers=headers, json=payload,
                             timeout=TIMEOUT)
    resposta.raise_for_status()


def main():
    """Monta o pacote e executa deploy, upload e release."""
    args = parse_argumentos()
    plano = carregar_plano(args.plano)

    caminho_zip = montar_zip(plano)
    tamanho_mb = os.path.getsize(caminho_zip) / 1024 / 1024

    if args.somente_zip:
        print('Pacote gerado: {0} ({1:.2f} MB, {2} arquivos)'.format(
            caminho_zip, tamanho_mb, len(plano['arquivos'])))
        return

    config = carregar_config(args.config)
    servidor = config['servidor'].rstrip('/')
    ambiente = obter_ambiente(config, plano['ambiente'])

    token, organizacao = realizar_login(servidor,
                                        ambiente['workspace'],
                                        ambiente['chave'])
    headers = montar_headers(token, organizacao)
    headers_upload = montar_headers(token, organizacao, json_body=False)

    try:
        criar_deploy(servidor, headers, plano, organizacao)
    except requests.HTTPError as erro:
        raise SystemExit(
            'Falha ao criar a versao {0} do bot {1}. Nada foi '
            'publicado. {2}'.format(plano['versao_nova'],
                                    plano['bot_id'],
                                    detalhar_erro(erro)))

    try:
        enviar_pacote(servidor, headers_upload, plano, caminho_zip)
    except requests.HTTPError as erro:
        raise SystemExit(
            'A versao {0} foi criada, mas o envio do pacote falhou. '
            'A versao em release continua sendo a {1}. Reenvie o '
            'pacote ou apague a versao no Maestro. {2}'.format(
                plano['versao_nova'], plano.get('versao_atual', '?'),
                detalhar_erro(erro)))

    try:
        publicar_release(servidor, headers, plano, organizacao)
    except requests.HTTPError as erro:
        raise SystemExit(
            'O pacote da versao {0} subiu, mas o release falhou. A '
            'versao em uso continua sendo a {1}; basta publicar a '
            'nova pelo Maestro. {2}'.format(
                plano['versao_nova'], plano.get('versao_atual', '?'),
                detalhar_erro(erro)))

    print('SUCESSO: {0} publicado no BotCity ({1}) na versao {2} '
          '(anterior: {3}). Pacote com {4} arquivos, {5:.2f} MB.'.format(
              plano['bot_id'], plano['ambiente'], plano['versao_nova'],
              plano.get('versao_atual') or 'nenhuma, bot novo',
              len(plano['arquivos']),
              tamanho_mb))


if __name__ == '__main__':
    main()
