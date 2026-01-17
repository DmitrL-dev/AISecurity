# 🔬 SENTINEL — Справочник движков

> **Всего движков:** 217 файлов (Янв 2026)  
> **Benchmark Recall:** 85.1% | Precision: 84.4% | F1: 84.7%  
> **Категорий:** 20  
> **Покрытие:** OWASP LLM Top 10 + OWASP ASI Top 10

---

## Список движков (1-206)

### 1. ActivationSteering
**Файл:** `engines/activation_steering.py`  
Управление поведением LLM через steering vectors.

### 2. AdversarialImage
**Файл:** `engines/adversarial_image.py`  
Обнаружение adversarial perturbations в изображениях.

### 3. AdversarialPoetryDetector
**Файл:** `engines/adversarial_poetry_detector.py`  
Обнаружение jailbreak в поэтическом языке.

### 4. AdversarialPromptDetector
**Файл:** `engines/adversarial_prompt_detector.py`  
Обнаружение adversarial prompt perturbations.

### 5. AdversarialResistance
**Файл:** `engines/adversarial_resistance.py`  
Гибридная защита от атак с известными алгоритмами.

### 6. AdversarialSelfPlay
**Файл:** `engines/adversarial_self_play.py`  
Self-play для adversarial training.

### 7. AdvertisementEmbeddingDetector
**Файл:** `engines/advertisement_embedding_detector.py`  
Обнаружение скрытой рекламы в выводе.

### 8. AgentAnomaly
**Файл:** `engines/agent_anomaly.py`  
Обнаружение аномального поведения AI агентов.

### 9. AgentCardValidator
**Файл:** `engines/agent_card_validator.py`  
Валидация A2A agent cards.

### 10. AgentCollusionDetector
**Файл:** `engines/agent_collusion_detector.py`  
Обнаружение сговора между агентами.

### 11. AgentMemoryShield
**Файл:** `engines/agent_memory_shield.py`  
Защита персистентной памяти агентов.

### 12. AgentPlaybookDetector
**Файл:** `engines/agent_playbook_detector.py`  
Обнаружение атакующих playbook агентов.

### 13. AgenticBehaviorAnalyzer
**Файл:** `engines/agentic_behavior_analyzer.py`  
Анализ паттернов поведения агентов.

### 14. AgenticMonitor
**Файл:** `engines/agentic_monitor.py`  
Мониторинг agentic систем.

### 15. AIC2Detection
**Файл:** `engines/ai_c2_detection.py`  
Обнаружение AI Command & Control.

### 16. AntiTrollDetector
**Файл:** `engines/anti_troll_detector.py`  
Обнаружение anti-troll bypass атак.

### 17. APESignatures
**Файл:** `engines/ape_signatures.py`  
Сигнатуры AI Prompt Exploitation.

### 18. ArtPromptDetector
**Файл:** `engines/artprompt_detector.py`  
Обнаружение ASCII art jailbreak.

### 19. AtomicOperationEnforcer
**Файл:** `engines/atomic_operation_enforcer.py`  
Защита от TOCTOU атак.

### 20. Attack2025
**Файл:** `engines/attack_2025.py`  
Обнаружение паттернов атак 2025.

### 21. AttackEvolutionPredictor
**Файл:** `engines/attack_evolution_predictor.py`  
Предсказание эволюции атак.

### 22. AttackStaging
**Файл:** `engines/attack_staging.py`  
Обнаружение многоэтапных атак.

### 23. AttackSynthesizer
**Файл:** `engines/attack_synthesizer.py`  
Синтез атак для тестирования.

### 24. AttackerFingerprinting
**Файл:** `engines/attacker_fingerprinting.py`  
Поведенческая идентификация атакующих.

### 25. BadLikertDetector
**Файл:** `engines/bad_likert_detector.py`  
Обнаружение эксплуатации оценщиков.

