# 🔬 SENTINEL — Engine Reference Guide

> **Total Engines:** 217 engine files (Jan 2026)  
> **Benchmark Recall:** 85.1% | Precision: 84.4% | F1: 84.7%  
> **Categories:** 20  
> **Coverage:** OWASP LLM Top 10 + OWASP ASI Top 10

---

## Engine List (1-206)

### 1. ActivationSteering
**File:** `engines/activation_steering.py`  
Controls LLM behavior via steering vectors.

### 2. AdversarialImage
**File:** `engines/adversarial_image.py`  
Detects adversarial perturbations in images.

### 3. AdversarialPoetryDetector
**File:** `engines/adversarial_poetry_detector.py`  
Detects jailbreaks embedded in poetic language.

### 4. AdversarialPromptDetector
**File:** `engines/adversarial_prompt_detector.py`  
Detects adversarial prompt perturbations.

### 5. AdversarialResistance
**File:** `engines/adversarial_resistance.py`  
Hybrid defense against known-algorithm attacks.

### 6. AdversarialSelfPlay
**File:** `engines/adversarial_self_play.py`  
Self-play for adversarial training.

### 7. AdvertisementEmbeddingDetector
**File:** `engines/advertisement_embedding_detector.py`  
Detects hidden advertisements in outputs.

### 8. AgentAnomaly
**File:** `engines/agent_anomaly.py`  
Detects anomalous AI agent behavior.

### 9. AgentCardValidator
**File:** `engines/agent_card_validator.py`  
Validates A2A agent cards.

### 10. AgentCollusionDetector
**File:** `engines/agent_collusion_detector.py`  
Detects collusion between agents.

### 11. AgentMemoryShield
**File:** `engines/agent_memory_shield.py`  
Protects persistent agent memory.

### 12. AgentPlaybookDetector
**File:** `engines/agent_playbook_detector.py`  
Detects agent attack playbooks.

### 13. AgenticBehaviorAnalyzer
**File:** `engines/agentic_behavior_analyzer.py`  
Analyzes agent behavior patterns.

### 14. AgenticMonitor
**File:** `engines/agentic_monitor.py`  
Monitors agentic systems.

### 15. AIC2Detection
**File:** `engines/ai_c2_detection.py`  
Detects AI Command & Control.

### 16. AntiTrollDetector
**File:** `engines/anti_troll_detector.py`  
Detects anti-troll bypass attacks.

### 17. APESignatures
**File:** `engines/ape_signatures.py`  
AI Prompt Exploitation signatures.

### 18. ArtPromptDetector
**File:** `engines/artprompt_detector.py`  
Detects ASCII art jailbreaks.

### 19. AtomicOperationEnforcer
**File:** `engines/atomic_operation_enforcer.py`  
TOCTOU attack defense.

### 20. Attack2025
**File:** `engines/attack_2025.py`  
2025 attack patterns detection.

### 21. AttackEvolutionPredictor
**File:** `engines/attack_evolution_predictor.py`  
Predicts attack evolution.

### 22. AttackStaging
**File:** `engines/attack_staging.py`  
Multi-stage attack detection.

### 23. AttackSynthesizer
**File:** `engines/attack_synthesizer.py`  
Synthesizes attacks for testing.

### 24. AttackerFingerprinting
**File:** `engines/attacker_fingerprinting.py`  
Behavioral attacker identification.

### 25. BadLikertDetector
**File:** `engines/bad_likert_detector.py`  
Detects evaluator exploitation.

### 26. Behavioral
**File:** `engines/behavioral.py`  
Behavioral anomaly detection.

### 27. BehavioralAPIVerifier
**File:** `engines/behavioral_api_verifier.py`  
User verification via behavior.

### 28. BootstrapPoisoning
**File:** `engines/bootstrap_poisoning.py`  
Bootstrap poisoning detection.

### 29. CacheIsolationGuardian
**File:** `engines/cache_isolation_guardian.py`  
Multi-tenant cache isolation.

### 30. CanaryTokens
**File:** `engines/canary_tokens.py`  
Data leakage detection watermarks.

### 31. CascadingGuard
**File:** `engines/cascading_guard.py`  
Multi-layer cascading defense.

