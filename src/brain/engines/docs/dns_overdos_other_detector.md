# dns_overdos_other_detector

## Overview
We've identified an aspect of Azure’s Private Endpoint architecture that could expose Azure resources to denial of service (DoS) attacks.
The post DNS OverDoS: Are Private Endpoints Too Private? appeared first on Unit 42.

## Details
- **Category**: other
- **Severity**: critical
- **Confidence**: 85%
- **Auto-generated**: Yes

## Detection Patterns
- `OverDoS`
- `Private`
- `Endpoints`
- `Azure`
- `Endpoint`
- `Unit`
- `RCE`

## Usage

### Python (SENTINEL Brain)
```python
from engines.dns_overdos_other_detector import DnsOverdosOtherDetector

engine = DnsOverdosOtherDetector()
result = engine.detect(content)
```

### TypeScript (SENTINEL-Claw)
```typescript
import { detect } from "./engines/dns_overdos_other_detector";

const result = detect(content);
```
