/**
 * Ad Shield Intelligence — Main App Orchestrator
 * Ties together RTB simulation, fraud detection, brand safety, and metrics
 */

import { generateBidRequest } from './rtb-simulator.js';
import { analyzeFraud, FRAUD_TYPES } from './fraud-engine.js';
import { analyzeBrandSafety } from './brand-safety.js';
import { MetricsTracker } from './metrics.js';

// --- State ---
let isRunning = false;
let intervalId = null;
let qps = 10;
const metrics = new MetricsTracker();
const MAX_FEED_ITEMS = 50;

// --- DOM References ---
const elements = {};

function $(id) { return document.getElementById(id); }

function initDomRefs() {
    elements.btnToggle = $('btn-toggle');
    elements.qpsSlider = $('qps-slider');
    elements.qpsValue = $('qps-value');
    elements.headerQps = $('header-qps');
    elements.rtbFeed = $('rtb-feed');
    elements.threatBadge = $('threat-level-badge');
    elements.gaugeLabel = $('gauge-label');
    elements.brandBadge = $('brand-level-badge');
    elements.brandLog = $('brand-log');
    elements.riskMatrix = $('risk-matrix');
    elements.footerTime = $('footer-time');
    
    // KPIs
    elements.kpiImpressions = $('kpi-impressions');
    elements.kpiFraudRate = $('kpi-fraud-rate');
    elements.kpiBlocked = $('kpi-blocked');
    elements.kpiEcpm = $('kpi-ecpm');
    elements.kpiLatency = $('kpi-latency');
    
    // Fraud counts
    elements.fraudBot = $('fraud-bot');
    elements.fraudClick = $('fraud-click');
    elements.fraudGeo = $('fraud-geo');
    elements.fraudSpoof = $('fraud-spoof');
    elements.fraudDevice = $('fraud-device');
}

// --- Ticker ---
function initTicker() {
    const tickerData = [
        { text: 'Google Ad Manager', flag: '📊', val: 'DOJ Antitrust Remedies Sep 2025', cls: 'down' },
        { text: 'Ad Fraud Losses', flag: '🚨', val: '$41.4B (+10% YoY)', cls: 'down' },
        { text: 'US Programmatic', flag: '🇺🇸', val: '$22B waste (64¢ lost per $1)', cls: 'down' },
        { text: 'Bot Traffic', flag: '🤖', val: '37% of web traffic', cls: 'down' },
        { text: 'MFA Sites', flag: '⚠️', val: '21% of display budgets drained', cls: 'down' },
        { text: 'Retail Media', flag: '🛒', val: '$100B by 2026 (+25%/yr)', cls: 'up' },
        { text: 'Amazon Ads', flag: '📦', val: '$60B revenue (2025)', cls: 'up' },
        { text: 'CTV US Spend', flag: '📺', val: '$33.5B (2025)', cls: 'up' },
        { text: 'Privacy Sandbox', flag: '🔒', val: 'Topics API + Protected Audience', cls: '' },
        { text: 'Prebid.js', flag: '🔧', val: 'Industry standard header bidding', cls: 'up' },
        { text: 'RTB Latency', flag: '⚡', val: '≤100ms end-to-end', cls: '' },
        { text: 'Naver ADVoost', flag: '🇰🇷', val: 'AI intent targeting (2025)', cls: 'up' },
    ];
    
    const inner = $('ticker-inner');
    // Duplicate for infinite scroll
    const html = tickerData.map(d => 
        `<span class="ticker-item"><span class="flag">${d.flag}</span>${d.text} <span class="val ${d.cls}">${d.val}</span></span>`
    ).join('');
    inner.innerHTML = html + html; // double for seamless loop
}

// --- Risk Matrix ---
function initRiskMatrix() {
    const categories = [
        { label: 'News', key: 'news' },
        { label: 'Tech', key: 'tech' },
        { label: 'Sports', key: 'sports' },
        { label: 'Social', key: 'social' },
        { label: 'MFA', key: 'mfa' },
        { label: 'Entertainment', key: 'entertain' },
        { label: 'Reference', key: 'reference' },
        { label: 'Other', key: 'other' },
    ];
    
    elements.riskMatrix.innerHTML = categories.map(c => 
        `<div class="risk-cell safe" id="risk-${c.key}">
            <span class="risk-val">0</span>
            <span class="risk-label">${c.label}</span>
        </div>`
    ).join('');
    
    // Store counters
    window._riskCounts = {};
    categories.forEach(c => window._riskCounts[c.key] = { safe: 0, moderate: 0, risky: 0, unsafe: 0, total: 0 });
}