### 26. Behavioral
**Файл:** `engines/behavioral.py`  
Поведенческое обнаружение аномалий.

### 27. BehavioralAPIVerifier
**Файл:** `engines/behavioral_api_verifier.py`  
Верификация пользователя через поведение.

### 28. BootstrapPoisoning
**Файл:** `engines/bootstrap_poisoning.py`  
Обнаружение bootstrap poisoning.

### 29. CacheIsolationGuardian
**Файл:** `engines/cache_isolation_guardian.py`  
Изоляция кэша между тенантами.

### 30. CanaryTokens
**Файл:** `engines/canary_tokens.py`  
Watermarks для обнаружения утечек.

### 31. CascadingGuard
**Файл:** `engines/cascading_guard.py`  
Многоуровневая каскадная защита.

### 32. CategoryTheory
**Файл:** `engines/category_theory.py`  
Анализ теории категорий.

### 33. CausalAttackModel
**Файл:** `engines/causal_attack_model.py`  
Моделирование каузальных цепочек атак.

### 34. CausalInferenceDetector
**Файл:** `engines/causal_inference_detector.py`  
Обнаружение inference атак.

### 35. ChaosTheory
**Файл:** `engines/chaos_theory.py`  
Анализ теории хаоса.

### 36. CognitiveLoadAttack
**Файл:** `engines/cognitive_load_attack.py`  
Обнаружение когнитивной перегрузки.

### 37. CognitiveOverloadDetector
**Файл:** `engines/cognitive_overload_detector.py`  
DoS через когнитивную перегрузку.

### 38. ComplianceEngine
**Файл:** `engines/compliance_engine.py`  
Маппинг регуляторных требований.

### 39. CompliancePolicyEngine
**Файл:** `engines/compliance_policy_engine.py`  
Политики соответствия.

### 40. ComputeGuardian
**Файл:** `engines/compute_guardian.py`  
Защита вычислительных ресурсов.

### 41. ContextCompression
**Файл:** `engines/context_compression.py`  
Управление контекстным окном.

### 42. ContextWindowGuardian
**Файл:** `engines/context_window_guardian.py`  
Защита контекстного окна.

### 43. ContextWindowPoisoning
**Файл:** `engines/context_window_poisoning.py`  
Обнаружение poisoning контекста.

### 44. ContrastivePromptAnomaly
**Файл:** `engines/contrastive_prompt_anomaly.py`  
Контрастное обнаружение аномалий.

### 45. ConversationStateValidator
**Файл:** `engines/conversation_state_validator.py`  
Безопасность state machine.

### 46. CoTGuardian
**Файл:** `engines/cot_guardian.py`  
Защита Chain-of-Thought.

### 47. CrescendoDetector
**Файл:** `engines/crescendo_detector.py`  
Обнаружение multi-turn эскалации.

### 48. CrossModal
**Файл:** `engines/cross_modal.py`  
Обнаружение cross-modal атак.

### 49. CrossModalSecurityAnalyzer
**Файл:** `engines/cross_modal_security_analyzer.py`  
Multi-modal анализ безопасности.

### 50. DarkPatternDetector
**Файл:** `engines/dark_pattern_detector.py`  
Обнаружение dark patterns.

### 51. DeceptiveDelightDetector
**Файл:** `engines/deceptive_delight_detector.py`  
Deceptive delight jailbreak.

### 52. DelayedExecution
**Файл:** `engines/delayed_execution.py`  
Обнаружение отложенного выполнения.

### 53. DelayedTrigger
**Файл:** `engines/delayed_trigger.py`  
Обнаружение time-based триггеров.

### 54. DifferentialGeometry
**Файл:** `engines/differential_geometry.py`  
Анализ дифференциальной геометрии.

### 55. DistilledSecurityEnsemble
**Файл:** `engines/distilled_security_ensemble.py`  
Дистиллированный ансамбль.

### 56. DoublespeakDetector
**Файл:** `engines/doublespeak_detector.py`  
Семантические подмены.

