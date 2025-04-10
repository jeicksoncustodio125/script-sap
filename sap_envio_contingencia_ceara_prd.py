import os
import requests
import time
 
def enviar_contingencia_lote() -> dict:
    """Realiza a execução da tarefa de envio da nota fiscal para o sistema SAP.

    Raises:
        Exception: Exception para arquivo em formato não compativel com o processamento.5

    Returns:
        dict: Retorna o dicionário com os dados do processamento para a situação especifica da nota fiscal.
    """

    # ---------------------------------------------
    # Credenciais para envio
    # ---------------------------------------------
    sap_user = "integragn" 
    sap_pass = "gentil#2022"

    # ---------------------------------------------
    # Definir a URL para envio da nota
    # ---------------------------------------------
    url = 'http://ALB-GENTIL-SAP-PRD-PI-228799892.us-east-1.elb.amazonaws.com:50000/XISOAPAdapter/MessageServlet?channel=PA_WEBINT:BC_WEBINT:CC_SND_SOAP_WEBINT_CFeCont'


    # ---------------------------------------------
    # Definir pasta das notas 
    # ---------------------------------------------
    pasta_notas = 'notas_contingencia_ceara'


    # Caminho base
    caminho_base = os.path.abspath('.')
    caminho_pasta_notas = os.path.join(caminho_base, pasta_notas)

    # Listar arquivos XML
    lista_arquivos = os.listdir(caminho_pasta_notas)

    lista_xmls = []

    # Selecionando apenas arquivos XML
    for arquivo in lista_arquivos:
        if arquivo.endswith('.xml'):
            lista_xmls.append(arquivo)


    # LOOP POR ARQUIVO ! ! ! ! !
    for xml in lista_xmls:

        # ---------------------------------------------
        # Definir conteudo a ser enviado
        # ---------------------------------------------
        path_xml = os.path.join(caminho_pasta_notas, xml)
        with open(path_xml, 'r', encoding='ISO-8859-1') as conteudo_xml:
            # conteudo_nota_fiscal = conteudo_xml.read()
            # conteudo_nota_fiscal = conteudo_xml.readline()
            conteudo_nota_fiscal = conteudo_xml.read().replace('\n', '')

            # Tratamento do conteudo da nota
            conteudo_nota_fiscal = conteudo_nota_fiscal.replace('<NFe xmlns="http://www.portalfiscal.inf.br/nfe">', '<NFe>')
            conteudo_nota_fiscal = conteudo_nota_fiscal.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            conteudo_nota_fiscal = conteudo_nota_fiscal.strip()


            payload = f"""
                <soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">
                    <soapenv:Header/>
                    <soapenv:Body>{conteudo_nota_fiscal}</soapenv:Body>
                </soapenv:Envelope>
            """

            headers = {
                'Accept-Encoding': 'gzip,deflate',
                'Content-Type': 'text/xml;charset=UTF-8',
                'Connection': 'Keep-Alive',
                'User-Agent': 'Apache-HttpClient/4.5.5 (Java/16.0.1)'
            }


            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=payload,
                auth=(sap_user, sap_pass),
                timeout=30
            )

            # Validar retorno da consulta e seus dados
            if not response.status_code == 200:
                raise Exception(f"Falha no envio do documento ao SAP: {response.status_code} URL {url} - {response.text} --- PAYLOAD {payload}")

            # Estrutura de retorno do status da nota
            status_envio = {
                "status_code": response.status_code
            }

            print(f"Enviado contingencia: {status_envio} {xml}")
            print("")

        time.sleep(2)


enviar_contingencia_lote()
