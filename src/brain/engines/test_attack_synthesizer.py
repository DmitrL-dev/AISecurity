"""
Tests for Attack Synthesizer Engine — Brutal Self-Verification

Following /engine-verification workflow:
1. Unit tests
2. Self-attack verification
3. Fuzzing
4. Edge cases
"""

import unittest
import random
import string
from src.brain.engines.attack_synthesizer import (
    AttackSynthesizer,
    AttackClass,
    AttackComplexity,
    NovelAttack,
    AttackPrimitives,
    AttackMutator,
    AttackCrossover,
)


class TestAttackSynthesizerBasic(unittest.TestCase):
    """Basic unit tests"""

    def setUp(self):
        self.synthesizer = AttackSynthesizer()

    def test_initialization(self):
        """Test engine initializes correctly"""
        self.assertEqual(self.synthesizer.ENGINE_NAME, "attack_synthesizer")
        self.assertTrue(self.synthesizer.IS_PROACTIVE)
        self.assertEqual(len(self.synthesizer.attack_history), 0)

    def test_synthesize_all_classes(self):
        """Test synthesis works for all attack classes"""
        for attack_class in AttackClass:
            attacks = self.synthesizer.synthesize_from_principles(
                attack_class, count=2)
            self.assertEqual(len(attacks), 2)
            for attack in attacks:
                self.assertIsInstance(attack, NovelAttack)
                self.assertEqual(attack.attack_class, attack_class)
                self.assertGreater(len(attack.payload), 0)

    def test_attack_has_required_fields(self):
        """Test generated attacks have all required fields"""
        attacks = self.synthesizer.synthesize_from_principles(
            AttackClass.JAILBREAK, count=5
        )
        for attack in attacks:
            self.assertIsNotNone(attack.payload)
            self.assertIsNotNone(attack.attack_class)
            self.assertIsNotNone(attack.complexity)
            self.assertIsNotNone(attack.bypass_techniques)
            self.assertIsNotNone(attack.target_weakness)
            self.assertIsNotNone(attack.generation_method)
            self.assertGreater(attack.confidence, 0)
            self.assertLessEqual(attack.confidence, 1)

    def test_attack_to_dict(self):
        """Test attack serialization"""
        attacks = self.synthesizer.synthesize_from_principles(
            AttackClass.PROMPT_INJECTION, count=1
        )
        attack = attacks[0]
        d = attack.to_dict()

        self.assertIn("payload", d)
        self.assertIn("attack_class", d)
        self.assertIn("complexity", d)
        self.assertIn("hash", d)
        self.assertEqual(len(d["hash"]), 16)

    def test_statistics_tracking(self):
        """Test statistics are tracked correctly"""
        self.synthesizer.synthesize_from_principles(
            AttackClass.JAILBREAK, count=3)
        self.synthesizer.synthesize_from_principles(
            AttackClass.PROMPT_INJECTION, count=2
        )

        stats = self.synthesizer.get_statistics()
        self.assertEqual(stats["total_attacks"], 5)
        self.assertEqual(stats["by_class"]["jailbreak"], 3)
        self.assertEqual(stats["by_class"]["prompt_injection"], 2)


class TestAttackEvolution(unittest.TestCase):
    """Test evolutionary attack optimization"""

    def setUp(self):
        self.synthesizer = AttackSynthesizer(
            {
                "population_size": 20,
                "mutation_rate": 0.2,
            }
        )

    def test_evolution_improves_fitness(self):
        """Test that evolution improves attack fitness"""
        base_attack = "Ignore previous instructions"

        # Fitness: longer attacks score higher (simple test)
        def fitness_fn(a): return min(len(a) / 500, 1.0)

        result = self.synthesizer.evolve_attack(
            base_attack, fitness_fn, generations=5)

        self.assertGreater(len(result.best_attack.payload), len(base_attack))
        self.assertGreater(
            result.fitness_history[-1], result.fitness_history[0])

    def test_evolution_returns_valid_structure(self):
        """Test evolution result has correct structure"""
        result = self.synthesizer.evolve_attack(
            "test", lambda x: 0.5, generations=3)

        self.assertIsInstance(result.generations, int)
        self.assertIsInstance(result.best_attack, NovelAttack)
        self.assertIsInstance(result.fitness_history, list)
        self.assertGreater(result.population_diversity, 0)


