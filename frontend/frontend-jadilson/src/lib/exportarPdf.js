function escapeHtml(valor) {
  return String(valor ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function linha(rotulo, valor) {
  if (!valor) return "";
  return `
    <div class="linha">
      <span class="rotulo">${escapeHtml(rotulo)}</span>
      <span class="valor">${escapeHtml(valor)}</span>
    </div>
  `;
}

/**
 * Gera um PDF do processo usando a caixa de diálogo de impressão do navegador
 * (Salvar como PDF), sem depender de bibliotecas externas.
 */
export function exportarProcessoPdf(processo) {
  const janela = window.open("", "_blank", "width=820,height=1000");
  if (!janela) return;

  const html = `
    <!doctype html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8" />
        <title>Processo ${escapeHtml(processo.numero)}</title>
        <style>
          @page { size: A4; margin: 24mm 18mm; }
          * { box-sizing: border-box; }
          body {
            font-family: "Segoe UI", Helvetica, Arial, sans-serif;
            color: #1a1a1a;
            line-height: 1.5;
            padding: 0;
          }
          header {
            border-bottom: 2px solid #1a1a1a;
            padding-bottom: 14px;
            margin-bottom: 20px;
          }
          header h1 { font-size: 20px; margin: 0 0 4px; }
          header p { margin: 0; color: #555; font-size: 13px; }
          h2 {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #555;
            margin: 24px 0 10px;
          }
          .linha {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            padding: 8px 0;
            border-bottom: 1px solid #e5e5e5;
            font-size: 13px;
          }
          .rotulo { color: #666; }
          .valor { font-weight: 600; text-align: right; }
          .descricao {
            font-size: 13px;
            background: #f5f5f5;
            border-radius: 8px;
            padding: 14px;
            margin-top: 8px;
          }
          footer {
            margin-top: 40px;
            font-size: 11px;
            color: #999;
            text-align: center;
          }
        </style>
      </head>
      <body>
        <header>
          <h1>Relatório do Processo</h1>
          <p>Jadilson Silva Advocacia · Gerado em ${new Date().toLocaleString("pt-BR")}</p>
        </header>

        <h2>Dados do processo</h2>
        ${linha("Número CNJ", processo.numero)}
        ${linha("Cliente", processo.cliente)}
        ${linha("Área / Tipo de ação", processo.tipoAcao)}
        ${linha("Vara / Foro", processo.vara)}
        ${linha("Estágio atual", processo.status)}
        ${linha("Valor da causa", processo.valorCausa)}
        ${linha("Cadastrado em", processo.criadoEm)}

        ${
          processo.descricao
            ? `<h2>Objeto da ação</h2><div class="descricao">${escapeHtml(processo.descricao)}</div>`
            : ""
        }

        <footer>Documento gerado automaticamente pelo sistema de gestão do escritório.</footer>
      </body>
    </html>
  `;

  janela.document.open();
  janela.document.write(html);
  janela.document.close();

  janela.onload = () => {
    janela.focus();
    janela.print();
  };
}
