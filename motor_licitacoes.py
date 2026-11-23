import math
import re
import threading
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURAÇÕES GERAIS
# ==============================================================================
URL_SRE = "https://sredivinopolis.educacao.mg.gov.br/licitacoes/dispensas-e-editais/escolas-aquisicao-simplificada/"
try:
    FUSO_BR = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    FUSO_BR = timezone(timedelta(hours=-3))
CACHE_TTL_SEGUNDOS = 1800  # Atualiza o Google Docs automaticamente a cada 30 min

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

OBJETOS_LICITACAO = {
    "generos_alimenticios_secos_e_mercearia": {
        "rotulo": "Gêneros Alimentícios (Mercearia / Secos)",
        "palavras_chave": [
            "genero alimenticio", "generos alimenticios", "alimentacao", "mercearia",
            "arroz", "feijao", "acucar", "cafe", "oleo", "macarrao", "farinha",
            "fuba", "polvilho", "biscoito", "bolacha", "molho de tomate", "extrato de tomate",
            "milho verde", "ervilha", "sardinha", "atum", "leite em po", "achocolatado",
            "sal", "vinagre", "tempero", "condimento", "cesta basica"
        ],
        "cnaes_7_digitos": {
            "4711301", "4711302", "4712100", "4729699",
            "4639701", "4639702", "4691599",
        },
    },
    "hortifruti_e_agricultura_familiar": {
        "rotulo": "Hortifrúti, Frutas, Verduras e Legumes",
        "palavras_chave": [
            "hortifruti", "hortifrutigranjeiro", "fruta", "verdura", "legume",
            "batata", "cebola", "tomate", "alface", "couve", "repolho", "cenoura",
            "banana", "maca", "laranja", "abacaxi", "mandioca", "aipim",
            "cheiro verde", "agricultura familiar", "pnae"
        ],
        "cnaes_7_digitos": {
            "4724500", "4633801", "4711302", "4712100",
            "0111301", "0119999", "0121101", "0122900",
        },
    },
    "carnes_aves_e_frios": {
        "rotulo": "Carnes, Aves, Pescados e Frios",
        "palavras_chave": [
            "acougue", "carne", "bovina", "bovino", "suina", "suino",
            "frango", "ave", "peito de frango", "coxa e sobrecoxa", "carne moida",
            "patinho", "acem", "musculo", "linguica", "salsicha", "presunto",
            "mussarela", "queijo", "frios", "embutido", "pescado", "peixe", "ovos"
        ],
        "cnaes_7_digitos": {
            "4722901", "4722902", "4729602", "4634601",
            "4634602", "4634603", "4631100", "4711302",
        },
    },
    "padaria_e_confeitaria": {
        "rotulo": "Panificação, Pães e Confeitaria",
        "palavras_chave": [
            "padaria", "panificacao", "pao", "paes", "pao frances", "pao de forma",
            "pao de queijo", "bolo", "biscoito caseiro", "salgado", "confeitaria"
        ],
        "cnaes_7_digitos": {
            "4721102", "4721101", "1091102", "4711302", "4712100",
        },
    },
    "agua_mineral_e_gas": {
        "rotulo": "Água Mineral e Gás GLP",
        "palavras_chave": [
            "agua mineral", "galao de agua", "agua potavel",
            "gas glp", "gas de cozinha", "botijao", "botijao de gas", "glp 13", "glp 45"
        ],
        "cnaes_7_digitos": {
            "4723700", "4635499", "4784900", "4682600",
        },
    },
    "material_de_limpeza_e_higiene": {
        "rotulo": "Material de Limpeza, Higiene e Descartáveis",
        "palavras_chave": [
            "material de limpeza", "produtos de limpeza", "limpeza", "higiene",
            "desinfetante", "agua sanitaria", "cloro", "detergente", "sabao em po",
            "sabao em barra", "sabonete", "alcool gel", "alcool 70", "papel higienico",
            "papel toalha", "guardanapo", "saco de lixo", "sacos de lixo", "esponja",
            "pano de chao", "flanela", "rodo", "vassoura", "luva de borracha", "copo descartavel"
        ],
        "cnaes_7_digitos": {
            "4649408", "4649499", "4712100", "4711302", "4789099", "4772500",
        },
    },
    "papelaria_e_material_escolar": {
        "rotulo": "Papelaria, Material Escolar e Expediente",
        "palavras_chave": [
            "papelaria", "material escolar", "material de expediente", "expediente",
            "escritorio", "papel a4", "resma", "sulfite", "caderno", "caneta",
            "lapis", "borracha", "regua", "cola", "fita adesiva", "durex", "grampeador",
            "grampo", "clips", "envelope", "pasta", "arquivo", "marcador", "pincel",
            "cartolina", "eva", "tinta guache", "tesoura escolar"
        ],
        "cnaes_7_digitos": {
            "4761003", "4647801", "4761001", "4761002",
        },
    },
    "informatica_e_suprimentos": {
        "rotulo": "Informática, Suprimentos e Equipamentos de TI",
        "palavras_chave": [
            "informatica", "suprimentos de informatica", "toner", "cartucho",
            "tinta de impressora", "impressora", "computador", "notebook", "monitor",
            "teclado", "mouse", "cabo hdmi", "cabo de rede", "roteador", "switch",
            "pen drive", "ssd", "estabilizador", "nobreak", "filtro de linha",
            "manutencao de computadores", "servico tecnico", "servicos tecnicos",
            "assistencia tecnica", "manutencao de impressora"
        ],
        "cnaes_7_digitos": {
            "4751201", "4651601", "4651602", "9511800", "4751202",
        },
    },
    "material_eletrico_e_iluminacao": {
        "rotulo": "Material Elétrico e Iluminação",
        "palavras_chave": [
            "material eletrico", "eletrica", "lampada", "led", "luminaria",
            "refletor", "tomada", "interruptor", "disjuntor", "fio", "fios",
            "cabo eletrico", "fita isolante", "quadro de distribuicao", "reator",
            "soquete", "canaleta"
        ],
        "cnaes_7_digitos": {
            "4742300", "4673700", "4321500",
        },
    },
    "material_hidraulico_e_construcao": {
        "rotulo": "Material de Construção, Hidráulica e Ferragens",
        "palavras_chave": [
            "material de construcao", "construcao civil", "hidraulico", "hidraulica",
            "cano", "tubo", "conexao", "conexoes", "pvc", "registro", "torneira",
            "sifao", "caixa d agua", "cimento", "areia", "brita", "argamassa",
            "tijolo", "bloco", "telha", "ferragem", "ferragens", "parafuso", "bucha",
            "cadeado", "dobradica", "fechadura", "tinta", "esmalte sintetico", "pincel de pintura"
        ],
        "cnaes_7_digitos": {
            "4744099", "4744001", "4744002", "4744003", "4744004",
            "4741500", "4679699", "4672900", "4679601",
        },
    },
    "manutencao_predial_e_reformas": {
        "rotulo": "Manutenção Predial, Pequenos Reparos e Serviços Gerais",
        "palavras_chave": [
            "manutencao predial", "reforma", "pequenos reparos", "alvenaria", "pedreiro",
            "pintura predial", "servicos de pintura", "telhado", "calha", "rufo",
            "impermeabilizacao", "revisao eletrica", "revisao hidraulica", "serralheria",
            "grade", "portao", "solda", "marcenaria", "carpintaria"
        ],
        "cnaes_7_digitos": {
            "4399103", "4330404", "4321500", "4322301",
            "2542000", "4399199", "8121400",
        },
    },
    "mobiliario_e_equipamentos_escolares": {
        "rotulo": "Mobiliário, Carteiras e Equipamentos Escolares",
        "palavras_chave": [
            "mobiliario", "moveis", "carteira escolar", "cadeira", "mesa",
            "armario", "estante", "arquivo de aco", "quadro branco", "lousa",
            "ventilador", "climatizador", "geladeira", "freezer", "fogao industrial",
            "liquidificador", "eletrodomestico"
        ],
        "cnaes_7_digitos": {
            "4754701", "4649401", "3101200", "3102100", "4753900",
        },
    },
    "uniformes_e_aviamentos": {
        "rotulo": "Uniformes, Vestuário e Aviamentos",
        "palavras_chave": [
            "uniforme", "camiseta", "jaleco", "avental",
            "vestuario", "tecido", "linha", "agulha", "aviamento", "costura"
        ],
        "cnaes_7_digitos": {
            "4781400", "4642701", "1412601", "4755503",
        },
    },
    "dedetizacao_e_controle_de_pragas": {
        "rotulo": "Dedetização, Desratização e Controle de Pragas",
        "palavras_chave": [
            "dedetizacao", "desratizacao", "descupinizacao", "controle de pragas",
            "controle de vetores", "sanitizacao", "pragas urbanas", "inseto", "roedor"
        ],
        "cnaes_7_digitos": {
            "8122200",
        },
    },
    "jardinagem_e_poda": {
        "rotulo": "Jardinagem, Roçagem e Poda",
        "palavras_chave": [
            "jardinagem", "rocagem", "rocada", "poda", "poda de arvores",
            "grama", "paisagismo", "manutencao de jardins", "rocadeira"
        ],
        "cnaes_7_digitos": {
            "8130300", "0161001",
        },
    },
}