// --- Feed Item ---
function createFeedItem(request, fraudResult, brandResult) {
    const item = document.createElement('div');
    item.className = 'feed-item';
    
    // Status dot
    let dotClass = 'safe';
    let tagClass = 'win';
    let tagText = 'WIN';
    let bidClass = '';
    
    if (fraudResult.shouldBlock) {
        dotClass = 'fraud';
        tagClass = 'blocked';
        tagText = 'BLOCKED';
        bidClass = 'blocked';
    } else if (fraudResult.isFraud) {
        dotClass = 'warn';
        tagClass = 'loss';
        tagText = 'FLAGGED';
    } else if (Math.random() < 0.3) {
        tagClass = 'loss';
        tagText = 'LOSS';
    }
    
    const signal = fraudResult.signals.length > 0 
        ? fraudResult.signals[0].reason 
        : brandResult.category;
    
    item.innerHTML = `
        <div class="dot ${dotClass}"></div>
        <div class="info">
            <span class="domain">${request.geo.flag} ${request.publisher.domain}</span>
            <span class="meta">${request.device.type} · ${signal}</span>
        </div>
        <span class="bid ${bidClass}">$${request.impression.winBid.toFixed(2)}</span>
        <span class="tag ${tagClass}">${tagText}</span>
    `;
    
    return item;
}

// --- Brand Log Entry ---
function createBrandEntry(brandResult) {
    const entry = document.createElement('div');
    entry.className = 'brand-entry';
    entry.innerHTML = `
        <span class="be-dot ${brandResult.level}"></span>
        <span class="be-domain">${brandResult.domain}</span>
        <span class="be-cat">${brandResult.category}</span>
    `;
    return entry;
}

// --- Update Risk Matrix Cell ---
function updateRiskCell(brandResult) {
    const catMap = {
        'News & Current Events': 'news',
        'Technology': 'tech',
        'Sports': 'sports',
        'Social Media': 'social',
        'Made For Advertising': 'mfa',
        'Entertainment': 'entertain',
        'Reference': 'reference',
    };
    
    const key = catMap[brandResult.category] || 'other';
    const counts = window._riskCounts[key];
    if (!counts) return;
    
    counts[brandResult.level]++;
    counts.total++;
    
    const cell = $(`risk-${key}`);
    if (!cell) return;
    
    // Determine dominant level
    let dominant = 'safe';
    let maxCount = counts.safe;
    for (const level of ['moderate', 'risky', 'unsafe']) {
        if (counts[level] > maxCount) {
            maxCount = counts[level];
            dominant = level;
        }
    }
    
    cell.className = `risk-cell ${dominant}`;
    cell.querySelector('.risk-val').textContent = counts.total;
}

// --- Process one bid request ---
function processBid() {
    const request = generateBidRequest();
    const fraudResult = analyzeFraud(request);
    const brandResult = analyzeBrandSafety(request);
    
    // Record metrics
    metrics.recordImpression(request, fraudResult, brandResult);
    
    // Update feed
    const feedItem = createFeedItem(request, fraudResult, brandResult);
    const feed = elements.rtbFeed;
    
    // Remove placeholder
    const empty = feed.querySelector('.feed-empty');
    if (empty) empty.remove();
    
    // Prepend
    feed.insertBefore(feedItem, feed.firstChild);
    
    // Limit items
    while (feed.children.length > MAX_FEED_ITEMS) {
        feed.lastChild.remove();
    }
    
    // Update brand log
    const brandEntry = createBrandEntry(brandResult);
    const brandLogEmpty = elements.brandLog.querySelector('.feed-empty');
    if (brandLogEmpty) brandLogEmpty.remove();
    
    elements.brandLog.insertBefore(brandEntry, elements.brandLog.firstChild);
    while (elements.brandLog.children.length > 30) {
        elements.brandLog.lastChild.remove();
    }
    
    // Update risk matrix
    updateRiskCell(brandResult);
}

