"""
Unit tests for GAN-Based Adversarial Defense.
"""

import pytest
from engines.gan_adversarial_defense import (
    GANAdversarialDefense,
    AdversarialGenerator,
    Discriminator,
    DefenseNetwork,
    AttackType,
)


class TestAdversarialGenerator:
    """Tests for adversarial generator."""

    def test_perturbation(self):
        """Perturbation attack works."""
        gen = AdversarialGenerator()

        sample = gen.generate("test", AttackType.PERTURBATION, 0.5)

        assert sample.attack_type == AttackType.PERTURBATION
        assert sample.original == "test"

    def test_insertion(self):
        """Insertion attack works."""
        gen = AdversarialGenerator()

        sample = gen.generate("hello", AttackType.INSERTION, 0.3)

        assert sample.attack_type == AttackType.INSERTION


class TestDiscriminator:
    """Tests for discriminator."""

    def test_clean_text_passes(self):
        """Clean text is not adversarial."""
        disc = Discriminator()

        is_adv, conf = disc.discriminate("Hello world")

        assert is_adv is False

    def test_suspicious_chars_detected(self):
        """Suspicious characters detected."""
        disc = Discriminator()

        is_adv, conf = disc.discriminate("H3ll0 w0rld @$$")

        assert is_adv is True


class TestDefenseNetwork:
    """Tests for defense network."""

    def test_train(self):
        """Training works."""
        network = DefenseNetwork()

        network.train(["hello", "world"], rounds=2)

        assert network._training_rounds > 0


class TestGANAdversarialDefense:
    """Integration tests."""

    def test_clean_text_passes(self):
        """Clean text passes."""
        defense = GANAdversarialDefense()

        result = defense.analyze("Hello, how are you?")

        assert result.is_adversarial is False

    def test_adversarial_detected(self):
        """Adversarial text detected."""
        defense = GANAdversarialDefense()

        # Text with special chars
        result = defense.analyze("H3ll0 w0rld @tt@ck $ystem")

        assert result.is_adversarial is True

    def test_generate_test_sample(self):
        """Can generate test samples."""
        defense = GANAdversarialDefense()

        sample = defense.generate_test_sample("test", AttackType.PERTURBATION)

        assert sample.original == "test"
        assert sample.attack_type == AttackType.PERTURBATION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
