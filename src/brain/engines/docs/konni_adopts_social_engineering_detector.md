# konni_adopts_social_engineering_detector

## Overview
Key Findings: Introduction Check Point Research (CPR) identified an ongoing phishing campaign that we associate with KONNI, a North Korean–linked threat actor active since at least 2014. KONNI is best known for targeting organizations and individuals in South Korea, with a focus on diplomatic channels, international relations, NGOs, academia, and government. The group typically relies [&#8230;]
The post KONNI Adopts AI to Generate PowerShell Backdoors appeared first on Check Point Research.

## Details
- **Category**: social_engineering
- **Severity**: high
- **Confidence**: 85%
- **Auto-generated**: Yes

## Detection Patterns
- `KONNI`
- `Adopts`
- `Generate`
- `PowerShell`
- `Backdoors`
- `Findings`
- `Check`
- `Point`
- `Research`
- `North`
- `Korean`
- `South`
- `Korea`
- `NGOs`
- `backdoor`

## Usage

### Python (SENTINEL Brain)
```python
from engines.konni_adopts_social_engineering_detector import KonniAdoptsSocialEngineeringDetector

engine = KonniAdoptsSocialEngineeringDetector()
result = engine.detect(content)
```

### TypeScript (SENTINEL-Claw)
```typescript
import { detect } from "./engines/konni_adopts_social_engineering_detector";

const result = detect(content);
```
