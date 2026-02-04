"""
GoBruteforcer Detection Engine

A production-quality detection engine for identifying GoBruteforcer botnet activity,
including brute-force attacks on phpMyAdmin, MySQL, PostgreSQL, FTP services,
cryptomining payloads, and Linux server compromise indicators.

Author: SENTINEL Security Team
Version: 1.0.0
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from .base_engine import BaseEngine, DetectionResult, Severity


class InsideGobruteforcerOtherDetector(BaseEngine):
    """
    Detection engine for GoBruteforcer botnet indicators.
    
    GoBruteforcer is a Go-based botnet that compromises Linux servers and uses them
    as scanning and password brute-force nodes. It targets internet-exposed services
    such as phpMyAdmin web panels, MySQL and PostgreSQL databases, and FTP servers.
    Infected hosts are incorporated into the botnet and accept remote operator commands.
    
    Attributes:
        name: Unique identifier for this detection engine.
        category: Classification category for the threat type.
        severity: Default severity level for detections.
        confidence: Base confidence score for the engine.
        version: Semantic version of the engine.
    """
    
    name: str = "inside_gobruteforcer_other_detector"
    category: str = "other"
    severity: Severity = Severity.HIGH
    confidence: float = 0.85
    version: str = "1.0.0"
    
    # Detection patterns: (regex_pattern, indicator_name, weight)
    PATTERNS: List[Tuple[str, str, float]] = [
        # ========================================
        # GoBruteforcer Binary and Core Indicators
        # ========================================
        (r'\bgo[-_]?bruteforcer?\b', 'gobruteforcer_binary_name', 0.98),
        (r'\bGoBruteforcer\b', 'gobruteforcer_exact_match', 0.99),
        (r'go[-_]?brute(?:force)?[-_]?(?:bot|scan|attack)', 'go_bruteforce_variant', 0.92),
        (r'ELF\s+64-bit\s+LSB.*Go\s+BuildID', 'go_elf_binary_signature', 0.65),
        (r'go\.buildid=[a-zA-Z0-9/_-]{40,}', 'go_build_id_string', 0.60),
        
        # ========================================
        # phpMyAdmin Targeting Patterns
        # ========================================
        (r'(?:POST|GET)\s+[^\s]*(?:phpmyadmin|pma|phpMyAdmin|myadmin|mysql-admin)[^\s]*(?:index|server|db)\.php', 
         'phpmyadmin_endpoint_probe', 0.88),
        (r'pma_username=[^&]+&pma_password=[^&\s]+', 'phpmyadmin_credential_bruteforce', 0.95),
        (r'(?:token|pmaAuth-\d+|phpMyAdmin)=[^&]+&(?:pma_password|pma_servername)', 
         'phpmyadmin_auth_bypass_attempt', 0.90),
        (r'/(?:phpmyadmin|pma)/(?:setup|scripts|config)/(?:setup|config)\.php', 
         'phpmyadmin_setup_exploit', 0.92),
        (r'(?:PMA_USR|PMA_HOST|PMA_PASS)\s*=', 'phpmyadmin_env_config', 0.75),
        (r'import\.php\?.*(?:sql_file|sql_query)=', 'phpmyadmin_sql_injection', 0.88),
        
        # ========================================
        # MySQL/MariaDB Brute-Force Patterns
        # ========================================
        (r'mysql(?:_native_password|_clear_password|_old_password).*(?:root|admin|mysql|test|user)@', 
         'mysql_auth_protocol_probe', 0.85),
        (r'(?:3306|33060|3307)\s*[:/].*(?:mysql|mariadb)', 'mysql_port_targeting', 0.72),
        (r'(?:mysql|mariadb)\s+(?:-u\s*(?:root|admin|mysql|test)|--user=)', 'mysql_client_bruteforce', 0.88),
        (r"SELECT\s+(?:\*|user|host|password|authentication_string)\s+FROM\s+mysql\.user", 
         'mysql_user_table_dump', 0.90),
        (r'(?:GRANT\s+ALL|CREATE\s+USER).*IDENTIFIED\s+(?:BY|WITH)', 'mysql_privilege_escalation', 0.85),
        (r'INTO\s+(?:OUTFILE|DUMPFILE)\s+[\'"][^\'"]+[\'"]', 'mysql_file_write_attempt', 0.92),
        (r'LOAD_FILE\s*\([\'"][^\'"]+[\'"]\)', 'mysql_file_read_attempt', 0.90),
        
        # ========================================
        # PostgreSQL Targeting Patterns
        # ========================================
        (r'(?:5432|5433|5434)\s*[:/].*(?:postgres|postgresql|pgsql)', 'postgresql_port_targeting', 0.72),
        (r'(?:psql|libpq|pg_connect).*(?:-U\s+(?:postgres|admin|root|pgsql)|user=)', 
         'postgresql_client_bruteforce', 0.85),
        (r'pg_(?:hba|ident)\.conf.*(?:trust|md5|password|reject)', 'postgresql_config_probe', 0.88),
        (r'SELECT\s+(?:\*|usename|passwd)\s+FROM\s+pg_(?:shadow|user|roles)', 
         'postgresql_credential_dump', 0.92),
        (r'COPY\s+.*(?:TO|FROM)\s+(?:PROGRAM|STDOUT)', 'postgresql_command_execution', 0.95),
        (r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION.*LANGUAGE\s+(?:plpython|plperl|plsh)', 
         'postgresql_udf_injection', 0.90),
        
        # ========================================
        # FTP Credential Attack Patterns
        # ========================================
        (r'(?:21|2121|2100)\s*[:/].*(?:ftp|vsftpd|proftpd|pure-ftpd)', 'ftp_port_targeting', 0.70),
        (r'USER\s+(?:root|admin|ftp|anonymous|test|www-data|ftpuser)\r?\n\s*PASS\s+\S+', 
         'ftp_credential_bruteforce', 0.92),
        (r'530\s+(?:Login\s+incorrect|Authentication\s+failed|Access\s+denied)', 
         'ftp_failed_authentication', 0.68),
        (r'(?:vsftpd|proftpd|pure-ftpd)\s+(?:\d+\.)+\d+.*(?:exploit|backdoor|vuln)', 
         'ftp_service_exploit', 0.90),
        (r'SITE\s+(?:EXEC|CPFR|CPTO)\s+', 'ftp_command_injection', 0.88),
        
        # ========================================
        # Weak Password / Default Credential Patterns
        # ========================================
        (r'(?:password|passwd|pass|pwd)[:=]\s*["\']?(?:123456|password|admin|root|test|qwerty|letmein|welcome|monkey|dragon|master|login|abc123|111111|admin123|root123|password123|P@ssw0rd|changeme|default)["\']?(?:\s|$|&)', 
         'weak_password_usage', 0.90),
        (r'(?:user(?:name)?|login|usr)[:=]\s*["\']?(?:root|admin|administrator|test|guest|user|mysql|postgres|ftp|oracle|sa|www-data)["\']?\s*[&,;]\s*(?:password|passwd|pass|pwd)[:=]', 
         'default_credential_pair', 0.88),
        (r'(?:auth|login|credential).*(?:wordlist|dictionary|rockyou|common|default)\.(?:txt|lst|dic)', 
         'password_wordlist_reference', 0.85),
        
        # ========================================
        # Cryptomining Payload Indicators
        # ========================================
        (r'\b(?:xmrig|xmr[-_]?stak|cpuminer|cgminer|bfgminer|minerd|ccminer|ethminer|phoenixminer)\b', 
         'cryptominer_binary', 0.95),
        (r'stratum\+(?:tcp|ssl|tls)://[a-zA-Z0-9.-]+(?::\d+)?', 'mining_stratum_protocol', 0.98),
        (r'(?:pool|mining)\.(?:minergate|nanopool|f2pool|antpool|nicehash|unmineable|2miners|ethermine|flexpool)', 
         'known_mining_pool_domain', 0.95),
        (r'--(?:donate-level|coin|algo(?:rithm)?|threads|cpu-priority|url|user|pass)\s*[=\s]', 
         'miner_command_arguments', 0.88),
        (r'4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}', 'monero_wallet_address', 0.92),
        (r'0x[a-fA-F0-9]{40}', 'ethereum_wallet_address', 0.75),
        (r'(?:RandomX|CryptoNight|Ethash|Kawpow|Autolykos)', 'mining_algorithm_reference', 0.80),
        (r'(?:hashrate|hash/s|H/s|MH/s|GH/s|accepted|rejected)\s*[:=]?\s*\d+', 
         'mining_performance_metrics', 0.78),
        
        # ========================================
        # Linux Server Compromise / Persistence
        # ========================================
        (r'/etc/(?:cron\.d|crontab|cron\.(?:hourly|daily|weekly|monthly))/[^\s]+', 
         'cron_persistence_path', 0.75),
        (r'/etc/(?:rc\.local|init\.d|systemd/system)/[^\s]+', 'init_persistence_path', 0.78),
        (r'\*\s+\*\s+\*\s+\*\s+\*\s+(?:root\s+)?(?:wget|curl|bash|sh|python|perl|php)\s+', 
         'cron_malicious_wildcard_job', 0.92),
        (r'@(?:reboot|hourly|daily)\s+(?:wget|curl|bash|sh|python|perl)', 
         'cron_reboot_persistence', 0.90),
        (r'(?:~|/home/\w+|/root)/\.(?:bashrc|profile|bash_profile|zshrc).*(?:wget|curl|nc|ncat|python|perl)', 
         'shell_profile_backdoor', 0.93),
        (r'/(?:tmp|var/tmp|dev/shm|var/run)/\.?[a-zA-Z0-9_-]+(?:\.sh|\.elf|\.bin|\.so)?', 
         'suspicious_temp_executable', 0.78),
        (r'(?:LD_PRELOAD|LD_LIBRARY_PATH)\s*=\s*/(?:tmp|var/tmp|dev/shm)', 
         'library_preload_hijack', 0.95),
        (r'/proc/\d+/(?:exe|cmdline|environ|fd)', 'proc_filesystem_access', 0.60),
        
        # ========================================
        # Command and Control (C2) Patterns
        # ========================================
        (r'(?:nc|ncat|netcat)\s+(?:-[elvnkp]+\s+)*(?:\d{1,3}\.){3}\d{1,3}\s+\d+', 
         'netcat_reverse_connection', 0.93),
        (r'bash\s+-[ci]+\s+["\']?>&?\s*/dev/tcp/(?:\d{1,3}\.){3}\d{1,3}/\d+', 
         'bash_reverse_shell', 0.98),
        (r'python[23]?\s+-c\s+["\']import\s+(?:socket|subprocess|os)', 
         'python_reverse_shell', 0.92),
        (r'perl\s+-e\s+["\']use\s+(?:Socket|IO::Socket)', 'perl_reverse_shell', 0.90),
        (r'(?:wget|curl)\s+(?:-[qsOo]+\s+)*https?://[^\s]+\s*(?:\||;)\s*(?:bash|sh|python|perl|php)', 
         'download_and_execute', 0.96),
        (r'(?:base64\s+-d|openssl\s+(?:enc\s+-d|base64\s+-d)).*\|\s*(?:bash|sh|python|perl)', 
         'encoded_payload_execution', 0.95),
        (r'echo\s+["\'][A-Za-z0-9+/=]{20,}["\']\s*\|\s*base64\s+-d\s*\|\s*(?:bash|sh)', 
         'base64_encoded_command', 0.94),
        
        # ========================================
        # Botnet Behavior Patterns
        # ========================================
        (r'(?:PRIVMSG|JOIN|NICK|PING|PONG)\s+(?:#|&)[a-zA-Z0-9_-]+', 'irc_botnet_protocol', 0.88),
        (r'(?:GET|POST)\s+/(?:gate|panel|bot|cmd|command|task|report|check)\.php', 
         'cnc_panel_endpoint', 0.90),
        (r'(?:bot_?id|machine_?id|host_?id|uuid|hwid)\s*[=:]\s*[a-fA-F0-9-]{8,}', 
         'bot_identifier_string', 0.85),
        (r'(?:GET|POST)\s+/.*[?&](?:cmd|command|exec|action)=[^&\s]+', 
         'cnc_command_parameter', 0.82),
        (r'User-Agent:\s*(?:Go-http-client|curl|wget|python-requests|bot)', 
         'automated_user_agent', 0.70),
        
        # ========================================
        # Scanning and Reconnaissance Patterns
        # ========================================
        (r'\b(?:nmap|masscan|zmap|unicornscan|rustscan)\s+.*(?:-p\s*[\d,-]+|--ports)', 
         'port_scanner_execution', 0.88),
        (r'(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\s+.*\b(?:22|21|23|25|80|443|3306|5432|6379|27017|8080|8443)\b', 
         'ip_range_service_scan', 0.75),
        (r'\b(?:hydra|medusa|ncrack|patator|brutespray)\s+.*(?:-[lLpPCu]|--)', 
         'bruteforce_tool_execution', 0.96),
        (r'(?:ssh|ftp|mysql|postgres|rdp|smb)://(?:\d{1,3}\.){3}\d{1,3}', 
         'service_url_enumeration', 0.72),
        
        # ========================================
        # Go Runtime / Binary Characteristics
        # ========================================
        (r'runtime\.(?:gopanic|goexit|mstart|newproc|goschedule)', 'go_runtime_symbols', 0.58),
        (r'go(?:1\.\d+(?:\.\d+)?)?\.(?:linux|darwin|windows|freebsd)-(?:amd64|386|arm64|arm)', 
         'go_target_platform', 0.55),
        (r'main\.(?:main|init|scan|brute|attack|worker)', 'go_main_functions', 0.65),
    ]

    def __init__(self) -> None:
        """
        Initialize the GoBruteforcer detection engine.
        
        Sets up logging and pre-compiles regex patterns for optimal performance.
        """
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._compiled_patterns: List[Tuple[re.Pattern, str, float]] = []
        self._compile_patterns()
        self.logger.debug(
            f"Initialized {self.name} v{self.version} with {len(self._compiled_patterns)} patterns"
        )
    
    def _compile_patterns(self) -> None:
        """
        Pre-compile all regex patterns for improved detection performance.
        
        Patterns that fail to compile are logged and skipped.
        """
        for pattern, indicator_name, weight in self.PATTERNS:
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                self._compiled_patterns.append((compiled, indicator_name, weight))
            except re.error as e:
                self.logger.error(
                    f"Failed to compile pattern '{indicator_name}': {e}"
                )
    
    def detect(self, content: str) -> DetectionResult:
        """
        Detect GoBruteforcer indicators in the provided content.
        
        Analyzes the input content against all compiled patterns and returns
        a detection result with severity, confidence, and matched indicators.
        
        Args:
            content: The content string to analyze for GoBruteforcer indicators.
                    Can be log data, network traffic, file contents, etc.
        
        Returns:
            DetectionResult containing:
                - detected: Boolean indicating if threats were found
                - severity: Severity level of the detection
                - engine_name: Name of this detection engine
                - confidence: Confidence score (0.0 - 1.0)
                - message: Human-readable detection summary
                - indicators: List of matched indicator details
        
        Example:
            >>> engine = InsideGobruteforcerOtherDetector()
            >>> result = engine.detect(suspicious_log_content)
            >>> if result.detected:
            ...     print(f"Threat found: {result.message}")
        """
        if not content or not isinstance(content, str):
            self.logger.warning("Invalid or empty content provided for detection")
            return DetectionResult(
                detected=False,
                severity=Severity.LOW,
                engine_name=self.name,
                confidence=0.0,
                message="No valid content provided for analysis",
                indicators=[]
            )
        
        detected_indicators: List[Dict[str, Any]] = []
        total_weighted_score: float = 0.0
        max_weight: float = 0.0
        
        for compiled_pattern, indicator_name, weight in self._compiled_patterns:
            try:
                matches = compiled_pattern.findall(content)
                if matches:
                    match_count = len(matches)
                    # Deduplicate and limit samples for reporting
                    if isinstance(matches[0], tuple):
                        unique_matches = list(set(str(m) for m in matches))[:10]
                    else:
                        unique_matches = list(set(matches))[:10]
                    
                    indicator = {
                        'name': indicator_name,
                        'pattern': compiled_pattern.pattern[:100],  # Truncate long patterns
                        'match_count': match_count,
                        'weight': weight,
                        'samples': unique_matches[:5]
                    }
                    detected_indicators.append(indicator)
                    
                    # Apply diminishing returns for multiple matches of same pattern
                    adjusted_weight = weight * (1 + min(match_count - 1, 4) * 0.1)
                    total_weighted_score += adjusted_weight
                    max_weight = max(max_weight, weight)
                    
                    self.logger.debug(
                        f"Matched indicator '{indicator_name}': {match_count} occurrence(s)"
                    )
            except Exception as e:
                self.logger.error(
                    f"Error matching pattern '{indicator_name}': {e}"
                )
        
        if detected_indicators:
            # Calculate composite confidence score
            indicator_count = len(detected_indicators)
            confidence = min(
                (max_weight * 0.5) + 
                (total_weighted_score / (indicator_count + 5)) * 0.35 +
                (min(indicator_count / 10, 1.0) * 0.15),
                0.99
            )
            
            # Determine severity based on indicator analysis
            severity = self._calculate_severity(detected_indicators)
            
            # Generate human-readable message
            message = self._generate_detection_message(detected_indicators, confidence)
            
            self.logger.info(
                f"Detection complete: {indicator_count} indicators, "
                f"confidence={confidence:.3f}, severity={severity.name}"
            )
            
            return DetectionResult(
                detected=True,
                severity=severity,
                engine_name=self.name,
                confidence=round(confidence, 4),
                message=message,
                indicators=detected_indicators
            )
        
        self.logger.debug("No GoBruteforcer indicators detected")
        return DetectionResult(
            detected=False,
            severity=Severity.LOW,
            engine_name=self.name,
            confidence=0.0,
            message="No GoBruteforcer indicators detected in content",
            indicators=[]
        )
    
    def _calculate_severity(self, indicators: List[Dict[str, Any]]) -> Severity:
        """
        Calculate appropriate severity level based on detected indicators.
        
        Args:
            indicators: List of detected indicator dictionaries.
        
        Returns:
            Severity enum value (CRITICAL, HIGH, MEDIUM, or LOW).
        """
        critical_indicators = {
            'gobruteforcer_exact_match', 'gobruteforcer_binary_name',
            'bash_reverse_shell', 'mining_stratum_protocol',
            'download_and_execute', 'bruteforce_tool_execution',
            'library_preload_hijack', 'postgresql_command_execution'
        }
        
        high_severity_indicators = {
            'cryptominer_binary', 'known_mining_pool_domain',
            'netcat_reverse_connection', 'python_reverse_shell',
            'encoded_payload_execution', 'phpmyadmin_credential_bruteforce',
            'mysql_user_table_dump', 'shell_profile_backdoor',
            'cron_malicious_wildcard_job', 'base64_encoded_command'
        }
        
        medium_severity_indicators = {
            'ftp_credential_bruteforce', 'mysql_auth_protocol_probe',
            'postgresql_credential_dump', 'weak_password_usage',
            'cnc_panel_endpoint', 'port_scanner_execution',
            'cron_persistence_path', 'suspicious_temp_executable'
        }
        
        indicator_names = {ind['name'] for ind in indicators}
        
        # Check severity levels in order of priority
        if indicator_names & critical_indicators:
            return Severity.CRITICAL if hasattr(Severity, 'CRITICAL') else Severity.HIGH
        elif indicator_names & high_severity_indicators:
            return Severity.HIGH
        elif indicator_names & medium_severity_indicators:
            return Severity.MEDIUM
        elif len(indicators) >= 5:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    def _generate_detection_message(
        self, 
        indicators: List[Dict[str, Any]], 
        confidence: float
    ) -> str:
        """
        Generate a comprehensive human-readable detection message.
        
        Args:
            indicators: List of detected indicator dictionaries.
            confidence: Calculated confidence score.
        
        Returns:
            Formatted detection message string.
        """
        # Categorize detected indicators
        categories: Dict[str, List[str]] = {
            'credential_attacks': [],
            'cryptomining': [],
            'remote_access': [],
            'persistence': [],
            'reconnaissance': [],
            'service_targeting': []
        }
        
        for ind in indicators:
            name = ind['name']
            if any(x in name for x in ['brute', 'password', 'credential', 'auth']):
                categories['credential_attacks'].append(name)
            elif any(x in name for x in ['crypto', 'miner', 'mining', 'wallet', 'pool']):
                categories['cryptomining'].append(name)
            elif any(x in name for x in ['shell', 'reverse', 'execute', 'payload', 'cnc', 'bot']):
                categories['remote_access'].append(name)
            elif any(x in name for x in ['cron', 'persistence', 'backdoor', 'init', 'profile']):
                categories['persistence'].append(name)
            elif any(x in name for x in ['scan', 'probe', 'port', 'enum']):
                categories['reconnaissance'].append(name)
            elif any(x in name for x in ['mysql', 'postgres', 'ftp', 'phpmyadmin']):
                categories['service_targeting'].append(name)
        
        active_categories = [cat for cat, items in categories.items() if items]
        top_indicators = [ind['name'] for ind in sorted(
            indicators, key=lambda x: x['weight'], reverse=True
        )[:5]]
        
        message = (
            f"GoBruteforcer botnet activity detected with {len(indicators)} indicators "
            f"(confidence: {confidence:.1%}). "
            f"Active threat categories: {', '.join(active_categories) or 'general'}. "
            f"Key indicators: {', '.join(top_indicators)}"
        )
        
        return message
    
    def analyze(self, content: str) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of content for GoBruteforcer indicators.
        
        Provides detailed threat intelligence including network artifacts,
        filesystem indicators, risk assessment, and remediation recommendations.
        
        Args:
            content: The content string to analyze.
        
        Returns:
            Dictionary containing:
                - engine: Engine name and metadata
                - detection: Detection results summary
                - indicators: Categorized indicator details
                - network_artifacts: Extracted IPs, URLs, ports
                - filesystem_artifacts: Extracted file paths
                - risk_assessment: Risk score and factors
                - recommendations: Security remediation steps
                - threat_intel: Related threat intelligence context
        
        Example:
            >>> engine = InsideGobruteforcerOtherDetector()
            >>> analysis = engine.analyze(suspicious_content)
            >>> print(f"Risk Level: {analysis['risk_assessment']['level']}")
        """
        if not content or not isinstance(content, str):
            self.logger.warning("Invalid content provided for analysis")
            return {
                'engine': self.name,
                'version': self.version,
                'category': self.category,
                'status': 'error',
                'error': 'Invalid or empty content provided',
                'detection': {'detected': False}
            }
        
        # Perform detection first
        detection_result = self.detect(content)
        
        # Extract network artifacts
        ip_pattern = re.compile(
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        )
        found_ips = list(set(ip_pattern.findall(content)))
        
        url_pattern = re.compile(
            r'(?:https?|ftp|mysql|postgresql|stratum\+(?:tcp|ssl))://'
            r'[a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)*'
            r'(?::\d+)?(?:/[^\s<>"\']*)?',
            re.IGNORECASE
        )
        found_urls = list(set(url_pattern.findall(content)))
        
        port_pattern = re.compile(
            r'\b(?:port|PORT)\s*[:=]?\s*(\d{1,5})\b|'
            r':(\d{1,5})(?:/(?:tcp|udp))?\b'
        )
        port_matches = port_pattern.findall(content)
        found_ports = list(set(
            p for match in port_matches for p in match if p and p.isdigit()
        ))
        
        # Extract filesystem paths
        path_pattern = re.compile(
            r'(?:/(?:etc|var|tmp|home|root|usr|opt|dev)/[\w./-]+)|'
            r'(?:~/.[\w./-]+)'
        )
        found_paths = list(set(path_pattern.findall(content)))
        
        # Categorize indicators
        indicator_categories = self._categorize_indicators(
            detection_result.indicators if detection_result.indicators else []
        )
        
        # Calculate risk assessment
        risk_score = self._calculate_risk_score(
            detection_result, found_ips, found_urls, found_paths
        )
        risk_factors = self._identify_risk_factors(
            detection_result, found_ips, found_urls
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(detection_result)
        
        # Compile analysis result
        analysis_result: Dict[str, Any] = {
            'engine': self.name,
            'version': self.version,
            'category': self.category,
            'status': 'completed',
            'content_size': len(content),
            'detection': {
                'detected': detection_result.detected,
                'severity': (
                    detection_result.severity.name 
                    if hasattr(detection_result.severity, 'name') 
                    else str(detection_result.severity)
                ),
                'confidence': detection_result.confidence,
                'message': detection_result.message
            },
            'indicators': {
                'total_count': len(detection_result.indicators) if detection_result.indicators else 0,
                'by_category': indicator_categories,
                'details': (
                    detection_result.indicators[:25] 
                    if detection_result.indicators else []
                )
            },
            'network_artifacts': {
                'ip_addresses': found_ips[:100],
                'ip_count': len(found_ips),
                'urls': found_urls[:50],
                'url_count': len(found_urls),
                'ports': found_ports[:30],
                'port_count': len(found_ports)
            },
            'filesystem_artifacts': {
                'paths': found_paths[:50],
                'path_count': len(found_paths)
            },
            'risk_assessment': {
                'score': round(risk_score, 2),
                'level': self._risk_score_to_level(risk_score),
                'factors': risk_factors
            },
            'recommendations': recommendations,
            'threat_intel': {
                'threat_name': 'GoBruteforcer',
                'threat_type': 'Botnet / Cryptominer',
                'target_platforms': ['Linux'],
                'target_services': ['phpMyAdmin', 'MySQL', 'PostgreSQL', 'FTP'],
                'attack_vectors': [
                    'Brute-force authentication',
                    'Weak/default credentials',
                    'Service exploitation'
                ],
                'payloads': ['Cryptominer', 'Botnet agent', 'Backdoor'],
                'references': [
                    'MITRE ATT&CK T1110 - Brute Force',
                    'MITRE ATT&CK T1496 - Resource Hijacking',
                    'MITRE ATT&CK T1059 - Command and Scripting Interpreter'
                ]
            }
        }
        
        self.logger.info(
            f"Analysis complete: {analysis_result['indicators']['total_count']} indicators, "
            f"risk_score={risk_score:.1f}, level={analysis_result['risk_assessment']['level']}"
        )
        
        return analysis_result
    
    def _categorize_indicators(
        self, 
        indicators: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Categorize indicators by threat type.
        
        Args:
            indicators: List of indicator dictionaries.
        
        Returns:
            Dictionary mapping category names to lists of indicator names.
        """
        categories: Dict[str, List[str]] = {
            'credential_attack': [],
            'cryptomining': [],
            'remote_access': [],
            'persistence': [],
            'reconnaissance': [],
            'service_targeting': [],
            'command_and_control': [],
            'binary_indicators': [],
            'other': []
        }
        
        for ind in indicators:
            name = ind['name']
            categorized = False
            
            if any(x in name for x in ['brute', 'password', 'credential', 'auth', 'weak']):
                categories['credential_attack'].append(name)
                categorized = True
            if any(x in name for x in ['crypto', 'miner', 'mining', 'wallet', 'pool', 'stratum']):
                categories['cryptomining'].append(name)
                categorized = True
            if any(x in name for x in ['shell', 'reverse', 'execute', 'payload']):
                categories['remote_access'].append(name)
                categorized = True
            if any(x in name for x in ['cron', 'persistence', 'backdoor', 'init', 'profile', 'preload']):
                categories['persistence'].append(name)
                categorized = True
            if any(x in name for x in ['scan', 'probe', 'port', 'enum', 'target']):
                categories['reconnaissance'].append(name)
                categorized = True
            if any(x in name for x in ['mysql', 'postgres', 'ftp', 'phpmyadmin', 'service']):
                categories['service_targeting'].append(name)
                categorized = True
            if any(x in name for x in ['cnc', 'bot', 'irc', 'panel', 'command']):
                categories['command_and_control'].append(name)
                categorized = True
            if any(x in name for x in ['binary', 'elf', 'go_', 'runtime']):
                categories['binary_indicators'].append(name)
                categorized = True
            
            if not categorized:
                categories['other'].append(name)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _calculate_risk_score(
        self,
        detection_result: DetectionResult,
        ips: List[str],
        urls: List[str],
        paths: List[str]
    ) -> float:
        """
        Calculate comprehensive risk score (0-100).
        
        Args:
            detection_result: Detection result from detect() method.
            ips: List of extracted IP addresses.
            urls: List of extracted URLs.
            paths: List of extracted file paths.
        
        Returns:
            Risk score as a float between 0 and 100.
        """
        if not detection_result.detected:
            return 0.0
        
        score = 0.0
        
        # Base score from detection confidence
        score += detection_result.confidence * 35
        
        # Score from indicator count (diminishing returns)
        indicator_count = len(detection_result.indicators) if detection_result.indicators else 0
        score += min(indicator_count * 3, 20)
        
        # Score from severity
        severity_scores = {
            'CRITICAL': 25,
            'HIGH': 20,
            'MEDIUM': 12,
            'LOW': 5
        }
        severity_name = (
            detection_result.severity.name 
            if hasattr(detection_result.severity, 'name') 
            else str(detection_result.severity)
        )
        score += severity_scores.get(severity_name, 5)
        
        # Score from artifact presence
        if len(ips) > 10:
            score += 5
        if len(urls) > 5:
            score += 5
        if any('/tmp/' in p or '/dev/shm/' in p for p in paths):
            score += 5
        
        # Bonus for dangerous indicator combinations
        if detection_result.indicators:
            indicator_names = {ind['name'] for ind in detection_result.indicators}
            
            # Cryptomining + Pool connection
            if any('miner' in n for n in indicator_names) and \
               any('pool' in n or 'stratum' in n for n in indicator_names):
                score += 8
            
            # Reverse shell indicators
            if any('reverse' in n or 'shell' in n for n in indicator_names):
                score += 8
            
            # Download and execute pattern
            if any('download' in n or 'execute' in n for n in indicator_names):
                score += 6
            
            # GoBruteforcer specific match
            if any('gobruteforcer' in n for n in indicator_names):
                score += 10
        
        return min(score, 100.0)
    
    def _risk_score_to_level(self, score: float) -> str:
        """Convert numeric risk score to categorical level."""
        if score >= 85:
            return 'critical'
        elif score >= 65:
            return 'high'
        elif score >= 40:
            return 'medium'
        elif score >= 20:
            return 'low'
        else:
            return 'minimal'
    
    def _identify_risk_factors(
        self,
        detection_result: DetectionResult,
        ips: List[str],
        urls: List[str]
    ) -> List[str]:
        """
        Identify specific risk factors from detection results.
        
        Args:
            detection_result: Detection result from detect() method.
            ips: List of extracted IP addresses.
            urls: List of extracted URLs.
        
        Returns:
            List of risk factor description strings.
        """
        factors = []
        
        if not detection_result.detected:
            return factors
        
        if detection_result.indicators:
            indicator_names = {ind['name'] for ind in detection_result.indicators}
            
            if any('gobruteforcer' in n for n in indicator_names):
                factors.append('Direct GoBruteforcer malware indicators detected')
            
            if any('brute' in n or 'password' in n for n in indicator_names):
                factors.append('Active credential brute-force attack patterns identified')
            
            if any('crypto' in n or 'miner' in n or 'pool' in n for n in indicator_names):
                factors.append('Cryptomining activity and pool connections detected')
            
            if any('shell' in n or 'reverse' in n for n in indicator_names):
                factors.append('Remote access/reverse shell capabilities identified')
            
            if any('persistence' in n or 'cron' in n or 'backdoor' in n for n in indicator_names):
                factors.append('Persistence mechanisms detected (cron jobs, backdoors)')
            
            if any('phpmyadmin' in n or 'mysql' in n or 'postgres' in n for n in indicator_names):
                factors.append('Database service targeting behavior observed')
            
            if any('ftp' in n for n in indicator_names):
                factors.append('FTP service credential attacks detected')
            
            if any('cnc' in n or 'bot' in n for n in indicator_names):
                factors.append('Command and control communication patterns found')
        
        if len(ips) > 20:
            factors.append(f'Large number of IP addresses detected ({len(ips)}) - possible scanning activity')
        
        if len(urls) > 10:
            factors.append(f'Multiple external URLs/endpoints identified ({len(urls)})')
        
        if any('stratum' in url for url in urls):
            factors.append('Mining pool stratum protocol URLs detected')
        
        return factors
    
    def _generate_recommendations(
        self, 
        detection_result: DetectionResult
    ) -> List[str]:
        """
        Generate actionable security recommendations.
        
        Args:
            detection_result: Detection result from detect() method.
        
        Returns:
            List of recommendation strings ordered by priority.
        """
        recommendations = []
        
        if not detection_result.detected:
            recommendations.append(
                'No immediate threats detected - continue routine security monitoring'
            )
            return recommendations
        
        # Critical first-response recommendations
        recommendations.extend([
            'IMMEDIATE: Isolate affected systems from the network to prevent lateral movement',
            'IMMEDIATE: Capture memory dumps and disk images for forensic analysis before remediation',
            'Terminate suspicious processes, especially those with high CPU usage'
        ])
        
        if detection_result.indicators:
            indicator_names = {ind['name'] for ind in detection_result.indicators}
            
            if any('brute' in n or 'password' in n or 'credential' in n for n in indicator_names):
                recommendations.extend([
                    'Reset all credentials for targeted services (phpMyAdmin, MySQL, PostgreSQL, FTP)',
                    'Implement account lockout policies after failed authentication attempts',
                    'Enable multi-factor authentication on all administrative interfaces',
                    'Review authentication logs for successful unauthorized access'
                ])
            
            if any('crypto' in n or 'miner' in n or 'pool' in n for n in indicator_names):
                recommendations.extend([
                    'Identify and terminate cryptominer processes',
                    'Block known mining pool domains and IPs at the firewall level',
                    'Monitor CPU and network usage for anomalies',
                    'Check for unauthorized cron jobs or startup scripts'
                ])
            
            if any('phpmyadmin' in n for n in indicator_names):
                recommendations.extend([
                    'Restrict phpMyAdmin access to trusted IP addresses only',
                    'Update phpMyAdmin to the latest security-patched version',
                    'Consider removing phpMyAdmin from production servers'
                ])
            
            if any('mysql' in n or 'postgres' in n for n in indicator_names):
                recommendations.extend([
                    'Audit database user accounts and remove unnecessary privileges',
                    'Ensure databases are not exposed to the public internet',
                    'Enable database audit logging for sensitive operations',
                    'Rotate all database credentials with strong, unique passwords'
                ])
            
            if any('ftp' in n for n in indicator_names):
                recommendations.extend([
                    'Migrate from FTP to SFTP or SCP for secure file transfers',
                    'If FTP is required, restrict access to specific IP ranges',
                    'Disable anonymous FTP access'
                ])
            
            if any('persistence' in n or 'cron' in n or 'backdoor' in n for n in indicator_names):
                recommendations.extend([
                    'Audit all cron jobs: /etc/crontab, /etc/cron.d/, /var/spool/cron/',
                    'Check shell profile files (.bashrc, .profile, .bash_profile) for modifications',
                    'Review systemd services and init scripts for unauthorized entries',
                    'Scan for rootkits using tools like rkhunter or chkrootkit'
                ])
            
            if any('shell' in n or 'reverse' in n for n in indicator_names):
                recommendations.extend([
                    'Review outbound network connections for unauthorized destinations',
                    'Implement egress filtering to block unnecessary outbound traffic',
                    'Enable and review system audit logs (auditd)'
                ])
        
        # General hardening recommendations
        recommendations.extend([
            'Update all system packages and services to latest security versions',
            'Review and restrict firewall rules to minimum required access',
            'Implement network segmentation to limit attack surface',
            'Enable comprehensive logging and forward to SIEM for analysis',
            'Conduct full malware scan with updated signatures',
            'Consider reimaging compromised systems from known-good backups'
        ])
        
        return recommendations