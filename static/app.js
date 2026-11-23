const formBusca = document.getElementById("form-busca");
const inputCnpj = document.getElementById("input-cnpj");
const btnBuscar = document.getElementById("btn-buscar");
const btnAtualizar = document.getElementById("btn-atualizar");
const statusDoc = document.getElementById("status-doc");
const msgErro = document.getElementById("mensagem-erro");
const painelResultados = document.getElementById("painel-resultados");

const listaDisponiveis = document.getElementById("lista-disponiveis");
const listaExpiradas = document.getElementById("lista-expiradas");
const listaSemPrazo = document.getElementById("lista-sem-prazo");

let consultaAtualId = 0;

function escapeHtml(texto) {
  return String(texto || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function aplicarMascaraCnpj(valor) {
  const digitos = valor.replace(/\D/g, "").slice(0, 14);
  return digitos
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2");
}

inputCnpj.addEventListener("input", (e) => {
  e.target.value = aplicarMascaraCnpj(e.target.value);
});

function mostrarErro(texto) {
  if (!texto) {
    msgErro.classList.add("oculto");
    msgErro.textContent = "";
    return;
  }
  msgErro.textContent = texto;
  msgErro.classList.remove("oculto");
}

function formatarDuracao(minutos) {
  if (minutos === null || minutos === undefined) return "";
  if (minutos >= 60) {
    const h = Math.floor(minutos / 60);
    const m = String(minutos % 60).padStart(2, "0");
    return ` (~${h}h ${m}min de carro)`;
  }
  return ` (~${minutos} min de carro)`;
}

async function carregarStatus(forcar = false) {
  statusDoc.textContent = forcar ? "Atualizando editais..." : "Verificando editais...";
  btnAtualizar.disabled = true;

  try {
    const resp = await fetch(forcar ? "/api/atualizar" : "/api/status", {
      method: forcar ? "POST" : "GET",
    });
    const dados = await resp.json();
    if (!resp.ok) throw new Error(dados.detail || "Falha ao carregar editais.");

    statusDoc.textContent = `${dados.mes_referencia} • ${dados.total_licitacoes} licitações (atualizado ${dados.atualizado_em})`;
  } catch (err) {
    statusDoc.textContent = "Erro ao carregar editais da SRE.";
  } finally {
    btnAtualizar.disabled = false;
  }
}

btnAtualizar.addEventListener("click", () => carregarStatus(true));

document.querySelectorAll(".aba").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".aba").forEach((b) => b.classList.remove("ativa"));
    btn.classList.add("ativa");

    const alvo = btn.dataset.aba;
    listaDisponiveis.classList.toggle("oculto", alvo !== "disponiveis");
    listaExpiradas.classList.toggle("oculto", alvo !== "expiradas");
    listaSemPrazo.classList.toggle("oculto", alvo !== "sem_prazo");
  });
});

function criarCardHtml(item, tipo, idx) {
  const classeTipo =
    tipo === "expiradas" ? "expirada" : tipo === "sem_prazo" ? "sem-prazo" : "";

  let badgePrazo = `<span class="badge badge-amarelo">Conferir prazo</span>`;
  if (tipo === "disponiveis" && item.tempo_restante) {
    badgePrazo = `<span class="badge badge-verde">${escapeHtml(item.tempo_restante)}</span>`;
  } else if (tipo === "expiradas" && item.prazo_formatado) {
    badgePrazo = `<span class="badge badge-vermelho">Expirado em ${escapeHtml(item.prazo_formatado)}</span>`;
  }

  const linhaDistancia =
    tipo === "disponiveis"
      ? `<div class="lic-linha"><strong>Distância:</strong> <span id="dist-${idx}" class="texto-suave">Calculando distância...</span></div>`
      : "";

  const cnaesHtml = item.cnaes_compativeis
    .map((c) => `${escapeHtml(c.codigo_formatado)} - ${escapeHtml(c.descricao)}`)
    .join(" | ");

  const botaoCopiar =
    item.id_compra && item.id_compra !== "Não identificado"
      ? `<button type="button" class="btn-copiar" data-copy="${escapeHtml(item.id_compra)}">Copiar ID</button>`
      : "";

  return `
    <article class="licitacao-card ${classeTipo}">
      <div class="lic-topo">
        <h3 class="lic-titulo">${escapeHtml(item.caixa_escolar)}</h3>
        ${badgePrazo}
      </div>
      <div class="lic-grade">
        <div class="lic-linha"><strong>Endereço:</strong> ${escapeHtml(item.endereco)}</div>
        ${linhaDistancia}
        <div class="lic-linha">
          <strong>ID de Compra:</strong>
          <span class="id-bloco">
            <span>${escapeHtml(item.id_compra)}</span>
            ${botaoCopiar}
            <a class="link-sgd" href="https://caixaescolar.educacao.mg.gov.br/selecionar-perfil" target="_blank" rel="noopener noreferrer">Abrir SGD ↗</a>
          </span>
        </div>
        <div class="lic-linha"><strong>Objeto:</strong> ${escapeHtml(item.objeto)}</div>
        <div class="lic-linha"><strong>Prazo:</strong> ${escapeHtml(item.prazo_texto)}</div>
      </div>
      <div class="cnaes-lista"><strong>CNAE(s) compatíveis:</strong> ${cnaesHtml}</div>
    </article>
  `;
}