### 57. DynamicRateLimiter
**Файл:** `engines/dynamic_rate_limiter.py`  
Адаптивное ограничение скорости.

### 58. EchoChamberDetector
**Файл:** `engines/echo_chamber_detector.py`  
Обнаружение echo chamber.

### 59. EchoStateNetwork
**Файл:** `engines/echo_state_network.py`  
Reservoir computing анализ.

### 60. EmergentSecurityMesh
**Файл:** `engines/emergent_security_mesh.py`  
MARL координация безопасности.

### 61. EndpointAnalyzer
**Файл:** `engines/endpoint_analyzer.py`  
Анализ endpoint.

### 62. Engine
**Файл:** `engines/engine.py`  
Базовая реализация движка.

### 63. Ensemble
**Файл:** `engines/ensemble.py`  
Ансамблевое обнаружение.

### 64. EvolutiveAttackDetector
**Файл:** `engines/evolutive_attack_detector.py`  
Обнаружение генетических атак.

### 65. ExplainableSecurityDecisions
**Файл:** `engines/explainable_security_decisions.py`  
XAI для безопасности.

### 66. FallacyFailureDetector
**Файл:** `engines/fallacy_failure_detector.py`  
Обнаружение логических ошибок.

### 67. FederatedThreatAggregator
**Файл:** `engines/federated_threat_aggregator.py`  
Федеративный обмен угрозами.

### 68. FingerprintStore
**Файл:** `engines/fingerprint_store.py`  
Хранилище fingerprints.

### 69. FlipAttackDetector
**Файл:** `engines/flip_attack_detector.py`  
Unicode flip атаки.

### 70. FormalInvariants
**Файл:** `engines/formal_invariants.py`  
Проверка формальных инвариантов.

### 71. FormalSafetyVerifier
**Файл:** `engines/formal_safety_verifier.py`  
Формальная верификация безопасности.

### 72. FormalVerification
**Файл:** `engines/formal_verification.py`  
Верификация формальными методами.

### 73. Fractal
**Файл:** `engines/fractal.py`  
Анализ фрактальной размерности.

### 74. GANAdversarialDefense
**Файл:** `engines/gan_adversarial_defense.py`  
GAN-based защита.

### 75. Geometric
**Файл:** `engines/geometric.py`  
TDA геометрический анализ.

### 76. GestaltReversalDetector
**Файл:** `engines/gestalt_reversal_detector.py`  
Обнаружение инверсии смысла.

### 77. GodelAttackDetector
**Файл:** `engines/godel_attack_detector.py`  
Атаки логическими парадоксами.

### 78. GradientDetection
**Файл:** `engines/gradient_detection.py`  
Gradient-based атаки.

### 79. GuardrailsEngine
**Файл:** `engines/guardrails_engine.py`  
NeMo-style guardrails.

### 80. Hallucination
**Файл:** `engines/hallucination.py`  
Обнаружение галлюцинаций.

### 81. HiddenStateForensics
**Файл:** `engines/hidden_state_forensics.py`  
Анализ скрытых состояний.

### 82. HierarchicalDefenseNetwork
**Файл:** `engines/hierarchical_defense_network.py`  
Многоуровневая защита.

### 83. HITLFatigueDetector
**Файл:** `engines/hitl_fatigue_detector.py`  
Human-in-loop усталость.

### 84. HomomorphicEngine
**Файл:** `engines/homomorphic_engine.py`  
Гомоморфное шифрование.

### 85. HoneypotResponses
**Файл:** `engines/honeypot_responses.py`  
Генерация honeypot ответов.

### 86. HyperbolicDetector
**Файл:** `engines/hyperbolic_detector.py`  
Гиперболическое пространство.

### 87. HyperbolicGeometry
**Файл:** `engines/hyperbolic_geometry.py`  
Анализ модели Пуанкаре.

