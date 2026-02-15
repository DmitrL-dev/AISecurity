/**
 * Metrics Tracker — real-time KPI tracking and chart management
 */

const MAX_CHART_POINTS = 30;

export class MetricsTracker {
    constructor() {
        this.totalImpressions = 0;
        this.totalFraud = 0;
        this.totalBlocked = 0;
        this.totalBidValue = 0;
        this.totalLatency = 0;
        this.latencyCount = 0;
        
        // Fraud breakdown
        this.fraudCounts = {
            bot_traffic: 0,
            click_fraud: 0,
            geo_mismatch: 0,
            domain_spoofing: 0,
            device_anomaly: 0,
        };
        
        // Brand safety breakdown
        this.brandCounts = {
            safe: 0,
            moderate: 0,
            risky: 0,
            unsafe: 0,
        };
        
        // Time series data
        this.series = {
            traffic: { labels: [], legitimate: [], fraudulent: [] },
            fraud: { labels: [], rates: [] },
            latency: { labels: [], p50: [], p95: [] },
        };
        
        // Current window (per-second accumulator)
        this._windowStart = Date.now();
        this._windowLegit = 0;
        this._windowFraud = 0;
        this._windowLatencies = [];
        
        // Charts
        this.charts = {};
        this.activeChart = 'traffic';
    }
    
    recordImpression(request, fraudResult, brandResult) {
        this.totalImpressions++;
        this.totalBidValue += request.impression.winBid;
        this.totalLatency += request.latencyMs;
        this.latencyCount++;
        this._windowLatencies.push(request.latencyMs);
        
        if (fraudResult.isFraud) {
            this.totalFraud++;
            this._windowFraud++;
            
            // Count by type
            const types = new Set(fraudResult.signals.map(s => s.type));
            for (const t of types) {
                if (this.fraudCounts[t] !== undefined) {
                    this.fraudCounts[t]++;
                }
            }
        } else {
            this._windowLegit++;
        }
        
        if (fraudResult.shouldBlock) {
            this.totalBlocked++;
        }
        
        // Brand safety
        if (brandResult && this.brandCounts[brandResult.level] !== undefined) {
            this.brandCounts[brandResult.level]++;
        }
    }
    