### 32. CategoryTheory
**File:** `engines/category_theory.py`  
Category theory analysis.

### 33. CausalAttackModel
**File:** `engines/causal_attack_model.py`  
Causal attack chain modeling.

### 34. CausalInferenceDetector
**File:** `engines/causal_inference_detector.py`  
Inference attack detection.

### 35. ChaosTheory
**File:** `engines/chaos_theory.py`  
Chaos theory analysis.

### 36. CognitiveLoadAttack
**File:** `engines/cognitive_load_attack.py`  
Cognitive overload detection.

### 37. CognitiveOverloadDetector
**File:** `engines/cognitive_overload_detector.py`  
DoS via cognitive overload.

### 38. ComplianceEngine
**File:** `engines/compliance_engine.py`  
Regulatory compliance mapping.

### 39. CompliancePolicyEngine
**File:** `engines/compliance_policy_engine.py`  
Policy-based compliance.

### 40. ComputeGuardian
**File:** `engines/compute_guardian.py`  
Compute cost protection.

### 41. ContextCompression
**File:** `engines/context_compression.py`  
Context window management.

### 42. ContextWindowGuardian
**File:** `engines/context_window_guardian.py`  
Context window protection.

### 43. ContextWindowPoisoning
**File:** `engines/context_window_poisoning.py`  
Context poisoning detection.

### 44. ContrastivePromptAnomaly
**File:** `engines/contrastive_prompt_anomaly.py`  
Contrastive anomaly detection.

### 45. ConversationStateValidator
**File:** `engines/conversation_state_validator.py`  
State machine security.

### 46. CoTGuardian
**File:** `engines/cot_guardian.py`  
Chain-of-thought protection.

### 47. CrescendoDetector
**File:** `engines/crescendo_detector.py`  
Multi-turn escalation detection.

### 48. CrossModal
**File:** `engines/cross_modal.py`  
Cross-modal attack detection.

### 49. CrossModalSecurityAnalyzer
**File:** `engines/cross_modal_security_analyzer.py`  
Multi-modal security analysis.

### 50. DarkPatternDetector
**File:** `engines/dark_pattern_detector.py`  
Dark pattern detection.

### 51. DeceptiveDelightDetector
**File:** `engines/deceptive_delight_detector.py`  
Deceptive delight jailbreak.

### 52. DelayedExecution
**File:** `engines/delayed_execution.py`  
Delayed execution detection.

### 53. DelayedTrigger
**File:** `engines/delayed_trigger.py`  
Time-based trigger detection.

### 54. DifferentialGeometry
**File:** `engines/differential_geometry.py`  
Differential geometry analysis.

### 55. DistilledSecurityEnsemble
**File:** `engines/distilled_security_ensemble.py`  
Distilled ensemble detection.

### 56. DoublespeakDetector
**File:** `engines/doublespeak_detector.py`  
Semantic substitution attacks.

### 57. DynamicRateLimiter
**File:** `engines/dynamic_rate_limiter.py`  
Adaptive rate limiting.

### 58. EchoChamberDetector
**File:** `engines/echo_chamber_detector.py`  
Echo chamber detection.

### 59. EchoStateNetwork
**File:** `engines/echo_state_network.py`  
Reservoir computing analysis.

### 60. EmergentSecurityMesh
**File:** `engines/emergent_security_mesh.py`  
MARL security coordination.

### 61. EndpointAnalyzer
**File:** `engines/endpoint_analyzer.py`  
Endpoint analysis.

### 62. Engine
**File:** `engines/engine.py`  
Base engine implementation.

### 63. Ensemble
**File:** `engines/ensemble.py`  
Ensemble detection.

### 64. EvolutiveAttackDetector
**File:** `engines/evolutive_attack_detector.py`  
Genetic attack detection.

### 65. ExplainableSecurityDecisions
**File:** `engines/explainable_security_decisions.py`  
XAI for security.

### 66. FallacyFailureDetector
**File:** `engines/fallacy_failure_detector.py`  
Logical fallacy detection.

### 67. FederatedThreatAggregator
**File:** `engines/federated_threat_aggregator.py`  
Federated threat sharing.

