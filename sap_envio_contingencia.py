import os
import requests
import time
import re
import shutil

# Cores usadas no Terminal:
RED = "\033[1;31m"     # Erro
GREEN = "\033[1;32m"   # Sucesso
YELLOW = "\033[1;33m"  # Atenção
BLUE = "\033[1;34m"    # Nome dos Xmls
RESET = "\033[0m"      # Reseta Cor

import os
import re
import shutil

def limpar_caut_xml():
    pasta_notas = 'notas_contingencia'
    pasta_erro_ean = 'notas_erro_ean'
    pasta_erro_aliquota = 'notas_erro_aliquota'
    pasta_canceladas = 'notas_canceladas'

    prefixos_cancelados = []

    contador_pix = 0
    contador_ean = 0
    contador_aliquota = 0

    for nome_arquivo in os.listdir(pasta_notas):
        if nome_arquivo.lower().endswith('.xml'):
            caminho_arquivo = os.path.join(pasta_notas, nome_arquivo)
            try:
                with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
                    linhas = arquivo.readlines()

                linhas_sem_declaracao = [
                    linha for linha in linhas
                    if not linha.strip().startswith('<?xml') or 'version="1.0"' not in linha
                ]

                with open(caminho_arquivo, 'w', encoding='utf-8') as arquivo:
                    arquivo.writelines(linhas_sem_declaracao)
            except Exception as e:
                print(f"Erro ao remover declaração do arquivo {nome_arquivo}: {e}")

    for arquivo in [f for f in os.listdir(pasta_notas) if f.endswith('.xml')]:
        caminho = os.path.join(pasta_notas, arquivo)
        if 'Canc' in arquivo:
            shutil.move(caminho, os.path.join(pasta_canceladas, arquivo))
            print(f"{YELLOW}Cancelamento detectado nota movida para notas_cancelada: {RESET}{BLUE}{arquivo}{RESET}\n")
            prefixos_cancelados.append(arquivo[:44])
            continue

    for arquivo in [f for f in os.listdir(pasta_notas) if f.endswith('.xml')]:
        caminho = os.path.join(pasta_notas, arquivo)
        try:
            prefixo_arquivo = arquivo[:44]
            if prefixo_arquivo in prefixos_cancelados:
                shutil.copy2(caminho, os.path.join(pasta_canceladas, arquivo))
                print(f"{YELLOW}Cancelamento detectado nota movida para notas_cancelada: {RESET}{BLUE}{arquivo}{RESET}\n")
                continue

            with open(caminho, 'r', encoding='utf-8') as f:
                content = f.read()

            if ('<cEAN>Sem EAN</cEAN>' in content or '<cEANTrib>Sem EAN</cEANTrib>' in content):
                shutil.move(caminho, os.path.join(pasta_erro_ean, arquivo))
                contador_ean += 1
                continue

            if '<PISOTR>' in content:
                shutil.move(caminho, os.path.join(pasta_erro_aliquota, arquivo))
                contador_aliquota += 1
                continue

            if '<cAut>' in content:
                # Substitui todos os <cAut> com mais de 8 caracteres por vazio
                novos_caut = re.findall(r'<cAut>(.*?)</cAut>', content)
                for valor in novos_caut:
                    if len(valor.strip()) > 8:
                        content = content.replace(f'<cAut>{valor}</cAut>', '<cAut></cAut>')
                        contador_pix += 1

                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(content)

        except Exception as e:
            print(f"{RED}Erro ao processar arquivo {YELLOW}{arquivo}{RESET}: {RED}{str(e)}{RESET}\n")

    if contador_pix > 0:
        print(f"{GREEN}Pix detectado → {contador_pix} ocorrência(s){RESET}")
    if contador_ean > 0:
        print(f"{YELLOW}Erro de EAN → {contador_ean} arquivo(s) afetado(s){RESET}")
    if contador_aliquota > 0:
        print(f"{YELLOW}Erro de alíquota (PISOTR) → {contador_aliquota} arquivo(s) afetado(s){RESET}")

    print(f"\n{GREEN}Tratamento dos dados finalizado com sucesso.{RESET}")

def enviar_contingencia_lote() -> dict:
    sap_user = "integragn"
    sap_pass = "gentil#2022"

    url = 'http://ALB-GENTIL-SAP-PRD-PI-228799892.us-east-1.elb.amazonaws.com:50000/XISOAPAdapter/MessageServlet?senderParty=PA_WEBINT&senderService=BC_WEBINT&receiverParty=&receiverService=&interface=SI_Asyn_Out_NFCe_Contingencia&interfaceNamespace=http://star-it.com/xi/NFCe_Contingencia'

    pasta_notas = 'notas_contingencia'
    caminho_base = os.path.abspath('.')
    caminho_pasta_notas = os.path.join(caminho_base, pasta_notas)

    lista_xmls = [f for f in os.listdir(caminho_pasta_notas) if f.endswith('.xml')]
    total = len(lista_xmls)

    for idx, xml in enumerate(lista_xmls, start=1):
        path_xml = os.path.join(caminho_pasta_notas, xml)
        with open(path_xml, 'r', encoding='ISO-8859-1') as conteudo_xml:
            conteudo_nota_fiscal = conteudo_xml.read().replace('\n', '')

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

            if not response.status_code == 200:
                raise Exception(f"Falha no envio do documento ao SAP: {response.status_code} URL {url} - {response.text} --- PAYLOAD {payload}")

            percentual = (idx / total) * 100
            barra_tamanho = 20
            blocos_preenchidos = int((percentual / 100) * barra_tamanho)
            barra = '█' * blocos_preenchidos + '-' * (barra_tamanho - blocos_preenchidos)

            print(f"{YELLOW}{idx} de {total} enviados{RESET} [{GREEN}{barra}{RESET}] {percentual:.1f}% - {BLUE}{xml}{RESET}\n")

        time.sleep(2)

# Executa as funções
limpar_caut_xml()
enviar_contingencia_lote()
