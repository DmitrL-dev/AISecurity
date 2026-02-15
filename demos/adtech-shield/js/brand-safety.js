/**
 * Brand Safety Analyzer — content context classification
 * Categorizes publisher inventory by risk level
 */

const BRAND_SAFETY_CATEGORIES = {
    SAFE: { level: 'safe', label: 'Safe', color: '#10b981' },
    MODERATE: { level: 'moderate', label: 'Moderate', color: '#f59e0b' },
    RISKY: { level: 'risky', label: 'Risky', color: '#f97316' },
    UNSAFE: { level: 'unsafe', label: 'Unsafe', color: '#ef4444' },
};

// IAB Content Taxonomy categories with risk scores
const CATEGORY_RISK = {
    'news': { risk: 0.3, label: 'News & Current Events', iabCode: 'IAB12' },
    'tech': { risk: 0.1, label: 'Technology', iabCode: 'IAB19' },
    'sports': { risk: 0.15, label: 'Sports', iabCode: 'IAB17' },
    'weather': { risk: 0.05, label: 'Weather', iabCode: 'IAB15' },
    'social': { risk: 0.35, label: 'Social Media', iabCode: 'IAB14' },
    'entertainment': { risk: 0.25, label: 'Entertainment', iabCode: 'IAB1' },
    'reference': { risk: 0.1, label: 'Reference', iabCode: 'IAB5' },
    'howto': { risk: 0.15, label: 'How-To & DIY', iabCode: 'IAB9' },
    'mfa': { risk: 0.9, label: 'Made For Advertising', iabCode: 'MFA' },
};

// Publisher domain risk overrides
const DOMAIN_RISK_OVERRIDES = {
    'clickbait-news.xyz': 0.95,
    'free-games-24.com': 0.85,
    'viral-stories-now.net': 0.9,
    'top10-lists.info': 0.8,
    'best-deals-today.click': 0.88,
};

/**
 * Analyze brand safety for a bid request
 * Returns: { level, score, category, reasons }
 */
export function analyzeBrandSafety(request) {
    const { domain, category, tier } = request.publisher;
    const reasons = [];
    
    let riskScore = 0;
    
    // 1. Category-based risk
    const catInfo = CATEGORY_RISK[category] || { risk: 0.3, label: 'Unknown', iabCode: 'UNK' };
    riskScore += catInfo.risk * 0.4; // 40% weight
    
    // 2. Domain-specific override
    const domainOverride = DOMAIN_RISK_OVERRIDES[domain];
    if (domainOverride !== undefined) {
        riskScore = domainOverride; // override
        reasons.push(`Domain flagged: ${domain}`);
    }
    
    // 3. Tier-based adjustment
    const tierRisk = { premium: -0.1, standard: 0, low: 0.15, mfa: 0.4 };
    riskScore += tierRisk[tier] || 0;
    
    // 4. MFA detection
    if (tier === 'mfa' || category === 'mfa') {
        reasons.push('MFA site detected — excessive ad density');
        riskScore = Math.max(riskScore, 0.8);
    }
    
    // 5. News adjacency risk
    if (category === 'news') {
        // Simulate occasional controversial content
        if (Math.random() < 0.15) {
            riskScore += 0.25;
            reasons.push('Adjacent to controversial news content');
        }
    }
    
    // Clamp
    riskScore = Math.max(0, Math.min(1, riskScore));
    
    // Determine level
    let safetyLevel;
    if (riskScore < 0.2) {
        safetyLevel = BRAND_SAFETY_CATEGORIES.SAFE;
    } else if (riskScore < 0.45) {
        safetyLevel = BRAND_SAFETY_CATEGORIES.MODERATE;
    } else if (riskScore < 0.7) {
        safetyLevel = BRAND_SAFETY_CATEGORIES.RISKY;
    } else {
        safetyLevel = BRAND_SAFETY_CATEGORIES.UNSAFE;
    }
    
    return {
        level: safetyLevel.level,
        label: safetyLevel.label,
        color: safetyLevel.color,
        score: parseFloat(riskScore.toFixed(3)),
        category: catInfo.label,
        iabCode: catInfo.iabCode,
        reasons,
        domain,
    };
}

export { BRAND_SAFETY_CATEGORIES };