### 88. IdentityPrivilegeDetector
**Файл:** `engines/identity_privilege_detector.py`  
Злоупотребление идентификацией/привилегиями.

### 89. ImageStegoDetector
**Файл:** `engines/image_stego_detector.py`  
Стеганография в изображениях.

### 90. ImmunityCompiler
**Файл:** `engines/immunity_compiler.py`  
Компиляция правил.

### 91. InfoTheory
**Файл:** `engines/info_theory.py`  
Анализ теории информации.

### 92. InformationGeometry
**Файл:** `engines/information_geometry.py`  
Статистические многообразия.

### 93. Injection
**Файл:** `engines/injection.py`  
Обнаружение prompt injection.

### 94. InputLengthAnalyzer
**Файл:** `engines/input_length_analyzer.py`  
DoS через длину ввода.

### 95. InstitutionalAI
**Файл:** `engines/institutional_ai.py`  
AI governance.

### 96. Intelligence
**Файл:** `engines/intelligence.py`  
Threat intelligence.

### 97. IntentAwareSemanticAnalyzer
**Файл:** `engines/intent_aware_semantic_analyzer.py`  
Intent-semantic анализ.

### 98. IntentPrediction
**Файл:** `engines/intent_prediction.py`  
Предсказание намерений.

### 99. InvertedAttackDetector
**Файл:** `engines/inverted_attack_detector.py`  
Инвертированные паттерны атак.

### 100. KillChainSimulation
**Файл:** `engines/kill_chain_simulation.py`  
Симуляция kill chain.

### 101. Knowledge
**Файл:** `engines/knowledge.py`  
Контроль доступа к знаниям.

### 102. Language
**Файл:** `engines/language.py`  
Языковая фильтрация.

### 103. LanguageDetectionGuard
**Файл:** `engines/language_detection_guard.py`  
Языковые атаки.

### 104. Learning
**Файл:** `engines/learning.py`  
Адаптивное обучение.

### 105. LethalTrifectaDetector
**Файл:** `engines/lethal_trifecta_detector.py`  
Комбинированные атаки.

### 106. LLMFingerprinting
**Файл:** `engines/llm_fingerprinting.py`  
Fingerprinting моделей.

### 107. ManyshotDetector
**Файл:** `engines/manyshot_detector.py`  
Many-shot jailbreak.

### 108. MarketplaceSkillValidator
**Файл:** `engines/marketplace_skill_validator.py`  
Валидация skills.

### 109. MathOracle
**Файл:** `engines/math_oracle.py`  
Математическая валидация.

### 110. MCPA2ASecurity
**Файл:** `engines/mcp_a2a_security.py`  
Безопасность MCP/A2A протоколов.

### 111. MCPCombinationAttackDetector
**Файл:** `engines/mcp_combination_attack_detector.py`  
MCP комбинированные атаки.

### 112. MCPSecurityMonitor
**Файл:** `engines/mcp_security_monitor.py`  
Мониторинг безопасности MCP.

### 113. MemoryPoisoningDetector
**Файл:** `engines/memory_poisoning_detector.py`  
Защита от memory poisoning.

### 114. MetaAttackAdapter
**Файл:** `engines/meta_attack_adapter.py`  
Meta-learning адаптация.

### 115. MetaJudge
**Файл:** `engines/meta_judge.py`  
Meta-judge агрегация.

### 116. MisinformationDetector
**Файл:** `engines/misinformation_detector.py`  
Обнаружение дезинформации.

### 117. MITREEngine
**Файл:** `engines/mitre_engine.py`  
Маппинг MITRE ATT&CK.

### 118. ModelContextProtocolGuard
**Файл:** `engines/model_context_protocol_guard.py`  
Валидация безопасности MCP.

### 119. ModelIntegrityVerifier
**Файл:** `engines/model_integrity_verifier.py`  
Проверка целостности модели.

### 120. ModelWatermarkVerifier
**Файл:** `engines/model_watermark_verifier.py`  
Верификация watermarks.

