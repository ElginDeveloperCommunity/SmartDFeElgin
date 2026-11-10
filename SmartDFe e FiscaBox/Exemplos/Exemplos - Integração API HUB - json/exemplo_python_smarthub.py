#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo Python COMPLETO - SmartDFe / FiscalBox API Hub (json)
Fonte oficial:
  https://github.com/ElginDeveloperCommunity/SmartDFeElgin/wiki/%5BSmartDFe-e-FiscalBox%5D-API-Hub-(json)
Mais o legado do Exemplo_frontend_javascript.html

Requisitos:
    pip install requests

Uso:
    python exemplo_python_smarthub.py

ÍNDICE
  0. Configuração global (host, prefixo, timeout, estado)
  1. Infraestrutura HTTP (helpers de requisição e resposta)
  2. Configuração do emitente
  3. NFC-e (mod 65)
       3.1 Emissão
       3.2 Consulta e situação
       3.3 Cancelamento e inutilização
       3.4 XML, PDF e ESC/POS
  4. NF-e (mod 55)
       4.1 Emissão
       4.2 Consulta e situação
       4.3 Cancelamento, CC-e e inutilização
       4.4 XML e PDF
  5. Serviços complementares (webhook, SMTP e health)
  6. Extras / endpoints legados
  7. Menu interativo
