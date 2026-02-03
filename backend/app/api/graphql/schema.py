"""
GraphQL Schema Definition.

Defines GraphQL types, queries, and mutations for the Floodingnaque API.
"""

import os
from datetime import datetime
from pathlib import Path

import graphene
from app.utils.logging import get_logger
from dotenv import load_dotenv
from graphene import Boolean, DateTime, Field, Float, Int, List, ObjectType, Schema, String
from graphene.types.scalars import Scalar

logger = get_logger(__name__)

# Load environment variables before checking GRAPHQL_ENABLED
# Skip in testing mode to allow test fixtures to control environment
_backend_dir = Path(__file__).resolve().parent.parent.parent.parent
if os.getenv("TESTING", "false").lower() != "true":
    # Load environment-specific file based on APP_ENV
    _app_env = os.getenv("APP_ENV", "development").lower()
    if _app_env in ("production", "prod"):
        load_dotenv(_backend_dir / ".env.production")
    elif _app_env in ("staging", "stage"):
        load_dotenv(_backend_dir / ".env.staging")
    else:
        load_dotenv(_backend_dir / ".env.development")

# Check if GraphQL is enabled
GRAPHQL_ENABLED = os.getenv("GRAPHQL_ENABLED", "false").lower() == "true"


# Health check functions
def check_database_health() -> dict:
    """Check database connection health.

    Returns:
        dict: Database health status with 'connected' key
    """
    try:
        from app.models.db import get_db_session
        from sqlalchemy import text

        with get_db_session() as session:
            # Execute a simple query to test connection
            session.execute(text("SELECT 1"))
        return {"status": "healthy", "connected": True}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {"status": "unhealthy", "connected": False, "error": str(e)}


def check_model_health() -> str:
    """Check model availability.

    Returns:
        str: 'healthy' if model is available, 'unhealthy' otherwise
    """
    try:
        # Check if model file exists and is loadable
        # For now, return a simple status - can be enhanced to check actual model loading
        import os
        from pathlib import Path

        # Check for model file existence
        model_dir = Path(__file__).resolve().parent.parent.parent / "models" / "saved"
        if model_dir.exists():
            # Could add more sophisticated checks here
            return "healthy"
        else:
            return "unhealthy"
    except Exception as e:
        logger.error(f"Model health check failed: {str(e)}")
        return "unhealthy"


# Custom scalar for handling various data types
class GenericScalar(Scalar):
    """Custom scalar for handling generic JSON data."""

    @staticmethod
    def serialize(value):
        return value

    @staticmethod
    def parse_literal(node):
        return node.value

    @staticmethod
    def parse_value(value):
        return value


# GraphQL Types
class WeatherDataType(ObjectType):
    """Weather data type for GraphQL."""

    id = String()
    timestamp = DateTime()
    latitude = Float()
    longitude = Float()
    temperature = Float()
    humidity = Float()
    precipitation = Float()
    wind_speed = Float()
    pressure = Float()
    source = String()


class FloodPredictionType(ObjectType):
    """Flood prediction type for GraphQL."""

    id = String()
    timestamp = DateTime()
    latitude = Float()
    longitude = Float()
    flood_risk = Float()
    confidence = Float()
    model_version = String()
    features = GenericScalar()


class HealthStatusType(ObjectType):
    """Health status type for GraphQL."""

    status = String()
    timestamp = DateTime()
    checks = GenericScalar()
    model_available = Boolean()
    database_connected = Boolean()


class RateLimitInfoType(ObjectType):
    """Rate limit information type for GraphQL."""

    authenticated = Boolean()
    tier = String()
    limits = GenericScalar()
    requests_remaining = Int()


class TaskStatusType(ObjectType):
    """Background task status type for GraphQL."""

    task_id = String()
    status = String()
    progress = Int()
    result = GenericScalar()
    error = String()
    created_at = DateTime()