# Caches globais protegidos por lock para múltiplas requisições simultâneas
_LOCK_DOCS = threading.Lock()
_CACHE_DOCS = {
    "url": None,
    "mes_referencia": None,
    "licitacoes": [],
    "atualizado_ts": 0.0,
    "atualizado_fmt": None,
}

_LOCK_GEO = threading.Lock()
_CACHE_COORDS = {}
_ULTIMA_REQ_NOMINATIM = 0.0
HEADERS_GEO = {"User-Agent": "BuscadorLicitacoesSRE/1.0 (contato-local-fastapi)"}


# ==============================================================================
# UTILITÁRIOS
# ==============================================================================
def agora_brasilia() -> datetime:
    return datetime.now(FUSO_BR)


def normalizar_texto(texto: str) -> str:
    texto = str(texto or "").lower()
    sem_acento = (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("utf-8")
    )
    return re.sub(r"\s+", " ", sem_acento).strip()


def normalizar_cnae(codigo) -> str:
    return re.sub(r"\D", "", str(codigo or ""))


def limpar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def formatar_tempo_restante(prazo_dt: datetime, agora: datetime) -> str:
    delta = prazo_dt - agora
    total_segundos = max(0, int(delta.total_seconds()))
    dias, resto = divmod(total_segundos, 86400)
    horas, resto = divmod(resto, 3600)
    minutos = resto // 60
    if dias > 0:
        return f"Faltam {dias}d {horas}h {minutos}min"
    return f"Faltam {horas}h {minutos}min"