"""

import json
import time

import requests

# =====================================================================
# 0. CONFIGURAÇÃO GLOBAL
# =====================================================================
# URL Base — Wiki:
#   Software (SmartDFe): http://localhost:8780
#   Hardware (FiscalBox): http://[IP_FISCALBOX]:8780
#   {{base}} da doc = http://127.0.0.1:8780/api/v1
HOST = "http://127.0.0.1:8780"
API_PREFIX = "/api/v1"
TIMEOUT = 30

# Chaves ativas — atualizadas automaticamente ao ler as respostas da API
ultima_chave_nfce = ""
ultima_chave_nfe = ""


# =====================================================================
# 1. INFRAESTRUTURA HTTP (HELPERS)
# =====================================================================

def _url(path: str) -> str:
    """Monta a URL completa a partir do HOST + prefixo da API."""
    return f"{HOST.rstrip('/')}{API_PREFIX}{path}"


def _headers_json() -> dict:
    """Cabeçalhos padrão para requisições com corpo JSON."""
    return {"Accept": "application/json", "Content-Type": "application/json"}


def _print_requisicao(resp: requests.Response):
    """Exibe claramente a requisição e o JSON que foi ENVIADO."""
    print(f"\n{'=' * 70}")
    print(f">>> REQUISIÇÃO: {resp.request.method} {resp.url}")
    print(f"{'=' * 70}")
    print(">>> JSON ENVIADO:")

    corpo = resp.request.body
    if not corpo:
        print("(nenhum corpo enviado)")
        return

    try:
        if isinstance(corpo, bytes):
            corpo = corpo.decode("utf-8")
        print(json.dumps(json.loads(corpo), indent=2, ensure_ascii=False))
    except (TypeError, ValueError):
        print(corpo)


_STATUS_SUCESSO = {"autorizado", "registrado", "cancelado", "inutilizado", "ok"}
_STATUS_FALHA = {"rejeitado", "erro", "denegado", "nao_encontrado"}
_STATUS_ANDAMENTO = {"processando"}


def _classificar_status(status: str) -> str:
    """Classifica o status retornado pela API (não o HTTP)."""
    s = (status or "").strip().lower()
    if s in _STATUS_SUCESSO:
        return "SUCESSO"
    if s in _STATUS_FALHA:
        return "FALHA"
    if s in _STATUS_ANDAMENTO:
        return "EM PROCESSAMENTO"
    return "VERIFICAR"


def _resumo_api(data: dict):
    """Extrai o resultado real da API: status e códigos de retorno."""
    status = data.get("status") or data.get("situacao") or ""
    erro = data.get("erro") if isinstance(data.get("erro"), dict) else {}
    sefaz = data.get("sefaz") if isinstance(data.get("sefaz"), dict) else {}
    sefaz_erro = erro.get("sefaz") if isinstance(erro.get("sefaz"), dict) else {}

    # Se o código veio dentro de "erro.sefaz", usa como fallback
    if not sefaz and sefaz_erro:
        sefaz = sefaz_erro

    linhas = []
    for campo in ("chave", "protocolo", "numero"):
        if data.get(campo):
            linhas.append((campo, data[campo]))

    if sefaz.get("codigo") or sefaz.get("mensagem"):
        linhas.append(("sefaz.codigo", sefaz.get("codigo", "")))
        linhas.append(("sefaz.mensagem", sefaz.get("mensagem", "")))

    if erro:
        linhas.append(("erro.codigo", erro.get("codigo", "")))
        linhas.append(("erro.mensagem", erro.get("mensagem", "")))
        if erro.get("campo"):
            linhas.append(("erro.campo", erro["campo"]))

    return status, linhas


def _print_recebimento(resp: requests.Response):
    """Exibe claramente o que foi RECEBIDO e atualiza a última chave conhecida."""
    global ultima_chave_nfce, ultima_chave_nfe

    print(f"\n{'-' * 70}")
    print(f">>> RESPOSTA RECEBIDA: HTTP {resp.status_code} {resp.reason}")
    print(f"{'-' * 70}")

    ctype = resp.headers.get("Content-Type", "")
    # Resposta binária (xml/pdf) -> devolve o conteúdo bruto
    if "application/pdf" in ctype or "application/xml" in ctype or "text/xml" in ctype:
        print(f">>> CONTEÚDO RECEBIDO (binário: {ctype}) — {len(resp.content)} bytes")
        return resp.content

    try:
        data = resp.json()

        if isinstance(data, dict):
            status, linhas = _resumo_api(data)
            campo_status = "situacao" if ("situacao" in data and "status" not in data) else "status"
            if status:
                print(f">>> RESULTADO DA API: {status.upper()}  [{_classificar_status(status)}]")
            else:
                print(">>> RESULTADO DA API:")
            print(f">>>   {campo_status:<14}: {status or '(não informado no corpo)'}")
            for nome, valor in linhas:
                if valor not in (None, ""):
                    print(f">>>   {nome:<14}: {valor}")
            print()

        print(">>> JSON RECEBIDO:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if isinstance(data, dict):
            # Formatos de chave retornados pela API: "chave" (novo) ou "chNFe" (legado)
            chave = data.get("chave") or data.get("chNFe")
            tipo = data.get("tipo", "")
            if chave:
                if tipo == "nfe":
                    ultima_chave_nfe = chave
                else:
                    ultima_chave_nfce = chave
                print(f"[INFO] Chave ativa atualizada ({tipo or 'nfce'}): {chave}")
        return data
    except ValueError:
        print(f">>> CONTEÚDO RECEBIDO (texto: {ctype or 'tipo desconhecido'}):")
        print(resp.text[:4000])
        return resp.text


def _print_resposta(resp: requests.Response):
    """Exibe o JSON enviado e, em seguida, o que foi recebido."""
    _print_requisicao(resp)
    return _print_recebimento(resp)


def _get(path: str):
    """GET simples com Accept: application/json."""
    return _print_resposta(
        requests.get(_url(path), headers={"Accept": "application/json"}, timeout=TIMEOUT)
    )


def _post(path: str, payload=None):
    """POST com corpo JSON."""
    return _print_resposta(
        requests.post(_url(path), headers=_headers_json(), json=payload or {}, timeout=TIMEOUT)
    )


def _baixar_arquivo(path: str, salvar: str, descricao: str, preview: bool = False):
    """GET de conteúdo binário (XML/PDF) e grava no arquivo indicado."""
    resp = requests.get(_url(path), headers={"Accept": "application/json"}, timeout=TIMEOUT)

    _print_requisicao(resp)

    if resp.ok:
        print(f"\n{'-' * 70}")
        print(f">>> RESPOSTA RECEBIDA: HTTP {resp.status_code} {resp.reason}")
        print(f"{'-' * 70}")
        with open(salvar, "wb") as f:
            f.write(resp.content)
        print(f">>> ARQUIVO RECEBIDO: {descricao} salvo em {salvar} ({len(resp.content)} bytes)")
        if preview:
            print("\n>>> CONTEÚDO RECEBIDO (XML):")
            print(resp.text[:2000])
    else:
        _print_recebimento(resp)
    return resp


# =====================================================================
# 2. CONFIGURAÇÃO DO EMITENTE
# =====================================================================

def configurar_emitente():
    """POST /config/emitente — configura os dados do emitente."""
    payload = {
        "emitente": {
            "CEP": "03679000",
            "CNPJ": "29720473000145",
            "CRT": "1",
            "IE": "128237060114",
            "UF": "SP",
            "cMun": "3550308",
            "cPais": "1058",
            "cUF": "35",
            "fone": "",
            "nro": "871",
            "xBairro": "VILA SAO FRANCISCO (ZONA LESTE)",
            "xCpl": "",
            "xFant": "29.720.473 FERNANDA SERAFIM ABRANTES",
            "xLgr": "RUA JOAO JOSE DE QUEIROZ",
            "xMun": "SAO PAULO",
            "xNome": "29.720.473 FERNANDA SERAFIM ABRANTES",
            "xPais": "Brasil",
        },
        "status": "ok",
    }
    return _post("/config/emitente", payload)


def consultar_emitente():
    """GET /config/emitente — consulta o emitente configurado."""
    return _get("/config/emitente")


# =====================================================================
# 3. NFC-E (MOD 65)
# =====================================================================

# ---------------------------------------------------------------------
# 3.1 Emissão
# ---------------------------------------------------------------------

def emitir_nfce():
    """POST /nfce — emite uma NFC-e em homologação."""
    payload = {
        "ref": f"NFE-{int(time.time() * 1000)}",
        "ambiente": "homologacao",
        "itens": [
            {
                "descricao": "Arroz Branco",
                "quantidade": 1.0,
                "valor_unitario": 12.0,
                "ncm": "10063021",
                "cfop": "5102",
                "gtin": "SEM GTIN",
                "tributacao": {
                    "origem": 0,
                    "icms": {"csosn": "102", "modalidade_base": 0},
                    "pis": {"cst": "49"},
                    "cofins": {"cst": "49"},
                    "ibs_cbs": {
                        "cst": "000",
                        "cClassTrib": "000001",
                        "pIBSUF": 0.1,
                        "pIBSMun": 0.0,
                        "pCBS": 0.9,
                    },
                },
            }
        ],
        "pagamentos": [
            {
                "forma": "credito",
                "valor": 12.0,
                "bandeira": "01",
                "cnpj_credenciadora": "45984642000100",
                "autorizacao": "123456",
                "integrado": True,
            }
        ],
    }
    print(f"Emitindo NFC-e ref={payload['ref']} ...")
    print("ATENÇÃO: 'ref' deve ser ÚNICO por requisição. Em caso de rejeição, gere outro ref.")
    return _post("/nfce", payload)


# ---------------------------------------------------------------------
# 3.2 Consulta e situação
# ---------------------------------------------------------------------

def consultar_nfce(chave=""):
    """GET /nfce/{chave} — consulta local (aceita chave de 44 dígitos ou UUID/ref)."""
    return _get(f"/nfce/{chave or ultima_chave_nfce}")


def situacao_nfce(chave=""):
    """GET /nfce/{chave}/situacao — situação do documento na SEFAZ."""
    return _get(f"/nfce/{chave or ultima_chave_nfce}/situacao")


# ---------------------------------------------------------------------
# 3.3 Cancelamento e inutilização
# ---------------------------------------------------------------------

def cancelar_nfce(chave="", justificativa="cancelamento de teste via colecao postman"):
    """POST /nfce/{chave}/cancelamento."""
    chave = chave or ultima_chave_nfce
    return _post(f"/nfce/{chave}/cancelamento", {"justificativa": justificativa})


def inutilizar_nfce(serie=1, inicial=900, final=902,
                    justificativa="inutilizacao de teste via colecao postman"):
    """POST /nfce/inutilizacao — inutiliza uma faixa de numeração."""
    return _post("/nfce/inutilizacao", {
        "serie": serie,
        "inicial": inicial,
        "final": final,
        "justificativa": justificativa,
    })


# ---------------------------------------------------------------------
# 3.4 XML, PDF e ESC/POS
# ---------------------------------------------------------------------

def xml_nfce(chave="", salvar="nfce.xml"):
    """GET /nfce/{chave}/xml — retorna o XML autorizado, salvando em arquivo."""
    chave = chave or ultima_chave_nfce
    return _baixar_arquivo(f"/nfce/{chave}/xml", salvar, "XML da NFC-e", preview=True)


def pdf_nfce(chave="", salvar="nfce_danfe.pdf"):
    """GET /nfce/{chave}/pdf — gera o DANFE em PDF, salvando em arquivo."""
    chave = chave or ultima_chave_nfce
    return _baixar_arquivo(f"/nfce/{chave}/pdf", salvar, "PDF da NFC-e")


def escpos_nfce(chave=""):
    """GET /nfce/{chave}/escpos — comandos ESC/POS p/ impressão térmica (FiscalBox)."""
    return _get(f"/nfce/{chave or ultima_chave_nfce}/escpos")


# =====================================================================
# 4. NF-E (MOD 55)
# =====================================================================

# ---------------------------------------------------------------------
# 4.1 Emissão
# ---------------------------------------------------------------------

def emitir_nfe():
    """POST /nfe — emite uma NF-e em homologação."""
    payload = {
        "ref": f"NFE-NORMAL-{int(time.time() * 1000)}",
        "ambiente": "homologacao",
        "natureza_operacao": "venda",
        "finalidade": "normal",
        "presenca": "presencial",
        "destinatario": {
            "documento": "45762835880",
            "nome": "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL",
            "indicador_ie": "nao_contribuinte",
            "endereco": {
                "logradouro": "Rua das Flores",
                "numero": "123",
                "bairro": "Centro",
                "codigo_municipio": "3550308",
                "municipio": "São Paulo",
                "uf": "SP",
                "cep": "01001000",
            },
        },
        "itens": [
            {
                "codigo": "123",
                "descricao": "NFCe - Homologacao",
                "quantidade": 1,
                "valor_unitario": 1.00,
                "unidade": "UN",
                "gtin": "SEM GTIN",
                "ncm": "22030000",
                "cfop": "5102",
                "cest": "0302100",
                "tributacao": {
                    "origem": "0",
                    "icms": {"csosn": "102"},
                    "pis": {"cst": "99", "aliquota": 1.65},
                    "cofins": {"cst": "01", "aliquota": 7.60},
                    "ibs_cbs": {
                        "cst": "000",
                        "cClassTrib": "000001",
                        "pIBSUF": 0.10,
                        "pIBSMun": 0.00,
                        "pCBS": 0.90,
                        "uf": {"pRedAliq": 0, "pAliqEfet": 0, "pDif": 0, "vDif": 0, "vDevTrib": 0},
                        "mun": {"pRedAliq": 0, "pAliqEfet": 0, "pDif": 0, "vDif": 0, "vDevTrib": 0},
                        "cbs": {"pRedAliq": 0, "pAliqEfet": 0, "pDif": 0, "vDif": 0, "vDevTrib": 0},
                    },
                },
            }
        ],
        "pagamentos": [{"forma": "dinheiro", "valor": 1.00}],
        "transporte": {"modFrete": "9"},
    }
    print(f"Emitindo NF-e ref={payload['ref']} ...")
    return _post("/nfe", payload)


# ---------------------------------------------------------------------
# 4.2 Consulta e situação
# ---------------------------------------------------------------------

def consultar_nfe(chave=""):
    """GET /nfe/{chave} — consulta local."""
    return _get(f"/nfe/{chave or ultima_chave_nfe}")


def situacao_nfe(chave=""):
    """GET /nfe/{chave}/situacao — situação do documento na SEFAZ."""
    return _get(f"/nfe/{chave or ultima_chave_nfe}/situacao")


# ---------------------------------------------------------------------
# 4.3 Cancelamento, CC-e e inutilização
# ---------------------------------------------------------------------

def cancelar_nfe(chave="", justificativa="cancelamento de teste da nf-e em homologacao via colecao"):
    """POST /nfe/{chave}/cancelamento."""
    return _post(f"/nfe/{chave or ultima_chave_nfe}/cancelamento", {"justificativa": justificativa})


def carta_correcao_nfe(chave="", correcao="correcao de dados nao fiscais do documento em homologacao"):
    """POST /nfe/{chave}/eventos — CC-e (documentação oficial atual)."""
    return _post(f"/nfe/{chave or ultima_chave_nfe}/eventos",
                 {"evento": "carta_correcao", "correcao": correcao})


def inutilizar_nfe(serie=78, inicial=16, final=16, justificativa="inutilizacao de teste via colecao postman"):
    """POST /nfe/inutilizacao — inutiliza uma faixa de numeração."""
    return _post("/nfe/inutilizacao", {
        "serie": serie,
        "inicial": inicial,
        "final": final,
        "justificativa": justificativa,
    })


# ---------------------------------------------------------------------
# 4.4 XML e PDF
# ---------------------------------------------------------------------

def xml_nfe(chave="", salvar="nfe.xml"):
    """GET /nfe/{chave}/xml — retorna o XML autorizado, salvando em arquivo."""
    chave = chave or ultima_chave_nfe
    return _baixar_arquivo(f"/nfe/{chave}/xml", salvar, "XML da NF-e")


def pdf_nfe(chave="", salvar="nfe_danfe.pdf"):
    """GET /nfe/{chave}/pdf — gera o DANFE em PDF, salvando em arquivo."""
    chave = chave or ultima_chave_nfe
    return _baixar_arquivo(f"/nfe/{chave}/pdf", salvar, "PDF da NF-e")


# =====================================================================
# 5. SERVIÇOS COMPLEMENTARES
# =====================================================================

# ---------------------------------------------------------------------
# 5.1 Webhook
# ---------------------------------------------------------------------

def configurar_webhook(url="http://127.0.0.1:8780/api/v1/webhook/inbound/",
                       ativo=True, retry_max=3, timeout_ms=5000):
    """POST /webhook — configura o webhook de retorno de eventos."""
    return _post("/webhook", {
        "Agent version": "01.03.48",
        "ativo": ativo,
        "command": "",
        "retryMax": retry_max,
        "secret": "",
        "timeoutMs": timeout_ms,
        "url": url,
    })


def consultar_webhook():
    """GET /webhook — consulta a configuração atual do webhook."""
    return _get("/webhook")


# ---------------------------------------------------------------------
# 5.2 SMTP (envio de e-mail)
# ---------------------------------------------------------------------

def configurar_smtp(host="smtp.gmail.com", porta=465, usuario="botautomacaopedidos@gmail.com",
                    senha="****", tls=False, remetente_email="botautomacaopedidos@gmail.com",
                    remetente_nome="Empresa Fiscal", assunto="Sua NFC-e nº {nNF}", ativo=True):
    """POST /smtp — configura o servidor de e-mail."""
    return _post("/smtp", {
        "smtp_host": host,
        "smtp_porta": porta,
        "smtp_usuario": usuario,
        "smtp_senha": senha,
        "smtp_tls": tls,
        "remetente_email": remetente_email,
        "remetente_nome": remetente_nome,
        "assunto": assunto,
        "ativo": ativo,
    })


def consultar_smtp():
    """GET /smtp — consulta a configuração atual de SMTP."""
    return _get("/smtp")


# ---------------------------------------------------------------------
# 5.3 Health check
# ---------------------------------------------------------------------

def health():
    """GET /health — verifica se o serviço está no ar."""
    return _get("/health")


# =====================================================================
# 6. EXTRAS / ENDPOINTS LEGADOS
# =====================================================================

def cancelamento_por_substituicao(chave_atual="", chave_ref="",
                                  justificativa="emitida com erro 'Justificatica'"):
    """POST /nfce/{chave}/cancellationBySubstitution — cancelamento por substituição."""
    return _post(f"/nfce/{chave_atual or ultima_chave_nfce}/cancellationBySubstitution",
                 {"chCFeRef": chave_ref, "tpAutor": 3, "xJust": justificativa})


def carta_correcao_legado(chave="", correcao="ncm invalido"):
    """POST /nfe/{chave}/electronicCorrectionLetter — CC-e no formato legado."""
    return _post(f"/nfe/{chave or ultima_chave_nfe}/electronicCorrectionLetter",
                 {"xCorrecao": correcao})


# =====================================================================
# 7. MENU INTERATIVO
# =====================================================================

def _menu_opcoes():
    """Agrupa as ações do menu por seção. Retorna [(descrição, função), ...]."""
    secoes = [
        ("Configuração", [
            ("POST   /config/emitente", configurar_emitente),
            ("GET    /config/emitente", consultar_emitente),
            ("GET    /health", health),
        ]),
        ("NFC-e (mod 65)", [
            ("POST   /nfce (emitir NFC-e)", emitir_nfce),
            ("GET    /nfce/{chave} (consulta local)",
             lambda: consultar_nfce(input("Chave/ref: ") or ultima_chave_nfce)),
            ("GET    /nfce/{chave}/situacao",
             lambda: situacao_nfce(input("Chave: ") or ultima_chave_nfce)),
            ("POST   /nfce/{chave}/cancelamento",
             lambda: cancelar_nfce(input("Chave: ") or ultima_chave_nfce)),
            ("POST   /nfce/inutilizacao", inutilizar_nfce),
            ("GET    /nfce/{chave}/xml",
             lambda: xml_nfce(input("Chave: ") or ultima_chave_nfce)),
            ("GET    /nfce/{chave}/pdf",
             lambda: pdf_nfce(input("Chave: ") or ultima_chave_nfce)),
            ("GET    /nfce/{chave}/escpos",
             lambda: escpos_nfce(input("Chave: ") or ultima_chave_nfce)),
            ("POST   /nfce/{chave}/cancellationBySubstitution",
             lambda: cancelamento_por_substituicao(
                 input("Chave atual: ") or ultima_chave_nfce, input("chCFeRef: "))),
        ]),
        ("NF-e (mod 55)", [
            ("POST   /nfe (emitir NF-e)", emitir_nfe),
            ("GET    /nfe/{chave} (consulta local)",
             lambda: consultar_nfe(input("Chave/ref: ") or ultima_chave_nfe)),
            ("GET    /nfe/{chave}/situacao",
             lambda: situacao_nfe(input("Chave: ") or ultima_chave_nfe)),
            ("POST   /nfe/{chave}/cancelamento",
             lambda: cancelar_nfe(input("Chave: ") or ultima_chave_nfe)),
            ("POST   /nfe/{chave}/eventos (CC-e)",
             lambda: carta_correcao_nfe(input("Chave: ") or ultima_chave_nfe)),
            ("POST   /nfe/inutilizacao", inutilizar_nfe),
            ("GET    /nfe/{chave}/xml",
             lambda: xml_nfe(input("Chave: ") or ultima_chave_nfe)),
            ("GET    /nfe/{chave}/pdf",
             lambda: pdf_nfe(input("Chave: ") or ultima_chave_nfe)),
            ("POST   /nfe/{chave}/electronicCorrectionLetter (legado)",
             lambda: carta_correcao_legado(input("Chave: ") or ultima_chave_nfe)),
        ]),
        ("Serviços complementares", [
            ("POST   /webhook", configurar_webhook),
            ("GET    /webhook", consultar_webhook),
            ("POST   /smtp", configurar_smtp),
            ("GET    /smtp", consultar_smtp),
        ]),
    ]

    opcoes = []
    for titulo, itens in secoes:
        opcoes.append((f"__SECAO__{titulo}", None))
        opcoes.extend(itens)
    return opcoes


def menu():
    global HOST

    opcoes = _menu_opcoes()
    acoes = [fn for desc, fn in opcoes if fn is not None]

    while True:
        print("\n==== SmartDFe API Hub (json) — Exemplo Python COMPLETO ====")
        print(f"HOST: {HOST}{API_PREFIX}")
        print(f"NFC-e: {ultima_chave_nfce or '(nenhuma)'} | NF-e: {ultima_chave_nfe or '(nenhuma)'}")
        print("  0 - Alterar HOST")

        numero = 0
        for desc, fn in opcoes:
            if fn is None:
                print(f"\n  -- {desc.replace('__SECAO__', '')} --")
                continue
            numero += 1
            print(f" {numero:>2} - {desc}")

        print("\n  q - Sair")
        esc = input("\nOpção: ").strip().lower()

        if esc == "q":
            break
        if esc == "0":
            HOST = (input(f"Novo HOST [{HOST}]: ").strip() or HOST).rstrip("/")
            continue

        try:
            idx = int(esc) - 1
        except ValueError:
            print("Opção inválida.")
            continue

        if idx < 0 or idx >= len(acoes):
            print("Opção inválida.")
            continue

        try:
            acoes[idx]()
        except requests.ConnectionError as e:
            print(f"[ERRO] Falha de conexão com {HOST}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"[ERRO] {e}")
        finally:
            input("\nJá conferiu o JSON enviado e o status/código retornado pela API? Pressione ENTER para voltar ao início...")


if __name__ == "__main__":
    menu()
