"""
Floodingnaque Shared Utilities Package.

Common modules shared across all microservices:
- config: Environment-aware configuration loading
- database: SQLAlchemy engine/session management
- auth: JWT token verification for inter-service auth
- health: Standardized health check endpoints
- messaging: Inter-service communication (HTTP + Redis pub/sub)
- discovery: Service discovery and registry
- errors: Shared error response formatting (RFC 7807)
- tracing: Distributed tracing with correlation IDs
"""

__version__ = "1.0.0"