# ==============================================================================
# MÓDULO 1 & 2: RASPAGEM DA SRE E PARSER DO GOOGLE DOCS
# ==============================================================================
def extrair_texto_google_docs(url_docs: str) -> str | None:
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url_docs)
    if not match:
        return None

    doc_id = match.group(1)
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    try:
        response = requests.get(export_url, timeout=15)
        if response.status_code == 200:
            response.encoding = "utf-8"
            texto = response.text.lstrip("\ufeff")
            texto = texto.replace("\u200b", "").replace("\xa0", " ")
            return texto.replace("\r\n", "\n").replace("\r", "\n").strip()
    except Exception:
        pass
    return None


def detectar_ano_no_html(link, soup: BeautifulSoup) -> str | None:
    m = re.search(r"\b(20\d{2})\b", link.get_text(" ", strip=True))
    if m:
        return m.group(1)

    for pai in link.parents:
        if not getattr(pai, "attrs", None):
            continue

        pai_id = pai.get("id") or ""
        m_id = re.search(r"(20\d{2})", pai_id)
        if m_id:
            return m_id.group(1)

        if pai_id:
            seletor_controle = (
                soup.find(attrs={"href": f"#{pai_id}"})
                or soup.find(attrs={"data-target": f"#{pai_id}"})
                or soup.find(attrs={"data-bs-target": f"#{pai_id}"})
                or soup.find(attrs={"aria-controls": pai_id})
            )
            if seletor_controle:
                m_ctrl = re.search(r"\b(20\d{2})\b", seletor_controle.get_text(" ", strip=True))
                if m_ctrl:
                    return m_ctrl.group(1)

        labelled_by = pai.get("aria-labelledby")
        if labelled_by:
            titulo = soup.find(id=labelled_by)
            if titulo:
                m_lbl = re.search(r"\b(20\d{2})\b", titulo.get_text(" ", strip=True))
                if m_lbl:
                    return m_lbl.group(1)

    for anterior in link.find_all_previous(
        ["h1", "h2", "h3", "h4", "h5", "h6", "button", "strong", "b", "th", "p", "a", "span"]
    ):
        txt = limpar_espacos(anterior.get_text(" ", strip=True))
        if 4 <= len(txt) <= 35:
            m_ant = re.search(r"\b(20\d{2})\b", txt)
            if m_ant:
                return m_ant.group(1)

    return None


