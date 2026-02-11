/**
 * Dashboard HTML template and data extraction.
 *
 * Extracted from dashboardProvider.ts for separation
 * of concerns: data extraction + HTML rendering.
 */

// ─── Data Interface ──────────────────────────────────

export interface DashboardData {
    version: string;
    // v1 index
    crystals: number;
    tokens: number;
    symbols: number;
    relations: number;
    health: string;
    staleFiles: number;
    // v2.1 health check
    storeHealth: string;
    routerHealth: string;
    factsCount: number;
    domainsCount: number;
    // Hierarchy
    l0Facts: number;
    l1Facts: number;
    l2Facts: number;
    l3Facts: number;
    totalFacts: number;
    // Compression
    rawTokens: number;
    compressionRatio: number;
    savingsPercent: string;
    // Session
    queries: number;
    tokensServed: number;
    tokensSaved: number;
    savingsSessionPercent: number;
}

// ─── Data Extraction ─────────────────────────────────

export function extractDashboardData(
    status: any,
    validation: any,
    sessionStats: any,
    healthCheck: any,
    hierarchyStats: any,
): DashboardData {
    const crystals = status.success
        ? status.index?.crystals || 0 : 0;
    const tokens = status.success
        ? status.index?.tokens || 0 : 0;
    const symbols = validation.success
        ? validation.symbols?.total_symbols || 0 : 0;
    const relations = validation.success
        ? validation.symbols?.defined_functions || 0
        : 0;
    const health = validation.success
        ? validation.health : 'unknown';
    const staleFiles = validation.success
        ? validation.stale_files || 0 : 0;

    // v2.1
    const hcOk =
        healthCheck.status === 'healthy'
        || healthCheck.success;
    const hcComponents = hcOk
        ? healthCheck.components || {} : {};
    const storeHealth =
        hcComponents.store?.status || 'unknown';
    const routerHealth =
        hcComponents.router?.status || 'unknown';
    const factsCount =
        hcComponents.store?.facts_count || 0;
    const domainsCount =
        hcComponents.store?.domains || 0;

    // Hierarchy
    const hsOk =
        hierarchyStats.status === 'success'
        || hierarchyStats.success;
    const hierarchy = hsOk
        ? hierarchyStats.memory_store || {} : {};
    const l0Facts =
        hierarchy.by_level?.L0_PROJECT || 0;
    const l1Facts =
        hierarchy.by_level?.L1_DOMAIN || 0;
    const l2Facts =
        hierarchy.by_level?.L2_MODULE || 0;
    const l3Facts =
        hierarchy.by_level?.L3_CODE || 0;
    const totalFacts = hierarchy.total_facts || 0;

    // Compression
    const rawTokens = tokens * 56;
    const compressionRatio = 56;
    const savingsPercent =
        ((1 - 1 / compressionRatio) * 100).toFixed(1);

    return {
        version: '2.1.0',
        crystals, tokens, symbols, relations,
        health, staleFiles,
        storeHealth, routerHealth,
        factsCount, domainsCount,
        l0Facts, l1Facts, l2Facts, l3Facts,
        totalFacts,
        rawTokens, compressionRatio, savingsPercent,
        queries:
            sessionStats.session?.queries || 0,
        tokensServed:
            sessionStats.session?.tokens_served || 0,
        tokensSaved:
            sessionStats.session?.tokens_saved || 0,
        savingsSessionPercent:
            sessionStats.session?.savings_percent || 0,
    };
}

// ─── Token Formatter ─────────────────────────────────

export function formatTokens(tokens: number): string {
    if (tokens >= 1000000) {
        return (tokens / 1000000).toFixed(1) + 'M';
    } else if (tokens >= 1000) {
        return (tokens / 1000).toFixed(1) + 'K';
    }
    return tokens.toString();
}

// ─── HTML Template ───────────────────────────────────

