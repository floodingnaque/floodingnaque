"""
GraphQL API Routes.

Provides GraphQL endpoint behind feature flag.
"""

from app.api.graphql.schema import GRAPHQL_ENABLED, get_graphql_schema
from app.api.middleware.rate_limit import limiter
from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_SERVICE_UNAVAILABLE
from app.utils.api_responses import api_error
from app.utils.observability.logging import get_logger
from flask import Blueprint, g, jsonify, request
from graphql import graphql_sync

logger = get_logger(__name__)

graphql_bp = Blueprint("graphql", __name__)

# GraphiQL HTML template for interactive IDE
GRAPHIQL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GraphiQL - Floodingnaque API</title>
    <link href="https://unpkg.com/graphiql/graphiql.min.css" rel="stylesheet" />
</head>
<body style="margin: 0;">
    <div id="graphiql" style="height: 100vh;"></div>
    <script crossorigin src="https://unpkg.com/react/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom/umd/react-dom.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/graphiql/graphiql.min.js"></script>
    <script>
        const fetcher = GraphiQL.createFetcher({ url: '/graphql' });
        ReactDOM.render(
            React.createElement(GraphiQL, { fetcher: fetcher }),
            document.getElementById('graphiql'),
        );
    </script>
</body>
</html>
"""


def init_graphql_route(app):
    """
    Initialize GraphQL route if enabled.

    Args:
        app: Flask application instance
    """
    if not GRAPHQL_ENABLED:
        logger.info("GraphQL is disabled (set GRAPHQL_ENABLED=true to enable)")
        return

    try:
        schema = get_graphql_schema()
        if not schema:
            logger.error("GraphQL schema is not available")
            return

        @app.route("/graphql", methods=["GET", "POST"])
        def graphql_endpoint():
            """Handle GraphQL requests."""
            # Return GraphiQL IDE for GET requests
            if request.method == "GET":
                return GRAPHIQL_HTML, 200, {"Content-Type": "text/html"}

            # Handle POST requests with GraphQL queries
            data = request.get_json()
            if not data:
                return jsonify({"errors": [{"message": "No GraphQL query provided"}]}), 400

            query = data.get("query", "")
            variables = data.get("variables")
            operation_name = data.get("operationName")

            # Use graphene's execute method or convert to GraphQL core schema
            result = schema.execute(
                query,
                variables=variables,
                operation_name=operation_name,
                context_value={"request": request},
            )

            response = {}
            if result.data:
                response["data"] = result.data
            if result.errors:
                response["errors"] = [{"message": str(e)} for e in result.errors]

            return jsonify(response)

        logger.info("GraphQL endpoint initialized at /graphql")

    except ImportError as e:
        logger.warning(f"GraphQL dependencies not available: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize GraphQL: {str(e)}")


@graphql_bp.route("/graphql/info", methods=["GET"])
@limiter.limit("60/minute")
def graphql_info():
    """
    Get GraphQL endpoint information.

    Returns:
        GraphQL endpoint status and information
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        schema = get_graphql_schema()

        if not GRAPHQL_ENABLED:
            return api_error(
                "GraphQLDisabled",
                "GraphQL is disabled. Set GRAPHQL_ENABLED=true to enable.",
                HTTP_SERVICE_UNAVAILABLE,
                request_id,
            )

        if not schema:
            return api_error(
                "GraphQLNotAvailable", "GraphQL schema is not available", HTTP_SERVICE_UNAVAILABLE, request_id
            )

        # Get schema information
        query_type = schema.query_type.name if schema.query_type else None
        mutation_type = schema.mutation_type.name if schema.mutation_type else None

        info = {
            "enabled": True,
            "endpoints": {
                "graphql": "/graphql",
                "graphql_raw": "/graphql/raw",
                "graphiql": "/graphql",  # GraphiQL IDE available
            },
            "schema": {
                "query_type": query_type,
                "mutation_type": mutation_type,
                "has_subscription": bool(schema.subscription_type),
            },
            "features": {"graphiql_ide": True, "introspection": True, "feature_flag": "GRAPHQL_ENABLED"},
            "usage": {
                "query_endpoint": "POST /graphql with JSON body",
                "query_format": '{"query": "{ health { status } }"}',
                "variables_format": '{"query": "...", "variables": {...}}',
            },
        }

        return jsonify(
            {"status": "success", "message": "GraphQL endpoint is available", "data": info, "request_id": request_id}
        )

    except Exception as e:
        logger.error(f"Failed to get GraphQL info [{request_id}]: {str(e)}")
        return api_error("GraphQLInfoFailed", "Failed to get GraphQL information", HTTP_BAD_REQUEST, request_id)


