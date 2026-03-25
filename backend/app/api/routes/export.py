"""
Data Export API.

Endpoints for exporting historical weather and prediction data
in CSV, JSON, and PDF formats.  Professional PDF layout includes
cover page, table of contents, data table, and privacy notice.
"""

import csv
import logging
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Any

from app.api.middleware.auth import require_auth_or_api_key, require_scope
from app.api.middleware.rate_limit import limiter
from app.models.db import AlertHistory, Prediction, WeatherData, get_db_session
from app.models.evacuation_center import EvacuationCenter
from flask import Blueprint, Response, g, jsonify, request

logger = logging.getLogger(__name__)

export_bp = Blueprint("export", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_user_label() -> str:
    """Best-effort extraction of current user identity for report metadata."""
    user = getattr(g, "current_user", None) or getattr(g, "user", None)
    if user:
        if hasattr(user, "email"):
            return str(user.email)
        if isinstance(user, dict):
            return user.get("email", user.get("sub", "System Administrator"))
    return "System Administrator"


def _date_range_label(start_date: str | None, end_date: str | None) -> str:
    if start_date and end_date:
        return f"{start_date} to {end_date}"
    if start_date:
        return f"From {start_date}"
    if end_date:
        return f"Up to {end_date}"
    return "All available data"


def _log_export(
    report_type: str,
    export_format: str,
    start_date: str | None,
    end_date: str | None,
    record_count: int,
    status: str,
    error_msg: str = "",
) -> None:
    """Log every report generation attempt for audit purposes."""
    extra = {
        "report_type": report_type,
        "format": export_format,
        "date_range": _date_range_label(start_date, end_date),
        "record_count": record_count,
        "user": _current_user_label(),
        "status": status,
    }
    if status == "success":
        logger.info("Report generated: %s %s (%d records)", report_type, export_format, record_count, extra=extra)
    else:
        logger.warning("Report generation failed: %s %s – %s", report_type, export_format, error_msg, extra=extra)


# ---------------------------------------------------------------------------
# CSV helper
# ---------------------------------------------------------------------------


def _build_csv(
    report_title: str,
    headers: list[str],
    rows: list[list[Any]],
    date_range: str = "",
) -> str:
    """Generate a clean CSV with metadata header, human-readable columns, and UTF-8 BOM."""
    output = StringIO()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    writer = csv.writer(output)

    # Row 1: metadata
    writer.writerow(["Report Type", report_title, "Date Range", date_range or "All data", "Generated At", generated_at])
    # Row 2: blank separator
    writer.writerow([])
    # Row 3: column headers
    writer.writerow(headers)
    # Row 4+: data
    for row in rows:
        writer.writerow(row)

    # UTF-8 BOM prefix so Excel auto-detects encoding
    return "\ufeff" + output.getvalue()


# ---------------------------------------------------------------------------
# PDF helper – professional layout
# ---------------------------------------------------------------------------


def _build_pdf(
    title: str,
    subtitle: str,
    headers: list[str],
    rows: list[list[Any]],
    date_range: str = "",
    report_type: str = "",
) -> bytes:
    """Generate a professional PDF report with cover page, ToC, page numbers, and privacy notice.

    Raises ImportError if reportlab is not installed.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = BytesIO()
    page_size = landscape(A4)
    page_w, page_h = page_size
    generated_at_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    user_label = _current_user_label()

    # ---- page header / footer drawn on every page ----
    pdf_title_for_footer = title

    def _draw_header_footer(canvas, doc):
        canvas.saveState()
        # Top rule
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.setLineWidth(0.5)
        canvas.line(1.5 * cm, page_h - 1.3 * cm, page_w - 1.5 * cm, page_h - 1.3 * cm)
        # Bottom rule
        canvas.line(1.5 * cm, 1.6 * cm, page_w - 1.5 * cm, 1.6 * cm)
        # Footer text
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748b"))
        footer_y = 1.0 * cm
        canvas.drawString(1.5 * cm, footer_y, pdf_title_for_footer)
        canvas.drawCentredString(page_w / 2, footer_y, f"Generated: {generated_at_str}")
        canvas.drawRightString(page_w - 1.5 * cm, footer_y, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2.0 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    cover_org = ParagraphStyle(
        "CoverOrg",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#1e40af"),
        alignment=1,
        spaceAfter=4,
    )
    cover_title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontSize=22,
        alignment=1,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=8,
    )
    cover_subtitle = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontSize=11,
        alignment=1,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=16,
    )
    section_heading = ParagraphStyle(
        "SectionH", parent=styles["Heading2"], fontSize=14, spaceAfter=8, textColor=colors.HexColor("#1e293b")
    )
    toc_entry = ParagraphStyle("TOC", parent=styles["Normal"], fontSize=10, leftIndent=1 * cm, spaceAfter=6)
    privacy_style = ParagraphStyle(
        "Privacy", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#64748b"), leading=12
    )
    meta_key = ParagraphStyle("MK", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#64748b"))
    meta_val = ParagraphStyle("MV", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")

    story: list[Any] = []

    # ======================= COVER PAGE =======================
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("Parañaque City Disaster Risk Reduction<br/>& Management Office (DRRMO)", cover_org))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="50%", color=colors.HexColor("#1e40af"), thickness=2, spaceAfter=1 * cm))
    story.append(Paragraph(title, cover_title))
    if subtitle:
        story.append(Paragraph(subtitle, cover_subtitle))
    story.append(Spacer(1, 1.5 * cm))

    # Cover metadata table
    meta_rows_data = [
        [Paragraph("Report Type:", meta_key), Paragraph(report_type or title, meta_val)],
        [Paragraph("Date Range:", meta_key), Paragraph(date_range or "All available data", meta_val)],
        [Paragraph("Generated By:", meta_key), Paragraph(user_label, meta_val)],
        [Paragraph("Generated At:", meta_key), Paragraph(generated_at_str, meta_val)],
        [Paragraph("Total Records:", meta_key), Paragraph(str(len(rows)), meta_val)],
    ]
    meta_table = Table(meta_rows_data, colWidths=[4 * cm, 10 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(meta_table)
    story.append(PageBreak())

    # ======================= TABLE OF CONTENTS =======================
    story.append(Paragraph("Table of Contents", section_heading))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("1. Report Summary (Cover Page)", toc_entry))
    story.append(Paragraph("2. Data Records", toc_entry))
    story.append(Paragraph("3. Privacy & Data Protection Notice", toc_entry))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.5))
    story.append(PageBreak())

    # ======================= DATA TABLE =======================
    story.append(Paragraph("Data Records", section_heading))
    story.append(Spacer(1, 0.3 * cm))

    if rows:
        table_data = [headers] + [[str(c) if c is not None else "" for c in row] for row in rows]
        col_count = len(headers)
        available_width = page_w - 3 * cm
        col_width = available_width / col_count

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
                    ("TOPPADDING", (0, 0), (-1, 0), 6),
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
    else:
        no_data = ParagraphStyle(
            "NoData",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#64748b"),
            alignment=1,
            spaceBefore=2 * cm,
        )
        story.append(Paragraph("No records found for the selected date range and criteria.", no_data))

    story.append(Spacer(1, 0.5 * cm))
    rc_style = ParagraphStyle("RC", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#94a3b8"))
    story.append(Paragraph(f"Total Records: {len(rows)}", rc_style))
    story.append(PageBreak())

    # ======================= PRIVACY NOTICE =======================
    story.append(Paragraph("Privacy & Data Protection Notice", section_heading))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "This report is generated by the Floodingnaque Flood Prediction System for Parañaque City "
            "and is intended solely for authorized personnel of the Disaster Risk Reduction & Management "
            "Office (DRRMO) and affiliated agencies.",
            privacy_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "This document may contain sensitive location data, timing information, and personally "
            "identifiable information (PII). Recipients must handle this report in accordance with the "
            "Data Privacy Act of 2012 (Republic Act No. 10173) and applicable local data protection "
            "policies.",
            privacy_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "Unauthorized reproduction, distribution, or disclosure of this report or its contents is "
            "strictly prohibited. If you have received this report in error, please notify the DRRMO "
            "immediately and destroy all copies.",
            privacy_style,
        )
    )

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Count endpoints (pre-export row estimation)
# ---------------------------------------------------------------------------


def _parse_date_filter(start_str: str | None, end_str: str | None):
    """Parse date filter strings and return datetime objects."""
    start_dt = None
    end_dt = None
    if start_str:
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        except ValueError:
            pass
    if end_str:
        try:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d")
        except ValueError:
            pass
    return start_dt, end_dt


@export_bp.route("/weather/count", methods=["GET"])
@require_auth_or_api_key
@require_scope("data")
@limiter.limit("30 per minute")
def count_weather():
    """Return estimated row count for weather export with current filters."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    source = request.args.get("source")
    start_dt, end_dt = _parse_date_filter(start_date, end_date)

    try:
        from sqlalchemy import func as sa_func

        with get_db_session() as session:
            q = session.query(sa_func.count(WeatherData.id)).filter(WeatherData.is_deleted.is_(False))
            if start_dt:
                q = q.filter(WeatherData.timestamp >= start_dt)
            if end_dt:
                q = q.filter(WeatherData.timestamp <= end_dt)
            if source:
                q = q.filter(WeatherData.source == source)
            count = q.scalar() or 0
        return jsonify({"success": True, "count": count}), 200
    except Exception:
        return jsonify({"success": False, "count": 0}), 500


@export_bp.route("/predictions/count", methods=["GET"])
@require_auth_or_api_key
@require_scope("data")
@limiter.limit("30 per minute")
def count_predictions():
    """Return estimated row count for predictions export with current filters."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    risk_level = request.args.get("risk_level")
    start_dt, end_dt = _parse_date_filter(start_date, end_date)

    try:
        from sqlalchemy import func as sa_func

        with get_db_session() as session:
            q = session.query(sa_func.count(Prediction.id)).filter(Prediction.is_deleted.is_(False))
            if start_dt:
                q = q.filter(Prediction.created_at >= start_dt)
            if end_dt:
                q = q.filter(Prediction.created_at <= end_dt)
            if risk_level:
                q = q.filter(Prediction.risk_level == risk_level)
            count = q.scalar() or 0
        return jsonify({"success": True, "count": count}), 200
    except Exception:
        return jsonify({"success": False, "count": 0}), 500


@export_bp.route("/alerts/count", methods=["GET"])
@require_auth_or_api_key
@require_scope("data")
@limiter.limit("30 per minute")
def count_alerts():
    """Return estimated row count for alerts export with current filters."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    risk_level = request.args.get("risk_level", type=int)
    start_dt, end_dt = _parse_date_filter(start_date, end_date)

    try:
        from sqlalchemy import func as sa_func

        with get_db_session() as session:
            q = session.query(sa_func.count(AlertHistory.id)).filter(AlertHistory.is_deleted.is_(False))
            if start_dt:
                q = q.filter(AlertHistory.created_at >= start_dt)
            if end_dt:
                q = q.filter(AlertHistory.created_at <= end_dt)
            if risk_level is not None:
                q = q.filter(AlertHistory.risk_level == risk_level)
            count = q.scalar() or 0
        return jsonify({"success": True, "count": count}), 200
    except Exception:
        return jsonify({"success": False, "count": 0}), 500


@export_bp.route("/weather", methods=["GET"])
@require_auth_or_api_key
@require_scope("data")
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
        source = request.args.get("source")
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

            if source:
                query = query.filter(WeatherData.source == source)

            # Order and limit
            query = query.order_by(WeatherData.timestamp.desc()).limit(limit)

            # Execute query and materialise to dicts inside session
            weather_data = [
                {
                    "id": r.id,
                    "timestamp": r.timestamp,
                    "temperature": r.temperature,
                    "humidity": r.humidity,
                    "precipitation": r.precipitation,
                    "wind_speed": r.wind_speed,
                    "pressure": r.pressure,
                    "location_lat": r.location_lat,
                    "location_lon": r.location_lon,
                    "source": r.source,
                }
                for r in query.all()
            ]

        date_range_label = _date_range_label(start_date, end_date)

        # Export as CSV
        if export_format == "csv":
            csv_headers = [
                "ID",
                "Timestamp",
                "Temperature (°C)",
                "Humidity (%)",
                "Precipitation (mm)",
                "Wind Speed (m/s)",
                "Pressure (hPa)",
                "Latitude",
                "Longitude",
                "Source",
            ]
            csv_rows = [
                [
                    record["id"],
                    record["timestamp"].isoformat() if record["timestamp"] else "",
                    record["temperature"],
                    record["humidity"],
                    record["precipitation"],
                    record["wind_speed"],
                    record["pressure"],
                    record["location_lat"],
                    record["location_lon"],
                    record["source"],
                ]
                for record in weather_data
            ]
            csv_data = _build_csv("Weather Data Report", csv_headers, csv_rows, date_range_label)
            _log_export("weather", "csv", start_date, end_date, len(weather_data), "success")

            return Response(
                csv_data,
                mimetype="text/csv; charset=utf-8",
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
                    "Source",
                ]
                rows = [
                    [
                        record["id"],
                        record["timestamp"].strftime("%Y-%m-%d %H:%M") if record["timestamp"] else "",
                        record["temperature"],
                        record["humidity"],
                        record["precipitation"],
                        record["wind_speed"],
                        record["pressure"],
                        record["location_lat"],
                        record["location_lon"],
                        record["source"],
                    ]
                    for record in weather_data
                ]
                pdf_bytes = _build_pdf(
                    title="Weather Data Report",
                    subtitle="Floodingnaque – Historical Weather Observations",
                    headers=headers_row,
                    rows=rows,
                    date_range=date_range_label,
                    report_type="Weather Data Report",
                )
                _log_export("weather", "pdf", start_date, end_date, len(weather_data), "success")
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename=weather_data_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.pdf',
                        "Content-Length": str(len(pdf_bytes)),
                    },
                )
            except ImportError:
                _log_export("weather", "pdf", start_date, end_date, 0, "error", "reportlab not installed")
                logger.error("reportlab is not installed; cannot generate PDF")
                return jsonify({"error": "PDF generation not available on this server"}), 503

        # Export as JSON (default)
        data_list = [
            {
                "id": record["id"],
                "timestamp": record["timestamp"].isoformat() if record["timestamp"] else None,
                "temperature": record["temperature"],
                "humidity": record["humidity"],
                "precipitation": record["precipitation"],
                "wind_speed": record["wind_speed"],
                "pressure": record["pressure"],
                "location_lat": record["location_lat"],
                "location_lon": record["location_lon"],
                "source": record["source"],
            }
            for record in weather_data
        ]
        _log_export("weather", "json", start_date, end_date, len(data_list), "success")
        return jsonify({"data": data_list, "count": len(data_list), "format": "json"}), 200

    except Exception as e:
        _log_export(
            "weather",
            request.args.get("format", "json"),
            request.args.get("start_date"),
            request.args.get("end_date"),
            0,
            "error",
            str(e),
        )
        logger.error(f"Error exporting weather data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@export_bp.route("/predictions", methods=["GET"])
@require_auth_or_api_key
@require_scope("data")
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

            # Execute query and materialise to dicts inside session
            predictions = [
                {
                    "id": r.id,
                    "created_at": r.created_at,
                    "prediction": r.prediction,
                    "risk_level": r.risk_level,
                    "confidence": r.confidence,
                    "temperature": getattr(r, "temperature", None),
                    "humidity": getattr(r, "humidity", None),
                    "precipitation": getattr(r, "precipitation", None),
                    "model_version": r.model_version,
                }
                for r in query.all()
            ]

        date_range_label = _date_range_label(start_date, end_date)

        # Export as CSV
        if export_format == "csv":
            csv_headers = [
                "ID",
                "Timestamp",
                "Prediction",
                "Risk Level",
                "Confidence",
                "Temperature (°C)",
                "Humidity (%)",
                "Precipitation (mm)",
                "Model Version",
            ]
            csv_rows = [
                [
                    record["id"],
                    record["created_at"].isoformat() if record["created_at"] else "",
                    record["prediction"],
                    record["risk_level"],
                    record["confidence"],
                    record["temperature"],
                    record["humidity"],
                    record["precipitation"],
                    record["model_version"],
                ]
                for record in predictions
            ]
            csv_data = _build_csv("Flood Predictions Report", csv_headers, csv_rows, date_range_label)
            _log_export("predictions", "csv", start_date, end_date, len(predictions), "success")

            return Response(
                csv_data,
                mimetype="text/csv; charset=utf-8",
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
                        record["id"],
                        record["created_at"].strftime("%Y-%m-%d %H:%M") if record["created_at"] else "",
                        record["prediction"],
                        record["risk_level"],
                        f"{record['confidence']:.2f}" if record["confidence"] is not None else "",
                        record["temperature"] or "",
                        record["humidity"] or "",
                        record["precipitation"] or "",
                        record["model_version"],
                    ]
                    for record in predictions
                ]
                pdf_bytes = _build_pdf(
                    title="Flood Predictions Report",
                    subtitle="Floodingnaque – Historical Flood Prediction Data",
                    headers=headers_row,
                    rows=rows,
                    date_range=date_range_label,
                    report_type="Flood Predictions Report",
                )
                _log_export("predictions", "pdf", start_date, end_date, len(predictions), "success")
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename=predictions_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.pdf',
                        "Content-Length": str(len(pdf_bytes)),
                    },
                )
            except ImportError:
                _log_export("predictions", "pdf", start_date, end_date, 0, "error", "reportlab not installed")
                logger.error("reportlab is not installed; cannot generate PDF")
                return jsonify({"error": "PDF generation not available on this server"}), 503

        # Export as JSON (default)
        data_list = [
            {
                "id": record["id"],
                "timestamp": record["created_at"].isoformat() if record["created_at"] else None,
                "prediction": record["prediction"],
                "risk_level": record["risk_level"],
                "confidence": record["confidence"],
                "temperature": record["temperature"],
                "humidity": record["humidity"],
                "precipitation": record["precipitation"],
                "model_version": record["model_version"],
            }
            for record in predictions
        ]
        _log_export("predictions", "json", start_date, end_date, len(data_list), "success")
        return jsonify({"data": data_list, "count": len(data_list), "format": "json"}), 200

    except Exception as e:
        _log_export(
            "predictions",
            request.args.get("format", "json"),
            request.args.get("start_date"),
            request.args.get("end_date"),
            0,
            "error",
            str(e),
        )
        logger.error(f"Error exporting predictions: {e}")
        return jsonify({"error": "Internal server error"}), 500


