/* Vestra application export runtime v1.0 — loaded only on explicit export. */
(() => {
  'use strict';

  function csvFromRows(rows) {
    return rows.map(row => row.map(value => `"${String(value ?? '')}"`).join(';')).join('\n');
  }

  function downloadText(content, filename, mimeType) {
    const BOM = String(mimeType || '').includes('csv') ? '\uFEFF' : '';
    const blob = new Blob([BOM + content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    setTimeout(() => {
      if (anchor.parentNode) anchor.parentNode.removeChild(anchor);
      URL.revokeObjectURL(url);
    }, 1500);
  }

  function serializeBackup(state) {
    const seen = new WeakSet();
    return JSON.stringify(state, function replacer(key, value) {
      if (typeof key === 'string' && key.startsWith('_')) return undefined;
      let next = value;
      if (value instanceof Set) next = Array.from(value);
      else if (value instanceof Map) next = Array.from(value.entries());
      if (next && typeof next === 'object' && !Array.isArray(next)) {
        if (seen.has(next)) return undefined;
        seen.add(next);
      }
      return next;
    }, 2);
  }

  function exportBackup(state, filename) {
    const json = serializeBackup(state);
    if (!json) throw new Error('Falha ao gerar o backup.');
    downloadText(json, filename, 'application/json');
    return { bytes: json.length };
  }

  function exportCashflowCsv({ transactions, label, parseNum }) {
    const header = ['Data', 'Tipo', 'Categoria', 'Valor (EUR)', 'Recorrente', 'Notas'];
    const rows = transactions.map(tx => [
      tx.date || '', tx.type === 'in' ? 'Entrada' : 'Saída', tx.category || '',
      parseNum(tx.amount).toFixed(2), tx.recurring || 'none', (tx.notes || '').replace(/"/g, "'"),
    ]);
    downloadText(csvFromRows([header, ...rows]), `balanco_${label}.csv`, 'text/csv;charset=utf-8;');
  }

  function exportPortfolioCsv({ assets, liabilities, date, parseNum, hasExplicitAppreciationPct }) {
    const header = ['Tipo', 'Classe', 'Nome', 'Valor (EUR)', 'Tipo Yield', 'Yield Valor', 'Valorização Esperada %', 'Capitalização', 'Vencimento', 'Custo Aquis.', 'Notas'];
    const rows = [
      ...assets.map(asset => [
        'Ativo', asset.class || '', asset.name || '', parseNum(asset.value).toFixed(2), asset.yieldType || 'none',
        parseNum(asset.yieldValue).toFixed(4), hasExplicitAppreciationPct(asset) ? parseNum(asset.appreciationPct).toFixed(4) : '',
        asset.compoundFreq || '', asset.maturityDate || '', parseNum(asset.costBasis || 0).toFixed(2), (asset.notes || '').replace(/"/g, "'"),
      ]),
      ...liabilities.map(liability => [
        'Passivo', liability.class || '', liability.name || '', parseNum(liability.value).toFixed(2), '', '', '', '', '', '',
        (liability.notes || '').replace(/"/g, "'"),
      ]),
    ];
    downloadText(csvFromRows([header, ...rows]), `portfolio_${date}.csv`, 'text/csv;charset=utf-8;');
  }

  function exportPortfolioXlsx({ XLSX, assets, liabilities, transactions, totals, passiveAnnual, date, parseNum, hasExplicitAppreciationPct, passiveFromItem }) {
    const assetRows = assets.map(asset => ({
      Tipo: 'Ativo', Classe: asset.class || '', Nome: asset.name || '', 'Valor EUR': parseNum(asset.value),
      'Tipo Yield': asset.yieldType || 'none', 'Yield Valor': parseNum(asset.yieldValue),
      'Valorização Esperada %': hasExplicitAppreciationPct(asset) ? parseNum(asset.appreciationPct) : '',
      Capitalização: asset.compoundFreq || '', Vencimento: asset.maturityDate || '',
      'Custo Aquis.': parseNum(asset.costBasis || 0), 'Rend. Anual EUR': passiveFromItem(asset), Notas: asset.notes || '',
    }));
    const liabilityRows = liabilities.map(liability => ({
      Tipo: 'Passivo', Classe: liability.class || '', Nome: liability.name || '', 'Valor EUR': parseNum(liability.value),
      'Tipo Yield': '', 'Yield Valor': '', Capitalização: '', Vencimento: '', 'Custo Aquis.': 0, 'Rend. Anual EUR': 0, Notas: liability.notes || '',
    }));
    const transactionRows = transactions.map(tx => ({
      Data: tx.date || '', Tipo: tx.type === 'in' ? 'Entrada' : 'Saída', Categoria: tx.category || '',
      'Valor EUR': parseNum(tx.amount), Recorrente: tx.recurring || 'none', Notas: tx.notes || '',
    }));
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet([...assetRows, ...liabilityRows]), 'Portfólio');
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(transactionRows), 'Movimentos');
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet([
      { Métrica: 'Ativos Total', Valor: totals.assetsTotal },
      { Métrica: 'Passivos Total', Valor: totals.liabsTotal },
      { Métrica: 'Património Líquido', Valor: totals.net },
      { Métrica: 'Rendimento Passivo Anual', Valor: passiveAnnual },
      { Métrica: 'Data Exportação', Valor: date },
    ]), 'Resumo');
    XLSX.writeFile(workbook, `patrimonio_${date}.xlsx`);
  }

  function exportFiscalCsv({ dividends, year, parseNum, getDividendGross, getDividendNet }) {
    const header = ['Data', 'Activo', 'Dividendo Bruto (EUR)', 'Retenção (EUR)', 'Líquido (EUR)'];
    const rows = dividends.map(dividend => [
      dividend.date || '', dividend.assetName || '', getDividendGross(dividend).toFixed(2),
      parseNum(dividend.taxWithheld || 0).toFixed(2), getDividendNet(dividend).toFixed(2),
    ]);
    downloadText(csvFromRows([header, ...rows]), `fiscal_${year}.csv`, 'text/csv;charset=utf-8;');
  }

  function buildAnnualReportText({ totals, portfolioYield, twr, diversification, pnl, year, generatedDate, fmtEUR, fmtPct }) {
    return [
      `RELATÓRIO PATRIMONIAL ${year}`,
      `Gerado em: ${generatedDate}`,
      '', '═══════════════════════════════════════', 'BALANÇO GLOBAL', '═══════════════════════════════════════',
      `Activos totais:       ${fmtEUR(totals.assetsTotal)}`,
      `Passivos totais:      ${fmtEUR(totals.liabsTotal)}`,
      `Património líquido:   ${fmtEUR(totals.net)}`,
      '', '═══════════════════════════════════════', 'RENDIMENTO & RETORNO', '═══════════════════════════════════════',
      `Rendimento passivo anual: ${fmtEUR(totals.displayedPassiveAnnual)}`,
      `Rendimento mensal:        ${fmtEUR(totals.displayedPassiveAnnual / 12)}`,
      `Rendimento base projectado: ${fmtPct(portfolioYield.weightedYield)}`,
      `Retorno total:          ${fmtPct(portfolioYield.totalReturnBlended)}`,
      twr ? `TWR anualizado:           ${fmtPct(twr.annualised)} (${twr.years} anos)` : '',
      '', '═══════════════════════════════════════', 'PORTFÓLIO DE ACÇÕES/ETFs', '═══════════════════════════════════════',
      `Investido:    ${fmtEUR(pnl.totalCost)}`,
      `Valor actual: ${fmtEUR(pnl.totalCurrent)}`,
      `Ganho latente: ${pnl.totalGain >= 0 ? '+' : ''}${fmtEUR(pnl.totalGain)} (${pnl.totalGain >= 0 ? '+' : ''}${fmtPct(pnl.totalGainPct)})`,
      `P&L realizado: ${pnl.totalRealized >= 0 ? '+' : ''}${fmtEUR(pnl.totalRealized || 0)}`,
      `Dividendos recebidos: +${fmtEUR(pnl.totalDivAll || 0)}`,
      `Retorno total: ${pnl.grandTotalReturn >= 0 ? '+' : ''}${fmtEUR(pnl.grandTotalReturn || 0)} (${pnl.grandTotalReturn >= 0 ? '+' : ''}${fmtPct(pnl.grandTotalReturnPct || 0)})`,
      '', 'POSIÇÕES (Nome | P&L latente | Realizado | Dividendos | Retorno total | Yield):',
      ...pnl.positions.map(({ asset, pos }) => {
        const realised = pos.realizedPnL || 0;
        const dividends = pos.divAll || 0;
        const yieldPct = pos.trueYieldPct || 0;
        return `  ${String(asset.name).padEnd(12)} Latente: ${pos.gain >= 0 ? '+' : ''}${fmtEUR(pos.gain)} (${fmtPct(pos.gainPct)})` +
          (Math.abs(realised) > 0 ? `  Realiz: ${realised >= 0 ? '+' : ''}${fmtEUR(realised)}` : '') +
          (dividends > 0 ? `  Div: +${fmtEUR(dividends)}${yieldPct > 0 ? ` (${fmtPct(yieldPct)}yield)` : ''}` : '') +
          `  TOTAL: ${pos.totalReturn >= 0 ? '+' : ''}${fmtEUR(pos.totalReturn)}`;
      }),
      '', '═══════════════════════════════════════', 'ANÁLISE DE RISCO', '═══════════════════════════════════════',
      `Score diversificação: ${diversification.score}/100 (${diversification.label})`,
      `Rácio dívida/activos: ${fmtPct(totals.assetsTotal > 0 ? totals.liabsTotal / totals.assetsTotal * 100 : 0)}`,
      '', 'DISTRIBUIÇÃO POR CLASSE:',
      ...diversification.breakdown.map(row => `  ${String(row.cls).padEnd(20)} ${fmtPct(row.pct).padStart(7)} (${fmtEUR(row.val)})`),
      '', '═══════════════════════════════════════', 'AVISO LEGAL', '═══════════════════════════════════════',
      'Este relatório é meramente informativo.',
      'Consulta sempre um TOC para matérias fiscais',
      'e um consultor financeiro para decisões de investimento.',
    ].join('\n');
  }

  function exportAnnualReport(options) {
    const text = buildAnnualReportText(options);
    downloadText(text, `relatorio_patrimonial_${options.year}.txt`, 'text/plain;charset=utf-8;');
  }

  window.VestraAppExports = Object.freeze({
    csvFromRows,
    downloadText,
    serializeBackup,
    exportBackup,
    exportCashflowCsv,
    exportPortfolioCsv,
    exportPortfolioXlsx,
    exportFiscalCsv,
    buildAnnualReportText,
    exportAnnualReport,
    version: '1.0',
  });
})();
