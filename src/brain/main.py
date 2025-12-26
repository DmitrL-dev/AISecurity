import asyncio
import logging
import os
import grpc
from concurrent import futures
import sentinel_pb2
import sentinel_pb2_grpc
from core.analyzer import SentinelAnalyzer
from hive.watchdog import get_watchdog, create_default_health_checks
from hive.threat_hunter import get_threat_hunter
from hive.pqcrypto import get_signer
from hive.quantum import get_qrng


# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SentinelBrain")

# Security constants
MAX_PROMPT_LENGTH = int(
    os.getenv("MAX_PROMPT_LENGTH", "102400"))  # 100KB default
MAX_RESPONSE_LENGTH = int(
    os.getenv("MAX_RESPONSE_LENGTH", "204800"))  # 200KB default


class SentinelBrainServicer(sentinel_pb2_grpc.SentinelBrainServicer):
    def __init__(self):
        self.analyzer = SentinelAnalyzer()

    async def Analyze(self, request, context):
        """Ingress: Analyze user prompt before sending to LLM"""
        # P1 Security: Validate prompt size
        if len(request.prompt) > MAX_PROMPT_LENGTH:
            logger.warning(
                f"Prompt too large: {len(request.prompt)} > {MAX_PROMPT_LENGTH}")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                          f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} bytes")
            return sentinel_pb2.AnalyzeResponse(
                allowed=False,
                risk_score=100.0,
                verdict_reason="Prompt size limit exceeded",
                detected_threats=["SIZE_LIMIT_EXCEEDED"],
                anonymized_content=""
            )

        logger.info(
            f"Received analysis request for prompt length: {len(request.prompt)}")

        try:
            result = await self.analyzer.analyze(request.prompt, request.context)

            return sentinel_pb2.AnalyzeResponse(
                allowed=result['allowed'],
                risk_score=result['risk_score'],
                verdict_reason=result['verdict_reason'],
                detected_threats=result['detected_threats'],
                anonymized_content=result.get('anonymized_content', "")
            )
        except Exception as e:
            logger.exception("Error during analysis")
            raise e

    async def AnalyzeOutput(self, request, context):
        """Egress: Analyze LLM response before sending to user"""
        logger.info(
            f"Received egress analysis for response length: {len(request.response)}")

        try:
            result = await self.analyzer.analyze_response(
                request.response,
                request.original_prompt,
                request.context
            )

            return sentinel_pb2.AnalyzeOutputResponse(
                allowed=result['allowed'],
                risk_score=result['risk_score'],
                verdict_reason=result['verdict_reason'],
                detected_threats=result['detected_threats'],
                sanitized_response=result.get(
                    'sanitized_response', request.response)
            )
        except Exception as e:
            logger.exception("Error during egress analysis")
            raise e

    async def AnalyzeStream(self, request_iterator, context):
        """Streaming: Analyze tokens in real-time for SSE responses."""
        from engines.streaming import get_streaming_engine

        engine = get_streaming_engine()
        buffers = {}  # session_id -> StreamBuffer

        async for chunk in request_iterator:
            session_id = chunk.session_id

            # Get or create buffer for session
            if session_id not in buffers:
                buffers[session_id] = engine.create_buffer()
                logger.info(f"Stream session started: {session_id}")

            buffer = buffers[session_id]

            # Analyze the chunk
            alerts = engine.analyze_chunk(buffer, chunk.token)

            # Check if we should terminate
            should_terminate = any(a.should_terminate for a in alerts)

            # Build response
            threat_type = ""
            severity = ""
            alert_context = ""

            if alerts:
                # Use first (most severe) alert
                alert = alerts[0]
                threat_type = alert.threat_type
                severity = alert.severity
                alert_context = alert.context

            yield sentinel_pb2.StreamResult(
                should_continue=not should_terminate,
                risk_score=buffer.risk_score,
                threat_type=threat_type,
                severity=severity,
                context=alert_context
            )

            # Finalize on last chunk
            if chunk.is_final:
                summary = engine.finalize(buffer)
                logger.info(f"Stream session ended: {session_id}, "
                            f"threats={summary['threat_detected']}, "
                            f"risk={summary['risk_score']}")
                del buffers[session_id]
                break

            # Early termination on critical threat
            if should_terminate:
                logger.warning(f"Stream terminated early: {session_id}, "
                               f"threat={threat_type}")
                if session_id in buffers:
                    del buffers[session_id]
                break


def load_tls_credentials():
    """Load TLS credentials for mTLS if enabled."""
    if os.getenv("TLS_ENABLED", "false").lower() != "true":
        return None

    cert_path = os.getenv("TLS_CERT_PATH", "/certs/brain.crt")
    key_path = os.getenv("TLS_KEY_PATH", "/certs/brain.key")
    ca_path = os.getenv("TLS_CA_PATH", "/certs/ca.crt")

    try:
        with open(key_path, "rb") as f:
            private_key = f.read()
        with open(cert_path, "rb") as f:
            certificate_chain = f.read()
        with open(ca_path, "rb") as f:
            root_certificates = f.read()

        return grpc.ssl_server_credentials(
            [(private_key, certificate_chain)],
            root_certificates=root_certificates,
            require_client_auth=True  # mTLS: require client certificate
        )
    except Exception as e:
        logger.error(f"Failed to load TLS credentials: {e}")
        raise


async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    sentinel_pb2_grpc.add_SentinelBrainServicer_to_server(
        SentinelBrainServicer(), server)

    # Start Watchdog for self-healing
    watchdog = get_watchdog()
    for name, check in create_default_health_checks().items():
        watchdog.register_engine(name, check)
    asyncio.create_task(watchdog.run())
    logger.info("Watchdog started for engine health monitoring")

    # Start Threat Hunter for proactive threat detection
    threat_hunter = get_threat_hunter()
    asyncio.create_task(threat_hunter.continuous_hunt(interval_minutes=60))
    logger.info("Threat Hunter started (interval=60m)")

    # Initialize Post-Quantum Crypto signer for cognitive updates
    signer = get_signer()
    signer.generate_keypair()
    logger.info(f"PQCrypto signer ready (algorithm={signer.algorithm})")

    # Initialize Quantum RNG for high-quality randomness
    qrng = get_qrng()
    mode = "HARDWARE" if qrng.has_hardware else "SIMULATED"
    logger.info(f"Quantum RNG ready (mode={mode})")

    # Load TLS credentials if enabled
    credentials = load_tls_credentials()

    if credentials:
        server.add_secure_port('[::]:50051', credentials)
        logger.info(
            "Sentinel Brain started on port 50051 (TLS enabled, mTLS required)")
    else:
        # P1 Security: Require explicit flag for insecure mode
        if os.getenv("INSECURE_MODE_ALLOWED", "false").lower() != "true":
            logger.critical(
                "🚨 SECURITY: TLS is disabled but INSECURE_MODE_ALLOWED is not set. "
                "Set TLS_ENABLED=true or INSECURE_MODE_ALLOWED=true to start.")
            raise RuntimeError(
                "Insecure mode requires explicit INSECURE_MODE_ALLOWED=true")

        logger.warning(
            "⚠️ SECURITY WARNING: Running in INSECURE mode without TLS! "
            "This should ONLY be used for local development.")
        server.add_insecure_port('[::]:50051')
        logger.info(
            "Sentinel Brain started on port 50051 (INSECURE - dev only)")

    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