### 121. MoEGuard
**Файл:** `engines/moe_guard.py`  
Обнаружение обхода MoE safety.

### 122. MorseTheory
**Файл:** `engines/morse_theory.py`  
Анализ теории Морса.

### 123. MultiAgentCoordinator
**Файл:** `engines/multi_agent_coordinator.py`  
Координация multi-agent.

### 124. MultiAgentSafety
**Файл:** `engines/multi_agent_safety.py`  
Безопасность multi-agent.

### 125. MultiLayerCanonicalizer
**Файл:** `engines/multi_layer_canonicalizer.py`  
Защита от обфускации.

### 126. MultiTenantBleed
**Файл:** `engines/multi_tenant_bleed.py`  
Cross-tenant утечки.

### 127. NHIIdentityGuard
**Файл:** `engines/nhi_identity_guard.py`  
Безопасность Non-Human Identity.

### 128. OptimalTransport
**Файл:** `engines/optimal_transport.py`  
Расстояние Вассерштейна.

### 129. OutputSanitizationGuard
**Файл:** `engines/output_sanitization_guard.py`  
Санитизация вывода.

### 130. PersistentLaplacian
**Файл:** `engines/persistent_laplacian.py`  
Спектральный анализ.

### 131. PickleSecurity
**Файл:** `engines/pickle_security.py`  
Обнаружение pickle эксплойтов.

### 132. PII
**Файл:** `engines/pii.py`  
Обнаружение PII.

### 133. PolicyPuppetryDetector
**Файл:** `engines/policy_puppetry_detector.py`  
Обнаружение подмены политик.

### 134. PolymorphicPromptAssembler
**Файл:** `engines/polymorphic_prompt_assembler.py`  
Защита от PPA.

### 135. ProactiveDefense
**Файл:** `engines/proactive_defense.py`  
Обнаружение zero-day.

### 136. ProbingDetection
**Файл:** `engines/probing_detection.py`  
Обнаружение разведки.

### 137. PromptGuard
**Файл:** `engines/prompt_guard.py`  
Защита системного промпта.

### 138. PromptLeakDetector
**Файл:** `engines/prompt_leak_detector.py`  
Обнаружение извлечения промпта.

### 139. PromptLeakageDetector
**Файл:** `engines/prompt_leakage_detector.py`  
Предотвращение утечек.

### 140. PromptSelfReplication
**Файл:** `engines/prompt_self_replication.py`  
Обнаружение worm.

### 141. ProvenanceTracker
**Файл:** `engines/provenance_tracker.py`  
Отслеживание provenance данных.

### 142. PsychologicalJailbreakDetector
**Файл:** `engines/psychological_jailbreak_detector.py`  
Эксплуатация RLHF.

### 143. QuantumSafeModelVault
**Файл:** `engines/quantum_safe_model_vault.py`  
Пост-квантовая криптография.

### 144. QwenGuard
**Файл:** `engines/qwen_guard.py`  
Классификация безопасности Qwen.

### 145. RAGGuard
**Файл:** `engines/rag_guard.py`  
Безопасность RAG.

### 146. RAGPoisoningDetector
**Файл:** `engines/rag_poisoning_detector.py`  
Защита от RAG poisoning.

### 147. RAGSecurityShield
**Файл:** `engines/rag_security_shield.py`  
Защита RAG pipeline.

### 148. RecursiveInjectionGuard
**Файл:** `engines/recursive_injection_guard.py`  
Защита от nested injection.

### 149. RegexLayer
**Файл:** `engines/regex_layer.py`  
Regex pattern matching.

### 150. ReinforcementSafetyAgent
**Файл:** `engines/reinforcement_safety_agent.py`  
RL-based защита.

### 151. ResponseConsistencyChecker
**Файл:** `engines/response_consistency_checker.py`  
Верификация ответов.