# Query Resolvers
class Query(ObjectType):
    """Root query type for GraphQL."""

    # Health queries
    health = Field(HealthStatusType)
    health_status = Field(String)

    # Weather data queries
    weather_data = List(
        WeatherDataType,
        latitude=Float(required=True),
        longitude=Float(required=True),
        start_date=DateTime(),
        end_date=DateTime(),
        limit=Int(default_value=100),
    )

    # Prediction queries
    flood_prediction = Field(
        FloodPredictionType, latitude=Float(required=True), longitude=Float(required=True), features=GenericScalar()
    )

    predictions = List(
        FloodPredictionType,
        latitude=Float(),
        longitude=Float(),
        start_date=DateTime(),
        end_date=DateTime(),
        limit=Int(default_value=100),
    )

    # Rate limit queries
    rate_limit_status = Field(RateLimitInfoType)

    # Task queries
    task_status = Field(TaskStatusType, task_id=String(required=True))

    # System info queries
    system_info = GenericScalar()

    def resolve_health(self, info):
        """Get system health status."""
        try:
            from app.utils.cache import get_cache_stats

            db_status = check_database_health()
            model_status = check_model_health()
            cache_stats = get_cache_stats()

            return HealthStatusType(
                status="healthy" if db_status.get("connected") and model_status == "healthy" else "unhealthy",
                timestamp=datetime.utcnow(),
                checks={"database": db_status, "model": model_status, "cache": cache_stats},
                model_available=model_status == "healthy",
                database_connected=db_status.get("connected", False),
            )
        except Exception as e:
            logger.error(f"GraphQL health query failed: {str(e)}")
            return HealthStatusType(
                status="unhealthy",
                timestamp=datetime.utcnow(),
                checks={"error": str(e)},
                model_available=False,
                database_connected=False,
            )

    def resolve_health_status(self, info):
        """Simple health status string."""
        try:
            db_status = check_database_health()
            model_status = check_model_health()

            return "healthy" if db_status.get("connected") and model_status == "healthy" else "unhealthy"
        except Exception:
            return "unhealthy"

    def resolve_weather_data(self, info, latitude, longitude, start_date=None, end_date=None, limit=100):
        """Get weather data for a location."""
        try:
            from app.models.db import WeatherData, get_db_session
            from sqlalchemy import desc

            with get_db_session() as session:
                query = session.query(WeatherData).filter(
                    WeatherData.latitude == latitude, WeatherData.longitude == longitude
                )

                if start_date:
                    query = query.filter(WeatherData.timestamp >= start_date)
                if end_date:
                    query = query.filter(WeatherData.timestamp <= end_date)

                results = query.order_by(desc(WeatherData.timestamp)).limit(limit).all()

                return [
                    WeatherDataType(
                        id=str(record.id),
                        timestamp=record.timestamp,
                        latitude=record.latitude,
                        longitude=record.longitude,
                        temperature=record.temperature,
                        humidity=record.humidity,
                        precipitation=record.precipitation,
                        wind_speed=record.wind_speed,
                        pressure=record.pressure,
                        source=record.source,
                    )
                    for record in results
                ]
        except Exception as e:
            logger.error(f"GraphQL weather data query failed: {str(e)}")
            return []

    def resolve_flood_prediction(self, info, latitude, longitude, features=None):
        """Get flood prediction for a location."""
        try:
            from app.services.predict import predict_flood

            # Use provided features or generate defaults
            if features is None:
                features = {
                    "temperature": 20.0,
                    "humidity": 70.0,
                    "precipitation": 5.0,
                    "wind_speed": 10.0,
                    "pressure": 1013.25,
                }

            prediction = predict_flood(latitude, longitude, features)

            return FloodPredictionType(
                id=str(prediction.get("id", "unknown")),
                timestamp=datetime.utcnow(),
                latitude=latitude,
                longitude=longitude,
                flood_risk=prediction.get("flood_risk", 0.0),
                confidence=prediction.get("confidence", 0.0),
                model_version=prediction.get("model_version", "unknown"),
                features=features,
            )
        except Exception as e:
            logger.error(f"GraphQL flood prediction query failed: {str(e)}")
            return FloodPredictionType(
                id="error",
                timestamp=datetime.utcnow(),
                latitude=latitude,
                longitude=longitude,
                flood_risk=0.0,
                confidence=0.0,
                model_version="error",
                features={"error": str(e)},
            )

    def resolve_predictions(self, info, latitude=None, longitude=None, start_date=None, end_date=None, limit=100):
        """Get historical flood predictions."""
        try:
            from app.models.db import Prediction as FloodPrediction
            from app.models.db import get_db_session
            from sqlalchemy import desc

            with get_db_session() as session:
                query = session.query(FloodPrediction)

                if latitude is not None:
                    query = query.filter(FloodPrediction.latitude == latitude)
                if longitude is not None:
                    query = query.filter(FloodPrediction.longitude == longitude)
                if start_date:
                    query = query.filter(FloodPrediction.timestamp >= start_date)
                if end_date:
                    query = query.filter(FloodPrediction.timestamp <= end_date)

                results = query.order_by(desc(FloodPrediction.timestamp)).limit(limit).all()

                return [
                    FloodPredictionType(
                        id=str(record.id),
                        timestamp=record.timestamp,
                        latitude=record.latitude,
                        longitude=record.longitude,
                        flood_risk=record.flood_risk,
                        confidence=record.confidence,
                        model_version=record.model_version,
                        features=record.features or {},
                    )
                    for record in results
                ]
        except Exception as e:
            logger.error(f"GraphQL predictions query failed: {str(e)}")
            return []

    def resolve_rate_limit_status(self, info):
        """Get current rate limiting status."""
        try:
            from app.utils.rate_limit_tiers import check_rate_limit_status
            from flask import g

            api_key_hash = getattr(g, "api_key_hash", None)
            status = check_rate_limit_status(api_key_hash)

            return RateLimitInfoType(
                authenticated=status["authenticated"],
                tier=status["tier"],
                limits=status["limits"],
                requests_remaining=None,  # Would need to get from Flask-Limiter
            )
        except Exception as e:
            logger.error(f"GraphQL rate limit status query failed: {str(e)}")
            return RateLimitInfoType(authenticated=False, tier="error", limits={"error": str(e)}, requests_remaining=0)

    def resolve_task_status(self, info, task_id):
        """Get status of a background task."""
        try:
            from app.services.tasks import get_task_status

            status = get_task_status(task_id)

            return TaskStatusType(
                task_id=status["task_id"],
                status=status["status"],
                progress=status.get("progress", 0),
                result=status.get("result"),
                error=None,
                created_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"GraphQL task status query failed: {str(e)}")
            return TaskStatusType(
                task_id=task_id, status="error", progress=0, result=None, error=str(e), created_at=datetime.utcnow()
            )

    def resolve_system_info(self, info):
        """Get system information."""
        try:
            import platform
            import sys

            return {
                "python_version": sys.version.split()[0],
                "platform": platform.system(),
                "platform_version": platform.version()[:50] if platform.version() else "unknown",
                "graphql_enabled": GRAPHQL_ENABLED,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"GraphQL system info query failed: {str(e)}")
            return {"error": str(e)}