### 68. FingerprintStore
**File:** `engines/fingerprint_store.py`  
Fingerprint storage.

### 69. FlipAttackDetector
**File:** `engines/flip_attack_detector.py`  
Unicode flip attacks.

### 70. FormalInvariants
**File:** `engines/formal_invariants.py`  
Formal invariant checking.

### 71. FormalSafetyVerifier
**File:** `engines/formal_safety_verifier.py`  
Formal safety verification.

### 72. FormalVerification
**File:** `engines/formal_verification.py`  
Formal methods verification.

### 73. Fractal
**File:** `engines/fractal.py`  
Fractal dimension analysis.

### 74. GANAdversarialDefense
**File:** `engines/gan_adversarial_defense.py`  
GAN-based defense.

### 75. Geometric
**File:** `engines/geometric.py`  
TDA geometric analysis.

### 76. GestaltReversalDetector
**File:** `engines/gestalt_reversal_detector.py`  
Meaning inversion detection.

### 77. GodelAttackDetector
**File:** `engines/godel_attack_detector.py`  
Logical paradox attacks.

### 78. GradientDetection
**File:** `engines/gradient_detection.py`  
Gradient-based attacks.

### 79. GuardrailsEngine
**File:** `engines/guardrails_engine.py`  
NeMo-style guardrails.

### 80. Hallucination
**File:** `engines/hallucination.py`  
Hallucination detection.

### 81. HiddenStateForensics
**File:** `engines/hidden_state_forensics.py`  
Hidden state analysis.

### 82. HierarchicalDefenseNetwork
**File:** `engines/hierarchical_defense_network.py`  
Multi-layer defense.

### 83. HITLFatigueDetector
**File:** `engines/hitl_fatigue_detector.py`  
Human-in-loop fatigue.

### 84. HomomorphicEngine
**File:** `engines/homomorphic_engine.py`  
Homomorphic encryption.

### 85. HoneypotResponses
**File:** `engines/honeypot_responses.py`  
Honeypot response generation.

### 86. HyperbolicDetector
**File:** `engines/hyperbolic_detector.py`  
Hyperbolic space detection.

### 87. HyperbolicGeometry
**File:** `engines/hyperbolic_geometry.py`  
Poincaré model analysis.

### 88. IdentityPrivilegeDetector
**File:** `engines/identity_privilege_detector.py`  
Identity/privilege abuse.

### 89. ImageStegoDetector
**File:** `engines/image_stego_detector.py`  
Image steganography.

### 90. ImmunityCompiler
**File:** `engines/immunity_compiler.py`  
Rule compilation.

### 91. InfoTheory
**File:** `engines/info_theory.py`  
Information theory analysis.

### 92. InformationGeometry
**File:** `engines/information_geometry.py`  
Statistical manifolds.

### 93. Injection
**File:** `engines/injection.py`  
Prompt injection detection.

### 94. InputLengthAnalyzer
**File:** `engines/input_length_analyzer.py`  
Input length DoS.

### 95. InstitutionalAI
**File:** `engines/institutional_ai.py`  
AI governance.

### 96. Intelligence
**File:** `engines/intelligence.py`  
Threat intelligence.

### 97. IntentAwareSemanticAnalyzer
**File:** `engines/intent_aware_semantic_analyzer.py`  
Intent-semantic analysis.

### 98. IntentPrediction
**File:** `engines/intent_prediction.py`  
Intent prediction.

### 99. InvertedAttackDetector
**File:** `engines/inverted_attack_detector.py`  
Inverted pattern attacks.

### 100. KillChainSimulation
**File:** `engines/kill_chain_simulation.py`  
Kill chain simulation.

### 101. Knowledge
**File:** `engines/knowledge.py`  
Knowledge access control.

### 102. Language
**File:** `engines/language.py`  
Language filtering.

### 103. LanguageDetectionGuard
**File:** `engines/language_detection_guard.py`  
Language-based attacks.

### 104. Learning
**File:** `engines/learning.py`  
Adaptive learning.

### 105. LethalTrifectaDetector
**File:** `engines/lethal_trifecta_detector.py`  
Combined attack detection.

