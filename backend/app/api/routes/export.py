"""
Data Export API.

Endpoints for exporting historical weather and prediction data
in CSV, JSON, and PDF formats.
"""

import csv
import logging
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Any

from app.api.middleware.auth import require_api_key
from app.api.middleware.rate_limit import limiter
from app.models.db import Prediction, WeatherData, get_db_session
from flask import Blueprint, Response, jsonify, request

logger = logging.getLogger(__name__)

export_bp = Blueprint("export", __name__)


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------


def _build_pdf(title: str, subtitle: str, headers: list[str], rows: list[list[Any]]) -> bytes:
    """Generate a PDF report using ReportLab and return raw bytes.

    Raises ImportError if reportlab is not installed.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=12,
    )

    story: list[Any] = [
        Paragraph(title, title_style),
        Paragraph(subtitle, subtitle_style),
        Spacer(1, 0.3 * cm),
    ]

    # Table data: header row first
    table_data = [headers] + [[str(c) if c is not None else "" for c in row] for row in rows]

    col_count = len(headers)
    page_width = landscape(A4)[0] - 3 * cm  # available width after margins
    col_width = page_width / col_count

    table = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                # Body
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        )
    )
    story.append(table)

    generated_at = Paragraph(
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  |  " f"Records: {len(rows)}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.grey, spaceBefore=8),
    )
    story.append(generated_at)

    doc.build(story)
    return buf.getvalue()


@export_bp.route("/weather", methods=["GET"])
@require_api_key
@limiter.limit("5 per minute")
def export_weather():
    """
    Export historical weather data.

    Query Parameters:
        format: csv, json, or pdf (default: json)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum records (default: 1000, max: 10000)

    Returns:
        200: Exported data
        400: Invalid parameters
    """
    try:
        # Get parameters
        export_format = request.args.get("format", "json").lower()
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        limit = int(request.args.get("limit", 1000))

        # Validate format
        if export_format not in ["csv", "json", "pdf"]:
            return jsonify({"error": "Invalid format. Must be csv, json, or pdf"}), 400

        # Validate limit
        max_limit = 10000
        if limit > max_limit:
            return jsonify({"error": f"Limit exceeds maximum of {max_limit}"}), 400

        # Build query
        with get_db_session() as session:
            query = session.query(WeatherData).filter_by(is_deleted=False)

            # Apply date filters
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(WeatherData.timestamp >= start_dt)
                except ValueError:
                    return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    query = query.filter(WeatherData.timestamp <= end_dt)
                except ValueError:
                    return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

            # Order and limit
            query = query.order_by(WeatherData.timestamp.desc()).limit(limit)

            # Execute query
            weather_data = query.all()

        if not weather_data:
            return jsonify({"message": "No data found", "count": 0}), 200

        # Export as CSV
        if export_format == "csv":
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "id",
                    "timestamp",
                    "temperature",
                    "humidity",
                    "precipitation",
                    "wind_speed",
                    "pressure",
                    "latitude",
                    "longitude",
                    "location",
                ]
            )

            # Write data
            for record in weather_data:
                writer.writerow(
                    [
                        record.id,
                        record.timestamp.isoformat() if record.timestamp else "",
                        record.temperature,
                        record.humidity,
                        record.precipitation,
                        record.wind_speed,
                        record.pressure,
                        record.latitude,
                        record.longitude,
                        record.location,
                    ]
                )

            csv_data = output.getvalue()
            output.close()

            return Response(
                csv_data,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename=weather_data_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.csv'
                },
            )

        # Export as PDF
        if export_format == "pdf":
            try:
                headers_row = [
                    "ID",
                    "Timestamp",
                    "Temp (°C)",
                    "Humidity (%)",
                    "Precip (mm)",
                    "Wind (m/s)",
                    "Pressure (hPa)",
                    "Latitude",
                    "Longitude",
                    "Location",
                ]
                rows = [
                    [
                        record.id,
                        record.timestamp.strftime("%Y-%m-%d %H:%M") if record.timestamp else "",
                        record.temperature,
                        record.humidity,
                        record.precipitation,
                        record.wind_speed,
                        record.pressure,
                        record.latitude,
                        record.longitude,
                        record.location,
                    ]
                    for record in weather_data
                ]
                date_range = ""
                if start_date and end_date:
                    date_range = f" ({start_date} to {end_date})"
                elif start_date:
                    date_range = f" (from {start_date})"
                elif end_date:
                    date_range = f" (to {end_date})"

                pdf_bytes = _build_pdf(
                    title="Weather Data Report",
                    subtitle=f"Floodingnaque – Historical Weather Observations{date_range}",
                    headers=headers_row,
                    rows=rows,
                )
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename=weather_data_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.pdf',
                        "Content-Length": str(len(pdf_bytes)),
                    },
                )
            except ImportError:
                logger.error("reportlab is not installed; cannot generate PDF")
                return jsonify({"error": "PDF generation not available on this server"}), 503

        # Export as JSON
        else:
            data_list = []
            for record in weather_data:
                data_list.append(
                    {
                        "id": record.id,
                        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                        "temperature": record.temperature,
                        "humidity": record.humidity,
                        "precipitation": record.precipitation,
                        "wind_speed": record.wind_speed,
                        "pressure": record.pressure,
                        "latitude": record.latitude,
                        "longitude": record.longitude,
                        "location": record.location,
                    }
                )

            return jsonify({"data": data_list, "count": len(data_list), "format": "json"}), 200

    except Exception as e:
        logger.error(f"Error exporting weather data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@export_bp.route("/predictions", methods=["GET"])
@require_api_key
@limiter.limit("5 per minute")
def export_predictions():
    """
    Export historical prediction data.

    Query Parameters:
        format: csv, json, or pdf (default: json)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        risk_level: Filter by risk level
        limit: Maximum records (default: 1000, max: 10000)

    Returns:
        200: Exported data
        400: Invalid parameters
    """
    try:
        # Get parameters
        export_format = request.args.get("format", "json").lower()
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        risk_level = request.args.get("risk_level")
        limit = int(request.args.get("limit", 1000))

        # Validate format
        if export_format not in ["csv", "json", "pdf"]:
            return jsonify({"error": "Invalid format. Must be csv, json, or pdf"}), 400

        # Validate limit
        max_limit = 10000
        if limit > max_limit:
            return jsonify({"error": f"Limit exceeds maximum of {max_limit}"}), 400

        # Build query
        with get_db_session() as session:
            query = session.query(Prediction).filter_by(is_deleted=False)

            # Apply filters
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(Prediction.created_at >= start_dt)
                except ValueError:
                    return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    query = query.filter(Prediction.created_at <= end_dt)
                except ValueError:
                    return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

            if risk_level:
                query = query.filter(Prediction.risk_level == risk_level)

            # Order and limit
            query = query.order_by(Prediction.created_at.desc()).limit(limit)

            # Execute query
            predictions = query.all()

        if not predictions:
            return jsonify({"message": "No data found", "count": 0}), 200

        # Export as CSV
        if export_format == "csv":
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "id",
                    "timestamp",
                    "prediction",
                    "risk_level",
                    "confidence",
                    "temperature",
                    "humidity",
                    "precipitation",
                    "model_version",
                ]
            )

            # Write data
            for record in predictions:
                writer.writerow(
                    [
                        record.id,
                        record.created_at.isoformat() if record.created_at else "",
                        record.prediction,
                        record.risk_level,
                        record.confidence,
                        getattr(record, "temperature", None),
                        getattr(record, "humidity", None),
                        getattr(record, "precipitation", None),
                        record.model_version,
                    ]
                )

            csv_data = output.getvalue()
            output.close()

            return Response(
                csv_data,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename=predictions_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.csv'
                },
            )

        # Export as PDF
        if export_format == "pdf":
            try:
                headers_row = [
                    "ID",
                    "Timestamp",
                    "Prediction",
                    "Risk Level",
                    "Confidence",
                    "Temp (°C)",
                    "Humidity (%)",
                    "Precip (mm)",
                    "Model Version",
                ]
                rows = [
                    [
                        record.id,
                        record.created_at.strftime("%Y-%m-%d %H:%M") if record.created_at else "",
                        record.prediction,
                        record.risk_level,
                        f"{record.confidence:.2f}" if record.confidence is not None else "",
                        getattr(record, "temperature", ""),
                        getattr(record, "humidity", ""),
                        getattr(record, "precipitation", ""),
                        record.model_version,
                    ]
                    for record in predictions
                ]
                date_range = ""
                if start_date and end_date:
                    date_range = f" ({start_date} to {end_date})"
                elif start_date:
                    date_range = f" (from {start_date})"
                elif end_date:
                    date_range = f" (to {end_date})"

                pdf_bytes = _build_pdf(
                    title="Flood Predictions Report",
                    subtitle=f"Floodingnaque – Historical Flood Prediction Data{date_range}",
                    headers=headers_row,
                    rows=rows,
                )
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename=predictions_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.pdf',
                        "Content-Length": str(len(pdf_bytes)),
                    },
                )
            except ImportError:
                logger.error("reportlab is not installed; cannot generate PDF")
                return jsonify({"error": "PDF generation not available on this server"}), 503

        # Export as JSON
        else:
            data_list = []
            for record in predictions:
                data_list.append(
                    {
                        "id": record.id,
                        "timestamp": record.created_at.isoformat() if record.created_at else None,
                        "prediction": record.prediction,
                        "risk_level": record.risk_level,
                        "confidence": record.confidence,
                        "temperature": getattr(record, "temperature", None),
                        "humidity": getattr(record, "humidity", None),
                        "precipitation": getattr(record, "precipitation", None),
                        "model_version": record.model_version,
                    }
                )

            return jsonify({"data": data_list, "count": len(data_list), "format": "json"}), 200

    except Exception as e:
        logger.error(f"Error exporting predictions: {e}")
        return jsonify({"error": "Internal server error"}), 500