function renderizarLista(container, itens, tipo, textoVazio) {
  if (!itens.length) {
    container.innerHTML = `<div class="vazio">${escapeHtml(textoVazio)}</div>`;
    return;
  }
  container.innerHTML = itens.map((item, idx) => criarCardHtml(item, tipo, idx)).join("");

  container.querySelectorAll(".btn-copiar").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        const original = btn.textContent;
        btn.textContent = "Copiado!";
        setTimeout(() => (btn.textContent = original), 1500);
      } catch (_) {}
    });
  });
}

async function preencherDistanciasProgressivamente(dados, idExecucao) {
  for (let i = 0; i < dados.disponiveis.length; i++) {
    // Interrompe se o usuário iniciou outra consulta
    if (idExecucao !== consultaAtualId) return;

    const item = dados.disponiveis[i];
    const spanDist = document.getElementById(`dist-${i}`);
    if (!spanDist) continue;

    try {
      const resp = await fetch("/api/distancia", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endereco_empresa: dados.empresa.endereco,
          endereco_licitacao: item.endereco,
        }),
      });
      const res = await resp.json();

      if (idExecucao !== consultaAtualId) return;

      if (res.distancia) {
        const d = res.distancia;
        spanDist.className = "";
        spanDist.textContent = `~${d.km} km${formatarDuracao(d.duracao_min)} (${d.metodo} • ${d.precisao})`;
      } else {
        spanDist.textContent = "Não foi possível estimar";
      }
    } catch (_) {
      if (spanDist) spanDist.textContent = "Indisponível no momento";
    }
  }
}

formBusca.addEventListener("submit", async (e) => {
  e.preventDefault();
  mostrarErro("");

  const cnpjLimpo = inputCnpj.value.replace(/\D/g, "");
  if (cnpjLimpo.length !== 14) {
    mostrarErro("Digite um CNPJ válido com 14 números.");
    return;
  }

  consultaAtualId += 1;
  const idExecucao = consultaAtualId;

  btnBuscar.disabled = true;
  btnBuscar.textContent = "Consultando...";

  try {
    const resp = await fetch(`/api/consultar/${cnpjLimpo}`);
    const dados = await resp.json();
    if (!resp.ok) throw new Error(dados.detail || "Erro ao realizar consulta.");

    // Cabeçalho da empresa
    document.getElementById("empresa-nome").textContent = dados.empresa.razao_social;
    document.getElementById("empresa-endereco").textContent =
      `Endereço: ${dados.empresa.endereco.endereco_completo}`;

    const badgeSit = document.getElementById("empresa-situacao");
    badgeSit.textContent = dados.empresa.situacao;
    badgeSit.className =
      "badge " + (dados.empresa.situacao.toUpperCase() === "ATIVA" ? "badge-verde" : "badge-amarelo");

    document.getElementById("qtd-disponiveis").textContent = dados.disponiveis.length;
    document.getElementById("qtd-expiradas").textContent = dados.expiradas.length;
    document.getElementById("qtd-total-docs").textContent = dados.documento.total_licitacoes;
    document.getElementById("hora-consulta").textContent = dados.consulta_em;

    document.getElementById("aba-qtd-disponiveis").textContent = dados.disponiveis.length;
    document.getElementById("aba-qtd-expiradas").textContent = dados.expiradas.length;
    document.getElementById("aba-qtd-sem-prazo").textContent = dados.sem_prazo.length;

    const btnAbaSemPrazo = document.getElementById("btn-aba-sem-prazo");
    btnAbaSemPrazo.classList.toggle("oculto", dados.sem_prazo.length === 0);

    // Renderiza listas
    renderizarLista(
      listaDisponiveis,
      dados.disponiveis,
      "disponiveis",
      "Nenhuma licitação aberta compatível encontrada para este CNPJ."
    );
    renderizarLista(
      listaExpiradas,
      dados.expiradas,
      "expiradas",
      "Nenhuma licitação compatível com prazo expirado."
    );
    renderizarLista(
      listaSemPrazo,
      dados.sem_prazo,
      "sem_prazo",
      "Nenhuma licitação sem prazo identificado."
    );

    // Sempre volta para a aba "Disponíveis" após nova busca
    document.querySelector('.aba[data-aba="disponiveis"]').click();
    painelResultados.classList.remove("oculto");

    // Atualiza o status superior com a referência carregada
    statusDoc.textContent = `${dados.documento.mes_referencia} • ${dados.documento.total_licitacoes} licitações (atualizado ${dados.documento.atualizado_em})`;

    // Inicia o cálculo progressivo das distâncias em segundo plano
    if (dados.disponiveis.length > 0) {
      preencherDistanciasProgressivamente(dados, idExecucao);
    }
  } catch (err) {
    mostrarErro(err.message);
  } finally {
    btnBuscar.disabled = false;
    btnBuscar.textContent = "Consultar Licitações";
  }
});

// Carrega o status inicial do documento ao abrir a página
carregarStatus(false);