# Result Types for Mutations
class MutationResultType(ObjectType):
    """Generic mutation result type."""

    success = Boolean(required=True)
    message = String()
    errors = List(String)


class WeatherDataResultType(ObjectType):
    """Weather data mutation result."""

    success = Boolean(required=True)
    message = String()
    data = Field(WeatherDataType)
    errors = List(String)


class PredictionResultType(ObjectType):
    """Prediction mutation result."""

    success = Boolean(required=True)
    message = String()
    data = Field(FloodPredictionType)
    errors = List(String)


class WebhookResultType(ObjectType):
    """Webhook mutation result."""

    success = Boolean(required=True)
    message = String()
    webhook_id = Int()
    url = String()
    events = List(String)
    secret = String()
    is_active = Boolean()
    errors = List(String)


class BulkDeleteResultType(ObjectType):
    """Bulk delete mutation result."""

    success = Boolean(required=True)
    message = String()
    deleted_count = Int()
    deleted_ids = List(Int)
    errors = List(String)


# Input Types for Mutations
class WeatherDataInput(graphene.InputObjectType):
    """Input type for creating/updating weather data."""

    temperature = Float(required=True, description="Temperature in Kelvin")
    humidity = Float(required=True, description="Humidity percentage (0-100)")
    precipitation = Float(required=True, description="Precipitation in mm")
    wind_speed = Float(description="Wind speed in m/s")
    pressure = Float(description="Atmospheric pressure in hPa")
    source = String(default_value="GraphQL", description="Data source")
    location_lat = Float(description="Latitude")
    location_lon = Float(description="Longitude")
    timestamp = DateTime(description="Measurement timestamp")


class WebhookInput(graphene.InputObjectType):
    """Input type for creating/updating webhooks."""

    url = String(required=True, description="Webhook URL")
    events = List(String, required=True, description="Events to subscribe to")
    secret = String(description="Webhook secret (auto-generated if not provided)")


