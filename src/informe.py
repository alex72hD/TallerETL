"""Genera el informe PDF del proceso ETL de Airbnb Bogotá."""

from __future__ import annotations

import argparse
import io
import json
import logging
import sqlite3
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter
from pymongo import MongoClient
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.etl_common import PROJECT_ROOT, get_mongodb_settings


COLECCIONES = ("Listings", "Reviews", "Calendar")
NOMBRES = {
    "Listings": "Alojamientos (Listings)",
    "Reviews": "Reseñas (Reviews)",
    "Calendar": "Calendario (Calendar)",
}
AZUL = colors.HexColor("#123A5A")
VERDE = colors.HexColor("#159A8C")


def _contar_nulos(collection, fields: list[str]) -> dict[str, int]:
    if not fields:
        return {}
    group = {"_id": None}
    for field in fields:
        group[field] = {
            "$sum": {
                "$cond": [
                    {"$eq": [{"$ifNull": [f"${field}", None]}, None]},
                    1,
                    0,
                ]
            }
        }
    result = next(collection.aggregate([{"$group": group}]), None)
    return {field: int(result[field]) for field in fields} if result else {}


def _estadisticas_outliers(frame: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    stats: dict[str, dict[str, float | int]] = {}
    for field in ("price", "minimum_nights", "availability_365"):
        if field not in frame:
            continue
        values = pd.to_numeric(frame[field], errors="coerce").dropna()
        if values.empty:
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        inliers = values[(values >= low) & (values <= high)]
        stats[field] = {
            "n": len(values),
            "nulls": int(frame[field].isna().sum()),
            "min": float(values.min()),
            "q1": float(q1),
            "median": float(values.median()),
            "q3": float(q3),
            "max": float(values.max()),
            "whislo": float(inliers.min()),
            "whishi": float(inliers.max()),
            "low": float(low),
            "high": float(high),
            "outliers": int(((values < low) | (values > high)).sum()),
        }
    return stats


def _collect_data() -> dict:
    uri, database = get_mongodb_settings()
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        db = client[database]
        present = set(db.list_collection_names())
        missing = [name for name in COLECCIONES if name not in present]
        if missing:
            raise ValueError(
                "Faltan colecciones requeridas en MongoDB: " + ", ".join(missing)
            )

        collections = {}
        nulls = {}
        for name in COLECCIONES:
            collection = db[name]
            sample = collection.find_one()
            fields = [field for field in (sample or {}) if field != "_id"]
            collections[name] = {
                "count": int(collection.estimated_document_count()),
                "source_fields": len(fields),
                "mongo_fields": len(fields) + (1 if sample and "_id" in sample else 0),
            }
            nulls[name] = _contar_nulos(collection, fields)

        listing_fields = {
            "_id": 0,
            "price": 1,
            "minimum_nights": 1,
            "availability_365": 1,
            "room_type": 1,
            "neighbourhood_cleansed": 1,
        }
        listings = pd.DataFrame(list(db["Listings"].find({}, listing_fields)))
        outliers = _estadisticas_outliers(listings)

        monthly = list(
            db["Calendar"].aggregate(
                [
                    {
                        "$group": {
                            "_id": {"$substr": ["$date", 0, 7]},
                            "records": {"$sum": 1},
                        }
                    },
                    {"$sort": {"_id": 1}},
                ],
                maxTimeMS=180_000,
                allowDiskUse=True,
            )
        )
        quote = db["Listings"].find_one(
            {"price_quote_raw": {"$exists": True, "$ne": None}},
            {"price_quote_raw": 1, "_id": 0},
        )
        currency = None
        raw_quote = (quote or {}).get("price_quote_raw")
        if isinstance(raw_quote, str):
            try:
                raw_quote = json.loads(raw_quote)
            except json.JSONDecodeError:
                raw_quote = None
        if isinstance(raw_quote, dict):
            currency = (
                raw_quote.get("quote", {}).get("currency")
                if isinstance(raw_quote.get("quote"), dict)
                else raw_quote.get("currency")
            )

        return {
            "database": database,
            "collections": collections,
            "nulls": nulls,
            "outliers": outliers,
            "monthly": monthly,
            "currency": currency,
        }
    finally:
        client.close()


def _image_buffer(figure) -> io.BytesIO:
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
    plt.close(figure)
    buffer.seek(0)
    return buffer


def _crear_graficos(data: dict) -> tuple[io.BytesIO, io.BytesIO]:
    outlier_stats = data["outliers"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    fields = (
        ("price", "Precio de noche"),
        ("minimum_nights", "Noches mínimas"),
        ("availability_365", "Disponibilidad anual"),
    )
    for axis, (field, title) in zip(axes, fields):
        stats = outlier_stats.get(field)
        axis.set_title(title)
        if stats is None:
            axis.text(0.5, 0.5, "Sin datos", ha="center", va="center")
            continue
        if field == "price":
            axis.set_xscale("log")
        axis.bxp(
            [
                {
                    "label": "",
                    "whislo": stats["whislo"],
                    "q1": stats["q1"],
                    "med": stats["median"],
                    "q3": stats["q3"],
                    "whishi": stats["whishi"],
                    "fliers": [],
                }
            ],
            vert=False,
            showfliers=False,
        )
        axis.set_yticks([])
        axis.set_xlabel("Escala logarítmica" if field == "price" else "Valor")
        axis.grid(axis="x", alpha=0.25)
    fig.suptitle("Distribución y resumen de variables de Listings")
    fig.tight_layout()
    outlier_chart = _image_buffer(fig)

    months = data["monthly"]
    fig, axis = plt.subplots(figsize=(11, 3.6))
    labels = [row["_id"] for row in months]
    values = [row["records"] for row in months]
    axis.bar(labels, values, color="#159A8C")
    axis.set_title("Registros del calendario por mes")
    axis.set_ylabel("Filas")
    axis.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"{value / 1000:.0f} mil")
    )
    axis.tick_params(axis="x", rotation=35)
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return outlier_chart, _image_buffer(fig)