def obter_documento_mes_atual() -> tuple[str | None, str | None, str]:
    hoje = agora_brasilia()
    ano_atual = str(hoje.year)
    mes_atual = MESES_PT[hoje.month]
    mes_norm = normalizar_texto(mes_atual)
    ref = f"{mes_atual}/{ano_atual}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(URL_SRE, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception:
        return None, None, ref

    candidatos = []
    urls_vistas = set()
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if "docs.google.com" not in href or href in urls_vistas:
            continue

        texto_link = normalizar_texto(link.get_text(" ", strip=True))
        if mes_norm in texto_link:
            urls_vistas.add(href)
            candidatos.append({
                "href": href,
                "ano_html": detectar_ano_no_html(link, soup),
            })

    if not candidatos:
        return None, None, ref

    def prioridade(item):
        if item["ano_html"] == ano_atual:
            return 0
        if item["ano_html"] is None:
            return 1
        return 2

    candidatos_ordenados = sorted(candidatos, key=prioridade)
    padrao_data_ano = re.compile(rf"\b\d{{2}}/\d{{2}}/{ano_atual}\b")
    fallback_valido = None

    for cand in candidatos_ordenados:
        texto = extrair_texto_google_docs(cand["href"])
        if not texto:
            continue

        if fallback_valido is None:
            fallback_valido = (cand["href"], texto)

        if padrao_data_ano.search(texto):
            return cand["href"], texto, ref

    if fallback_valido:
        return fallback_valido[0], fallback_valido[1], ref
    return None, None, ref


def separar_licitacoes(texto_completo: str) -> list[str]:
    padrao_aviso = re.compile(
        r"(?im)(?=^\s*AVISO\s+DE\s+(?:PUBLICA[CÇ][AÃ]O|AQUISI[CÇ][AÃ]O|DISPENSA|LICITA[CÇ][AÃ]O))"
    )
    blocos_brutos = padrao_aviso.split(texto_completo)

    blocos_refinados = []
    for trecho in blocos_brutos:
        qtd_ids = len(re.findall(r"(?i)Id\.?\s*(?:d[ea]\s+)?Compra", trecho))
        if qtd_ids > 1:
            blocos_refinados.extend(re.split(r"(?im)(?=^\s*Caixa\s+Escolar\b)", trecho))
        else:
            blocos_refinados.append(trecho)

    blocos_validos = []
    for bloco in blocos_refinados:
        bloco_limpo = re.sub(r"\n\s*\d{2}/\d{2}/\d{4}\s*$", "", bloco.strip()).strip()
        if re.search(
            r"(?i)(Id\.?\s*(?:d[ea]\s+)?Compra|Especifica[cç][aã]o\s+do\s+objeto|Prazo\s+para\s+apresenta[cç][aã]o)",
            bloco_limpo,
        ):
            blocos_validos.append(bloco_limpo)

    return blocos_validos


def extrair_prazo(bloco: str) -> tuple[datetime | None, str]:
    padrao_prazo = re.compile(
        r"(?is)(Prazo\s+(?:para\s+)?apresenta[cç][aã]o[\s\S]{0,180}?"
        r"(\d{2}/\d{2}/\d{4})"
        r"(?:[\s\S]{0,20}?(?:[àa]s?\s*)?(\d{1,2})\s*(?::(\d{2})|h(?:oras?)?\s*(\d{2})?))?"
        r"[^\n]*)"
    )
    match = padrao_prazo.search(bloco)

    if not match:
        padrao_ate = re.compile(
            r"(?is)((?:at[eé]|dia)\s+(?:o\s+dia\s+)?"
            r"(\d{2}/\d{2}/\d{4})"
            r"(?:[\s\S]{0,20}?(?:[àa]s?\s*)?(\d{1,2})\s*(?::(\d{2})|h(?:oras?)?\s*(\d{2})?))?"
            r"[^\n]*)"
        )
        match = padrao_ate.search(bloco)

    if not match:
        return None, "Prazo não identificado"

    trecho_bruto = limpar_espacos(match.group(1))
    data_str = match.group(2)
    hora_str = match.group(3)
    minuto_str = match.group(4) or match.group(5)

    try:
        dia, mes, ano = map(int, data_str.split("/"))
        if hora_str is not None:
            hora = int(hora_str)
            minuto = int(minuto_str) if minuto_str is not None else 0
        else:
            hora = 23
            minuto = 59
        prazo_dt = datetime(ano, mes, dia, hora, minuto, tzinfo=FUSO_BR)
        return prazo_dt, trecho_bruto
    except ValueError:
        return None, trecho_bruto