// --- UI Updates (called every 500ms) ---
function updateUI() {
    // KPIs
    elements.kpiImpressions.textContent = formatNumber(metrics.totalImpressions);
    elements.kpiFraudRate.textContent = metrics.fraudRate.toFixed(1) + '%';
    elements.kpiBlocked.textContent = formatNumber(metrics.totalBlocked);
    elements.kpiEcpm.textContent = '$' + metrics.avgEcpm.toFixed(2);
    elements.kpiLatency.textContent = metrics.avgLatency.toFixed(0) + 'ms';
    
    // Header QPS
    elements.headerQps.textContent = isRunning ? `${qps} req/s` : '0 req/s';
    
    // Fraud breakdown
    elements.fraudBot.textContent = metrics.fraudCounts.bot_traffic;
    elements.fraudClick.textContent = metrics.fraudCounts.click_fraud;
    elements.fraudGeo.textContent = metrics.fraudCounts.geo_mismatch;
    elements.fraudSpoof.textContent = metrics.fraudCounts.domain_spoofing;
    elements.fraudDevice.textContent = metrics.fraudCounts.device_anomaly;
    
    // Threat gauge
    const rate = metrics.fraudRate;
    elements.gaugeLabel.textContent = rate.toFixed(1) + '%';
    metrics.updateGauge(rate);
    
    // Threat badge
    if (rate < 10) {
        elements.threatBadge.textContent = 'SAFE';
        elements.threatBadge.className = 'panel-badge threat';
    } else if (rate < 25) {
        elements.threatBadge.textContent = 'ELEVATED';
        elements.threatBadge.className = 'panel-badge threat elevated';
    } else {
        elements.threatBadge.textContent = 'CRITICAL';
        elements.threatBadge.className = 'panel-badge threat critical';
    }
    
    // Brand safety badge
    const unsafeRatio = metrics.totalImpressions > 0 
        ? (metrics.brandCounts.unsafe + metrics.brandCounts.risky) / metrics.totalImpressions 
        : 0;
    if (unsafeRatio < 0.1) {
        elements.brandBadge.textContent = 'SAFE';
        elements.brandBadge.className = 'panel-badge safe';
    } else if (unsafeRatio < 0.25) {
        elements.brandBadge.textContent = 'MODERATE';
        elements.brandBadge.className = 'panel-badge threat elevated';
    } else {
        elements.brandBadge.textContent = 'AT RISK';
        elements.brandBadge.className = 'panel-badge threat critical';
    }
    
    // Footer time
    elements.footerTime.textContent = new Date().toLocaleTimeString();
}

// --- Format number ---
function formatNumber(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
    return n.toString();
}

// --- Simulation Control ---
function startSimulation() {
    if (isRunning) return;
    isRunning = true;
    
    elements.btnToggle.classList.add('active');
    elements.btnToggle.innerHTML = `<svg viewBox="0 0 24 24" fill="none" width="18" height="18"><rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor"/><rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor"/></svg>`;
    
    // Generate bids at configured QPS
    intervalId = setInterval(() => {
        processBid();
    }, 1000 / qps);
    
    // UI refresh loop
    window._uiInterval = setInterval(updateUI, 500);
    
    // Chart data flush every 1s
    window._flushInterval = setInterval(() => {
        metrics.flushWindow();
        metrics.updateChart();
    }, 1000);
}

function stopSimulation() {
    if (!isRunning) return;
    isRunning = false;
    
    elements.btnToggle.classList.remove('active');
    elements.btnToggle.innerHTML = `<svg viewBox="0 0 24 24" fill="none" width="18" height="18"><polygon points="8,5 19,12 8,19" fill="currentColor"/></svg>`;
    
    clearInterval(intervalId);
    clearInterval(window._uiInterval);
    clearInterval(window._flushInterval);
}

// --- Init ---
function init() {
    initDomRefs();
    initTicker();
    initRiskMatrix();
    
    // Charts
    metrics.initCharts('main-chart');
    metrics.initGauge('threat-gauge-chart');
    
    // Event: Toggle
    elements.btnToggle.addEventListener('click', () => {
        if (isRunning) stopSimulation();
        else startSimulation();
    });
    
    // Event: QPS slider
    elements.qpsSlider.addEventListener('input', (e) => {
        qps = parseInt(e.target.value);
        elements.qpsValue.textContent = qps;
        
        if (isRunning) {
            clearInterval(intervalId);
            intervalId = setInterval(processBid, 1000 / qps);
        }
    });
    
    // Event: Chart tabs
    document.querySelectorAll('.chart-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            metrics.switchChart(tab.dataset.chart);
        });
    });
    
    // Footer time
    updateUI();
    setInterval(() => {
        elements.footerTime.textContent = new Date().toLocaleTimeString();
    }, 1000);
    
    // Auto-start after 500ms
    setTimeout(() => {
        startSimulation();
    }, 500);
}

// Boot
document.addEventListener('DOMContentLoaded', init);
