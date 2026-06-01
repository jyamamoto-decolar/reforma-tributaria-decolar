import io
import os
import re
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import date, datetime
import copy

app = FastAPI(title="Reforma Tributária Decolar")

# ─── DATA IN MEMORY ─────────────────────────────────────────────────────────

STEPS = [
    {
        "id": 1,
        "ano": 2023,
        "titulo": "EC 132/2023 — Aprovação da Reforma",
        "descricao": "Emenda Constitucional que extingue PIS, Cofins, IPI, ICMS e ISS e cria CBS, IBS e IS.",
        "status": "concluido",
        "categoria": "legislativo",
        "impacto_decolar": "Marco legal que determina o novo regime tributário para OTAs. Agências de viagem ganham regime especial na LC 214/2025.",
        "prazo": "2023-12-20",
        "marcos": [],
    },
    {
        "id": 2,
        "ano": 2025,
        "titulo": "LC 214/2025 — Regulamentação do IBS, CBS e IS",
        "descricao": "Lei Complementar que regulamenta os novos tributos. Define regime especial para turismo e agências de viagem: tributação sobre comissões e taxas de intermediação (não sobre valor bruto dos pacotes).",
        "status": "concluido",
        "categoria": "legislativo",
        "impacto_decolar": "Decolar tributa apenas sobre receita própria (comissões), não sobre o valor total das passagens/pacotes. Redução estimada de ~40% na alíquota efetiva vs. alíquota padrão.",
        "prazo": "2025-01-01",
        "marcos": [],
    },
    {
        "id": 3,
        "ano": 2026,
        "titulo": "2026 — Fase de Testes CBS + IBS (jan-dez)",
        "descricao": "Período experimental: obrigatoriedade de destacar CBS (0,9%) e IBS (0,1%) nos documentos fiscais eletrônicos (NF-e, NFC-e, CT-e, NFS-e). Não há recolhimento efetivo. Objetivo: adaptar sistemas, parametrizar cadastros, validar estrutura de crédito.",
        "status": "em_andamento",
        "categoria": "operacional",
        "impacto_decolar": "Decolar deve adaptar ERP/sistemas de faturamento para destacar CBS e IBS individualizados por operação em todas as NF-e emitidas. Simples Nacional e MEI dispensados em 2026.",
        "prazo": "2026-12-31",
        "marcos": [
            {
                "data": "2026-08-01",
                "descricao": "Obrigatoriedade plena do destaque nos documentos fiscais (Ato Conjunto RFB/CGIBS nº 1/2025). Prazo de adequação: 31/07/2026.",
                "critico": True,
            }
        ],
    },
    {
        "id": 4,
        "ano": 2027,
        "titulo": "2027 — Início da CBS plena + Imposto Seletivo",
        "descricao": "CBS passa a ser cobrada em alíquota plena, substituindo PIS e Cofins. Imposto Seletivo (IS) entra em vigor para bens e serviços com impacto negativo à saúde ou meio ambiente. IPI com alíquota zerada (exceto Zona Franca de Manaus). Início gradual do split payment.",
        "status": "pendente",
        "categoria": "compliance",
        "impacto_decolar": "Substituição efetiva de PIS/Cofins pela CBS. Revisão de contratos com fornecedores e parceiros. Implementação do split payment impacta fluxo de caixa — imposto retido na fonte na transação.",
        "prazo": "2027-01-01",
        "marcos": [],
    },
    {
        "id": 5,
        "ano": 2029,
        "titulo": "2029 — Transição IBS: 10% IBS / 90% ICMS+ISS",
        "descricao": "Início da transição gradual do IBS. ICMS e ISS começam a regredir proporcionalmente.",
        "status": "pendente",
        "categoria": "compliance",
        "impacto_decolar": "Início da convivência dual: Decolar opera com dois regimes simultaneamente. Necessidade de controles paralelos para ICMS/ISS (regressivo) e IBS (progressivo).",
        "prazo": "2029-01-01",
        "marcos": [],
    },
    {
        "id": 6,
        "ano": 2030,
        "titulo": "2030 — Transição IBS: 20% IBS / 80% ICMS+ISS",
        "descricao": "Segunda etapa da transição gradual.",
        "status": "pendente",
        "categoria": "compliance",
        "impacto_decolar": "Revisão de sistemas e controles. Monitoramento contínuo da alíquota efetiva.",
        "prazo": "2030-01-01",
        "marcos": [],
    },
    {
        "id": 7,
        "ano": 2031,
        "titulo": "2031 — Transição IBS: 30% IBS / 70% ICMS+ISS",
        "descricao": "Terceira etapa da transição gradual.",
        "status": "pendente",
        "categoria": "compliance",
        "impacto_decolar": "Acompanhamento da evolução da alíquota e impacto no pricing de pacotes.",
        "prazo": "2031-01-01",
        "marcos": [],
    },
    {
        "id": 8,
        "ano": 2032,
        "titulo": "2032 — Transição IBS: 40% IBS / 60% ICMS+ISS",
        "descricao": "Quarta e última etapa da transição gradual antes da vigência plena.",
        "status": "pendente",
        "categoria": "compliance",
        "impacto_decolar": "Revisão final de modelos de crédito tributário e estratégia fiscal.",
        "prazo": "2032-01-01",
        "marcos": [],
    },
    {
        "id": 9,
        "ano": 2033,
        "titulo": "2033 — Vigência Plena: Extinção do ICMS e ISS",
        "descricao": "IBS e CBS operam com alíquota integral. Extinção total do ICMS e do ISS. Consolidação do modelo de IVA dual brasileiro.",
        "status": "pendente",
        "categoria": "legislativo",
        "impacto_decolar": "Sistema tributário 100% no novo regime. Decolar opera exclusivamente com CBS e IBS sobre comissões e receita própria.",
        "prazo": "2033-01-01",
        "marcos": [],
    },
]