def extrair_dados_licitacao(bloco: str, indice: int) -> dict:
    caixa = "Não identificado"
    m_caixa = re.search(r"(?im)^\s*(?:A\s+)?(Caixa\s+Escolar\s*:?\s*[^\n]+)", bloco)
    if m_caixa:
        caixa = limpar_espacos(m_caixa.group(1))

    endereco = "Não identificado"
    m_end = re.search(
        r"(?is)Endere[cç]o\s*[:\-–]\s*(.+?)"
        r"(?=\n\s*(?:Aquisi[cç][aã]o|Id\.?\s*(?:d[ea]\s+)?Compra|Subprograma|Especifica[cç][aã]o|Objeto|Informa[cç][õo]es|Prazo)|$)",
        bloco,
    )
    if m_end:
        endereco = limpar_espacos(m_end.group(1)).rstrip(".,; ")

    id_compra = "Não identificado"
    padroes_id = [
        r"(?i)\bId\.?\s*(?:d[ea]\s+)?Compra\s*(?:n[º°o\.]?)?\s*[:\-–]?\s*(\d{4}\.\d+|\d[\d./-]*)",
        r"(?i)\bID\s*(?:n[º°o\.]?)?\s*[:\-–]\s*(\d{4}\.\d+|\d[\d./-]*)",
        r"(?i)Aquisi[cç][aã]o\s+Simplificada[^\n]*?(\d{4}\.\d{4,})",
        r"(?i)(?:Edital|Processo|Dispensa|Chamada\s+P[úu]blica)\s*(?:n[º°o\.]?)?\s*[:\-–]?\s*(\d+[\d./-]*)",
    ]
    for padrao in padroes_id:
        m_id = re.search(padrao, bloco)
        if m_id:
            id_compra = limpar_espacos(m_id.group(1)).rstrip(".,;:")
            break

    objeto = "Não identificado"
    m_obj = re.search(
        r"(?is)(?:Especifica[cç][aã]o\s+do\s+)?Objeto\s*[:\-–]\s*(.+?)"
        r"(?=\n\s*(?:Informa[cç][õo]es|Prazo|Observa[cç][aã]o|Subprograma|Endere[cç]o|Aquisi[cç][aã]o|AVISO\s+DE)|$)",
        bloco,
    )
    if m_obj:
        objeto = limpar_espacos(m_obj.group(1)).rstrip(".,; ")

    prazo_dt, prazo_texto = extrair_prazo(bloco)

    return {
        "indice": indice,
        "caixa_escolar": caixa,
        "endereco": endereco,
        "id_compra": id_compra,
        "objeto": objeto,
        "prazo_dt": prazo_dt,
        "prazo_texto": prazo_texto,
        "texto_bruto": bloco,
    }


def obter_licitacoes_cacheadas(forcar: bool = False) -> dict:
    with _LOCK_DOCS:
        agora_ts = time.time()
        cache_valido = (
            not forcar
            and bool(_CACHE_DOCS["licitacoes"])
            and (agora_ts - _CACHE_DOCS["atualizado_ts"]) < CACHE_TTL_SEGUNDOS
        )
        if cache_valido:
            return dict(_CACHE_DOCS)

        url, texto, mes_ref = obter_documento_mes_atual()
        if not url or not texto:
            if _CACHE_DOCS["licitacoes"]:
                return dict(_CACHE_DOCS)
            raise RuntimeError("Não foi possível baixar o documento de licitações da SRE Divinópolis.")

        blocos = separar_licitacoes(texto)
        licitacoes = [extrair_dados_licitacao(b, i + 1) for i, b in enumerate(blocos)]

        _CACHE_DOCS.update({
            "url": url,
            "mes_referencia": mes_ref,
            "licitacoes": licitacoes,
            "atualizado_ts": agora_ts,
            "atualizado_fmt": agora_brasilia().strftime("%d/%m/%Y às %H:%M"),
        })
        return dict(_CACHE_DOCS)


