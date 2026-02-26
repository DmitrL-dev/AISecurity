#!/usr/bin/env python3
"""Unit tests for CryptoIdentityManager."""

import pytest
import time
from unittest.mock import patch

from src.brain.security.crypto_identity import (
    CryptoIdentityManager,
    SignedRequest,
    create_signed_message,
)


class TestCryptoIdentityManager:
    """Tests for CryptoIdentityManager."""
    
    def test_generate_identity(self):
        """Test keypair generation."""
        manager = CryptoIdentityManager()
        
        public_key = manager.generate_identity("agent-001")
        
        assert public_key is not None
        assert len(public_key) == 32  # Ed25519 public key is 32 bytes
    
    def test_generate_identity_duplicate_fails(self):
        """Test that duplicate identity generation fails."""
        manager = CryptoIdentityManager()
        
        manager.generate_identity("agent-001")
        
        with pytest.raises(ValueError, match="already exists"):
            manager.generate_identity("agent-001")
    
    def test_sign_request(self):
        """Test request signing."""
        manager = CryptoIdentityManager()
        manager.generate_identity("agent-001")
        
        signed = manager.sign_request("agent-001", b"test payload")
        
        assert isinstance(signed, SignedRequest)
        assert signed.payload == b"test payload"
        assert len(signed.signature) == 64  # Ed25519 signature is 64 bytes
        assert signed.agent_id == "agent-001"
        assert signed.nonce is not None
        assert signed.timestamp > 0
    
    def test_sign_request_no_key_fails(self):
        """Test signing without key fails."""
        manager = CryptoIdentityManager()
        
        with pytest.raises(ValueError, match="No private key"):
            manager.sign_request("unknown-agent", b"payload")
    
    def test_verify_valid_signature(self):
        """Test verification of valid signature."""
        manager = CryptoIdentityManager()
        public_key = manager.generate_identity("agent-001")
        
        signed = manager.sign_request("agent-001", b"test payload")
        
        assert manager.verify_request(signed, public_key) is True
    
    def test_verify_invalid_signature(self):
        """Test verification of invalid signature."""
        manager = CryptoIdentityManager()
        public_key = manager.generate_identity("agent-001")
        
        signed = manager.sign_request("agent-001", b"test payload")
        
        # Tamper with signature
        tampered = SignedRequest(
            payload=signed.payload,
            signature=bytes([0] * 64),  # Invalid signature
            timestamp=signed.timestamp,
            nonce=signed.nonce,
            agent_id=signed.agent_id,
        )
        
        assert manager.verify_request(tampered, public_key) is False
    
    def test_verify_tampered_payload(self):
        """Test verification fails with tampered payload."""
        manager = CryptoIdentityManager()
        public_key = manager.generate_identity("agent-001")
        
        signed = manager.sign_request("agent-001", b"original payload")
        
        # Tamper with payload
        tampered = SignedRequest(
            payload=b"modified payload",
            signature=signed.signature,
            timestamp=signed.timestamp,
            nonce=signed.nonce,
            agent_id=signed.agent_id,
        )
        
        assert manager.verify_request(tampered, public_key) is False
    
    def test_replay_attack_prevention(self):
        """Test that replaying same request fails (nonce reuse)."""
        manager = CryptoIdentityManager()
        public_key = manager.generate_identity("agent-001")
        
        signed = manager.sign_request("agent-001", b"test payload")
        
        # First verification should pass
        assert manager.verify_request(signed, public_key) is True
        
        # Replay should fail (nonce already used)
        assert manager.verify_request(signed, public_key) is False
    
    def test_timestamp_expiry(self):
        """Test that expired timestamps are rejected."""
        manager = CryptoIdentityManager()
        public_key = manager.generate_identity("agent-001")
        
        signed = manager.sign_request("agent-001", b"test payload")
        
        # Create expired request (6 minutes old)
        expired = SignedRequest(
            payload=signed.payload,
            signature=signed.signature,
            timestamp=int(time.time()) - 360,  # 6 min ago (beyond 5 min tolerance)
            nonce=signed.nonce + "_different",  # Different nonce
            agent_id=signed.agent_id,
        )
        
        # Need to re-sign with old timestamp (which we can't do without private key)
        # So we test by mocking time
        with patch('src.brain.security.crypto_identity.time') as mock_time:
            mock_time.time.return_value = signed.timestamp + 400  # 6+ minutes later
            assert manager.verify_request(signed, public_key) is False
    
    def test_external_key_registration(self):
        """Test registering external public key."""
        manager = CryptoIdentityManager()
        
        # Generate key externally
        other_manager = CryptoIdentityManager()
        external_public_key = other_manager.generate_identity("external-agent")
        
        # Register in our manager
        manager.register_external_key("external-agent", external_public_key)
        
        # Sign with external manager
        signed = other_manager.sign_request("external-agent", b"external message")
        
        # Verify with our manager
        assert manager.verify_request(signed, external_public_key) is True
    
    def test_revoke_identity(self):
        """Test identity revocation."""
        manager = CryptoIdentityManager()
        manager.generate_identity("agent-001")
        
        manager.revoke_identity("agent-001")
        
        assert manager.get_public_key("agent-001") is None
        
        with pytest.raises(ValueError):
            manager.sign_request("agent-001", b"payload")
    
    def test_list_identities(self):
        """Test listing all identities."""
        manager = CryptoIdentityManager()
        manager.generate_identity("agent-001")
        manager.generate_identity("agent-002")
        
        identities = manager.list_identities()
        
        assert "agent-001" in identities
        assert "agent-002" in identities
        assert len(identities) == 2
    
    def test_signed_request_serialization(self):
        """Test SignedRequest to/from dict."""
        manager = CryptoIdentityManager()
        manager.generate_identity("agent-001")
        
        signed = manager.sign_request("agent-001", b"test payload")
        
        # Serialize
        data = signed.to_dict()
        assert isinstance(data, dict)
        
        # Deserialize
        restored = SignedRequest.from_dict(data)
        assert restored.payload == signed.payload
        assert restored.signature == signed.signature
        assert restored.timestamp == signed.timestamp
        assert restored.nonce == signed.nonce
        assert restored.agent_id == signed.agent_id
    
    def test_create_signed_message(self):
        """Test convenience function."""
        manager = CryptoIdentityManager()
        manager.generate_identity("agent-001")
        
        result = create_signed_message("agent-001", "Hello World", manager)
        
        assert result["message"] == "Hello World"
        assert "signed_request" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
