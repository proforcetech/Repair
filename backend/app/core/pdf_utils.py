## File: backend/app/core/pdf_utils.py
# This file contains utility functions for generating PDF documents from purchase orders.
import pdfkit
from jinja2 import Template

def generate_po_pdf(po, items):
    html = Template("""
    <h2>Purchase Order: {{ po.id }}</h2>
    <p>Vendor: {{ po.vendor }}</p>
    <table border="1" cellpadding="4">
        <tr><th>Part</th><th>Qty</th><th>Cost</th></tr>
        {% for item in items %}
        <tr>
            <td>{{ item.partId }}</td>
            <td>{{ item.quantity }}</td>
            <td>${{ item.cost }}</td>
        </tr>
        {% endfor %}
    </table>
    """).render(po=po, items=items)

    pdf_path = f"/tmp/po_{po.id}.pdf"
    pdfkit.from_string(html, pdf_path)
    return pdf_path