# ==============================================================================
# MÓDULO 3: CONSULTA DE CNPJ (RECEITAWS + FALLBACK BRASIL API)
# ==============================================================================
def montar_endereco_empresa(logradouro, numero, bairro, municipio, uf, cep="", tipo_logradouro="") -> dict:
    log = str(logradouro or "").strip()
    tipo = str(tipo_logradouro or "").strip()
    rua = f"{tipo} {log}".strip() if tipo and not log.lower().startswith(tipo.lower()) else log
    num = str(numero or "").strip()
    bai = str(bairro or "").strip()
    mun = str(municipio or "").strip()
    estado = str(uf or "").strip()

    partes = [
        f"{rua} {num}".strip() if num else rua,
        bai,
        f"{mun} / {estado}".strip(" /"),
    ]
    endereco_fmt = ", ".join(p for p in partes if p)

    return {
        "endereco_completo": endereco_fmt or "Não informado",
        "municipio": mun,
        "uf": estado,
        "cep": re.sub(r"\D", "", str(cep or "")),
    }


def buscar_dados_cnpj(cnpj: str) -> tuple[dict | None, str | None]:
    cnpj_limpo = re.sub(r"\D", "", str(cnpj or ""))
    if len(cnpj_limpo) != 14:
        return None, "CNPJ inválido. Informe os 14 dígitos numéricos."

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    erro_ultimo = "Não foi possível consultar o CNPJ nas APIs públicas."

    # Tentativa 1: ReceitaWS
    try:
        resp = requests.get(f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}", headers=headers, timeout=12)
        if resp.status_code == 200:
            dados = resp.json()
            if dados.get("status") != "ERROR":
                atividades = dados.get("atividade_principal", []) + dados.get("atividades_secundarias", [])
                cnaes = []
                for a in atividades:
                    cod_norm = normalizar_cnae(a.get("code"))
                    if cod_norm and cod_norm != "0000000":
                        cnaes.append({
                            "codigo": cod_norm,
                            "codigo_formatado": a.get("code", ""),
                            "descricao": a.get("text", ""),
                        })
                return {
                    "cnpj": cnpj_limpo,
                    "razao_social": dados.get("nome", "Não informada"),
                    "situacao": dados.get("situacao", "Não informada"),
                    "endereco": montar_endereco_empresa(
                        dados.get("logradouro"),
                        dados.get("numero"),
                        dados.get("bairro"),
                        dados.get("municipio"),
                        dados.get("uf"),
                        dados.get("cep"),
                    ),
                    "cnaes": cnaes,
                }, None
            erro_ultimo = dados.get("message") or erro_ultimo
    except Exception:
        pass

    # Tentativa 2: Brasil API
    try:
        resp = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}", headers=headers, timeout=12)
        if resp.status_code == 200:
            dados = resp.json()
            cnaes = []
            cod_princ = normalizar_cnae(dados.get("cnae_fiscal"))
            if cod_princ:
                cnaes.append({
                    "codigo": cod_princ,
                    "codigo_formatado": str(dados.get("cnae_fiscal")),
                    "descricao": dados.get("cnae_fiscal_descricao", ""),
                })
            for sec in dados.get("cnaes_secundarios", []):
                cod_sec = normalizar_cnae(sec.get("codigo"))
                if cod_sec and cod_sec != "0000000":
                    cnaes.append({
                        "codigo": cod_sec,
                        "codigo_formatado": str(sec.get("codigo")),
                        "descricao": sec.get("descricao", ""),
                    })
            return {
                "cnpj": cnpj_limpo,
                "razao_social": dados.get("razao_social", "Não informada"),
                "situacao": dados.get("descricao_situacao_cadastral", "Não informada"),
                "endereco": montar_endereco_empresa(
                    dados.get("logradouro"),
                    dados.get("numero"),
                    dados.get("bairro"),
                    dados.get("municipio"),
                    dados.get("uf"),
                    dados.get("cep"),
                    dados.get("descricao_tipo_de_logradouro", ""),
                ),
                "cnaes": cnaes,
            }, None
        elif resp.status_code == 404:
            erro_ultimo = "CNPJ não encontrado na base da Receita Federal."
    except Exception:
        pass

    return None, erro_ultimo