ATUALIZACOES = [
    {
        "id": 1,
        "data": "2026-05-24",
        "titulo": "50 projetos no Congresso tentam alterar a Reforma",
        "descricao": "Folha de S.Paulo apurou que 70% focam no Imposto Seletivo. Equipe econômica e entidades setoriais defendem manutenção do cronograma.",
        "fonte": "Folha de S.Paulo",
        "url": "https://www1.folha.uol.com.br/mercado/2026/05/reforma-tributaria-enfrenta-pressao-de-50-projetos-no-congresso-em-ano-eleitoral.shtml",
        "urgencia": "alta",
        "relevante_decolar": True,
        "tags": ["congresso", "imposto-seletivo", "risco-alteracao"],
    },
    {
        "id": 2,
        "data": "2026-05-01",
        "titulo": "Reforma tributária e o setor de turismo: nova fase operacional",
        "descricao": "Artigo da Panrotas analisa que a reforma exige revisão profunda de processos contratuais, atualização de sistemas ERP e controle rigoroso de insumos para agências e OTAs.",
        "fonte": "Panrotas",
        "url": "https://www.panrotas.com.br/mercado/economia-e-politica/2026/03/reforma-tributaria-inaugura-nova-fase-para-o-turismo-brasileiro-entenda-por-que_226782.html",
        "urgencia": "media",
        "relevante_decolar": True,
        "tags": ["turismo", "OTA", "operacional"],
    },
    {
        "id": 3,
        "data": "2026-04-01",
        "titulo": "Decreto nº 12.955/2026 — Impactos da CBS no segmento hoteleiro",
        "descricao": "Análise dos impactos específicos da CBS para hotelaria e viagens. Relevante para negociação de contratos B2B de Decolar com hotéis.",
        "fonte": "Hotelier News",
        "url": "https://hoteliernews.com.br/os-impactos-da-cbs-no-segmento-hoteleiro-sob-o-decreto-no-12-955-2026/",
        "urgencia": "media",
        "relevante_decolar": True,
        "tags": ["CBS", "hotelaria", "B2B", "contratos"],
    },
    {
        "id": 4,
        "data": "2026-01-01",
        "titulo": "Ato Conjunto RFB/CGIBS nº 1/2025 — Regras para documentos fiscais em 2026",
        "descricao": "Define exigências de destaque de CBS e IBS nas NF-e. A partir de 1º de agosto de 2026, obrigatoriedade plena. Prazo de adequação: 31/07/2026.",
        "fonte": "Receita Federal",
        "url": "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/reforma-tributaria-do-consumo/orientacoes-2026",
        "urgencia": "alta",
        "relevante_decolar": True,
        "tags": ["NF-e", "CBS", "IBS", "documentos-fiscais", "agosto-2026"],
    },
    {
        "id": 5,
        "data": "2025-12-01",
        "titulo": "Tax Free incluído na Reforma Tributária",
        "descricao": "Presidente Lula sancionou inclusão do Tax Free: reembolso de IBS e CBS para turistas estrangeiros. Oportunidade para Decolar posicionar produtos para turismo receptivo.",
        "fonte": "Ministério do Turismo",
        "url": "https://www.gov.br/turismo/pt-br/assuntos/noticias/presidente-lula-inclui-tax-free-na-reforma-tributaria-incentivando-o-turismo-e-a-economia-nacional",
        "urgencia": "baixa",
        "relevante_decolar": True,
        "tags": ["tax-free", "turismo-receptivo", "oportunidade"],
    },
]