export function renderDashboardHtml(d: DashboardData): string {
    const storeIcon = d.storeHealth === 'healthy' ? '✅' : '⚠️';
    const storeClass = d.storeHealth === 'healthy' ? 'success' : '';
    const routerIcon = d.routerHealth === 'healthy' ? '✅ embeddings' : '⚠️ ' + d.routerHealth;
    const routerClass = d.routerHealth === 'healthy' ? 'success' : '';
    const healthDot = d.health === 'good' ? 'good' : 'warning';
    const compressionLabel = d.totalFacts > 0 ? '~33x' : '-';
    const savedLabel = d.totalFacts > 0 ? '~97%' : '-';

    const warningBanner = d.staleFiles > 0
        ? '<div class="warning-banner">'
        + '<span class="warning-icon">⚠️</span>'
        + '<span class="warning-text">Index outdated (' + d.staleFiles + ' files changed)</span>'
        + '<button onclick="reindex()" class="warning-btn">Update</button>'
        + '</div>'
        : '';

    return '<!DOCTYPE html>'
    + '<html><head><style>'
    + 'body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); padding: 10px; font-size: 13px; }'
    + '.header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid var(--vscode-panel-border); }'
    + '.header h2 { margin: 0; font-size: 14px; font-weight: 600; }'
    + '.version { color: var(--vscode-descriptionForeground); font-size: 11px; }'
    + '.section { margin-bottom: 16px; }'
    + '.section-title { font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }'
    + '.stat-row { display: flex; justify-content: space-between; margin: 4px 0; padding: 2px 0; }'
    + '.stat-label { color: var(--vscode-descriptionForeground); }'
    + '.stat-value { font-weight: 500; }'
    + '.stat-value.success { color: var(--vscode-testing-iconPassed); }'
    + '.progress-bar { height: 8px; background: var(--vscode-progressBar-background); border-radius: 4px; margin: 8px 0; overflow: hidden; }'
    + '.progress-fill { height: 100%; background: linear-gradient(90deg, var(--vscode-testing-iconPassed) 0%, var(--vscode-charts-green) 100%); border-radius: 4px; }'
    + '.button-row { display: flex; gap: 8px; margin-top: 8px; }'
    + 'button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; flex: 1; }'
    + 'button:hover { background: var(--vscode-button-hoverBackground); }'
    + '.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }'
    + '.status-dot.good { background: var(--vscode-testing-iconPassed); }'
    + '.status-dot.warning { background: var(--vscode-testing-iconQueued); }'
    + '.status-dot.error { background: var(--vscode-testing-iconFailed); }'
    + '.icon { font-size: 14px; }'
    + '.info-section { background: var(--vscode-textBlockQuote-background); border-left: 3px solid var(--vscode-textLink-foreground); }'
    + '.info-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; }'
    + '.info-icon { font-size: 14px; }'
    + '.info-text { color: var(--vscode-foreground); }'
    + '.info-text strong { color: var(--vscode-textLink-foreground); }'
    + 'select { background: var(--vscode-dropdown-background); color: var(--vscode-dropdown-foreground); border: 1px solid var(--vscode-dropdown-border); padding: 4px 8px; border-radius: 4px; font-size: 12px; flex: 1; }'
    + '.warning-banner { display: flex; align-items: center; gap: 8px; padding: 8px 12px; margin: 0 0 8px 0; background: var(--vscode-inputValidation-warningBackground); border: 1px solid var(--vscode-inputValidation-warningBorder); border-radius: 4px; }'
    + '.warning-icon { font-size: 14px; }'
    + '.warning-text { flex: 1; font-size: 12px; color: var(--vscode-foreground); }'
    + '.warning-btn { padding: 4px 8px; font-size: 11px; background: var(--vscode-button-background); }'
    + '</style></head><body>'

    // Header
    + '<div class="header">'
    + '<span class="icon">🔮</span>'
    + '<h2>RLM-Toolkit</h2>'
    + '<span class="version">v' + d.version + '</span>'
    + '</div>'

    + warningBanner

    // Enterprise v2.1
    + '<div class="section">'
    + '<div class="section-title"><span class="icon">🏗️</span> Enterprise v2.1</div>'
    + statRow('Total Facts', String(d.totalFacts))
    + statRow('Domains', String(d.domainsCount))
    + '<div class="button-row">'
    + '<button onclick="discover()">🚀 Discover</button>'
    + '<button onclick="gitHook()">🪝 Git Hook</button>'
    + '</div></div>'

    // Health Check
    + '<div class="section">'
    + '<div class="section-title"><span class="icon">🔒</span> Health Check</div>'
    + '<div class="stat-row"><span class="stat-label">Store</span>'
    + '<span class="stat-value ' + storeClass + '">' + storeIcon + ' ' + d.factsCount + ' facts</span></div>'
    + '<div class="stat-row"><span class="stat-label">Router</span>'
    + '<span class="stat-value ' + routerClass + '">' + routerIcon + '</span></div>'
    + '</div>'

    // Hierarchical Memory
    + '<div class="section">'
    + '<div class="section-title"><span class="icon">📊</span> Hierarchical Memory (L0-L3)</div>'
    + statRow('L0 Project', String(d.l0Facts))
    + statRow('L1 Domain', String(d.l1Facts))
    + statRow('L2 Module', String(d.l2Facts))
    + statRow('L3 Code', String(d.l3Facts))
    + '<div class="button-row"><button onclick="indexEmbeddings()">💉 Index Embeddings</button></div>'
    + '</div>'

    // Token Economics
    + '<div class="section">'
    + '<div class="section-title"><span class="icon">📈</span> Token Economics</div>'
    + statRow('Raw Project', formatTokens(d.totalFacts * 500))
    + statRow('As Facts', formatTokens(d.totalFacts * 15))
    + '<div class="stat-row"><span class="stat-label">Compression</span><span class="stat-value good">' + compressionLabel + '</span></div>'
    + '<div class="stat-row"><span class="stat-label">Saved</span><span class="stat-value good">' + savedLabel + '</span></div>'
    + '</div>'

    // Project Index
    + '<div class="section">'
    + '<div class="section-title"><span class="icon">📊</span> Project Index '
    + '<span class="status-dot ' + healthDot + '"></span></div>'
    + statRow('Files', d.crystals.toLocaleString())
    + statRow('Tokens', formatTokens(d.tokens))
    + statRow('Symbols', d.symbols.toLocaleString())
    + statRow('Relations', d.relations.toLocaleString())
    + '<div class="button-row">'
    + '<button onclick="reindex()">🔄 Reindex</button>'
    + '<button onclick="validate()">✓ Validate</button>'
    + '</div></div>'

    // Compression
    + '<div class="section">'
    + '<div class="section-title"><span class="icon">⚡</span> Compression</div>'
    + statRow('Raw Context', formatTokens(d.rawTokens))
    + statRowSuccess('After RLM', formatTokens(d.tokens))
    + statRowSuccess('Compression', d.compressionRatio + 'x')
    + '<div class="progress-bar"><div class="progress-fill" style="width: ' + d.savingsPercent + '%"></div></div>'
    + statRowSuccess('Savings', d.savingsPercent + '%')
    + '</div>'

    // Session Stats
    + '<div class="section">'
    + '<div class="section-title"><span class="icon">📈</span> Session Stats (Live)</div>'
    + statRow('RLM Queries', String(d.queries))
    + statRow('Tokens Served', formatTokens(d.tokensServed))
    + statRowSuccess('Tokens Saved', formatTokens(d.tokensSaved))
    + statRowSuccess('Savings', d.savingsSessionPercent + '%')
    + '<div class="stat-note"><small>* Updates on RLM MCP tool calls (query, reindex)</small></div>'
    + '</div>'

    // Memory
    + '<div class="section">'
    + '<div class="section-title"><span class="icon">🧠</span> Memory (H-MEM)</div>'
    + statRow('Status', 'Active')
    + '<div class="button-row"><button onclick="consolidate()">🔄 Consolidate</button></div>'
    + '</div>'

    // How It Works
    + '<div class="section info-section">'
    + '<div class="section-title"><span class="icon">💡</span> How It Works</div>'
    + '<div class="info-row"><span class="info-icon">💾</span><span class="info-text">Code indexed <strong>locally</strong></span></div>'
    + '<div class="info-row"><span class="info-icon">📡</span><span class="info-text">AI receives <strong>compressed context</strong></span></div>'
    + '<div class="info-row"><span class="info-icon">🔒</span><span class="info-text">Savings: <strong>' + d.savingsPercent + '% traffic</strong></span></div>'
    + '<div class="stat-note"><small>Your code never leaves your machine in full</small></div>'
    + '</div>'

    // Script
    + '<script>'
    + 'const vscode = acquireVsCodeApi();'
    + 'function reindex() { vscode.postMessage({ command: "reindex" }); }'
    + 'function validate() { vscode.postMessage({ command: "validate" }); }'
    + 'function consolidate() { vscode.postMessage({ command: "consolidate" }); }'
    + 'function discover() { vscode.postMessage({ command: "discover" }); }'
    + 'function gitHook() { vscode.postMessage({ command: "gitHook" }); }'
    + 'function indexEmbeddings() { vscode.postMessage({ command: "indexEmbeddings" }); }'
    + 'function refresh() { vscode.postMessage({ command: "refresh" }); }'
    + 'setInterval(refresh, 30000);'
    + '</script>'

    + '</body></html>';
}

// ─── Helpers ─────────────────────────────────────────

function statRow(label: string, value: string): string {
    return '<div class="stat-row">'
        + '<span class="stat-label">' + label + '</span>'
        + '<span class="stat-value">' + value + '</span>'
        + '</div>';
}

function statRowSuccess(label: string, value: string): string {
    return '<div class="stat-row">'
        + '<span class="stat-label">' + label + '</span>'
        + '<span class="stat-value success">' + value + '</span>'
        + '</div>';
}