# Mutation Resolvers
class Mutation(ObjectType):
    """Root mutation type for GraphQL."""

    # Weather Data mutations
    create_weather_data = Field(WeatherDataResultType, input=WeatherDataInput(required=True))

    update_weather_data = Field(WeatherDataResultType, id=Int(required=True), input=WeatherDataInput(required=True))

    delete_weather_data = Field(MutationResultType, id=Int(required=True))

    bulk_delete_weather_data = Field(BulkDeleteResultType, ids=List(Int, required=True), confirm=Boolean(required=True))

    # Webhook mutations
    create_webhook = Field(WebhookResultType, input=WebhookInput(required=True))

    update_webhook = Field(
        WebhookResultType, id=Int(required=True), url=String(), events=List(String), is_active=Boolean()
    )

    delete_webhook = Field(MutationResultType, id=Int(required=True))

    toggle_webhook = Field(WebhookResultType, id=Int(required=True))

    # Task mutations
    trigger_model_retraining = Field(TaskStatusType, model_id=String())

    trigger_data_processing = Field(TaskStatusType, data_batch=List(GenericScalar))

    def resolve_create_weather_data(self, info, input):
        """Create new weather data entry."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            from datetime import timezone

            from app.models.db import WeatherData, get_db_session

            # Validate temperature
            if input.temperature < 173.15 or input.temperature > 333.15:
                return WeatherDataResultType(
                    success=False,
                    message="Validation failed",
                    errors=["Temperature must be between 173.15K and 333.15K"],
                )

            # Validate humidity
            if input.humidity < 0 or input.humidity > 100:
                return WeatherDataResultType(
                    success=False, message="Validation failed", errors=["Humidity must be between 0 and 100"]
                )

            # Validate precipitation
            if input.precipitation < 0:
                return WeatherDataResultType(
                    success=False, message="Validation failed", errors=["Precipitation cannot be negative"]
                )

            with get_db_session() as session:
                weather_data = WeatherData(
                    temperature=input.temperature,
                    humidity=input.humidity,
                    precipitation=input.precipitation,
                    wind_speed=input.wind_speed,
                    pressure=input.pressure,
                    source=input.source or "GraphQL",
                    location_lat=input.location_lat,
                    location_lon=input.location_lon,
                    timestamp=input.timestamp or datetime.now(timezone.utc),
                )
                session.add(weather_data)
                session.flush()

                result = WeatherDataType(
                    id=str(weather_data.id),
                    timestamp=weather_data.timestamp,
                    latitude=weather_data.location_lat,
                    longitude=weather_data.location_lon,
                    temperature=weather_data.temperature,
                    humidity=weather_data.humidity,
                    precipitation=weather_data.precipitation,
                    wind_speed=weather_data.wind_speed,
                    pressure=weather_data.pressure,
                    source=weather_data.source,
                )

            return WeatherDataResultType(success=True, message="Weather data created successfully", data=result)
        except Exception as e:
            logger.error(f"GraphQL create weather data failed: {str(e)}")
            return WeatherDataResultType(success=False, message="Failed to create weather data", errors=[str(e)])

    def resolve_update_weather_data(self, info, id, input):
        """Update existing weather data."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            from app.models.db import WeatherData, get_db_session

            with get_db_session() as session:
                weather_data = (
                    session.query(WeatherData).filter(WeatherData.id == id, WeatherData.is_deleted == False).first()
                )

                if not weather_data:
                    return WeatherDataResultType(
                        success=False, message=f"Weather data with id {id} not found", errors=["Record not found"]
                    )

                # Update fields
                weather_data.temperature = input.temperature
                weather_data.humidity = input.humidity
                weather_data.precipitation = input.precipitation
                if input.wind_speed is not None:
                    weather_data.wind_speed = input.wind_speed
                if input.pressure is not None:
                    weather_data.pressure = input.pressure
                if input.source:
                    weather_data.source = input.source
                if input.location_lat is not None:
                    weather_data.location_lat = input.location_lat
                if input.location_lon is not None:
                    weather_data.location_lon = input.location_lon

                result = WeatherDataType(
                    id=str(weather_data.id),
                    timestamp=weather_data.timestamp,
                    latitude=weather_data.location_lat,
                    longitude=weather_data.location_lon,
                    temperature=weather_data.temperature,
                    humidity=weather_data.humidity,
                    precipitation=weather_data.precipitation,
                    wind_speed=weather_data.wind_speed,
                    pressure=weather_data.pressure,
                    source=weather_data.source,
                )

            return WeatherDataResultType(success=True, message="Weather data updated successfully", data=result)
        except Exception as e:
            logger.error(f"GraphQL update weather data failed: {str(e)}")
            return WeatherDataResultType(success=False, message="Failed to update weather data", errors=[str(e)])

    def resolve_delete_weather_data(self, info, id):
        """Delete weather data (soft delete)."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            from app.models.db import WeatherData, get_db_session

            with get_db_session() as session:
                weather_data = (
                    session.query(WeatherData).filter(WeatherData.id == id, WeatherData.is_deleted == False).first()
                )

                if not weather_data:
                    return MutationResultType(
                        success=False, message=f"Weather data with id {id} not found", errors=["Record not found"]
                    )

                weather_data.soft_delete()

            return MutationResultType(success=True, message="Weather data deleted successfully")
        except Exception as e:
            logger.error(f"GraphQL delete weather data failed: {str(e)}")
            return MutationResultType(success=False, message="Failed to delete weather data", errors=[str(e)])

    def resolve_bulk_delete_weather_data(self, info, ids, confirm):
        """Bulk delete weather data."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            if not confirm:
                return BulkDeleteResultType(
                    success=False, message="Bulk delete requires confirm=true", errors=["Confirmation required"]
                )

            if len(ids) > 1000:
                return BulkDeleteResultType(
                    success=False, message="Maximum 1000 IDs per request", errors=["Too many IDs"]
                )

            from app.models.db import WeatherData, get_db_session

            deleted_ids = []
            with get_db_session() as session:
                records = (
                    session.query(WeatherData).filter(WeatherData.id.in_(ids), WeatherData.is_deleted == False).all()
                )

                for record in records:
                    record.soft_delete()
                    deleted_ids.append(record.id)

            return BulkDeleteResultType(
                success=True,
                message=f"Successfully deleted {len(deleted_ids)} records",
                deleted_count=len(deleted_ids),
                deleted_ids=deleted_ids,
            )
        except Exception as e:
            logger.error(f"GraphQL bulk delete weather data failed: {str(e)}")
            return BulkDeleteResultType(success=False, message="Failed to bulk delete", errors=[str(e)])

    def resolve_create_webhook(self, info, input):
        """Create a new webhook."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            import json
            import secrets

            from app.models.db import Webhook, get_db_session

            # Validate URL
            url = input.url
            if not url.startswith("http://") and not url.startswith("https://"):
                return WebhookResultType(
                    success=False, message="Invalid URL format", errors=["URL must start with http:// or https://"]
                )

            # Validate events
            events = input.events or []
            valid_events = ["flood_detected", "critical_risk", "high_risk", "medium_risk", "low_risk"]
            invalid_events = [e for e in events if e not in valid_events]
            if invalid_events:
                return WebhookResultType(
                    success=False,
                    message="Invalid events",
                    errors=[f"Invalid events: {invalid_events}. Valid: {valid_events}"],
                )

            # Generate secret if not provided
            secret = input.secret or secrets.token_urlsafe(32)

            with get_db_session() as session:
                webhook = Webhook(url=url, events=json.dumps(events), secret=secret, is_active=True)
                session.add(webhook)
                session.flush()
                webhook_id = webhook.id

            return WebhookResultType(
                success=True,
                message="Webhook created successfully",
                webhook_id=webhook_id,
                url=url,
                events=events,
                secret=secret,
                is_active=True,
            )
        except Exception as e:
            logger.error(f"GraphQL create webhook failed: {str(e)}")
            return WebhookResultType(success=False, message="Failed to create webhook", errors=[str(e)])

    def resolve_update_webhook(self, info, id, url=None, events=None, is_active=None):
        """Update an existing webhook."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            import json
            from datetime import timezone

            from app.models.db import Webhook, get_db_session

            with get_db_session() as session:
                webhook = session.query(Webhook).filter(Webhook.id == id, Webhook.is_deleted == False).first()

                if not webhook:
                    return WebhookResultType(
                        success=False, message=f"Webhook with id {id} not found", errors=["Webhook not found"]
                    )

                if url is not None:
                    if not url.startswith("http://") and not url.startswith("https://"):
                        return WebhookResultType(
                            success=False,
                            message="Invalid URL format",
                            errors=["URL must start with http:// or https://"],
                        )
                    webhook.url = url

                if events is not None:
                    valid_events = ["flood_detected", "critical_risk", "high_risk", "medium_risk", "low_risk"]
                    invalid = [e for e in events if e not in valid_events]
                    if invalid:
                        return WebhookResultType(
                            success=False, message="Invalid events", errors=[f"Invalid events: {invalid}"]
                        )
                    webhook.events = json.dumps(events)

                if is_active is not None:
                    webhook.is_active = is_active

                webhook.updated_at = datetime.now(timezone.utc)

                return WebhookResultType(
                    success=True,
                    message="Webhook updated successfully",
                    webhook_id=webhook.id,
                    url=webhook.url,
                    events=json.loads(webhook.events),
                    is_active=webhook.is_active,
                )
        except Exception as e:
            logger.error(f"GraphQL update webhook failed: {str(e)}")
            return WebhookResultType(success=False, message="Failed to update webhook", errors=[str(e)])

    def resolve_delete_webhook(self, info, id):
        """Delete a webhook."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            from datetime import timezone

            from app.models.db import Webhook, get_db_session

            with get_db_session() as session:
                webhook = session.query(Webhook).filter(Webhook.id == id, Webhook.is_deleted == False).first()

                if not webhook:
                    return MutationResultType(
                        success=False, message=f"Webhook with id {id} not found", errors=["Webhook not found"]
                    )

                webhook.is_deleted = True
                webhook.deleted_at = datetime.now(timezone.utc)

            return MutationResultType(success=True, message="Webhook deleted successfully")
        except Exception as e:
            logger.error(f"GraphQL delete webhook failed: {str(e)}")
            return MutationResultType(success=False, message="Failed to delete webhook", errors=[str(e)])

    def resolve_toggle_webhook(self, info, id):
        """Toggle webhook active status."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            import json
            from datetime import timezone

            from app.models.db import Webhook, get_db_session

            with get_db_session() as session:
                webhook = session.query(Webhook).filter(Webhook.id == id, Webhook.is_deleted == False).first()

                if not webhook:
                    return WebhookResultType(
                        success=False, message=f"Webhook with id {id} not found", errors=["Webhook not found"]
                    )

                webhook.is_active = not webhook.is_active
                webhook.updated_at = datetime.now(timezone.utc)
                new_status = webhook.is_active

                return WebhookResultType(
                    success=True,
                    message=f'Webhook {"enabled" if new_status else "disabled"} successfully',
                    webhook_id=webhook.id,
                    url=webhook.url,
                    events=json.loads(webhook.events),
                    is_active=new_status,
                )
        except Exception as e:
            logger.error(f"GraphQL toggle webhook failed: {str(e)}")
            return WebhookResultType(success=False, message="Failed to toggle webhook", errors=[str(e)])

    def resolve_trigger_model_retraining(self, info, model_id=None):
        """Trigger model retraining task."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            from app.services.tasks import trigger_model_retraining

            result = trigger_model_retraining(model_id)

            return TaskStatusType(
                task_id=result["task_id"],
                status="queued",
                progress=0,
                result=result,
                error=None,
                created_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"GraphQL model retraining mutation failed: {str(e)}")
            return TaskStatusType(
                task_id="error", status="error", progress=0, result=None, error=str(e), created_at=datetime.utcnow()
            )

    def resolve_trigger_data_processing(self, info, data_batch):
        """Trigger data processing task."""
        try:
            if not GRAPHQL_ENABLED:
                raise Exception("GraphQL is disabled")

            from app.services.tasks import trigger_data_processing

            result = trigger_data_processing(data_batch)

            return TaskStatusType(
                task_id=result["task_id"],
                status="queued",
                progress=0,
                result=result,
                error=None,
                created_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"GraphQL data processing mutation failed: {str(e)}")
            return TaskStatusType(
                task_id="error", status="error", progress=0, result=None, error=str(e), created_at=datetime.utcnow()
            )


# Create GraphQL schema
schema = Schema(query=Query, mutation=Mutation)


def get_graphql_schema():
    """Get the GraphQL schema if enabled."""
    if GRAPHQL_ENABLED:
        return schema
    else:
        return None