PLANOS = [
    {
        "id": 1,
        "titulo": "Adaptação do ERP para destaque CBS/IBS nas NF-e",
        "area": "TI / Fiscal",
        "responsavel": "Time de TI",
        "prazo": "2026-07-31",
        "status": "em_andamento",
        "prioridade": "critica",
        "descricao": "Parametrização dos sistemas de emissão de NF-e para incluir campos de CBS (0,9%) e IBS (0,1%) individualizados por operação.",
        "step_relacionado_id": 3,
    },
    {
        "id": 2,
        "titulo": "Revisão de contratos com fornecedores (hotelaria, aéreo)",
        "area": "Jurídico / Comercial",
        "responsavel": "Time Jurídico",
        "prazo": "2026-12-31",
        "status": "pendente",
        "prioridade": "alta",
        "descricao": "Revisão de todos os contratos B2B para adequação ao novo regime de créditos tributários CBS/IBS.",
        "step_relacionado_id": 4,
    },
    {
        "id": 3,
        "titulo": "Mapeamento da base de cálculo — receita própria vs. repasse",
        "area": "Fiscal / Financeiro",
        "responsavel": "Time Fiscal",
        "prazo": "2026-09-30",
        "status": "pendente",
        "prioridade": "alta",
        "descricao": "Separação clara entre receita própria (comissões/taxas) e repasse de terceiros para correta aplicação do regime especial de agências de viagem (LC 214/2025).",
        "step_relacionado_id": 3,
    },
    {
        "id": 4,
        "titulo": "Análise de impacto do split payment no fluxo de caixa",
        "area": "Financeiro",
        "responsavel": "Time Financeiro",
        "prazo": "2026-12-31",
        "status": "pendente",
        "prioridade": "media",
        "descricao": "Modelagem financeira do impacto do split payment (previsto para 2027): retenção do imposto na transação e efeito no capital de giro.",
        "step_relacionado_id": 4,
    },
    {
        "id": 5,
        "titulo": "Avaliação oportunidade Tax Free para turismo receptivo",
        "area": "Produto / Comercial",
        "responsavel": "Time de Produto",
        "prazo": "2026-10-31",
        "status": "pendente",
        "prioridade": "baixa",
        "descricao": "Avaliar como posicionar produtos de Decolar para turistas estrangeiros aproveitando o benefício de reembolso de CBS/IBS via Tax Free.",
        "step_relacionado_id": 3,
    },
]

_plano_id_counter = 6  # next auto-increment

# ─── REUNIÕES DATA ────────────────────────────────────────────────────────────

REUNIOES = []
_reuniao_id_counter = 1

# ─── KEYWORDS E VERBOS ───────────────────────────────────────────────────────