# ==============================================================================
# MÓDULO 4: CRUZAMENTO CNAE x OBJETO + CLASSIFICAÇÃO POR PRAZO
# ==============================================================================
def verificar_compatibilidade_licitacao(licitacao: dict, cnaes_empresa: list[dict]) -> dict:
    texto_alvo = (
        licitacao["objeto"]
        if licitacao["objeto"] != "Não identificado"
        else licitacao["texto_bruto"]
    )
    texto_norm = normalizar_texto(texto_alvo)

    mapa_cnaes = {c["codigo"]: c for c in cnaes_empresa}
    codigos_empresa = set(mapa_cnaes.keys())

    categorias_casadas = []
    cnaes_compativeis = {}

    for dados_cat in OBJETOS_LICITACAO.values():
        termo_encontrado = None
        for termo in dados_cat["palavras_chave"]:
            termo_norm = normalizar_texto(termo)
            if len(termo_norm) >= 4 and not termo_norm.endswith("s"):
                padrao = rf"(?<!\w){re.escape(termo_norm)}(?:es|s)?(?!\w)"
            else:
                padrao = rf"(?<!\w){re.escape(termo_norm)}(?!\w)"

            if re.search(padrao, texto_norm):
                termo_encontrado = termo
                break

        if termo_encontrado:
            intersecao = codigos_empresa.intersection(dados_cat["cnaes_7_digitos"])
            if intersecao:
                categorias_casadas.append(dados_cat["rotulo"])
                for cod in intersecao:
                    cnaes_compativeis[cod] = mapa_cnaes[cod]

    return {
        "compativel": len(cnaes_compativeis) > 0,
        "categorias_atendidas": categorias_casadas,
        "cnaes_compativeis": list(cnaes_compativeis.values()),
    }


def serializar_item(lic: dict, analise: dict, agora: datetime, expirada: bool) -> dict:
    prazo_dt = lic["prazo_dt"]
    return {
        "caixa_escolar": lic["caixa_escolar"],
        "endereco": lic["endereco"],
        "id_compra": lic["id_compra"],
        "objeto": lic["objeto"],
        "prazo_texto": lic["prazo_texto"],
        "prazo_formatado": prazo_dt.strftime("%d/%m/%Y às %H:%M") if prazo_dt else None,
        "tempo_restante": (
            formatar_tempo_restante(prazo_dt, agora) if (prazo_dt and not expirada) else None
        ),
        "categorias_atendidas": analise["categorias_atendidas"],
        "cnaes_compativeis": analise["cnaes_compativeis"],
    }


def consultar_oportunidades(cnpj: str) -> dict:
    agora = agora_brasilia()
    cache = obter_licitacoes_cacheadas(forcar=False)
    dados_empresa, erro = buscar_dados_cnpj(cnpj)

    if erro or not dados_empresa:
        raise ValueError(erro or "Falha ao consultar CNPJ.")

    disponiveis = []
    expiradas = []
    sem_prazo = []

    for lic in cache["licitacoes"]:
        analise = verificar_compatibilidade_licitacao(lic, dados_empresa["cnaes"])
        if not analise["compativel"]:
            continue

        prazo_dt = lic["prazo_dt"]
        if prazo_dt is None:
            sem_prazo.append((None, serializar_item(lic, analise, agora, expirada=False)))
        elif prazo_dt >= agora:
            disponiveis.append((prazo_dt, serializar_item(lic, analise, agora, expirada=False)))
        else:
            expiradas.append((prazo_dt, serializar_item(lic, analise, agora, expirada=True)))

    # Ordena abertas por prazo mais próximo; expiradas pela mais recente
    disponiveis.sort(key=lambda par: par[0])
    expiradas.sort(key=lambda par: par[0], reverse=True)

    return {
        "consulta_em": agora.strftime("%d/%m/%Y às %H:%M:%S"),
        "documento": {
            "mes_referencia": cache["mes_referencia"],
            "url": cache["url"],
            "atualizado_em": cache["atualizado_fmt"],
            "total_licitacoes": len(cache["licitacoes"]),
        },
        "empresa": dados_empresa,
        "disponiveis": [item for _, item in disponiveis],
        "expiradas": [item for _, item in expiradas],
        "sem_prazo": [item for _, item in sem_prazo],
    }