@graphql_bp.route("/graphql/schema", methods=["GET"])
@limiter.limit("30/minute")
def graphql_schema_introspection():
    """
    Get GraphQL schema introspection result.

    Returns:
        Full GraphQL schema for introspection
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        if not GRAPHQL_ENABLED:
            return api_error("GraphQLDisabled", "GraphQL is disabled", HTTP_SERVICE_UNAVAILABLE, request_id)

        schema = get_graphql_schema()
        if not schema:
            return api_error(
                "GraphQLNotAvailable", "GraphQL schema is not available", HTTP_SERVICE_UNAVAILABLE, request_id
            )

        # Get introspection query result
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                queryType { name }
                mutationType { name }
                subscriptionType { name }
                types {
                    kind
                    name
                    description
                    fields {
                        name
                        description
                        type {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                }
                            }
                        }
                        args {
                            name
                            description
                            type {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                }
                            }
                            defaultValue
                        }
                    }
                    inputFields {
                        name
                        description
                        type {
                            kind
                            name
                            ofType {
                                kind
                                name
                            }
                        }
                        defaultValue
                    }
                }
                directives {
                    name
                    description
                    locations
                    args {
                        name
                        description
                        type {
                            kind
                            name
                            ofType {
                                kind
                                name
                            }
                        }
                        defaultValue
                    }
                }
            }
        }
        """

        # Execute introspection query
        result = graphql_sync(schema, introspection_query)

        if result.errors:
            logger.error(f"GraphQL introspection failed: {result.errors}")
            return api_error("IntrospectionFailed", "Schema introspection failed", HTTP_BAD_REQUEST, request_id)

        return jsonify(
            {
                "status": "success",
                "message": "GraphQL schema introspection",
                "data": result.data,
                "request_id": request_id,
            }
        )

    except Exception as e:
        logger.error(f"Failed to get GraphQL schema [{request_id}]: {str(e)}")
        return api_error("GraphQLSchemaFailed", "Failed to get GraphQL schema", HTTP_BAD_REQUEST, request_id)


# Example GraphQL queries for documentation
EXAMPLE_QUERIES = {
    "health_check": {
        "query": """
        query {
            health {
                status
                timestamp
                modelAvailable
                databaseConnected
            }
        }
        """,
        "description": "Get system health status",
    },
    "weather_data": {
        "query": """
        query GetWeatherData($latitude: Float!, $longitude: Float!) {
            weatherData(latitude: $latitude, longitude: $longitude, limit: 10) {
                id
                timestamp
                temperature
                humidity
                precipitation
                source
            }
        }
        """,
        "variables": '{"latitude": 40.7128, "longitude": -74.0060}',
        "description": "Get weather data for New York City",
    },
    "flood_prediction": {
        "query": """
        query GetFloodPrediction($latitude: Float!, $longitude: Float!) {
            floodPrediction(latitude: $latitude, longitude: $longitude) {
                floodRisk
                confidence
                modelVersion
                timestamp
            }
        }
        """,
        "variables": '{"latitude": 40.7128, "longitude": -74.0060}',
        "description": "Get flood prediction for a location",
    },
    "system_info": {
        "query": """
        query {
            systemInfo {
                pythonVersion
                platform
                graphqlEnabled
                timestamp
            }
        }
        """,
        "description": "Get system information",
    },
}


@graphql_bp.route("/graphql/examples", methods=["GET"])
@limiter.limit("30/minute")
def graphql_examples():
    """
    Get example GraphQL queries.

    Returns:
        Example queries for testing and documentation
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        return jsonify(
            {
                "status": "success",
                "message": "GraphQL example queries",
                "data": {
                    "examples": EXAMPLE_QUERIES,
                    "usage_notes": {
                        "endpoint": "POST /graphql",
                        "headers": {"Content-Type": "application/json"},
                        "body_format": '{"query": "...", "variables": {...}}',
                        "graphiql_available": "Visit /graphql for interactive IDE",
                    },
                },
                "request_id": request_id,
            }
        )

    except Exception as e:
        logger.error(f"Failed to get GraphQL examples [{request_id}]: {str(e)}")
        return api_error("GraphQLExamplesFailed", "Failed to get GraphQL examples", HTTP_BAD_REQUEST, request_id)