KEYWORDS_TOPICOS = {
    "CBS": "CBS — Contribuição sobre Bens e Serviços",
    "IBS": "IBS — Imposto sobre Bens e Serviços",
    "split payment": "Split Payment",
    "NF-e": "Documentos Fiscais (NF-e)",
    "reforma tributária": "Reforma Tributária",
    "imposto seletivo": "Imposto Seletivo",
    "ERP": "Sistemas ERP",
    "ICMS": "ICMS",
    "ISS": "ISS",
    "LC 214": "LC 214/2025",
    "regime especial": "Regime Especial para OTAs",
    "comissão": "Comissões e Receita Própria",
    "fluxo de caixa": "Fluxo de Caixa",
    "contrato": "Revisão de Contratos",
    "prazo": "Prazos de Adequação",
    "crédito tributário": "Créditos Tributários",
    "tax free": "Tax Free",
}

VERBOS_ACAO = [
    "implementar", "revisar", "analisar", "mapear", "adaptar", "verificar",
    "criar", "definir", "contratar", "avaliar", "atualizar", "parametrizar",
    "adequar", "desenvolver", "elaborar", "preparar", "monitorar", "acompanhar",
    "negociar", "ajustar", "configurar", "testar", "validar", "migrar",
    "precisamos", "devemos", "vamos", "temos que", "é necessário", "há necessidade",
    "será necessário", "deve ser feito", "tem que ser", "precisa ser",
]

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────