    // Flush accumulated window data into time series (call every ~1s)
    flushWindow() {
        const now = new Date();
        const label = `${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
        
        // Traffic series
        this._pushSeries(this.series.traffic.labels, label);
        this._pushSeries(this.series.traffic.legitimate, this._windowLegit);
        this._pushSeries(this.series.traffic.fraudulent, this._windowFraud);
        
        // Fraud rate series
        const total = this._windowLegit + this._windowFraud;
        const rate = total > 0 ? (this._windowFraud / total * 100) : 0;
        this._pushSeries(this.series.fraud.labels, label);
        this._pushSeries(this.series.fraud.rates, parseFloat(rate.toFixed(1)));
        
        // Latency series
        const sorted = [...this._windowLatencies].sort((a, b) => a - b);
        const p50 = sorted.length > 0 ? sorted[Math.floor(sorted.length * 0.5)] : 0;
        const p95 = sorted.length > 0 ? sorted[Math.floor(sorted.length * 0.95)] : 0;
        this._pushSeries(this.series.latency.labels, label);
        this._pushSeries(this.series.latency.p50, parseFloat(p50.toFixed(1)));
        this._pushSeries(this.series.latency.p95, parseFloat(p95.toFixed(1)));
        
        // Reset window
        this._windowLegit = 0;
        this._windowFraud = 0;
        this._windowLatencies = [];
    }
    
    _pushSeries(arr, value) {
        arr.push(value);
        if (arr.length > MAX_CHART_POINTS) arr.shift();
    }
    
    // KPI getters
    get fraudRate() {
        if (this.totalImpressions === 0) return 0;
        return (this.totalFraud / this.totalImpressions * 100);
    }
    
    get avgEcpm() {
        if (this.totalImpressions === 0) return 0;
        return (this.totalBidValue / this.totalImpressions * 1000);
    }
    
    get avgLatency() {
        if (this.latencyCount === 0) return 0;
        return this.totalLatency / this.latencyCount;
    }
    
    // Initialize Chart.js charts
    initCharts(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        // Shared chart options
        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 300 },
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#94a3b8',
                        font: { family: "'Inter', sans-serif", size: 11 },
                        boxWidth: 12,
                        padding: 16,
                    },
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255,255,255,0.06)',
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8,
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#64748b', font: { size: 10 } },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#64748b', font: { size: 10 } },
                    beginAtZero: true,
                },
            },
        };

        // Traffic chart
        this.charts.traffic = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Legitimate',
                        data: [],
                        backgroundColor: 'rgba(16, 185, 129, 0.6)',
                        borderColor: '#10b981',
                        borderWidth: 1,
                        borderRadius: 3,
                    },
                    {
                        label: 'Fraudulent',
                        data: [],
                        backgroundColor: 'rgba(239, 68, 68, 0.6)',
                        borderColor: '#ef4444',
                        borderWidth: 1,
                        borderRadius: 3,
                    },
                ],
            },
            options: { ...baseOptions, scales: { ...baseOptions.scales, x: { ...baseOptions.scales.x, stacked: true }, y: { ...baseOptions.scales.y, stacked: true } } },
        });

        // Fraud rate chart (hidden initially)
        this.charts.fraud = null;
        this.charts.latency = null;
        
        // Store canvas and options for switching
        this._canvasId = canvasId;
        this._baseOptions = baseOptions;
    }
    
    switchChart(type) {
        this.activeChart = type;
        const ctx = document.getElementById(this._canvasId);
        if (!ctx) return;
        
        // Destroy current chart
        const currentKey = Object.keys(this.charts).find(k => this.charts[k]?.canvas === ctx);
        for (const key of Object.keys(this.charts)) {
            if (this.charts[key]) {
                this.charts[key].destroy();
                this.charts[key] = null;
            }
        }
        
        const opts = this._baseOptions;
        
        if (type === 'traffic') {
            this.charts.traffic = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: [...this.series.traffic.labels],
                    datasets: [
                        { label: 'Legitimate', data: [...this.series.traffic.legitimate], backgroundColor: 'rgba(16, 185, 129, 0.6)', borderColor: '#10b981', borderWidth: 1, borderRadius: 3 },
                        { label: 'Fraudulent', data: [...this.series.traffic.fraudulent], backgroundColor: 'rgba(239, 68, 68, 0.6)', borderColor: '#ef4444', borderWidth: 1, borderRadius: 3 },
                    ],
                },
                options: { ...opts, scales: { ...opts.scales, x: { ...opts.scales.x, stacked: true }, y: { ...opts.scales.y, stacked: true } } },
            });
        } else if (type === 'fraud') {
            this.charts.fraud = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [...this.series.fraud.labels],
                    datasets: [{
                        label: 'Fraud Rate %',
                        data: [...this.series.fraud.rates],
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 2,
                        pointBackgroundColor: '#ef4444',
                    }],
                },
                options: { ...opts, scales: { ...opts.scales, y: { ...opts.scales.y, max: 100 } } },
            });
        } else if (type === 'latency') {
            this.charts.latency = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [...this.series.latency.labels],
                    datasets: [
                        { label: 'P50 Latency (ms)', data: [...this.series.latency.p50], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', fill: true, tension: 0.3, pointRadius: 2 },
                        { label: 'P95 Latency (ms)', data: [...this.series.latency.p95], borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true, tension: 0.3, pointRadius: 2 },
                    ],
                },
                options: opts,
            });
        }
    }
    
    updateChart() {
        const chart = this.charts[this.activeChart];
        if (!chart) return;
        
        const series = this.series[this.activeChart];
        
        if (this.activeChart === 'traffic') {
            chart.data.labels = [...series.labels];
            chart.data.datasets[0].data = [...series.legitimate];
            chart.data.datasets[1].data = [...series.fraudulent];
        } else if (this.activeChart === 'fraud') {
            chart.data.labels = [...series.labels];
            chart.data.datasets[0].data = [...series.rates];
        } else if (this.activeChart === 'latency') {
            chart.data.labels = [...series.labels];
            chart.data.datasets[0].data = [...series.p50];
            chart.data.datasets[1].data = [...series.p95];
        }
        
        chart.update('none'); // no animation for perf
    }
    
    // Initialize the threat gauge (doughnut)
    initGauge(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        this.gaugeChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['rgba(16, 185, 129, 0.8)', 'rgba(255,255,255,0.03)'],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
            },
        });
    }
    
    updateGauge(rate) {
        if (!this.gaugeChart) return;
        
        const clamped = Math.min(rate, 100);
        this.gaugeChart.data.datasets[0].data = [clamped, 100 - clamped];
        
        // Color based on rate
        let color;
        if (rate < 10) color = 'rgba(16, 185, 129, 0.8)';      // green
        else if (rate < 25) color = 'rgba(245, 158, 11, 0.8)';  // yellow
        else if (rate < 50) color = 'rgba(249, 115, 22, 0.8)';  // orange
        else color = 'rgba(239, 68, 68, 0.8)';                   // red
        
        this.gaugeChart.data.datasets[0].backgroundColor[0] = color;
        this.gaugeChart.update('none');
    }
}
