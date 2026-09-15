from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def build_report(entity, findings, dimensions):
    output = BytesIO(); pdf = canvas.Canvas(output, pagesize=A4); width, height = A4; y = height - 55
    pdf.setTitle(f'SAT-SA Supervisory Report - {entity.name}')
    pdf.setFont('Helvetica-Bold', 18); pdf.drawString(48, y, 'SAT-SA SUPERVISORY REPORT'); y -= 24
    pdf.setFont('Helvetica', 11); pdf.drawString(48, y, f'{entity.name} | {entity.sector} | Risk index {entity.risk_score}/100'); y -= 35
    pdf.setFont('Helvetica-Bold', 12); pdf.drawString(48, y, 'Dimension assessment'); y -= 18; pdf.setFont('Helvetica', 10)
    for dimension in dimensions: pdf.drawString(60, y, f"{dimension.dimension}: {dimension.score:.0f}/100 - {dimension.rationale}"); y -= 15
    y -= 15; pdf.setFont('Helvetica-Bold', 12); pdf.drawString(48, y, 'Supervisory findings'); y -= 18; pdf.setFont('Helvetica', 9)
    for finding in findings:
        if y < 80: pdf.showPage(); y = height - 55
        pdf.drawString(60, y, f'{finding.severity.upper()} | {finding.title}'); y -= 13
        pdf.setFont('Helvetica', 8); pdf.drawString(72, y, f'Confidence {finding.confidence:.0%} | {finding.detector}'); y -= 20; pdf.setFont('Helvetica', 9)
    pdf.save(); output.seek(0); return output