def _register_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\arial.ttf")
    bold = Path(r"C:\Windows\Fonts\arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("ReportArial", str(regular)))
        pdfmetrics.registerFont(TTFont("ReportArial-Bold", str(bold)))
        return "ReportArial", "ReportArial-Bold"
    return "Helvetica", "Helvetica-Bold"


def _format_number(value: int | float) -> str:
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _status_etl() -> tuple[str, str]:
    output_db = PROJECT_ROOT / "output" / "airbnb.sqlite"
    workbooks = [
        PROJECT_ROOT / "output" / "excel" / f"{name.lower()}.xlsx"
        for name in COLECCIONES
    ]
    logs = sorted((PROJECT_ROOT / "logs").glob("log_*.log"))
    completed_log = next(
        (
            path
            for path in reversed(logs)
            if "Proceso ETL terminado correctamente" in path.read_text(
                encoding="utf-8", errors="replace"
            )
        ),
        None,
    )
    if completed_log and output_db.exists() and all(path.exists() for path in workbooks):
        with sqlite3.connect(output_db) as connection:
            counts = {
                name.lower(): connection.execute(
                    f'SELECT COUNT(*) FROM "{name.lower()}"'
                ).fetchone()[0]
                for name in COLECCIONES
            }
        return (
            "Se encontraron el log de finalización, la base SQLite y los tres "
            "libros XLSX. Filas verificables en SQLite: "
            + ", ".join(f"{key}: {_format_number(value)}" for key, value in counts.items())
            + ".",
            completed_log.read_text(encoding="utf-8", errors="replace"),
        )

    recent = logs[-1].read_text(encoding="utf-8", errors="replace") if logs else ""
    return (
        "La evidencia disponible confirma conexión y extracción, pero no un "
        "ciclo ETL completo con SQLite y XLSX. Ejecuta `python -m src.main` "
        "y vuelve a generar este informe antes de entregar si las salidas no existen.",
        recent,
    )


def _styles(font: str, bold_font: str) -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=bold_font,
            fontSize=25,
            leading=31,
            textColor=AZUL,
            alignment=TA_CENTER,
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName=font,
            fontSize=14,
            leading=19,
            textColor=colors.HexColor("#36566F"),
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "ReportH1",
            parent=base["Heading1"],
            fontName=bold_font,
            fontSize=16,
            leading=20,
            textColor=AZUL,
            spaceBefore=7,
            spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "ReportH2",
            parent=base["Heading2"],
            fontName=bold_font,
            fontSize=11,
            leading=15,
            textColor=VERDE,
            spaceBefore=7,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.2,
            leading=13.2,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontName=font,
            fontSize=8,
            leading=10,
        ),
        "cover": ParagraphStyle(
            "ReportCover",
            parent=base["Normal"],
            fontName=font,
            fontSize=11,
            leading=17,
            alignment=TA_CENTER,
        ),
    }