# ==============================================================================
# MÓDULO 5: GEOLOCALIZAÇÃO E DISTÂNCIA (NOMINATIM + OSRM + HAVERSINE)
# ==============================================================================
def limpar_endereco_edital(endereco_bruto: str) -> str:
    texto = str(endereco_bruto or "").strip()
    texto = re.split(r"(?i)\bou\s+pel[oa]\b|\be-?mail\b|\btelefone\b|\btel\.?\b", texto)[0]
    texto = re.sub(r"(?i)\bn[º°\.]?\s*(?=\d)", "", texto)
    texto = re.sub(r"(?i)\bbairro\s+", "", texto)
    texto = re.sub(r"\s*[/–-]\s*([A-Z]{2})\b", r", \1, Brasil", texto)
    return limpar_espacos(texto).rstrip(".,; ")


def extrair_cidade_uf(endereco_bruto: str) -> str | None:
    texto = re.split(r"(?i)\bou\s+pel[oa]\b|\be-?mail\b", str(endereco_bruto or ""))[0]
    match = re.search(r"(?:,|^|\s-\s)\s*([^,/–-]+?)\s*[/–-]\s*([A-Z]{2})\b", texto)
    if match:
        cidade = limpar_espacos(match.group(1))
        uf = match.group(2).strip()
        return f"{cidade}, {uf}, Brasil"
    return None


def consultar_nominatim(query: str) -> tuple[float, float] | None:
    global _ULTIMA_REQ_NOMINATIM
    chave = normalizar_texto(query)

    with _LOCK_GEO:
        if chave in _CACHE_COORDS:
            return _CACHE_COORDS[chave]

        decorrido = time.time() - _ULTIMA_REQ_NOMINATIM
        if decorrido < 1.1:
            time.sleep(1.1 - decorrido)

        coords = None
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "br"},
                headers=HEADERS_GEO,
                timeout=10,
            )
            _ULTIMA_REQ_NOMINATIM = time.time()
            if resp.status_code == 200:
                resultados = resp.json()
                if resultados:
                    coords = (float(resultados[0]["lat"]), float(resultados[0]["lon"]))
        except Exception:
            _ULTIMA_REQ_NOMINATIM = time.time()

        _CACHE_COORDS[chave] = coords
        return coords


def geocodificar(endereco_bruto: str, cidade_fallback: str | None = None) -> tuple[tuple[float, float] | None, str]:
    end_limpo = limpar_endereco_edital(endereco_bruto)
    if end_limpo and end_limpo.lower() not in {"não identificado", "não informado"}:
        coords = consultar_nominatim(end_limpo)
        if coords:
            return coords, "endereço exato"

    alvo_cidade = cidade_fallback or extrair_cidade_uf(endereco_bruto)
    if alvo_cidade:
        coords = consultar_nominatim(alvo_cidade)
        if coords:
            return coords, "aproximada por cidade"

    return None, "não localizado"


def distancia_haversine_km(coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, coord1)
    lat2, lon2 = map(math.radians, coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def calcular_distancia(endereco_empresa: dict, endereco_licitacao: str) -> dict | None:
    cidade_emp = (
        f"{endereco_empresa['municipio']}, {endereco_empresa['uf']}, Brasil"
        if endereco_empresa.get("municipio") and endereco_empresa.get("uf")
        else None
    )
    coord_origem, prec_origem = geocodificar(endereco_empresa.get("endereco_completo", ""), cidade_emp)
    coord_destino, prec_destino = geocodificar(endereco_licitacao)

    if not coord_origem or not coord_destino:
        return None

    precisao = (
        "endereço exato"
        if prec_origem == "endereço exato" and prec_destino == "endereço exato"
        else "aproximada por cidade"
    )

    try:
        lat1, lon1 = coord_origem
        lat2, lon2 = coord_destino
        url_osrm = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}?overview=false"
        )
        resp = requests.get(url_osrm, headers=HEADERS_GEO, timeout=8)
        if resp.status_code == 200:
            dados = resp.json()
            if dados.get("routes"):
                rota = dados["routes"][0]
                return {
                    "km": round(rota["distance"] / 1000, 1),
                    "duracao_min": round(rota["duration"] / 60),
                    "metodo": "rota rodoviária",
                    "precisao": precisao,
                }
    except Exception:
        pass

    km_reta = distancia_haversine_km(coord_origem, coord_destino)
    return {
        "km": round(km_reta * 1.25, 1),
        "duracao_min": None,
        "metodo": "estimativa",
        "precisao": precisao,
    }