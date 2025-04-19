# ---------------------------------------------
# Importação de bibliotecas necessárias
# ---------------------------------------------
import os               # Manipulação de diretórios e arquivos
import requests         # Realização de requisições HTTP
import time             # Controle de tempo (sleep)
import re               # Expressões regulares | Regular expression (Regex)
import shutil           # Operações de movimentação e cópia de arquivos

# ---------------------------------------------
# Definição de constantes de cor para terminal
# ---------------------------------------------
RED = "\033[1;31m"     # Erro
GREEN = "\033[1;32m"   # Sucesso
YELLOW = "\033[1;33m"  # Alerta / Atenção
BLUE = "\033[1;34m"    # Nome dos arquivos XML
RESET = "\033[0m"      # Reset de cor

def limpar_caut_xml():
    """Realiza o pré-processamento de arquivos XML de notas fiscais em contingência.

    Essa função varre a pasta de notas em contingência, movendo arquivos com:
    - Cancelamentos para a pasta de cancelados.
    - Problemas de EAN para a pasta de erro de EAN.
    - Problemas de alíquota (PISOutr) para a pasta de erro de alíquota.
    Além disso, retira o conteudo tag <cAut> quando possuem mais de 8 caracteres (PIX).
    """

    # Define as pastas utilizadas no tratamento
    pasta_notas = 'notas_contingencia'
    pasta_erro_ean = 'notas_erro_ean'
    pasta_erro_aliquota = 'notas_erro_aliquota'
    pasta_canceladas = 'notas_canceladas'

    prefixos_cancelados = [] # Armazena prefixos de notas canceladas

    # Contadores de ocorrências
    contador_pix = 0
    contador_ean = 0
    contador_aliquota = 0

    # Primeira varredura: identifica notas com 'Canc' e move para pasta de canceladas
    for arquivo in [f for f in os.listdir(pasta_notas) if f.endswith('.xml')]:
        caminho = os.path.join(pasta_notas, arquivo)
        if 'Canc' in arquivo:
            shutil.move(caminho, os.path.join(pasta_canceladas, arquivo))
            print(f"{YELLOW}Cancelamento detectado nota movida para notas_cancelada: {RESET}{BLUE}{arquivo}{RESET}\n")
            prefixos_cancelados.append(arquivo[:44])
            continue

    # Segunda varredura: trata arquivos restaram da primeira varredura
    for arquivo in [f for f in os.listdir(pasta_notas) if f.endswith('.xml')]:
        caminho = os.path.join(pasta_notas, arquivo)
        try:
            prefixo_arquivo = arquivo[:44]

            # Usa o prefixo da primeira varredura para verificar se a nota é um cancelamento
            if prefixo_arquivo in prefixos_cancelados:
                shutil.copy2(caminho, os.path.join(pasta_canceladas, arquivo))
                print(f"{YELLOW}Cancelamento detectado nota movida para notas_cancelada: {RESET}{BLUE}{arquivo}{RESET}\n")
                continue

            with open(caminho, 'r', encoding='utf-8') as f:
                content = f.read()

            # Busca por notas com EAN vazio e move para pasta de erro de EAN
            if ('<cEAN>Sem EAN</cEAN>' in content or '<cEANTrib>Sem EAN</cEANTrib>' in content):
                shutil.move(caminho, os.path.join(pasta_erro_ean, arquivo))
                contador_ean += 1
                continue

            # Verifica se contem a TAG <PISOutr>, caso sim envia para pasta de erro de aliquota
            if '<PISOutr>' in content:
                shutil.move(caminho, os.path.join(pasta_erro_aliquota, arquivo))
                contador_aliquota += 1
                continue

            # Tratamento da retirada do <CAut> das notas PIX
            if '<cAut>' in content:
                # Substitui todos os <cAut> com mais de 8 caracteres por vazio
                novos_caut = re.findall(r'<cAut>(.*?)</cAut>', content)
                for valor in novos_caut:
                    if len(valor.strip()) > 8:
                        content = content.replace(f'<cAut>{valor}</cAut>', '<cAut></cAut>')
                        contador_pix += 1

                # Sobrescreve o arquivo com a versão corrigida
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(content)

        except Exception as e:
            print(f"{RED}Erro ao processar arquivo {YELLOW}{arquivo}{RESET}: {RED}{str(e)}{RESET}\n")

    # Impressão de resumo no terminal
    if contador_pix > 0:
        print(f"{GREEN}Pix detectado → {contador_pix} ocorrência(s){RESET}")
    if contador_ean > 0:
        print(f"{YELLOW}Erro de EAN → {contador_ean} arquivo(s) afetado(s){RESET}")
    if contador_aliquota > 0:
        print(f"{YELLOW}Erro de alíquota (PISOutr) → {contador_aliquota} arquivo(s) afetado(s){RESET}")

    print(f"\n{GREEN}Tratamento dos dados finalizado com sucesso.{RESET}")