def generar_informe(output_path: str | Path | None = None) -> Path:
    """Consulta MongoDB y genera el informe PDF con resultados actuales."""
    data = _collect_data()
    output = Path(output_path or PROJECT_ROOT / "Informe_Taller_2_ETL_Airbnb_Bogota.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)

    font, bold_font = _register_fonts()
    styles = _styles(font, bold_font)
    outlier_chart, monthly_chart = _crear_graficos(data)
    status, log_text = _status_etl()
    document = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        title="Informe Taller 2 ETL Airbnb Bogotá",
        author="Robin Alexander Montoya Velasquez",
    )
    story = [
        Spacer(1, 2.0 * cm),
        Paragraph("INSTITUCIÓN UNIVERSITARIA ITM", styles["h2"]),
        Spacer(1, 1.3 * cm),
        Paragraph("INFORME FINAL<br/>TALLER EVALUATIVO 2", styles["title"]),
        Paragraph("Proceso ETL con los datasets de Airbnb Bogotá", styles["subtitle"]),
        Spacer(1, 1.1 * cm),
        Paragraph(
            "Inteligencia de negocios<br/><br/>"
            "<b>Estudiante:</b> Robin Alexander Montoya Velasquez<br/>"
            "<b>Modalidad:</b> trabajo individual<br/>"
            f"<b>Fecha:</b> {date.today().strftime('%d/%m/%Y')}<br/>"
            "Bogotá, Colombia",
            styles["cover"],
        ),
        PageBreak(),
        Paragraph("1. Introducción", styles["h1"]),
        Paragraph(
            "Este trabajo implementa un flujo ETL en Python para explorar y "
            "preparar los datos de alojamientos, reseñas y calendario de Airbnb "
            "en Bogotá. La fuente de extracción es MongoDB local, no los CSV "
            "directamente. El desarrollo y la documentación fueron realizados "
            "individualmente por el estudiante indicado en la portada.",
            styles["body"],
        ),
        Paragraph("2. Descripción de la fuente", styles["h1"]),
        Paragraph(
            f"La base consultada es <b>{escape(data['database'])}</b>. "
            "Las columnas de negocio provienen de los datasets de Bogotá; "
            "MongoDB agrega el campo técnico <code>_id</code>, conservado como "
            "identificador y excluido de la comparación de duplicados.",
            styles["body"],
        ),
    ]

    collection_rows = [["Colección", "Registros", "Campos fuente", "Campos MongoDB"]]
    for name in COLECCIONES:
        item = data["collections"][name]
        collection_rows.append(
            [
                NOMBRES[name],
                _format_number(item["count"]),
                str(item["source_fields"]),
                str(item["mongo_fields"]),
            ]
        )
    story.extend(
        [
            _make_table(
                collection_rows,
                [6.2 * cm, 3.1 * cm, 3 * cm, 3.5 * cm],
                font,
                bold_font,
            ),
            Spacer(1, 7),
            Paragraph("3. Análisis exploratorio y hallazgos", styles["h1"]),
            Paragraph(
                "Listings contiene información de precios, anfitriones, "
                "características y disponibilidad. Reviews es una colección "
                "de eventos asociados a anuncios; Calendar contiene una fila "
                "por anuncio y fecha. Por ello, Calendar concentra la mayor "
                "parte del volumen y requiere procesamiento por bloques.",
                styles["body"],
            ),
            Paragraph("Calidad de datos", styles["h2"]),
        ]
    )
    null_rows = [["Colección", "Celdas nulas", "Columnas con nulos"]]
    for name in COLECCIONES:
        counts = data["nulls"][name]
        total = sum(counts.values())
        affected = sum(value > 0 for value in counts.values())
        null_rows.append(
            [NOMBRES[name], _format_number(total), str(affected)]
        )
    story.append(
        _make_table(null_rows, [7 * cm, 4 * cm, 4.8 * cm], font, bold_font)
    )
    story.extend(
        [
            Spacer(1, 5),
            Paragraph(
                "Los nulos parciales se conservan para no perder observaciones "
                "válidas de otras variables. La detección de duplicados se "
                "realiza ignorando el <code>_id</code> técnico de MongoDB; al "
                "actualizar ese criterio deben regenerarse las salidas del "
                "Notebook antes de reportar un conteo de duplicados.",
                styles["body"],
            ),
            Paragraph("Valores atípicos en Listings", styles["h2"]),
        ]
    )

    stat_rows = [
        [
            "Variable",
            "Válidos",
            "Nulos",
            "Mediana",
            "Máximo",
            "Atípicos IQR",
        ]
    ]
    field_labels = {
        "price": f"Precio ({data['currency'] or 'unidad de origen'})",
        "minimum_nights": "Noches mínimas",
        "availability_365": "Disponibilidad 365",
    }
    for field, stats in data["outliers"].items():
        stat_rows.append(
            [
                field_labels[field],
                _format_number(stats["n"]),
                _format_number(stats["nulls"]),
                _format_number(stats["median"]),
                _format_number(stats["max"]),
                _format_number(stats["outliers"]),
            ]
        )
    story.extend(
        [
            _make_table(
                stat_rows,
                [4.5 * cm, 2.2 * cm, 1.7 * cm, 2.5 * cm, 3 * cm, 2.1 * cm],
                font,
                bold_font,
            ),
            Spacer(1, 5),
            Paragraph(
                "El criterio IQR marca observaciones para revisión, no errores "
                "automáticos. En particular, el precio máximo muy superior al "
                "tercer cuartil debe validarse con su moneda, unidad y valor "
                "original antes de excluirlo. La disponibilidad baja también "
                "puede ser un estado real del anuncio.",
                styles["body"],
            ),
            Image(outlier_chart, width=17.2 * cm, height=4.8 * cm),
            Paragraph(
                "Los bigotes llegan al mínimo y máximo dentro de los límites "
                "IQR; los conteos de valores fuera de esos límites aparecen "
                "en la tabla. El eje del precio es logarítmico para distinguir "
                "valores centrales frente a la cola larga.",
                styles["small"],
            ),
            Paragraph("Cobertura temporal de Calendar", styles["h2"]),
            Image(monthly_chart, width=17.2 * cm, height=5.4 * cm),
            Paragraph(
                "La cobertura observada va de "
                f"{escape(data['monthly'][0]['_id'])} a "
                f"{escape(data['monthly'][-1]['_id'])}. Las diferencias "
                "mensuales reflejan la cobertura del calendario y sus fechas, "
                "no necesariamente cambios en demanda.",
                styles["body"],
            ),
            PageBreak(),
            Paragraph("4. Transformaciones implementadas", styles["h1"]),
            Paragraph(
                "El proceso limpia filas totalmente vacías y duplicados exactos "
                "(sin comparar el identificador técnico <code>_id</code>), "
                "elimina columnas totalmente nulas y conserva nulos parciales. "
                "Los documentos anidados se aplanan, las listas se serializan "
                "en JSON y <code>amenities_count</code> resume la cantidad de "
                "servicios.",
                styles["body"],
            ),
            Paragraph(
                "El campo <code>price</code> se normaliza a valor numérico, "
                "quitando símbolos monetarios y separadores; los valores no "
                "interpretables generan advertencias. Las fechas pasan al "
                "formato YYYY-MM-DD y, para <code>date</code>, se derivan año, "
                "mes, día y trimestre. El precio se agrupa por terciles "
                "calculados sobre los valores válidos.",
                styles["body"],
            ),
            Paragraph(
                "La ejecución principal procesa MongoDB por bloques. SQLite "
                "se verifica contra el total transformado y cada XLSX se "
                "escribe en modo de bajo uso de memoria, creando hojas "
                "adicionales al alcanzar el máximo de filas de Excel.",
                styles["body"],
            ),
            Paragraph("5. Evidencia de ejecución y validación", styles["h1"]),
            Paragraph(escape(status), styles["body"]),
        ]
    )
    log_excerpt = [
        line
        for line in log_text.splitlines()
        if any(
            token in line
            for token in (
                "Conexión a MongoDB",
                "Colección Listings extraída",
                "Colección Reviews extraída",
                "Colección Calendar extraída",
                "Proceso ETL terminado correctamente",
            )
        )
    ]
    if log_excerpt:
        story.append(
            Paragraph(
                "<br/>".join(escape(line) for line in log_excerpt[-6:]),
                ParagraphStyle(
                    "LogExcerpt",
                    parent=styles["small"],
                    backColor=colors.HexColor("#F1F5F8"),
                    borderColor=colors.HexColor("#CBD5E1"),
                    borderWidth=0.5,
                    borderPadding=7,
                    leading=11,
                ),
            )
        )
    story.extend(
        [
            Spacer(1, 6),
            Paragraph(
                "Las pruebas unitarias del proyecto cubren extracción, "
                "transformación, carga a SQLite, escritura XLSX por bloques y "
                "división de hojas. La validación integral sobre todas las "
                "7.003.255 filas de Calendar debe confirmarse con el log de "
                "finalización y los artefactos de salida, no solo con el log "
                "de extracción.",
                styles["body"],
            ),
            Paragraph("6. Conclusiones", styles["h1"]),
            Paragraph(
                "Las tres colecciones tienen utilidad analítica complementaria: "
                "Listings permite describir oferta y precios; Reviews permite "
                "estudiar actividad y experiencia; Calendar permite analizar "
                "disponibilidad en el tiempo. La cantidad de datos y la "
                "dispersión de precio exigen procesos reproducibles y "
                "validaciones explícitas.",
                styles["body"],
            ),
            Paragraph(
                "La limpieza conserva la información parcial en vez de "
                "descartar filas completas. Los valores atípicos se documentan "
                "pero no se eliminan sin contexto de negocio. El procesamiento "
                "por bloques y la exportación en varias hojas responden al "
                "volumen real encontrado en MongoDB.",
                styles["body"],
            ),
            Paragraph("7. Referencias", styles["h1"]),
            Paragraph(
                "• Institución Universitaria ITM. Taller evaluativo 2: "
                "<i>Proceso ETL con los datasets de Airbnb Bogotá</i> (guía "
                "entregada para el curso).<br/>"
                "• Inside Airbnb. Datasets detallados de Listings, Calendar "
                "y Reviews para Bogotá, Colombia (archivos fuente indicados "
                "en la guía).<br/>"
                "• MongoDB Documentation. Manual de consultas y cursores.<br/>"
                "• pandas Documentation. Manual de DataFrames y limpieza "
                "de datos.",
                styles["body"],
            ),
        ]
    )
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output


def _make_table(
    rows: list[list[str]], widths: list[float], font: str, bold_font: str
) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D3DC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6F8")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D4DEE7"))
    canvas.line(1.8 * cm, 1.25 * cm, letter[0] - 1.8 * cm, 1.25 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#5B6B79"))
    canvas.drawString(1.8 * cm, 0.85 * cm, "Taller 2 ETL · Airbnb Bogotá")
    canvas.drawRightString(
        letter[0] - 1.8 * cm, 0.85 * cm, f"Página {document.page}"
    )
    canvas.restoreState()


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el informe PDF del ETL.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Ruta del PDF de entrega (por defecto, en la raíz del proyecto).",
    )
    args = parser.parse_args()
    path = generar_informe(args.output)
    logging.getLogger(__name__).info("Informe generado: %s", path)
    print(f"Informe generado: {path}")


if __name__ == "__main__":
    main()