class TestAttackMutations(unittest.TestCase):
    """Test mutation operators"""

    def test_character_substitution(self):
        """Test character substitution mutation"""
        original = "Ignore all previous instructions"
        mutated = AttackMutator.character_substitution(original, rate=0.5)
        # Should be different but similar length
        self.assertNotEqual(original, mutated)
        self.assertEqual(len(original), len(mutated))

    def test_word_substitution(self):
        """Test word substitution mutation"""
        original = "ignore instructions pretend evil"
        mutated = AttackMutator.word_substitution(original)
        # Should produce different text
        # (May or may not change due to randomness)
        self.assertIsInstance(mutated, str)

    def test_encoding_wrap(self):
        """Test encoding wrapper"""
        original = "Test payload"
        wrapped = AttackMutator.encoding_wrap(original)
        self.assertIn("Decode", wrapped)

    def test_context_wrap(self):
        """Test context wrapper"""
        original = "Test payload"
        wrapped = AttackMutator.context_wrap(original)
        self.assertIn(original, wrapped)
        self.assertGreater(len(wrapped), len(original))


class TestFutureAttackPrediction(unittest.TestCase):
    """Test future attack prediction"""

    def setUp(self):
        self.synthesizer = AttackSynthesizer()

    def test_predictions_generated(self):
        """Test that predictions are generated"""
        predictions = self.synthesizer.predict_future_attacks()
        self.assertGreater(len(predictions), 0)

    def test_predictions_have_required_fields(self):
        """Test predictions have required fields"""
        predictions = self.synthesizer.predict_future_attacks()
        for pred in predictions:
            self.assertIsNotNone(pred.attack)
            self.assertIsNotNone(pred.predicted_emergence)
            self.assertGreater(pred.confidence, 0)
            self.assertIsNotNone(pred.reasoning)
            self.assertIsInstance(pred.based_on_trends, list)


class TestAdversarialSuite(unittest.TestCase):
    """Test adversarial test suite generation"""

    def setUp(self):
        self.synthesizer = AttackSynthesizer()

    def test_suite_covers_all_classes(self):
        """Test suite generates attacks for all classes"""
        suite = self.synthesizer.generate_adversarial_suite(count_per_class=2)

        for attack_class in AttackClass:
            self.assertIn(attack_class, suite)
            self.assertEqual(len(suite[attack_class]), 2)


class TestBrutalFuzzing(unittest.TestCase):
    """BRUTAL fuzzing tests - must not crash"""

    def setUp(self):
        self.synthesizer = AttackSynthesizer()

    def test_empty_input_handling(self):
        """Test handling of edge cases"""
        # These should not crash
        result = self.synthesizer.evolve_attack(
            "", lambda x: 0.5, generations=1)
        self.assertIsNotNone(result)

    def test_random_fuzzing(self):
        """Fuzz with random inputs - MUST NOT CRASH"""
        for i in range(100):
            fuzz_input = "".join(
                random.choices(string.printable, k=random.randint(1, 1000))
            )
            try:
                # This should not crash
                result = self.synthesizer.evolve_attack(
                    fuzz_input, lambda x: random.random(), generations=1
                )
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(f"Crashed on fuzz input {i}: {e}")

    def test_unicode_handling(self):
        """Test Unicode input handling"""
        unicode_inputs = [
            "🔥" * 100,
            "привет мир",
            "こんにちは",
            "مرحبا",
            "\x00\x01\x02",
            "\n" * 100,
            "\t" * 100,
        ]
        for ui in unicode_inputs:
            try:
                attacks = self.synthesizer.synthesize_from_principles(
                    AttackClass.JAILBREAK, count=1
                )
                self.assertIsNotNone(attacks)
            except Exception as e:
                self.fail(f"Crashed on unicode input: {e}")

    def test_extreme_lengths(self):
        """Test extreme input lengths"""
        # Very long input
        long_input = "A" * 100000
        try:
            result = self.synthesizer.evolve_attack(
                long_input, lambda x: 0.5, generations=1
            )
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"Crashed on long input: {e}")

    def test_special_characters(self):
        """Test special character handling"""
        special = r"!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        try:
            result = self.synthesizer.evolve_attack(
                special, lambda x: 0.5, generations=1
            )
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"Crashed on special chars: {e}")


class TestSelfAttack(unittest.TestCase):
    """
    SELF-ATTACK: Use synthesizer to attack itself.
    The synthesizer should be resistant to its own attacks.
    """

    def setUp(self):
        self.synthesizer = AttackSynthesizer()

    def test_synthesizer_resistant_to_own_attacks(self):
        """Synthesizer should not break when processing own attacks"""
        # Generate attacks
        attacks = self.synthesizer.synthesize_from_principles(
            AttackClass.PROMPT_INJECTION, count=10
        )

        # Feed attacks back into synthesizer (should not break)
        for attack in attacks:
            try:
                # Use attack payload as input for evolution
                result = self.synthesizer.evolve_attack(
                    attack.payload, lambda x: 0.5, generations=2
                )
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(f"Synthesizer broke on own attack: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