### 106. LLMFingerprinting
**File:** `engines/llm_fingerprinting.py`  
Model fingerprinting.

### 107. ManyshotDetector
**File:** `engines/manyshot_detector.py`  
Many-shot jailbreak.

### 108. MarketplaceSkillValidator
**File:** `engines/marketplace_skill_validator.py`  
Skill validation.

### 109. MathOracle
**File:** `engines/math_oracle.py`  
Mathematical validation.

### 110. MCPA2ASecurity
**File:** `engines/mcp_a2a_security.py`  
MCP/A2A protocol security.

### 111. MCPCombinationAttackDetector
**File:** `engines/mcp_combination_attack_detector.py`  
MCP combination attacks.

### 112. MCPSecurityMonitor
**File:** `engines/mcp_security_monitor.py`  
MCP security monitoring.

### 113. MemoryPoisoningDetector
**File:** `engines/memory_poisoning_detector.py`  
Memory poisoning defense.

### 114. MetaAttackAdapter
**File:** `engines/meta_attack_adapter.py`  
Meta-learning adaptation.

### 115. MetaJudge
**File:** `engines/meta_judge.py`  
Meta-judge aggregation.

### 116. MisinformationDetector
**File:** `engines/misinformation_detector.py`  
Misinformation detection.

### 117. MITREEngine
**File:** `engines/mitre_engine.py`  
MITRE ATT&CK mapping.

### 118. ModelContextProtocolGuard
**File:** `engines/model_context_protocol_guard.py`  
MCP security validation.

### 119. ModelIntegrityVerifier
**File:** `engines/model_integrity_verifier.py`  
Model integrity checking.

### 120. ModelWatermarkVerifier
**File:** `engines/model_watermark_verifier.py`  
Watermark verification.

### 121. MoEGuard
**File:** `engines/moe_guard.py`  
MoE safety bypass detection.

### 122. MorseTheory
**File:** `engines/morse_theory.py`  
Morse theory analysis.

### 123. MultiAgentCoordinator
**File:** `engines/multi_agent_coordinator.py`  
Multi-agent coordination.

### 124. MultiAgentSafety
**File:** `engines/multi_agent_safety.py`  
Multi-agent security.

### 125. MultiLayerCanonicalizer
**File:** `engines/multi_layer_canonicalizer.py`  
Obfuscation defense.

### 126. MultiTenantBleed
**File:** `engines/multi_tenant_bleed.py`  
Cross-tenant leakage.

### 127. NHIIdentityGuard
**File:** `engines/nhi_identity_guard.py`  
Non-human identity security.

### 128. OptimalTransport
**File:** `engines/optimal_transport.py`  
Wasserstein distance.

### 129. OutputSanitizationGuard
**File:** `engines/output_sanitization_guard.py`  
Output sanitization.

### 130. PersistentLaplacian
**File:** `engines/persistent_laplacian.py`  
Spectral analysis.

### 131. PickleSecurity
**File:** `engines/pickle_security.py`  
Pickle exploit detection.

### 132. PII
**File:** `engines/pii.py`  
PII detection.

### 133. PolicyPuppetryDetector
**File:** `engines/policy_puppetry_detector.py`  
Policy spoofing detection.

### 134. PolymorphicPromptAssembler
**File:** `engines/polymorphic_prompt_assembler.py`  
PPA defense.

### 135. ProactiveDefense
**File:** `engines/proactive_defense.py`  
Zero-day detection.

### 136. ProbingDetection
**File:** `engines/probing_detection.py`  
Reconnaissance detection.

### 137. PromptGuard
**File:** `engines/prompt_guard.py`  
System prompt protection.

### 138. PromptLeakDetector
**File:** `engines/prompt_leak_detector.py`  
Prompt extraction detection.

### 139. PromptLeakageDetector
**File:** `engines/prompt_leakage_detector.py`  
Leakage prevention.

### 140. PromptSelfReplication
**File:** `engines/prompt_self_replication.py`  
Worm detection.

### 141. ProvenanceTracker
**File:** `engines/provenance_tracker.py`  
Data provenance tracking.