def enviar_contingencia_lote() -> dict:
    """Realiza a execução da tarefa de envio da nota fiscal para o sistema SAP.

    A função coleta todos os arquivos XML da pasta de contingência, trata o conteúdo
    para garantir o formato adequado, monta um envelope SOAP e envia ao SAP PI via HTTP.

    Raises:
        Exception: Caso o envio falhe ou o SAP retorne erro.

    Returns:
        dict: Retorna o dicionário com os dados do processamento para a situação específica da nota fiscal.
    """


    # ---------------------------------------------
    # Credenciais para envio
    # ---------------------------------------------
    sap_user = "integragn"
    sap_pass = "gentil#2022"

    #---------------------------------------------
    # Definir a URL para envio da nota
    # ---------------------------------------------
    url = 'http://ALB-GENTIL-SAP-PRD-PI-228799892.us-east-1.elb.amazonaws.com:50000/XISOAPAdapter/MessageServlet?senderParty=PA_WEBINT&senderService=BC_WEBINT&receiverParty=&receiverService=&interface=SI_Asyn_Out_NFCe_Contingencia&interfaceNamespace=http://star-it.com/xi/NFCe_Contingencia'

    # ---------------------------------------------
    # Definir pasta das notas
    # ---------------------------------------------
    pasta_notas = 'notas_contingencia'

    # Caminho base
    caminho_base = os.path.abspath('.')
    caminho_pasta_notas = os.path.join(caminho_base, pasta_notas)

    # Listar arquivos XML
    lista_xmls = [f for f in os.listdir(caminho_pasta_notas) if f.endswith('.xml')]
    total = len(lista_xmls)

    # ---------------------------------------------
    # Loop para envio de cada XML ao SAP
    # ---------------------------------------------
    for idx, xml in enumerate(lista_xmls, start=1):
        path_xml = os.path.join(caminho_pasta_notas, xml)

        # Leitura do conteúdo do XML
        with open(path_xml, 'r', encoding='ISO-8859-1') as conteudo_xml:
            conteudo_nota_fiscal = conteudo_xml.read().replace('\n', '')

            # Tratamento do conteudo da nota
            conteudo_nota_fiscal = conteudo_nota_fiscal.replace('<NFe xmlns="http://www.portalfiscal.inf.br/nfe">', '<NFe>')
            conteudo_nota_fiscal = conteudo_nota_fiscal.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            conteudo_nota_fiscal = conteudo_nota_fiscal.strip()

            # Monta o corpo da requisição SOAP
            payload = f"""
                <soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
                    <soapenv:Header/>
                    <soapenv:Body>{conteudo_nota_fiscal}</soapenv:Body>
                </soapenv:Envelope>
            """

            # Cabeçalhos da requisição
            headers = {
                'Accept-Encoding': 'gzip,deflate',
                'Content-Type': 'text/xml;charset=UTF-8',
                'Connection': 'Keep-Alive',
                'User-Agent': 'Apache-HttpClient/4.5.5 (Java/16.0.1)'
            }


            # Envio da requisição para o SAP
            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=payload,
                auth=(sap_user, sap_pass),
                timeout=30
            )

            # Verificação do status de resposta
            if not response.status_code == 200:
                raise Exception(f"Falha no envio do documento ao SAP: {response.status_code} URL {url} - {response.text} --- PAYLOAD {payload}")

            # ---------------------------------------------
            # Exibição de progresso no terminal
            # ---------------------------------------------
            percentual = (idx / total) * 100
            barra_tamanho = 20
            blocos_preenchidos = int((percentual / 100) * barra_tamanho)
            barra = '█' * blocos_preenchidos + '-' * (barra_tamanho - blocos_preenchidos)

            print(f"{YELLOW}{idx} de {total} enviados{RESET} [{GREEN}{barra}{RESET}] {percentual:.1f}% - {BLUE}{xml}{RESET}\n")

        # Espera entre os envios para evitar sobrecarga
        time.sleep(2)


# ---------------------------------------------
# Execução do tratamento e envio dos XML para O PI --> SAP
# ---------------------------------------------
limpar_caut_xml()
enviar_contingencia_lote()