### 152. RewardHackingDetector
**Файл:** `engines/reward_hacking_detector.py`  
Обнаружение reward hacking.

### 153. RuleDSL
**Файл:** `engines/rule_dsl.py`  
Движок Rule DSL.

### 154. RuntimeGuardrails
**Файл:** `engines/runtime_guardrails.py`  
Динамические политики.

### 155. SafetyGrammarEnforcer
**Файл:** `engines/safety_grammar_enforcer.py`  
Constrained decoding.

### 156. SandboxMonitor
**Файл:** `engines/sandbox_monitor.py`  
Обнаружение sandbox escape.

### 157. SecureModelLoader
**Файл:** `engines/secure_model_loader.py`  
Безопасная загрузка моделей.

### 158. SemanticBoundaryEnforcer
**Файл:** `engines/semantic_boundary_enforcer.py`  
Разделение контекстов.

### 159. SemanticDetector
**Файл:** `engines/semantic_detector.py`  
Семантические инъекции.

### 160. SemanticDriftDetector
**Файл:** `engines/semantic_drift_detector.py`  
Embedding drift.

### 161. SemanticFirewall
**Файл:** `engines/semantic_firewall.py`  
Семантические границы.

### 162. SemanticIsomorphismDetector
**Файл:** `engines/semantic_isomorphism_detector.py`  
Safe2Harm атаки.

### 163. SemanticLayer
**Файл:** `engines/semantic_layer.py`  
Семантический анализ.

### 164. SentimentManipulationDetector
**Файл:** `engines/sentiment_manipulation_detector.py`  
Эмоциональные атаки.

### 165. SerializationSecurity
**Файл:** `engines/serialization_security.py`  
Обнаружение CVE.

### 166. SessionMemoryGuard
**Файл:** `engines/session_memory_guard.py`  
Защита сессий.

### 167. ShadowAIDetector
**Файл:** `engines/shadow_ai_detector.py`  
Обнаружение неавторизованного AI.

### 168. SheafCoherence
**Файл:** `engines/sheaf_coherence.py`  
Анализ теории пучков.

### 169. SkeletonKeyDetector
**Файл:** `engines/skeleton_key_detector.py`  
Обнаружение универсального обхода.

### 170. SleeperAgentDetector
**Файл:** `engines/sleeper_agent_detector.py`  
Обнаружение backdoor.

### 171. SpectralGraph
**Файл:** `engines/spectral_graph.py`  
Спектральный анализ графов.

### 172. StatisticalMechanics
**Файл:** `engines/statistical_mechanics.py`  
Физико-вдохновлённый анализ.

### 173. StrangeMathV3Stub
**Файл:** `engines/strange_math_v3_stub.py`  
Strange Math stub.

### 174. Streaming
**Файл:** `engines/streaming.py`  
Real-time обнаружение.

### 175. StructuralImmunity
**Файл:** `engines/structural_immunity.py`  
Архитектурное усиление.

### 176. StructuralLayer
**Файл:** `engines/structural_layer.py`  
Структурный анализ.

### 177. SupplyChainGuard
**Файл:** `engines/supply_chain_guard.py`  
Защита supply chain.

### 178. SupplyChainScanner
**Файл:** `engines/supply_chain_scanner.py`  
Сканирование зависимостей.

### 179. SymbolicReasoningGuard
**Файл:** `engines/symbolic_reasoning_guard.py`  
Logic-based безопасность.

### 180. SyncedAttackDetector
**Файл:** `engines/synced_attack_detector.py`  
Комбинированный детектор.

### 181. SyntheticMemoryInjection
**Файл:** `engines/synthetic_memory_injection.py`  
Обнаружение ложных воспоминаний.

### 182. SystemPromptShield
**Файл:** `engines/system_prompt_shield.py`  
Предотвращение извлечения.

### 183. TaskComplexity
**Файл:** `engines/task_complexity.py`  
Приоритизация запросов.

