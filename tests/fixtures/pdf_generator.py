from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle


def generate_test_pdf(header_lines: list[str], table_data: list[list[str]] = []):
    buffer = BytesIO()  # Create a BytesIO buffer to store the PDF content
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    flowables = []

    for line in header_lines:
        para = Paragraph(line, styles["Normal"])
        flowables.append(para)

    if table_data:
        table = Table(table_data)
        table_style = TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1, colors.black),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("BOX", (0, 0), (0, -1), 1, colors.black),
            ]
        )
        table.setStyle(table_style)
        flowables.append(table)

    doc.build(flowables)

    # Get the content of the buffer as bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()  # Close the buffer

    return pdf_bytes