@export_bp.route("/alerts", methods=["GET"])
@require_auth_or_api_key
@require_scope("data")
@limiter.limit("5 per minute")
def export_alerts():
    """
    Export alert / incident history (DRRMO report).

    Query Parameters:
        format: csv, json, or pdf (default: json)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        risk_level: Filter by risk level (0, 1, 2)
        limit: Maximum records (default: 1000, max: 10000)

    Returns:
        200: Exported data
        400: Invalid parameters
    """
    try:
        export_format = request.args.get("format", "json").lower()
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        risk_level = request.args.get("risk_level", type=int)
        limit = int(request.args.get("limit", 1000))

        if export_format not in ["csv", "json", "pdf"]:
            return jsonify({"error": "Invalid format. Must be csv, json, or pdf"}), 400

        max_limit = 10000
        if limit > max_limit:
            return jsonify({"error": f"Limit exceeds maximum of {max_limit}"}), 400

        with get_db_session() as session:
            query = session.query(AlertHistory).filter(AlertHistory.is_deleted.is_(False))

            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(AlertHistory.created_at >= start_dt)
                except ValueError:
                    return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    query = query.filter(AlertHistory.created_at <= end_dt)
                except ValueError:
                    return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

            if risk_level is not None:
                query = query.filter(AlertHistory.risk_level == risk_level)

            query = query.order_by(AlertHistory.created_at.desc()).limit(limit)

            # Execute query and materialise to dicts inside session
            alerts = [
                {
                    "id": r.id,
                    "created_at": r.created_at,
                    "risk_level": r.risk_level,
                    "risk_label": r.risk_label,
                    "location": r.location,
                    "message": r.message,
                    "delivery_status": r.delivery_status,
                    "delivery_channel": r.delivery_channel,
                    "delivered_at": r.delivered_at,
                }
                for r in query.all()
            ]

        date_range_label = _date_range_label(start_date, end_date)

        # Export as CSV
        if export_format == "csv":
            csv_headers = [
                "ID",
                "Created At",
                "Risk Level",
                "Risk Label",
                "Location",
                "Message",
                "Delivery Status",
                "Channel",
                "Delivered At",
            ]
            csv_rows = [
                [
                    rec["id"],
                    rec["created_at"].isoformat() if rec["created_at"] else "",
                    rec["risk_level"],
                    rec["risk_label"],
                    rec["location"],
                    rec["message"],
                    rec["delivery_status"],
                    rec["delivery_channel"],
                    rec["delivered_at"].isoformat() if rec["delivered_at"] else "",
                ]
                for rec in alerts
            ]
            csv_data = _build_csv("DRRMO Incident Report", csv_headers, csv_rows, date_range_label)
            _log_export("alerts", "csv", start_date, end_date, len(alerts), "success")

            return Response(
                csv_data,
                mimetype="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=drrmo_incident_report_"
                        f'{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.csv'
                    )
                },
            )

        # Export as PDF
        if export_format == "pdf":
            try:
                headers_row = [
                    "ID",
                    "Timestamp",
                    "Risk Level",
                    "Risk Label",
                    "Location",
                    "Message",
                    "Status",
                    "Channel",
                    "Delivered At",
                ]
                rows = [
                    [
                        rec["id"],
                        rec["created_at"].strftime("%Y-%m-%d %H:%M") if rec["created_at"] else "",
                        rec["risk_level"],
                        rec["risk_label"],
                        rec["location"] or "",
                        (rec["message"] or "")[:80],
                        rec["delivery_status"],
                        rec["delivery_channel"],
                        rec["delivered_at"].strftime("%Y-%m-%d %H:%M") if rec["delivered_at"] else "",
                    ]
                    for rec in alerts
                ]
                pdf_bytes = _build_pdf(
                    title="DRRMO Incident Report",
                    subtitle="Floodingnaque – Alert History & Incident Log",
                    headers=headers_row,
                    rows=rows,
                    date_range=date_range_label,
                    report_type="DRRMO Incident Report",
                )
                _log_export("alerts", "pdf", start_date, end_date, len(alerts), "success")
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={
                        "Content-Disposition": (
                            f"attachment; filename=drrmo_incident_report_"
                            f'{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.pdf'
                        ),
                        "Content-Length": str(len(pdf_bytes)),
                    },
                )
            except ImportError:
                _log_export("alerts", "pdf", start_date, end_date, 0, "error", "reportlab not installed")
                logger.error("reportlab is not installed; cannot generate PDF")
                return jsonify({"error": "PDF generation not available on this server"}), 503

        # Export as JSON (default)
        data_list = [
            {
                "id": rec["id"],
                "created_at": rec["created_at"].isoformat() if rec["created_at"] else None,
                "risk_level": rec["risk_level"],
                "risk_label": rec["risk_label"],
                "location": rec["location"],
                "message": rec["message"],
                "delivery_status": rec["delivery_status"],
                "delivery_channel": rec["delivery_channel"],
                "delivered_at": rec["delivered_at"].isoformat() if rec["delivered_at"] else None,
            }
            for rec in alerts
        ]
        _log_export("alerts", "json", start_date, end_date, len(data_list), "success")
        return jsonify({"data": data_list, "count": len(data_list), "format": "json"}), 200

    except Exception as e:
        _log_export(
            "alerts",
            request.args.get("format", "json"),
            request.args.get("start_date"),
            request.args.get("end_date"),
            0,
            "error",
            str(e),
        )
        logger.error(f"Error exporting alerts: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Model Metrics export
# ---------------------------------------------------------------------------


@export_bp.route("/model-metrics", methods=["GET"])
@require_auth_or_api_key
@require_scope("data")
@limiter.limit("5 per minute")
def export_model_metrics():
    """
    Export ML model performance metrics.

    Returns model version, accuracy, precision, recall, F1, feature
    importance, and progressive training history in CSV, JSON, or PDF.

    Query Parameters:
        format: csv, json, or pdf (default: json)
    """
    export_format = request.args.get("format", "json").lower()
    if export_format not in ("csv", "json", "pdf"):
        return jsonify({"error": "Invalid format. Must be csv, json, or pdf"}), 400

    try:
        from app.services.predict import get_model_metadata

        metadata = get_model_metadata()
        if not metadata:
            _log_export("model-metrics", export_format, None, None, 0, "error", "No model metadata found")
            return jsonify({"error": "No model metadata available"}), 404

        # ── Assemble rows: one per metric + feature importance rows ────────
        metrics = metadata.get("metrics", {})
        version = metadata.get("version", "unknown")
        trained_at = metadata.get("trained_at", metadata.get("date", "N/A"))
        features = metadata.get("features", metadata.get("feature_names", []))
        importance = metadata.get("feature_importance", {})

        summary_rows: list[list[Any]] = [
            ["Model Version", version, ""],
            ["Trained At", trained_at, ""],
            ["Accuracy", str(metrics.get("accuracy", "N/A")), ""],
            ["Precision", str(metrics.get("precision", "N/A")), ""],
            ["Recall", str(metrics.get("recall", "N/A")), ""],
            ["F1 Score", str(metrics.get("f1_score", metrics.get("f1", "N/A"))), ""],
            ["ROC AUC", str(metrics.get("roc_auc", "N/A")), ""],
            ["Cross-validation Mean", str(metrics.get("cv_mean", "N/A")), ""],
            ["Training Samples", str(metrics.get("training_samples", metadata.get("n_samples", "N/A"))), ""],
        ]

        # Add feature importance rows
        if importance:
            summary_rows.append(["", "", ""])
            summary_rows.append(["FEATURE IMPORTANCE", "", ""])
            for feat_name, feat_val in sorted(importance.items(), key=lambda x: -float(x[1]) if x[1] else 0):
                summary_rows.append([feat_name, str(feat_val), "feature_importance"])
        elif features:
            summary_rows.append(["", "", ""])
            summary_rows.append(["FEATURES USED", "", ""])
            for feat in features:
                summary_rows.append([feat, "", "feature"])

        headers = ["Metric", "Value", "Category"]
        record_count = len(summary_rows)

        if export_format == "csv":
            csv_data = _build_csv("ML Model Performance Report", headers, summary_rows)
            _log_export("model-metrics", "csv", None, None, record_count, "success")
            return Response(
                csv_data,
                mimetype="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename=model_metrics_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.csv'
                },
            )

        if export_format == "pdf":
            try:
                pdf_bytes = _build_pdf(
                    title="ML Model Performance Report",
                    subtitle=f"Floodingnaque – Model {version} Evaluation Metrics",
                    headers=headers,
                    rows=summary_rows,
                    report_type="ML Model Performance",
                )
                _log_export("model-metrics", "pdf", None, None, record_count, "success")
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename=model_metrics_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.pdf',
                        "Content-Length": str(len(pdf_bytes)),
                    },
                )
            except ImportError:
                _log_export("model-metrics", "pdf", None, None, 0, "error", "reportlab not installed")
                return jsonify({"error": "PDF generation not available on this server"}), 503

        # JSON default
        _log_export("model-metrics", "json", None, None, record_count, "success")
        return jsonify({
            "data": {
                "version": version,
                "trained_at": trained_at,
                "metrics": metrics,
                "features": features,
                "feature_importance": importance,
            },
            "format": "json",
        }), 200

    except Exception as e:
        _log_export("model-metrics", export_format, None, None, 0, "error", str(e))
        logger.error(f"Error exporting model metrics: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Disaster Preparedness export
# ---------------------------------------------------------------------------


@export_bp.route("/disaster-preparedness", methods=["GET"])
@require_auth_or_api_key
@require_scope("data")
@limiter.limit("5 per minute")
def export_disaster_preparedness():
    """
    Export disaster preparedness report based on evacuation center data.

    Includes shelter capacity, current occupancy, barangay coverage, and
    readiness status for all registered evacuation centers.

    Query Parameters:
        format: csv, json, or pdf (default: json)
    """
    export_format = request.args.get("format", "json").lower()
    if export_format not in ("csv", "json", "pdf"):
        return jsonify({"error": "Invalid format. Must be csv, json, or pdf"}), 400

    try:
        with get_db_session() as session:
            centers = (
                session.query(EvacuationCenter)
                .filter(EvacuationCenter.is_deleted.is_(False))
                .order_by(EvacuationCenter.barangay)
                .all()
            )
            center_dicts = [c.to_dict() for c in centers]

        if not center_dicts:
            _log_export("disaster-preparedness", export_format, None, None, 0, "error", "No evacuation centers")
            return jsonify({"error": "No evacuation center data available"}), 404

        # ── Compute summary stats ─────────────────────────────────────────
        total_centers = len(center_dicts)
        active_centers = sum(1 for c in center_dicts if c["is_active"])
        total_capacity = sum(c["capacity_total"] for c in center_dicts)
        total_occupancy = sum(c["capacity_current"] for c in center_dicts)
        total_available = sum(c["available_slots"] for c in center_dicts)
        barangays_covered = len({c["barangay"] for c in center_dicts})
        overall_occupancy_pct = round(total_occupancy / total_capacity * 100, 1) if total_capacity else 0

        headers = [
            "Center Name",
            "Barangay",
            "Address",
            "Capacity",
            "Current Occupancy",
            "Available Slots",
            "Occupancy %",
            "Status",
            "Contact",
        ]
        rows: list[list[Any]] = [
            [
                c["name"],
                c["barangay"],
                c["address"],
                c["capacity_total"],
                c["capacity_current"],
                c["available_slots"],
                f'{c["occupancy_pct"]}%',
                "Active" if c["is_active"] else "Inactive",
                c["contact_number"] or "",
            ]
            for c in center_dicts
        ]

        # Append summary section
        rows.append([""] * len(headers))
        rows.append(["SUMMARY", "", "", "", "", "", "", "", ""])
        rows.append(["Total Centers", str(total_centers), "", "", "", "", "", "", ""])
        rows.append(["Active Centers", str(active_centers), "", "", "", "", "", "", ""])
        rows.append(["Barangays Covered", str(barangays_covered), "", "", "", "", "", "", ""])
        rows.append(["Total Capacity", str(total_capacity), "", "", "", "", "", "", ""])
        rows.append(["Current Occupancy", str(total_occupancy), "", "", "", "", "", "", ""])
        rows.append(["Available Slots", str(total_available), "", "", "", "", "", "", ""])
        rows.append(["Overall Occupancy", f"{overall_occupancy_pct}%", "", "", "", "", "", "", ""])

        record_count = len(center_dicts)

        if export_format == "csv":
            csv_data = _build_csv("Disaster Preparedness Report", headers, rows)
            _log_export("disaster-preparedness", "csv", None, None, record_count, "success")
            return Response(
                csv_data,
                mimetype="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=disaster_preparedness_"
                        f'{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.csv'
                    )
                },
            )

        if export_format == "pdf":
            try:
                pdf_bytes = _build_pdf(
                    title="Disaster Preparedness Report",
                    subtitle="Floodingnaque – Evacuation Center Readiness & Shelter Capacity",
                    headers=headers,
                    rows=rows,
                    report_type="Disaster Preparedness",
                )
                _log_export("disaster-preparedness", "pdf", None, None, record_count, "success")
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={
                        "Content-Disposition": (
                            f"attachment; filename=disaster_preparedness_"
                            f'{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.pdf'
                        ),
                        "Content-Length": str(len(pdf_bytes)),
                    },
                )
            except ImportError:
                _log_export("disaster-preparedness", "pdf", None, None, 0, "error", "reportlab not installed")
                return jsonify({"error": "PDF generation not available on this server"}), 503

        # JSON default
        _log_export("disaster-preparedness", "json", None, None, record_count, "success")
        return jsonify({
            "data": {
                "summary": {
                    "total_centers": total_centers,
                    "active_centers": active_centers,
                    "barangays_covered": barangays_covered,
                    "total_capacity": total_capacity,
                    "total_occupancy": total_occupancy,
                    "total_available": total_available,
                    "overall_occupancy_pct": overall_occupancy_pct,
                },
                "centers": center_dicts,
            },
            "count": record_count,
            "format": "json",
        }), 200

    except Exception as e:
        _log_export("disaster-preparedness", export_format, None, None, 0, "error", str(e))
        logger.error(f"Error exporting disaster preparedness data: {e}")
        return jsonify({"error": "Internal server error"}), 500
