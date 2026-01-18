# Security-Detections-MCP Fork — Requirements

## Overview
Fork and integrate Security-Detections-MCP for AI-assisted detection engineering.

## User Stories

### US-1: Fork Repository
**As a** SENTINEL developer  
**I want** to fork security-detections-mcp  
**So that** I can customize it for SENTINEL

**Acceptance Criteria:**
- [ ] Fork from dkuzsmar/security-detections-mcp
- [ ] Rename to sentinel-detections-mcp
- [ ] Update README with SENTINEL context

### US-2: SENTINEL Integration
**As a** SENTINEL Brain  
**I want** to use MCP for detection generation  
**So that** R&D findings auto-convert to rules

**Acceptance Criteria:**
- [ ] MCP server callable from Brain
- [ ] Input: threat description, CVE, attack pattern
- [ ] Output: Sigma rule, KQL, YARA

### US-3: Pattern Library
**As a** security researcher  
**I want** SENTINEL patterns in the MCP  
**So that** AI knows our signature format

**Acceptance Criteria:**
- [ ] Add jailbreaks.yaml patterns
- [ ] Add engine detection signatures
- [ ] Document SENTINEL-specific formats

### US-4: Automation Pipeline
**As a** SOC analyst  
**I want** R&D → Detection pipeline  
**So that** new threats auto-generate rules

**Acceptance Criteria:**
- [ ] Trigger: new R&D report
- [ ] Generate: detection rules
- [ ] Review: human approval queue
- [ ] Deploy: push to SIEM

## Technical Requirements

### TR-1: MCP Protocol
- Compatible with Anthropic MCP spec
- Tool definitions for SENTINEL
- Resource access for pattern files

### TR-2: Output Formats
- Sigma (YAML)
- KQL (Azure Sentinel)
- SPL (Splunk)
- YARA (file scanning)

## OWASP Mapping
- **LLM03**: Training Data Poisoning → Verified detection sources
- **ASI01**: Prompt Injection → Rule validation before deploy