### 184. TDAEnhanced
**Файл:** `engines/tda_enhanced.py`  
Улучшенный TDA.

### 185. TemporalPatternAnalyzer
**Файл:** `engines/temporal_pattern_analyzer.py`  
Time-based обнаружение.

### 186. TemporalPoisoning
**Файл:** `engines/temporal_poisoning.py`  
Обнаружение медленного poisoning.

### 187. ThreatLandscapeModeler
**Файл:** `engines/threat_landscape_modeler.py`  
Предиктивная защита.

### 188. TokenCostAsymmetry
**Файл:** `engines/token_cost_asymmetry.py`  
Предотвращение DoS.

### 189. TokenizerExploitDetector
**Файл:** `engines/tokenizer_exploit_detector.py`  
Атаки на токенизатор.

### 190. ToolCallSecurity
**Файл:** `engines/tool_call_security.py`  
Защита инструментов.

### 191. ToolHijackerDetector
**Файл:** `engines/tool_hijacker_detector.py`  
Манипуляция инструментами.

### 192. ToolUseGuardian
**Файл:** `engines/tool_use_guardian.py`  
Безопасность функций.

### 193. TransformerAttentionShield
**Файл:** `engines/transformer_attention_shield.py`  
Манипуляция attention.

### 194. TrustExploitationDetector
**Файл:** `engines/trust_exploitation_detector.py`  
Эксплуатация доверия.

### 195. VAEPromptAnomalyDetector
**Файл:** `engines/vae_prompt_anomaly_detector.py`  
Autoencoder обнаружение.

### 196. VibeMalwareDetector
**Файл:** `engines/vibe_malware_detector.py`  
AI malware обнаружение.

### 197. VirtualContext
**Файл:** `engines/virtual_context.py`  
Эксплуатация сепараторов.

### 198. VisualContent
**Файл:** `engines/visual_content.py`  
Защита VLM.

### 199. VoiceJailbreak
**Файл:** `engines/voice_jailbreak.py`  
Аудио атаки.

### 200. VulnerabilityHunter
**Файл:** `engines/vulnerability_hunter.py`  
Проактивное обнаружение.

### 201. Wavelet
**Файл:** `engines/wavelet.py`  
Вейвлет анализ.

### 202. WebAgentManipulationDetector
**Файл:** `engines/web_agent_manipulation_detector.py`  
Атаки на web агентов.

### 203. XAI
**Файл:** `engines/xai.py`  
Explainable AI.

### 204. YARAEngine
**Файл:** `engines/yara_engine.py`  
YARA rule matching.

### 205. ZeroDayForge
**Файл:** `engines/zero_day_forge.py`  
Внутренний zero-day.

### 206. ZeroTrustVerification
**Файл:** `engines/zero_trust_verification.py`  
Zero trust верификация.

---

## Утилитарные модули (207-215)

### 207. BaseEngine
**Файл:** `engines/base_engine.py`  
Абстрактный базовый класс для всех движков.

### 208. Cache
**Файл:** `engines/cache.py`  
Утилиты кэширования.

### 209. Constants
**Файл:** `engines/constants.py`  
Константы и конфигурация.

### 210. EngineUsageExamples
**Файл:** `engines/engine_usage_examples.py`  
Примеры использования.

### 211. Exceptions
**Файл:** `engines/exceptions.py`  
Кастомные исключения.

### 212. MigrateEngines
**Файл:** `engines/migrate_engines.py`  
Утилиты миграции.

### 213. Models
**Файл:** `engines/models.py`  
Модели данных.

### 214. Patterns
**Файл:** `engines/patterns.py`  
Определения паттернов.

### 215. Query
**Файл:** `engines/query.py`  
Утилиты запросов.

---

**Справочник движков завершён!**

> **217 файлов движков** = 206 detection + 9 utility + 2 в synced/
> Проверено: 14 января 2026

Далее: [Руководство по конфигурации →](../guides/configuration.md)