### 142. PsychologicalJailbreakDetector
**File:** `engines/psychological_jailbreak_detector.py`  
RLHF exploitation.

### 143. QuantumSafeModelVault
**File:** `engines/quantum_safe_model_vault.py`  
Post-quantum crypto.

### 144. QwenGuard
**File:** `engines/qwen_guard.py`  
Qwen safety classification.

### 145. RAGGuard
**File:** `engines/rag_guard.py`  
RAG security.

### 146. RAGPoisoningDetector
**File:** `engines/rag_poisoning_detector.py`  
RAG poisoning defense.

### 147. RAGSecurityShield
**File:** `engines/rag_security_shield.py`  
RAG pipeline protection.

### 148. RecursiveInjectionGuard
**File:** `engines/recursive_injection_guard.py`  
Nested injection defense.

### 149. RegexLayer
**File:** `engines/regex_layer.py`  
Regex pattern matching.

### 150. ReinforcementSafetyAgent
**File:** `engines/reinforcement_safety_agent.py`  
RL-based defense.

### 151. ResponseConsistencyChecker
**File:** `engines/response_consistency_checker.py`  
Response verification.

### 152. RewardHackingDetector
**File:** `engines/reward_hacking_detector.py`  
Reward hacking detection.

### 153. RuleDSL
**File:** `engines/rule_dsl.py`  
Rule DSL engine.

### 154. RuntimeGuardrails
**File:** `engines/runtime_guardrails.py`  
Dynamic policy enforcement.

### 155. SafetyGrammarEnforcer
**File:** `engines/safety_grammar_enforcer.py`  
Constrained decoding.

### 156. SandboxMonitor
**File:** `engines/sandbox_monitor.py`  
Sandbox escape detection.

### 157. SecureModelLoader
**File:** `engines/secure_model_loader.py`  
Safe model loading.

### 158. SemanticBoundaryEnforcer
**File:** `engines/semantic_boundary_enforcer.py`  
Context separation.

### 159. SemanticDetector
**File:** `engines/semantic_detector.py`  
Semantic injection.

### 160. SemanticDriftDetector
**File:** `engines/semantic_drift_detector.py`  
Embedding drift.

### 161. SemanticFirewall
**File:** `engines/semantic_firewall.py`  
Semantic boundary.

### 162. SemanticIsomorphismDetector
**File:** `engines/semantic_isomorphism_detector.py`  
Safe2Harm attacks.

### 163. SemanticLayer
**File:** `engines/semantic_layer.py`  
Semantic analysis.

### 164. SentimentManipulationDetector
**File:** `engines/sentiment_manipulation_detector.py`  
Emotional attacks.

### 165. SerializationSecurity
**File:** `engines/serialization_security.py`  
CVE detection.

### 166. SessionMemoryGuard
**File:** `engines/session_memory_guard.py`  
Session protection.

### 167. ShadowAIDetector
**File:** `engines/shadow_ai_detector.py`  
Unauthorized AI detection.

### 168. SheafCoherence
**File:** `engines/sheaf_coherence.py`  
Sheaf theory analysis.

### 169. SkeletonKeyDetector
**File:** `engines/skeleton_key_detector.py`  
Universal bypass detection.

### 170. SleeperAgentDetector
**File:** `engines/sleeper_agent_detector.py`  
Backdoor detection.

### 171. SpectralGraph
**File:** `engines/spectral_graph.py`  
Graph spectral analysis.

### 172. StatisticalMechanics
**File:** `engines/statistical_mechanics.py`  
Physics-inspired analysis.

### 173. StrangeMathV3Stub
**File:** `engines/strange_math_v3_stub.py`  
Strange Math stub.

### 174. Streaming
**File:** `engines/streaming.py`  
Real-time detection.

### 175. StructuralImmunity
**File:** `engines/structural_immunity.py`  
Architectural hardening.

### 176. StructuralLayer
**File:** `engines/structural_layer.py`  
Structural analysis.

### 177. SupplyChainGuard
**File:** `engines/supply_chain_guard.py`  
Supply chain protection.

### 178. SupplyChainScanner
**File:** `engines/supply_chain_scanner.py`  
Dependency scanning.

