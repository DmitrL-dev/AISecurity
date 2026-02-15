/**
 * Fraud Engine — pattern-based fraud detection scoring
 * Simulates real-time IVT detection with multi-signal analysis
 */

const FRAUD_TYPES = {
    BOT_TRAFFIC: 'bot_traffic',
    CLICK_FRAUD: 'click_fraud',
    GEO_MISMATCH: 'geo_mismatch',
    DOMAIN_SPOOFING: 'domain_spoofing',
    DEVICE_ANOMALY: 'device_anomaly',
};

// Known bot patterns (AhoCorasick-style hints)
const BOT_HINTS = [
    'googlebot', 'bingbot', 'python-requests', 'curl/',
    'wget/', 'scrapy', 'phantomjs', 'headlesschrome',
    'selenium', 'puppeteer',
];

// High-risk geos (for this demo)
const HIGH_RISK_GEOS = ['XX', 'NG', 'VN', 'PH'];

// Suspicious bid floor / win price ratios
const MIN_SUSPICIOUS_BID_RATIO = 3.0;

/**
 * Analyze a bid request for fraud signals
 * Returns: { isFraud, confidence, signals: [{type, reason, score}] }
 */
export function analyzeFraud(request) {
    const signals = [];
    
    // 1. Bot UA detection
    const uaLower = (request.device.ua || '').toLowerCase();
    if (!uaLower) {
        signals.push({
            type: FRAUD_TYPES.BOT_TRAFFIC,
            reason: 'Empty User-Agent',
            score: 0.95,
        });
    } else {
        for (const hint of BOT_HINTS) {
            if (uaLower.includes(hint)) {
                signals.push({
                    type: FRAUD_TYPES.BOT_TRAFFIC,
                    reason: `Bot pattern: ${hint}`,
                    score: 0.9,
                });
                break;
            }
        }
    }
    
    // 2. Known bot flag
    if (request.device.isKnownBot) {
        const existing = signals.find(s => s.type === FRAUD_TYPES.BOT_TRAFFIC);
        if (!existing) {
            signals.push({
                type: FRAUD_TYPES.BOT_TRAFFIC,
                reason: 'Known bot device fingerprint',
                score: 0.85,
            });
        }
    }
    
    // 3. Geo anomaly
    if (HIGH_RISK_GEOS.includes(request.geo.code)) {
        const isProxy = request.geo.code === 'XX';
        signals.push({
            type: FRAUD_TYPES.GEO_MISMATCH,
            reason: isProxy ? 'Proxy/VPN detected' : `High-risk geo: ${request.geo.name}`,
            score: isProxy ? 0.85 : 0.5,
        });
    }
    
    // 4. Domain spoofing (MFA sites)
    if (request.publisher.tier === 'mfa') {
        signals.push({
            type: FRAUD_TYPES.DOMAIN_SPOOFING,
            reason: `MFA site: ${request.publisher.domain}`,
            score: 0.8,
        });
    }
    
    // 5. Bid price anomaly
    const bidRatio = request.impression.winBid / Math.max(request.impression.bidFloor, 0.01);
    if (bidRatio > MIN_SUSPICIOUS_BID_RATIO) {
        signals.push({
            type: FRAUD_TYPES.CLICK_FRAUD,
            reason: `Anomalous bid ratio: ${bidRatio.toFixed(1)}x`,
            score: 0.6,
        });
    }
    
    // 6. Device anomaly (unknown device + suspicious patterns)
    if (request.device.type === 'unknown') {
        signals.push({
            type: FRAUD_TYPES.DEVICE_ANOMALY,
            reason: 'Unknown device type',
            score: 0.55,
        });
    }
    
    // 7. CTV + mobile UA mismatch
    if (request.device.type === 'ctv' && uaLower.includes('android')) {
        signals.push({
            type: FRAUD_TYPES.DEVICE_ANOMALY,
            reason: 'CTV with mobile UA mismatch',
            score: 0.7,
        });
    }
    
    // 8. Latency anomaly (extremely fast = likely bot)
    if (request.latencyMs < 3) {
        signals.push({
            type: FRAUD_TYPES.BOT_TRAFFIC,
            reason: `Suspiciously fast response: ${request.latencyMs}ms`,
            score: 0.45,
        });
    }
    
    // Calculate aggregate confidence (compound scoring)
    let maxScore = 0;
    const typeSet = new Set();
    for (const s of signals) {
        if (s.score > maxScore) maxScore = s.score;
        typeSet.add(s.type);
    }
    
    // Multi-signal boost (like SENTINEL compound scoring)
    let confidence = maxScore;
    if (typeSet.size >= 3) {
        confidence = Math.min(confidence * 1.4, 1.0); // 3+ signal types = high confidence
    } else if (typeSet.size >= 2) {
        confidence = Math.min(confidence * 1.2, 1.0); // 2 signal types
    }
    
    const isFraud = confidence >= 0.65;
    
    return {
        isFraud,
        confidence: parseFloat(confidence.toFixed(3)),
        signals,
        shouldBlock: confidence >= 0.75,
    };
}

export { FRAUD_TYPES };