def _extrair_texto_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def _extrair_texto_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extrair_texto_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def analisar_transcricao(texto: str, nome_arquivo: str) -> dict:
    texto_lower = texto.lower()
    linhas = texto.split("\n")

    participantes = set()
    pat_nome_dois_pontos = re.compile(r"^([A-ZÁÉÍÓÚÀÃÕÂÊÎÔÛÇ][a-záéíóúàãõâêîôûç]+(?:\s[A-ZÁÉÍÓÚÀÃÕÂÊÎÔÛÇ][a-záéíóúàãõâêîôûç]+)*):")
    pat_colchetes = re.compile(r"\[([A-ZÁÉÍÓÚÀÃÕÂÊÎÔÛÇ][a-záéíóúàãõâêîôûç]+(?:\s[A-ZÁÉÍÓÚÀÃÕÂÊÎÔÛÇ][a-záéíóúàãõâêîôûç]+)*)\]")
    pat_speaker = re.compile(r"(?:Speaker|Participante|Orador)\s+\d+:", re.IGNORECASE)
    pat_secao = re.compile(r"(?:Participantes?|Presentes?):\s*(.+)", re.IGNORECASE)

    for linha in linhas:
        linha_strip = linha.strip()
        if not linha_strip:
            continue
        m = pat_nome_dois_pontos.match(linha_strip)
        if m:
            participantes.add(m.group(1))
        for m2 in pat_colchetes.finditer(linha_strip):
            participantes.add(m2.group(1))
        if pat_speaker.match(linha_strip):
            participantes.add(linha_strip.split(":")[0].strip())
        m3 = pat_secao.match(linha_strip)
        if m3:
            for nome in re.split(r"[,;]", m3.group(1)):
                nome = nome.strip()
                if nome:
                    participantes.add(nome)

    participantes = list(participantes)[:20]

    topicos = []
    for kw, label in KEYWORDS_TOPICOS.items():
        if kw.lower() in texto_lower:
            topicos.append(label)

    marcadores_decisao = [
        "decidimos", "ficou definido", "ficou acordado", "aprovamos", "aprovado",
        "deliberamos", "concluímos", "foi decidido", "ficou estabelecido",
        "consenso", "alinhamos que",
    ]
    sentencas = re.split(r"[.!?\n]", texto)
    decisoes = []
    for s in sentencas:
        s_lower = s.lower()
        if any(m in s_lower for m in marcadores_decisao):
            s_clean = s.strip()
            if len(s_clean) > 15:
                decisoes.append(s_clean)

    marcadores_passos = [
        "próximos passos", "próxima etapa", "até o dia", "até o mês",
        "vai ficar responsável", "fica responsável", "encaminhamentos",
        "ação:", "tarefa:", "follow up", "acompanhar",
    ]
    proximos_passos = []
    for s in sentencas:
        s_lower = s.lower()
        if any(m in s_lower for m in marcadores_passos):
            s_clean = s.strip()
            if len(s_clean) > 15:
                proximos_passos.append(s_clean)

    total_palavras = len(texto.split())
    duracao_min = max(1, total_palavras // 130)
    duracao_estimada = f"{duracao_min} min"

    return {
        "participantes": participantes,
        "topicos_principais": topicos,
        "decisoes": decisoes,
        "proximos_passos": proximos_passos,
        "duracao_estimada": duracao_estimada,
        "total_palavras": total_palavras,
    }


def extrair_planos_sugeridos(texto: str) -> list:
    sentencas_raw = re.split(r"[.!?\n]", texto)
    sentencas = [s.strip() for s in sentencas_raw if s.strip()]

    def contar_verbos(sent: str) -> int:
        sl = sent.lower()
        return sum(1 for v in VERBOS_ACAO if v in sl)

    def inferir_area(sent: str) -> str:
        sl = sent.lower()
        if any(k in sl for k in ["erp", "sistema", "ti ", "tecnologia", "software"]):
            return "TI / Fiscal"
        if any(k in sl for k in ["contrato", "jurídico", "legal", "compliance"]):
            return "Jurídico / Comercial"
        if any(k in sl for k in ["fluxo de caixa", "financeiro", "orçamento", "capital"]):
            return "Financeiro"
        if any(k in sl for k in ["produto", "cliente", "comercial", "pricing"]):
            return "Produto / Comercial"
        return "Fiscal / Tributário"

    def inferir_responsavel(sentencas: list, idx: int) -> str:
        contexto = " ".join(sentencas[max(0, idx - 2):idx + 1])
        pat = re.compile(r"\b([A-ZÁÉÍÓÚÀÃÕÂÊÎÔÛÇ][a-záéíóúàãõâêîôûç]+(?:\s[A-ZÁÉÍÓÚÀÃÕÂÊÎÔÛÇ][a-záéíóúàãõâêîôûç]+)?)\b")
        nomes = pat.findall(contexto)
        stop = {"O", "A", "Os", "As", "Um", "Uma", "De", "Do", "Da", "Dos", "Das", "Em",
                "Para", "Com", "Por", "Que", "Se", "Não", "Na", "No"}
        nomes = [n for n in nomes if n not in stop and len(n) > 2]
        return nomes[0] if nomes else "A definir"

    def inferir_prazo(sent: str) -> str:
        m = re.search(r"\d{2}/\d{2}/\d{4}", sent)
        if m:
            return m.group(0)
        m = re.search(r"até\s+\w+\s+de\s+\d{4}", sent, re.IGNORECASE)
        if m:
            return m.group(0)
        m = re.search(r"até\s+o\s+dia\s+\d+", sent, re.IGNORECASE)
        if m:
            return m.group(0)
        return "A definir"

    def inferir_prioridade(sent: str) -> str:
        sl = sent.lower()
        if any(k in sl for k in ["urgente", "crítico", "imediato", "prioridade alta"]):
            return "critica"
        if any(k in sl for k in ["importante", "prioritário"]):
            return "alta"
        return "media"

    candidatos = []
    for i, sent in enumerate(sentencas):
        n_verbos = contar_verbos(sent)
        if n_verbos > 0:
            candidatos.append((n_verbos, i, sent))

    candidatos.sort(key=lambda x: x[0], reverse=True)
    candidatos = candidatos[:8]
    candidatos.sort(key=lambda x: x[1])

    planos = []
    for idx_plano, (n_verbos, i, sent) in enumerate(candidatos):
        titulo = sent[:80].strip()
        if len(titulo) < 20:
            continue
        planos.append({
            "idx": idx_plano,
            "titulo": titulo,
            "area": inferir_area(sent),
            "responsavel": inferir_responsavel(sentencas, i),
            "prazo": inferir_prazo(sent),
            "prioridade": inferir_prioridade(sent),
            "descricao": sent[:500].strip(),
            "trecho_origem": sent[:200].strip(),
            "status": "pendente",
        })

    return planos


# ─── PYDANTIC MODELS ─────────────────────────────────────────────────────────

class PlanoCreate(BaseModel):
    titulo: str
    area: str
    responsavel: str
    prazo: str
    status: str
    prioridade: str
    descricao: str
    step_relacionado_id: Optional[int] = None


class PlanoUpdate(BaseModel):
    titulo: Optional[str] = None
    area: Optional[str] = None
    responsavel: Optional[str] = None
    prazo: Optional[str] = None
    status: Optional[str] = None
    prioridade: Optional[str] = None
    descricao: Optional[str] = None
    step_relacionado_id: Optional[int] = None


# ─── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/api/steps")
def get_steps():
    return STEPS


@app.get("/api/steps/{step_id}")
def get_step(step_id: int):
    for s in STEPS:
        if s["id"] == step_id:
            return s
    raise HTTPException(status_code=404, detail="Step not found")


@app.get("/api/atualizacoes")
def get_atualizacoes():
    return sorted(ATUALIZACOES, key=lambda x: x["data"], reverse=True)


@app.get("/api/planos")
def get_planos():
    return PLANOS


@app.post("/api/planos", status_code=201)
def create_plano(plano: PlanoCreate):
    global _plano_id_counter
    new_plano = {"id": _plano_id_counter, **plano.model_dump()}
    _plano_id_counter += 1
    PLANOS.append(new_plano)
    return new_plano


@app.put("/api/planos/{plano_id}")
def update_plano(plano_id: int, update: PlanoUpdate):
    for i, p in enumerate(PLANOS):
        if p["id"] == plano_id:
            updates = {k: v for k, v in update.model_dump().items() if v is not None}
            PLANOS[i] = {**p, **updates}
            return PLANOS[i]
    raise HTTPException(status_code=404, detail="Plano not found")


@app.delete("/api/planos/{plano_id}")
def delete_plano(plano_id: int):
    for i, p in enumerate(PLANOS):
        if p["id"] == plano_id:
            PLANOS.pop(i)
            return {"ok": True}
    raise HTTPException(status_code=404, detail="Plano not found")


@app.get("/api/stats")
def get_stats():
    today = date.today()
    steps_concluidos = sum(1 for s in STEPS if s["status"] == "concluido")
    steps_em_andamento = sum(1 for s in STEPS if s["status"] == "em_andamento")
    steps_pendentes = sum(1 for s in STEPS if s["status"] == "pendente")
    planos_criticos = sum(1 for p in PLANOS if p["prioridade"] == "critica" and p["status"] != "concluido")

    proximos_marcos = []
    for s in STEPS:
        for m in s.get("marcos", []):
            marco_date = datetime.strptime(m["data"], "%Y-%m-%d").date()
            days_left = (marco_date - today).days
            proximos_marcos.append({
                "data": m["data"],
                "descricao": m["descricao"],
                "critico": m.get("critico", False),
                "step_titulo": s["titulo"],
                "days_left": days_left,
            })

    proximos_marcos.sort(key=lambda x: x["data"])

    return {
        "steps_concluidos": steps_concluidos,
        "steps_em_andamento": steps_em_andamento,
        "steps_pendentes": steps_pendentes,
        "planos_criticos": planos_criticos,
        "proximos_marcos": proximos_marcos[:5],
    }


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard():
    today = date.today()
    steps_concluidos = sum(1 for s in STEPS if s["status"] == "concluido")
    steps_em_andamento = sum(1 for s in STEPS if s["status"] == "em_andamento")
    steps_pendentes = sum(1 for s in STEPS if s["status"] == "pendente")
    planos_criticos = sum(1 for p in PLANOS if p["prioridade"] == "critica" and p["status"] != "concluido")

    proximos_marcos = []
    for s in STEPS:
        for m in s.get("marcos", []):
            marco_date = datetime.strptime(m["data"], "%Y-%m-%d").date()
            days_left = (marco_date - today).days
            proximos_marcos.append({
                "data": m["data"],
                "descricao": m["descricao"],
                "critico": m.get("critico", False),
                "step_titulo": s["titulo"],
                "days_left": days_left,
            })

    proximos_marcos.sort(key=lambda x: x["data"])

    total_reunioes = len(REUNIOES)
    planos_sugeridos_pendentes = sum(
        1 for r in REUNIOES
        for p in r["planos_sugeridos"]
        if p["status"] == "pendente"
    )

    return {
        "steps_concluidos": steps_concluidos,
        "steps_em_andamento": steps_em_andamento,
        "steps_pendentes": steps_pendentes,
        "planos_criticos": planos_criticos,
        "proximos_marcos": proximos_marcos[:5],
        "total_reunioes": total_reunioes,
        "planos_sugeridos_pendentes": planos_sugeridos_pendentes,
    }


# ─── REUNIÕES ENDPOINTS ───────────────────────────────────────────────────────

@app.post("/api/reunioes/upload", status_code=201)
async def upload_reuniao(file: UploadFile = File(...)):
    global _reuniao_id_counter

    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("txt", "pdf", "docx"):
        raise HTTPException(
            status_code=400,
            detail=f"Extensão '{ext}' não suportada. Use .txt, .pdf ou .docx",
        )

    file_bytes = await file.read()

    if ext == "txt":
        texto = _extrair_texto_txt(file_bytes)
    elif ext == "docx":
        texto = _extrair_texto_docx(file_bytes)
    else:
        texto = _extrair_texto_pdf(file_bytes)

    resumo = analisar_transcricao(texto, filename)
    planos_sugeridos = extrair_planos_sugeridos(texto)

    reuniao = {
        "id": _reuniao_id_counter,
        "data_upload": datetime.utcnow().isoformat(),
        "nome_arquivo": filename,
        "texto_transcricao": texto,
        "resumo": resumo,
        "planos_sugeridos": planos_sugeridos,
    }
    _reuniao_id_counter += 1
    REUNIOES.append(reuniao)
    return reuniao


@app.get("/api/reunioes")
def get_reunioes():
    return [{k: v for k, v in r.items() if k != "texto_transcricao"} for r in REUNIOES]


@app.get("/api/reunioes/{reuniao_id}")
def get_reuniao(reuniao_id: int):
    for r in REUNIOES:
        if r["id"] == reuniao_id:
            return r
    raise HTTPException(status_code=404, detail="Reunião não encontrada")


@app.post("/api/reunioes/{reuniao_id}/aprovar/{plano_idx}")
def aprovar_plano_sugerido(reuniao_id: int, plano_idx: int):
    global _plano_id_counter

    reuniao = None
    for r in REUNIOES:
        if r["id"] == reuniao_id:
            reuniao = r
            break
    if not reuniao:
        raise HTTPException(status_code=404, detail="Reunião não encontrada")

    plano_sug = None
    for p in reuniao["planos_sugeridos"]:
        if p["idx"] == plano_idx:
            plano_sug = p
            break
    if not plano_sug:
        raise HTTPException(status_code=404, detail="Plano sugerido não encontrado")

    plano_sug["status"] = "aprovado"

    novo_plano = {
        "id": _plano_id_counter,
        "titulo": plano_sug["titulo"],
        "area": plano_sug["area"],
        "responsavel": plano_sug["responsavel"],
        "prazo": plano_sug["prazo"],
        "status": "pendente",
        "prioridade": plano_sug["prioridade"],
        "descricao": plano_sug["descricao"],
        "step_relacionado_id": None,
    }
    _plano_id_counter += 1
    PLANOS.append(novo_plano)
    return novo_plano


@app.post("/api/reunioes/{reuniao_id}/rejeitar/{plano_idx}")
def rejeitar_plano_sugerido(reuniao_id: int, plano_idx: int):
    reuniao = None
    for r in REUNIOES:
        if r["id"] == reuniao_id:
            reuniao = r
            break
    if not reuniao:
        raise HTTPException(status_code=404, detail="Reunião não encontrada")

    for p in reuniao["planos_sugeridos"]:
        if p["idx"] == plano_idx:
            p["status"] = "rejeitado"
            return {"ok": True}

    raise HTTPException(status_code=404, detail="Plano sugerido não encontrado")


# ─── STATIC FILES + SPA ──────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
@app.get("/{full_path:path}")
def serve_spa(full_path: str = ""):
    return FileResponse("static/index.html")