### 179. SymbolicReasoningGuard
**File:** `engines/symbolic_reasoning_guard.py`  
Logic-based security.

### 180. SyncedAttackDetector
**File:** `engines/synced_attack_detector.py`  
Combined detector.

### 181. SyntheticMemoryInjection
**File:** `engines/synthetic_memory_injection.py`  
False memory detection.

### 182. SystemPromptShield
**File:** `engines/system_prompt_shield.py`  
Extraction prevention.

### 183. TaskComplexity
**File:** `engines/task_complexity.py`  
Request prioritization.

### 184. TDAEnhanced
**File:** `engines/tda_enhanced.py`  
Enhanced TDA.

### 185. TemporalPatternAnalyzer
**File:** `engines/temporal_pattern_analyzer.py`  
Time-based detection.

### 186. TemporalPoisoning
**File:** `engines/temporal_poisoning.py`  
Slow poisoning detection.

### 187. ThreatLandscapeModeler
**File:** `engines/threat_landscape_modeler.py`  
Predictive defense.

### 188. TokenCostAsymmetry
**File:** `engines/token_cost_asymmetry.py`  
DoS prevention.

### 189. TokenizerExploitDetector
**File:** `engines/tokenizer_exploit_detector.py`  
Tokenizer attacks.

### 190. ToolCallSecurity
**File:** `engines/tool_call_security.py`  
Tool protection.

### 191. ToolHijackerDetector
**File:** `engines/tool_hijacker_detector.py`  
Tool manipulation.

### 192. ToolUseGuardian
**File:** `engines/tool_use_guardian.py`  
Function security.

### 193. TransformerAttentionShield
**File:** `engines/transformer_attention_shield.py`  
Attention manipulation.

### 194. TrustExploitationDetector
**File:** `engines/trust_exploitation_detector.py`  
Trust exploitation.

### 195. VAEPromptAnomalyDetector
**File:** `engines/vae_prompt_anomaly_detector.py`  
Autoencoder detection.

### 196. VibeMalwareDetector
**File:** `engines/vibe_malware_detector.py`  
AI malware detection.

### 197. VirtualContext
**File:** `engines/virtual_context.py`  
Separator exploitation.

### 198. VisualContent
**File:** `engines/visual_content.py`  
VLM protection.

### 199. VoiceJailbreak
**File:** `engines/voice_jailbreak.py`  
Audio attack detection.

### 200. VulnerabilityHunter
**File:** `engines/vulnerability_hunter.py`  
Proactive discovery.

### 201. Wavelet
**File:** `engines/wavelet.py`  
Wavelet analysis.

### 202. WebAgentManipulationDetector
**File:** `engines/web_agent_manipulation_detector.py`  
Web agent attacks.

### 203. XAI
**File:** `engines/xai.py`  
Explainable AI.

### 204. YARAEngine
**File:** `engines/yara_engine.py`  
YARA rule matching.

### 205. ZeroDayForge
**File:** `engines/zero_day_forge.py`  
Internal zero-day.

### 206. ZeroTrustVerification
**File:** `engines/zero_trust_verification.py`  
Zero trust verification.

---

## Utility Modules (207-215)

### 207. BaseEngine
**File:** `engines/base_engine.py`  
Abstract base class for all engines.

### 208. Cache
**File:** `engines/cache.py`  
Caching utilities for engines.

### 209. Constants
**File:** `engines/constants.py`  
Engine constants and configuration.

### 210. EngineUsageExamples
**File:** `engines/engine_usage_examples.py`  
Usage examples for engines.

### 211. Exceptions
**File:** `engines/exceptions.py`  
Custom exceptions for engines.

### 212. MigrateEngines
**File:** `engines/migrate_engines.py`  
Engine migration utilities.

### 213. Models
**File:** `engines/models.py`  
Data models for engines.

### 214. Patterns
**File:** `engines/patterns.py`  
Pattern definitions.

### 215. Query
**File:** `engines/query.py`  
Query utilities.

---

**Engine Reference Complete!**

> **217 total engine files** = 206 detection engines + 9 utility modules + 2 in synced/
> Verified: Jan 14, 2026

Next step: [Configuration Guide →](../guides/configuration.md)
