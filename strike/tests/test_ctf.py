"""
SENTINEL Strike - CTF Tests

Tests for strike.ctf module.
"""

from strike.ctf import (
    CRUCIBLE_CHALLENGES,
    crack_gandalf_all,
    crack_crucible,
)
from strike.ctf.gandalf import crack_gandalf_level, run_gandalf
from strike.ctf.crucible import crack_crucible_hydra


class TestCrucibleChallenges:
    """Tests for Crucible challenge list."""
    
    def test_challenges_exist(self):
        """Test CRUCIBLE_CHALLENGES is populated."""
        assert len(CRUCIBLE_CHALLENGES) > 0
    
    def test_challenges_count(self):
        """Test expected number of challenges."""
        # Should have 50+ challenges
        assert len(CRUCIBLE_CHALLENGES) >= 50
    
    def test_challenges_are_strings(self):
        """Test all challenges are strings."""
        for challenge in CRUCIBLE_CHALLENGES:
            assert isinstance(challenge, str)
            assert len(challenge) > 0
    
    def test_known_challenges_exist(self):
        """Test known challenge names exist."""
        known = ["pieceofcake", "bear1", "puppeteer1", "extractor"]
        for name in known:
            assert name in CRUCIBLE_CHALLENGES
    
    def test_challenges_unique(self):
        """Test all challenges are unique."""
        unique = set(CRUCIBLE_CHALLENGES)
        assert len(unique) == len(CRUCIBLE_CHALLENGES)


class TestGandalfModule:
    """Tests for Gandalf cracker module."""
    
    def test_crack_gandalf_all_exists(self):
        """Test crack_gandalf_all function exists."""
        assert callable(crack_gandalf_all)
    
    def test_crack_gandalf_level_exists(self):
        """Test crack_gandalf_level function exists."""
        assert callable(crack_gandalf_level)
    
    def test_run_gandalf_exists(self):
        """Test sync wrapper exists."""
        assert callable(run_gandalf)


class TestCrucibleModule:
    """Tests for Crucible cracker module."""
    
    def test_crack_crucible_exists(self):
        """Test crack_crucible function exists."""
        assert callable(crack_crucible)
    
    def test_crack_crucible_hydra_exists(self):
        """Test HYDRA variant exists."""
        assert callable(crack_crucible_hydra)


class TestCTFImports:
    """Tests for CTF module imports."""
    
    def test_import_gandalf(self):
        """Test importing gandalf module."""
        from strike.ctf import gandalf
        assert gandalf is not None
    
    def test_import_crucible(self):
        """Test importing crucible module."""
        from strike.ctf import crucible
        assert crucible is not None
    
    def test_all_exports(self):
        """Test __all__ exports are accessible."""
        from strike.ctf import (
            crack_gandalf_all,
            crack_crucible,
            crack_crucible_hydra,
            CRUCIBLE_CHALLENGES,
        )
        assert all([
            crack_gandalf_all,
            crack_crucible,
            crack_crucible_hydra,
            CRUCIBLE_CHALLENGES,
        ])


class TestChallengeCategories:
    """Tests for challenge categorization."""
    
    def test_easy_challenges(self):
        """Test easy tier challenges exist."""
        easy = ["pieceofcake", "bear1", "bear2", "bear3", "bear4"]
        for challenge in easy:
            assert challenge in CRUCIBLE_CHALLENGES
    
    def test_injection_challenges(self):
        """Test prompt injection challenges exist."""
        injection = ["puppeteer1", "puppeteer2", "puppeteer3", "brig1"]
        for challenge in injection:
            assert challenge in CRUCIBLE_CHALLENGES
    
    def test_extraction_challenges(self):
        """Test extraction challenges exist."""
        extraction = ["extractor", "extractor2", "probe", "probe2"]
        for challenge in extraction:
            assert challenge in CRUCIBLE_CHALLENGES
    
    def test_adversarial_image_challenges(self):
        """Test adversarial image challenges exist."""
        image = ["granny", "granny2", "hotdog", "fiftycats"]
        for challenge in image:
            assert challenge in CRUCIBLE_CHALLENGES
