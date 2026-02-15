/**
 * RTB Simulator — generates synthetic bid requests
 * Simulates OpenRTB 2.6 bid request flow
 */

const PUBLISHERS = [
    { domain: 'nytimes.com', category: 'news', tier: 'premium' },
    { domain: 'cnn.com', category: 'news', tier: 'premium' },
    { domain: 'bbc.com', category: 'news', tier: 'premium' },
    { domain: 'techcrunch.com', category: 'tech', tier: 'premium' },
    { domain: 'theverge.com', category: 'tech', tier: 'premium' },
    { domain: 'espn.com', category: 'sports', tier: 'premium' },
    { domain: 'weather.com', category: 'weather', tier: 'standard' },
    { domain: 'reddit.com', category: 'social', tier: 'standard' },
    { domain: 'buzzfeed.com', category: 'entertainment', tier: 'standard' },
    { domain: 'dailymail.co.uk', category: 'news', tier: 'standard' },
    { domain: 'about.com', category: 'reference', tier: 'standard' },
    { domain: 'ehow.com', category: 'howto', tier: 'low' },
    { domain: 'clickbait-news.xyz', category: 'mfa', tier: 'mfa' },
    { domain: 'free-games-24.com', category: 'mfa', tier: 'mfa' },
    { domain: 'viral-stories-now.net', category: 'mfa', tier: 'mfa' },
    { domain: 'top10-lists.info', category: 'mfa', tier: 'mfa' },
    { domain: 'best-deals-today.click', category: 'mfa', tier: 'mfa' },
];

const GEOS = [
    { code: 'US', name: 'United States', flag: '🇺🇸', weight: 0.35 },
    { code: 'GB', name: 'United Kingdom', flag: '🇬🇧', weight: 0.1 },
    { code: 'DE', name: 'Germany', flag: '🇩🇪', weight: 0.08 },
    { code: 'JP', name: 'Japan', flag: '🇯🇵', weight: 0.07 },
    { code: 'KR', name: 'South Korea', flag: '🇰🇷', weight: 0.06 },
    { code: 'BR', name: 'Brazil', flag: '🇧🇷', weight: 0.05 },
    { code: 'IN', name: 'India', flag: '🇮🇳', weight: 0.08 },
    { code: 'RU', name: 'Russia', flag: '🇷🇺', weight: 0.04 },
    { code: 'CN', name: 'China', flag: '🇨🇳', weight: 0.06 },
    { code: 'NG', name: 'Nigeria', flag: '🇳🇬', weight: 0.03 },
    { code: 'VN', name: 'Vietnam', flag: '🇻🇳', weight: 0.03 },
    { code: 'PH', name: 'Philippines', flag: '🇵🇭', weight: 0.02 },
    { code: 'XX', name: 'Proxy/VPN', flag: '🏴‍☠️', weight: 0.03 },
];

const DEVICES = ['desktop', 'mobile', 'tablet', 'ctv', 'unknown'];
const AD_FORMATS = ['banner', 'video', 'native', 'interstitial'];

const USER_AGENTS = [
    { ua: 'Chrome/120 Win10', isBot: false },
    { ua: 'Safari/17 macOS', isBot: false },
    { ua: 'Firefox/121 Linux', isBot: false },
    { ua: 'Edge/120 Win11', isBot: false },
    { ua: 'Samsung Browser/23', isBot: false },
    { ua: 'Chrome/120 Android', isBot: false },
    { ua: 'Mozilla/5.0 (compatible; Googlebot/2.1)', isBot: true },
    { ua: 'python-requests/2.31', isBot: true },
    { ua: 'curl/8.4', isBot: true },
    { ua: 'HeadlessChrome/120', isBot: true },
    { ua: 'PhantomJS/2.1', isBot: true },
    { ua: '', isBot: true }, // empty UA
];

let requestId = 0;

function weightedRandom(items, weightKey = 'weight') {
    const totalWeight = items.reduce((sum, item) => sum + item[weightKey], 0);
    let random = Math.random() * totalWeight;
    for (const item of items) {
        random -= item[weightKey];
        if (random <= 0) return item;
    }
    return items[items.length - 1];
}

function pickRandom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

export function generateBidRequest() {
    requestId++;
    
    const publisher = pickRandom(PUBLISHERS);
    const geo = weightedRandom(GEOS);
    const device = pickRandom(DEVICES);
    const format = pickRandom(AD_FORMATS);
    const ua = pickRandom(USER_AGENTS);
    
    // Base bid price depends on publisher tier
    const tierPricing = { premium: 8, standard: 3, low: 1.5, mfa: 0.3 };
    const baseCpm = tierPricing[publisher.tier] || 2;
    const bidFloor = baseCpm * (0.5 + Math.random() * 0.8);
    const winBid = bidFloor * (1 + Math.random() * 0.6);
    
    // Simulate latency (2-80ms, occasionally spikes)
    const latency = Math.random() < 0.05 
        ? 50 + Math.random() * 80  // spike
        : 2 + Math.random() * 30;   // normal

    return {
        id: `req-${requestId.toString(36).padStart(6, '0')}`,
        timestamp: Date.now(),
        publisher: {
            domain: publisher.domain,
            category: publisher.category,
            tier: publisher.tier,
        },
        geo: {
            code: geo.code,
            name: geo.name,
            flag: geo.flag,
        },
        device: {
            type: device,
            ua: ua.ua,
            isKnownBot: ua.isBot,
        },
        impression: {
            format: format,
            bidFloor: parseFloat(bidFloor.toFixed(2)),
            winBid: parseFloat(winBid.toFixed(2)),
        },
        latencyMs: parseFloat(latency.toFixed(1)),
    };
}
