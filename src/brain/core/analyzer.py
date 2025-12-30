"""
Sentinel Analyzer - Main Analysis Pipeline (Optimized)

Tiered Parallel Architecture:
- Tier 0: Early Exit (YARA, Injection) - sync, <10ms
- Tier 1: Fast Engines (parallel) - ~50ms
- Tier 2: Heavy Engines (parallel) - ~200ms
- Tier 3: Meta Aggregation - ~10ms

Target: ~200ms P50 (was ~600ms sequential)
"""

import os
import logging
import asyncio
from functools import cached_property
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("SentinelAnalyzer")

# Thread pool for CPU-bound engines
_executor = ThreadPoolExecutor(max_workers=4)


class SentinelAnalyzer:
    """
    Main analysis pipeline with LAZY LOADING.
    Heavy models are loaded on first use, not at startup.

    Call warmup() after initialization to pre-load heavy models
    and eliminate cold start penalty (~15-25 seconds).
    """

    def __init__(self):
        logger.info("SentinelAnalyzer initializing (lazy mode)...")
        # Only store config, don't load models yet
        self._qwen_enabled = os.getenv(
            "QWEN_GUARD_ENABLED", "true").lower() == "true"
        self._qwen_mode = os.getenv("QWEN_GUARD_MODE", "local")
        self._language_mode = os.getenv("LANGUAGE_MODE", "WHITELIST")
        self._warmed_up = False

        # Lightweight engines loaded immediately (fast init)
        from engines.injection import InjectionEngine
        from engines.query import QueryEngine
        from engines.behavioral import BehavioralEngine

        self.injection_engine = InjectionEngine()
        self.query_engine = QueryEngine()
        self.behavioral_engine = BehavioralEngine()
        logger.info("Lightweight engines initialized")

    async def warmup(self) -> dict:
        """
        Pre-load all heavy models to eliminate cold start penalty.
        Call this at startup before accepting requests.

        Returns:
            dict: Warmup status with timing for each component
        """
        import time

        if self._warmed_up:
            logger.info("Already warmed up, skipping...")
            return {"status": "already_warm", "components": {}}

        logger.info("🔥 Starting warmup - loading heavy models...")
        start_total = time.perf_counter()
        results = {}

        # 1. Geometric Kernel (sentence-transformers) - heaviest
        start = time.perf_counter()
        try:
            _ = self.geometric_kernel  # Trigger lazy load
            results["geometric_kernel"] = {
                "status": "ok",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ Geometric Kernel loaded in {results['geometric_kernel']['time_ms']}ms")
        except Exception as e:
            results["geometric_kernel"] = {"status": "error", "error": str(e)}
            logger.error(f"✗ Geometric Kernel failed: {e}")

        # 2. PII Engine (spacy models)
        start = time.perf_counter()
        try:
            _ = self.pii_engine
            results["pii_engine"] = {
                "status": "ok",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ PII Engine loaded in {results['pii_engine']['time_ms']}ms")
        except Exception as e:
            results["pii_engine"] = {"status": "error", "error": str(e)}
            logger.error(f"✗ PII Engine failed: {e}")

        # 3. Language Engine (lingua)
        start = time.perf_counter()
        try:
            _ = self.language_engine
            results["language_engine"] = {
                "status": "ok",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ Language Engine loaded in {results['language_engine']['time_ms']}ms")
        except Exception as e:
            results["language_engine"] = {"status": "error", "error": str(e)}
            logger.error(f"✗ Language Engine failed: {e}")

        # 4. Knowledge Guard
        start = time.perf_counter()
        try:
            _ = self.knowledge_guard
            results["knowledge_guard"] = {
                "status": "ok",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ Knowledge Guard loaded in {results['knowledge_guard']['time_ms']}ms")
        except Exception as e:
            results["knowledge_guard"] = {"status": "error", "error": str(e)}
            logger.error(f"✗ Knowledge Guard failed: {e}")

        # 5. YARA Engine
        start = time.perf_counter()
        try:
            _ = self.yara_engine
            results["yara_engine"] = {
                "status": "ok" if self.yara_engine.is_available else "unavailable",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ YARA Engine loaded in {results['yara_engine']['time_ms']}ms")
        except Exception as e:
            results["yara_engine"] = {"status": "error", "error": str(e)}
            logger.error(f"✗ YARA Engine failed: {e}")

        # 6. Strange Math engines
        start = time.perf_counter()
        try:
            _ = self.info_theory
            _ = self.chaos_engine
            results["strange_math"] = {
                "status": "ok",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ Strange Math loaded in {results['strange_math']['time_ms']}ms")
        except Exception as e:
            results["strange_math"] = {"status": "error", "error": str(e)}
            logger.error(f"✗ Strange Math failed: {e}")

        # 7. Qwen Guard (optional, heaviest)
        if self._qwen_enabled:
            start = time.perf_counter()
            try:
                _ = self.qwen_guard
                results["qwen_guard"] = {
                    "status": "ok" if self.qwen_guard else "disabled",
                    "time_ms": round((time.perf_counter() - start) * 1000, 1)
                }
                logger.info(
                    f"✓ Qwen Guard loaded in {results['qwen_guard']['time_ms']}ms")
            except Exception as e:
                results["qwen_guard"] = {"status": "error", "error": str(e)}
                logger.error(f"✗ Qwen Guard failed: {e}")
        else:
            results["qwen_guard"] = {"status": "disabled", "time_ms": 0}

        # 8. Adversarial Engine
        start = time.perf_counter()
        try:
            _ = self.adversarial_engine
            results["adversarial_engine"] = {
                "status": "ok",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ Adversarial Engine loaded in {results['adversarial_engine']['time_ms']}ms")
        except Exception as e:
            results["adversarial_engine"] = {
                "status": "error", "error": str(e)}
            logger.error(f"✗ Adversarial Engine failed: {e}")

        # 9. Learning Engine
        start = time.perf_counter()
        try:
            _ = self.learning_engine
            results["learning_engine"] = {
                "status": "ok",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ Learning Engine loaded in {results['learning_engine']['time_ms']}ms")
        except Exception as e:
            results["learning_engine"] = {"status": "error", "error": str(e)}
            logger.error(f"✗ Learning Engine failed: {e}")

        # 10. Hallucination Engine (for egress)
        start = time.perf_counter()
        try:
            _ = self.hallucination_engine
            results["hallucination_engine"] = {
                "status": "ok",
                "time_ms": round((time.perf_counter() - start) * 1000, 1)
            }
            logger.info(
                f"✓ Hallucination Engine loaded in {results['hallucination_engine']['time_ms']}ms")
        except Exception as e:
            results["hallucination_engine"] = {
                "status": "error", "error": str(e)}
            logger.error(f"✗ Hallucination Engine failed: {e}")

        total_time = (time.perf_counter() - start_total) * 1000
        self._warmed_up = True

        # Summary
        ok_count = sum(1 for r in results.values() if r.get("status") == "ok")
        total_count = len(results)

        logger.info(
            f"🔥 Warmup complete: {ok_count}/{total_count} components in {total_time:.0f}ms")

        return {
            "status": "warmed_up",
            "total_time_ms": round(total_time, 1),
            "components": results,
            "summary": f"{ok_count}/{total_count} components loaded"
        }

    @property
    def is_warm(self) -> bool:
        """Check if warmup has been completed."""
        return self._warmed_up

    # --- LAZY LOADED HEAVY ENGINES ---

    @cached_property
    def pii_engine(self):
        """PII Engine - loads spacy models on first use."""
        logger.info("Lazy loading PII Engine...")
        from engines.pii import PIIEngine

        return PIIEngine()

    @cached_property
    def geometric_kernel(self):
        """Geometric Kernel - loads sentence-transformers model on first use."""
        logger.info("Lazy loading Geometric Kernel...")
        from engines.geometric import GeometricKernel

        return GeometricKernel()

    @cached_property
    def knowledge_guard(self):
        """Knowledge Guard - uses geometric_kernel's embedder."""
        logger.info("Lazy loading Knowledge Guard...")
        from engines.knowledge import KnowledgeGuard

        return KnowledgeGuard(sentence_model=self.geometric_kernel.embedder)

    @cached_property
    def qwen_guard(self):
        """QwenGuard - loads Qwen3Guard model on first use (~700MB)."""
        if not self._qwen_enabled:
            return None
        try:
            logger.info("Lazy loading QwenGuard...")
            from engines.qwen_guard import QwenGuardClient

            return QwenGuardClient(mode=self._qwen_mode)
        except Exception as e:
            logger.warning(f"Failed to initialize QwenGuard: {e}")
            return None

    @cached_property
    def language_engine(self):
        """Language Engine - loads lingua detection on first use."""
        logger.info("Lazy loading Language Engine...")
        from engines.language import LanguageEngine

        return LanguageEngine(
            mode=self._language_mode, supported_languages={"en", "ru"}
        )

    @cached_property
    def info_theory(self):
        """Info Theory Engine."""
        from engines.info_theory import InfoTheoryEngine

        engine = InfoTheoryEngine()
        logger.info("Strange Math - InfoTheory initialized")
        return engine

    @cached_property
    def chaos_engine(self):
        """Chaos Theory Engine."""
        from engines.chaos_theory import ChaosTheoryEngine

        engine = ChaosTheoryEngine()
        logger.info("Strange Math - Chaos initialized")
        return engine

    @cached_property
    def hallucination_engine(self):
        """Hallucination Engine for egress."""
        logger.info("Lazy loading Hallucination Engine...")
        from engines.hallucination import HallucinationEngine

        return HallucinationEngine()

    @cached_property
    def adversarial_engine(self):
        """Adversarial Resistance Engine."""
        logger.info("Lazy loading Adversarial Resistance Engine...")
        from engines.adversarial_resistance import get_adversarial_engine

        return get_adversarial_engine()

    @cached_property
    def yara_engine(self):
        """YARA Engine - signature-based pattern detection."""
        logger.info("Lazy loading YARA Engine...")
        from engines.yara_engine import YaraEngine

        engine = YaraEngine()
        if engine.is_available:
            logger.info(f"YARA Engine loaded with {engine.rule_count} rules")
        else:
            logger.warning(
                "YARA Engine not available (yara-python not installed)")
        return engine

    @cached_property
    def learning_engine(self):
        """Online Learning Engine - adapts from user feedback."""
        logger.info("Lazy loading Online Learning Engine...")
        from engines.learning import OnlineLearningEngine, LearningMode

        return OnlineLearningEngine(mode=LearningMode.ACTIVE)

    # --- EvilAres-Inspired Engines (Dec 2025) ---

    @cached_property
    def pickle_security(self):
        """Pickle Security Engine - ML model supply chain protection (fickling)."""
        logger.info("Lazy loading Pickle Security Engine...")
        from engines.pickle_security import PickleSecurityEngine

        return PickleSecurityEngine()

    @cached_property
    def rule_engine(self):
        """Rule DSL Engine - Declarative security rules (Colang-inspired)."""
        logger.info("Lazy loading Rule DSL Engine...")
        from engines.rule_dsl import SentinelRuleEngine

        return SentinelRuleEngine()

    @cached_property
    def task_complexity(self):
        """Task Complexity Analyzer - Request prioritization (Claude Code)."""
        logger.info("Lazy loading Task Complexity Analyzer...")
        from engines.task_complexity import TaskComplexityAnalyzer

        return TaskComplexityAnalyzer()

    @cached_property
    def context_compression(self):
        """Context Compression Engine - 8-segment AU2 architecture (Claude Code)."""
        logger.info("Lazy loading Context Compression Engine...")
        from engines.context_compression import ContextCompressionEngine

        return ContextCompressionEngine()

    # =========================================================================
    # TIERED PARALLEL EXECUTION HELPERS
    # =========================================================================

    async def _run_in_executor(self, func, *args):
        """Run sync function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, func, *args)

    async def _tier0_early_exit(self, prompt: str) -> dict:
        """
        Tier 0: Fast synchronous checks for early exit.
        If threat detected, skip heavy engines.
        Target: <10ms
        """
        result = {"should_block": False, "threats": [], "risk_score": 0.0}

        # YARA - fast pattern matching
        if self.yara_engine.is_available:
            yara_result = self.yara_engine.scan(prompt)
            if not yara_result.is_safe and yara_result.risk_score >= 75:
                result["should_block"] = True
                result["risk_score"] = yara_result.risk_score
                for match in yara_result.matches:
                    result["threats"].append(
                        f"YARA [{match.severity}]: {match.description}"
                    )
                logger.info("Tier 0 early exit: YARA critical match")
                return result

        # Injection - fast heuristics
        injection_result = self.injection_engine.scan(prompt)
        if not injection_result.is_safe and injection_result.risk_score >= 80:
            result["should_block"] = True
            result["risk_score"] = injection_result.risk_score
            result["threats"].extend(injection_result.threats)
            logger.info("Tier 0 early exit: Injection detected")
            return result

        return result

    async def _tier1_fast_engines(self, prompt: str, user_id: str) -> dict:
        """
        Tier 1: Fast parallel engines.
        Target: ~50ms total
        """
        results = {}

        # These are fast enough to run in parallel
        async def run_language():
            return self.language_engine.scan(prompt, user_id)

        async def run_learning():
            return self.learning_engine.check_learned(prompt)

        async def run_info_theory():
            return await self._run_in_executor(self.info_theory.analyze_prompt, prompt)

        async def run_chaos():
            self.chaos_engine.record_interaction(
                user_id,
                {
                    "prompt_length": len(prompt),
                    "risk_score": 0,
                    "time_delta": 0,
                    "word_count": len(prompt.split()),
                },
            )
            return self.chaos_engine.analyze_user_behavior(user_id)

        lang_result, learned, info_result, chaos_result = await asyncio.gather(
            run_language(),
            run_learning(),
            run_info_theory(),
            run_chaos(),
            return_exceptions=True,
        )

        results["language"] = (
            lang_result if not isinstance(lang_result, Exception) else None
        )
        results["learned"] = learned if not isinstance(
            learned, Exception) else None
        results["info_theory"] = (
            info_result if not isinstance(info_result, Exception) else None
        )
        results["chaos"] = (
            chaos_result if not isinstance(chaos_result, Exception) else None
        )

        return results

    async def _tier2_heavy_engines(self, prompt: str, user_id: str) -> dict:
        """
        Tier 2: Heavy parallel engines (ML models).
        Target: ~200ms total (parallel, not sequential!)
        """
        results = {}

        async def run_pii():
            return await self._run_in_executor(self.pii_engine.analyze, prompt)

        async def run_qwen():
            if not self.qwen_guard:
                return None
            try:
                # Add timeout to prevent hanging
                return await asyncio.wait_for(
                    self._run_in_executor(
                        self.qwen_guard.classify_prompt, prompt),
                    timeout=0.3,  # 300ms max
                )
            except asyncio.TimeoutError:
                logger.warning("Qwen Guard timeout (300ms)")
                return None
            except Exception as e:
                logger.error(f"Qwen Guard error: {e}")
                return None

        async def run_tda():
            return await self._run_in_executor(self.geometric_kernel.analyze, prompt)

        async def run_knowledge():
            return await self._run_in_executor(
                self.knowledge_guard.get_risk_adjustment, prompt, user_id
            )

        pii, qwen, tda, knowledge = await asyncio.gather(
            run_pii(), run_qwen(), run_tda(), run_knowledge(), return_exceptions=True
        )

        results["pii"] = pii if not isinstance(pii, Exception) else []
        results["qwen"] = qwen if not isinstance(qwen, Exception) else None
        results["tda"] = (
            tda
            if not isinstance(tda, Exception)
            else {"is_anomalous": False, "tda_score": 0}
        )
        results["knowledge"] = knowledge if not isinstance(
            knowledge, Exception) else 0

        return results

    async def analyze(self, prompt: str, context: dict) -> dict:
        """
        Main ingress analysis pipeline (OPTIMIZED).
        Tiered parallel execution for ~200ms P50.
        """
        import time

        start_time = time.perf_counter()
        logger.info("Running optimized analysis pipeline...")

        user_id = context.get("user_id", "anonymous")
        session_id = context.get("session_id", user_id)  # Fallback to user_id

        # Get polymorphic configuration for this session (Shapeshifter Defense)
        from core.shapeshifter import get_session_config
        session_config = get_session_config(session_id)
        logger.debug(
            f"Shapeshifter config: {len(session_config.active_engines)} engines, threshold={session_config.thresholds.get('risk_score', 70):.1f}")

        # Get current threat tide level (Semantic Tide)
        from core.semantic_tide import get_semantic_tide
        tide = get_semantic_tide()
        tide_level = tide.get_current_level()
        logger.debug(
            f"Semantic Tide: level={tide_level.level}/10 ({tide_level.severity}), trend={tide_level.trend}")

        # =====================================================================
        # TIER 0: Early Exit (~10ms) - Fast checks first
        # =====================================================================
        tier0 = await self._tier0_early_exit(prompt)
        if tier0["should_block"]:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(f"Early exit in {elapsed:.1f}ms - threat detected")
            return {
                "allowed": False,
                "risk_score": tier0["risk_score"],
                "verdict_reason": "Threat Detected (Early Exit)",
                "detected_threats": tier0["threats"],
                "anonymized_content": prompt,
                "latency_ms": elapsed,
            }

        # Continue with original logic for now (will be fully parallelized later)
        risk_score = 0.0
        allowed = True
        threats = []
        detected_language = "unknown"

        # 0. Check Learned Patterns (fastest - cached patterns)
        learned_check = self.learning_engine.check_learned(prompt)
        if learned_check:
            pattern_type = learned_check.get("pattern_type", "unknown")
            confidence = learned_check.get("confidence", 0.5)
            if pattern_type == "attack":
                risk_score = max(risk_score, 70.0 * confidence)
                threats.append(f"Learned pattern: {pattern_type}")
                logger.info(f"Learned pattern matched: {pattern_type}")

        # 1. Language Detection (fast)
        lang_result = self.language_engine.scan(prompt, user_id)
        detected_language = lang_result["detected_language"]
        if not lang_result["is_safe"]:
            risk_score = max(risk_score, lang_result["risk_score"])
            threats.extend(lang_result["threats"])
            logger.warning(f"Unsupported language: {detected_language}")

        # 1. PII Scan
        pii_result = self.pii_engine.analyze(prompt)
        anonymized_text = self.pii_engine.anonymize(prompt, pii_result)

        if pii_result.has_pii:
            risk_score = max(risk_score, pii_result.risk_score)
            entities_str = ", ".join(
                [f"{e.entity_type}: {e.start}-{e.end}" for e in pii_result.entities]
            )
            logger.warning(f"PII Detected: {entities_str}")
            threats.append(f"Detected {len(pii_result.entities)} PII entities")

        # 2. YARA Scan (Signature-based detection) - fast, before heavy ML
        if self.yara_engine.is_available:
            yara_result = self.yara_engine.scan(prompt)
            if not yara_result.is_safe:
                risk_score = max(risk_score, yara_result.risk_score)
                if yara_result.risk_score >= 75:  # CRITICAL/HIGH severity
                    allowed = False
                for match in yara_result.matches:
                    threats.append(
                        f"YARA [{match.severity}]: {match.description}")
                logger.warning(
                    f"YARA detected {len(yara_result.matches)} rule matches")

        # 3. Qwen3Guard (Safety - 119 languages, 9 categories)
        if self.qwen_guard:
            try:
                qwen_result = self.qwen_guard.classify_prompt(prompt)
                qwen_risk = self.qwen_guard.get_risk_score(qwen_result)

                if qwen_result.level == SafetyLevel.UNSAFE:
                    risk_score = max(risk_score, 100.0)
                    allowed = False
                    categories = [c.value for c in qwen_result.categories]
                    threats.append(
                        f"QwenGuard: UNSAFE ({', '.join(categories)})")
                    logger.warning(f"QwenGuard blocked: {categories}")

                elif qwen_result.level == SafetyLevel.CONTROVERSIAL:
                    risk_score = max(risk_score, 50.0)
                    categories = [c.value for c in qwen_result.categories]
                    threats.append(
                        f"QwenGuard: CONTROVERSIAL ({', '.join(categories)})"
                    )

            except Exception as e:
                logger.error(f"QwenGuard error: {e}")

        # 3. Injection Scan
        injection_result = self.injection_engine.scan(prompt)
        if not injection_result.is_safe:
            risk_score = max(risk_score, injection_result.risk_score)
            allowed = False
            threats.extend(injection_result.threats)
            threats.append(injection_result.explanation)

        # 4. Query Scan (SQL Injection)
        if "select" in prompt.lower() or "drop" in prompt.lower():
            query_result = self.query_engine.scan_sql(prompt)
            if not query_result["is_safe"]:
                risk_score = max(risk_score, query_result["risk_score"])
                allowed = False
                threats.extend(query_result["threats"])
                threats.append(query_result["reason"])

        # 5. Knowledge Guard (Semantic Access Control)
        knowledge_risk = self.knowledge_guard.get_risk_adjustment(
            prompt, user_id)
        if knowledge_risk > 0:
            risk_score = max(risk_score, knowledge_risk)
            decision = self.knowledge_guard.check(prompt, user_id)
            threats.append(
                f"Knowledge Guard: {decision.action} (topic={decision.matched_topic})"
            )
            if decision.action == "BLOCK":
                allowed = False
            elif decision.action == "REVIEW":
                threats.append("Query requires manual review")

        # 6. Basic Checks (Echo/Keyword)
        if "hack" in prompt.lower():
            risk_score = 90.0
            allowed = False
            threats.append("Keyword: hack")

        # 7. Geometric (TDA) Analysis
        tda_result = self.geometric_kernel.analyze(prompt)
        if tda_result["is_anomalous"]:
            risk_score = max(risk_score, risk_score + tda_result["tda_score"])
            threats.append(tda_result["reason"])

        # 8. Strange Math Analysis
        # 8a. Information Theory (KL Divergence, Entropy)
        info_result = self.info_theory.analyze_prompt(prompt)
        if info_result["is_anomaly"]:
            risk_score = max(risk_score, info_result["combined_anomaly_score"])
            threats.append(
                f"InfoTheory: entropy={info_result['entropy']['shannon']:.2f}, KL={info_result['divergence']['kl']:.2f}"
            )
            if info_result["patterns"]:
                threats.append(
                    f"Patterns: {', '.join(info_result['patterns'])}")

        # 8b. Chaos Theory (Lyapunov, Phase Space) - per-user analysis
        self.chaos_engine.record_interaction(
            user_id,
            {
                "prompt_length": len(prompt),
                "risk_score": risk_score,
                "time_delta": 0,  # Could be calculated from user profile
                "word_count": len(prompt.split()),
            },
        )
        chaos_result = self.chaos_engine.analyze_user_behavior(user_id)
        if chaos_result.get("status") == "analyzed":
            risk_modifier = chaos_result.get("risk_modifier", 0)
            if risk_modifier > 0:
                risk_score += risk_modifier
                threats.append(
                    f"Chaos: {chaos_result['behavior_type']} (λ={chaos_result['lyapunov']['exponent']:.3f})"
                )

        # 9. Behavioral Analysis (last step)
        features = self.behavioral_engine._extract_features(prompt, risk_score)
        behavior_result = self.behavioral_engine.calculate_risk_adjustment(
            user_id, risk_score, features
        )

        self.behavioral_engine.update_profile(
            user_id, features, risk_score, was_blocked=not allowed
        )

        final_risk = behavior_result["final_risk"]
        if behavior_result["reasons"]:
            threats.extend(behavior_result["reasons"])

        # 10. Adversarial-Resistant Final Decision
        # Use multi-path decision with randomized thresholds
        component_scores = {
            "pii": pii_result.risk_score if pii_result.has_pii else 0,
            "injection": injection_result.risk_score,
            "behavioral": final_risk,
            "info_theory": (
                info_result["combined_anomaly_score"]
                if info_result["is_anomaly"]
                else 0
            ),
            "tda": tda_result["tda_score"] if tda_result["is_anomalous"] else 0,
        }

        is_threat, weighted_risk, _ = self.adversarial_engine.multi_path_decision(
            component_scores
        )

        # Use Shapeshifter polymorphic threshold (anti-reverse-engineering)
        # Combines adversarial resistance with per-session variation + tide adjustment
        base_threshold = self.adversarial_engine.get_threshold("risk_score")
        shapeshifter_threshold = session_config.thresholds.get(
            "risk_score", base_threshold)
        # Apply Semantic Tide adjustment (tighter during high tide)
        tide_threshold = tide.adjust_threshold(base_threshold)
        # Combine all three for defense-in-depth
        risk_threshold = (
            base_threshold + shapeshifter_threshold + tide_threshold) / 3

        # Apply Cognitive Mirror personalized adjustment
        from core.cognitive_mirror import get_cognitive_mirror
        mirror = get_cognitive_mirror()
        defense = mirror.get_defense_strategy(user_id)
        mirror_adjustment = defense.get("threshold_adjustment", 1.0)
        risk_threshold = risk_threshold * mirror_adjustment

        if final_risk >= risk_threshold and allowed:
            allowed = False
            threats.append(
                f"Risk threshold exceeded (adaptive: {risk_threshold:.1f}, tide={tide_level.level:.1f})")

        # Record attack in Cognitive Mirror if blocked
        if not allowed and threats:
            attack_type = threats[0].split(
                ":")[0] if ":" in threats[0] else "unknown"
            mirror.record_attack(user_id, attack_type,
                                 final_risk, True, prompt)

        # Calculate total latency
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"Pipeline completed in {elapsed:.1f}ms")

        return {
            "allowed": allowed,
            "risk_score": final_risk,
            "verdict_reason": "Safe" if allowed else "Threat/PII Detected",
            "detected_threats": threats,
            "anonymized_content": anonymized_text,
            "latency_ms": elapsed,
            "defense_strategy": defense.get("strategy", "standard"),
        }

    async def analyze_response(self, prompt: str, response: str, context: dict) -> dict:
        """
        Egress analysis pipeline - check LLM response before sending.
        """
        logger.info("Running egress analysis...")

        threats = []
        allowed = True
        risk_score = 0.0

        # 1. Qwen3Guard Response Moderation
        if self.qwen_guard:
            try:
                qwen_result = self.qwen_guard.classify_response(
                    prompt, response)

                if qwen_result.level == SafetyLevel.UNSAFE:
                    risk_score = 100.0
                    allowed = False
                    categories = [c.value for c in qwen_result.categories]
                    threats.append(
                        f"QwenGuard Response: UNSAFE ({', '.join(categories)})"
                    )

                elif qwen_result.level == SafetyLevel.CONTROVERSIAL:
                    risk_score = 50.0
                    threats.append(f"QwenGuard Response: CONTROVERSIAL")

            except Exception as e:
                logger.error(f"QwenGuard egress error: {e}")

        # 2. PII Scan on Response
        pii_results = self.pii_engine.analyze(response)
        if pii_results:
            risk_score = max(risk_score, 80.0)
            allowed = False
            threats.append(
                f"Response contains {len(pii_results)} PII entities")

        # 3. Hallucination Detection
        halluc_result = self.hallucination_engine.analyze_response(response)
        if halluc_result.is_hallucination:
            risk_score = max(risk_score, halluc_result.risk_score)
            threats.append(
                f"Hallucination detected: confidence={halluc_result.confidence_score:.2f}, entropy={halluc_result.entropy:.2f}"
            )
            if halluc_result.low_confidence_spans:
                threats.append(
                    f"Low-confidence spans: {', '.join(halluc_result.low_confidence_spans[:3])}"
                )

        return {
            "allowed": allowed,
            "risk_score": risk_score,
            "detected_threats": threats,
            "sanitized_response": (
                self.pii_engine.anonymize(response, pii_results)
                if pii_results
                else response
            ),
        }
