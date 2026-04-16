import base64
from datetime import datetime


SEVERITY_COLORS = {
    "High": "#e74c3c",
    "Medium": "#f39c12",
    "Low": "#27ae60"
}

PRIORITY_COLORS = {
    "Immediate": "#e74c3c",
    "Short-term": "#f39c12",
    "Long-term": "#2980b9"
}


def _severity_badge(severity: str) -> str:
    color = SEVERITY_COLORS.get(severity, "#888")
    return f'<span style="background:{color};color:white;padding:3px 10px;border-radius:12px;font-size:13px;font-weight:bold;">{severity}</span>'


def _priority_badge(priority: str) -> str:
    color = PRIORITY_COLORS.get(priority, "#888")
    return f'<span style="background:{color};color:white;padding:3px 10px;border-radius:12px;font-size:13px;">{priority}</span>'


def _image_html(images: list, tag: str) -> str:
    """Return HTML for images matching the tag (inspection/thermal/none)."""
    if tag == "none" or not images:
        return '<p style="color:#888;font-style:italic;">Image Not Available</p>'

    filtered = [img for img in images if tag in img["caption"].lower()]
    if not filtered:
        return '<p style="color:#888;font-style:italic;">Image Not Available</p>'

    html = '<div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:10px;">'
    for img in filtered[:2]:  # max 2 images per section
        src = f"data:image/{img['ext']};base64,{img['base64']}"
        html += f'''
        <figure style="margin:0;text-align:center;">
            <img src="{src}" style="max-width:300px;max-height:220px;border:1px solid #ddd;border-radius:6px;" />
            <figcaption style="font-size:11px;color:#666;margin-top:4px;">{img["caption"]}</figcaption>
        </figure>'''
    html += '</div>'
    return html


def build_html_report(ddr: dict, inspection_images: list, thermal_images: list) -> str:
    """
    Build a full HTML DDR report with embedded images.
    """
    all_images = inspection_images + thermal_images
    date_str = datetime.now().strftime("%B %d, %Y")

    # ── Section 1: Property Issue Summary ──
    summary_html = f'<p>{ddr.get("property_issue_summary", "Not Available")}</p>'

    # ── Section 2: Area-wise Observations ──
    area_html = ""
    for area_data in ddr.get("area_wise_observations", []):
        area_name = area_data.get("area", "Unknown Area")
        observations = area_data.get("observations", [])
        thermal = area_data.get("thermal_findings", [])
        img_tag = area_data.get("image_tag", "none")

        obs_list = "".join(f"<li>{o}</li>" for o in observations) if observations else "<li>Not Available</li>"
        thermal_list = "".join(f"<li>{t}</li>" for t in thermal) if thermal else "<li>Not Available</li>"

        tag_for_filter = "inspection" if img_tag == "inspection" else ("thermal" if img_tag == "thermal" else "none")
        images_to_use = inspection_images if img_tag == "inspection" else (thermal_images if img_tag == "thermal" else [])

        area_html += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin-bottom:16px;background:#fafafa;">
            <h3 style="color:#2c3e50;margin-top:0;">📍 {area_name}</h3>
            <p><strong>Observations:</strong></p>
            <ul style="margin:0 0 10px 0;">{obs_list}</ul>
            <p><strong>Thermal Findings:</strong></p>
            <ul style="margin:0 0 10px 0;">{thermal_list}</ul>
            {_image_html(images_to_use, tag_for_filter)}
        </div>"""

    if not area_html:
        area_html = "<p>Not Available</p>"

    # ── Section 3: Probable Root Cause ──
    cause_html = ""
    for item in ddr.get("probable_root_cause", []):
        cause_html += f"""
        <div style="margin-bottom:12px;padding:12px;background:#fff8e1;border-left:4px solid #f39c12;border-radius:4px;">
            <strong>{item.get("issue", "")}</strong><br/>
            {item.get("cause", "Not Available")}
        </div>"""
    if not cause_html:
        cause_html = "<p>Not Available</p>"

    # ── Section 4: Severity Assessment ──
    severity_html = '<table style="width:100%;border-collapse:collapse;">'
    severity_html += '<tr style="background:#34495e;color:white;"><th style="padding:10px;text-align:left;">Area</th><th style="padding:10px;">Severity</th><th style="padding:10px;text-align:left;">Reasoning</th></tr>'
    for item in ddr.get("severity_assessment", []):
        sev = item.get("severity", "")
        severity_html += f"""
        <tr style="border-bottom:1px solid #eee;">
            <td style="padding:10px;">{item.get("area", "")}</td>
            <td style="padding:10px;text-align:center;">{_severity_badge(sev)}</td>
            <td style="padding:10px;">{item.get("reasoning", "Not Available")}</td>
        </tr>"""
    severity_html += "</table>"

    # ── Section 5: Recommended Actions ──
    actions_html = ""
    for item in ddr.get("recommended_actions", []):
        priority = item.get("priority", "")
        actions_html += f"""
        <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:10px;padding:12px;border:1px solid #eee;border-radius:6px;">
            {_priority_badge(priority)}
            <span>{item.get("action", "Not Available")}</span>
        </div>"""
    if not actions_html:
        actions_html = "<p>Not Available</p>"

    # ── Section 6: Additional Notes ──
    notes_html = f'<p>{ddr.get("additional_notes", "Not Available")}</p>'

    # ── Section 7: Missing or Unclear Info ──
    missing = ddr.get("missing_or_unclear_information", [])
    missing_html = "".join(f"<li>{m}</li>" for m in missing) if missing else "<li>Not Available</li>"
    missing_html = f"<ul>{missing_html}</ul>"

    # ── Full HTML ──
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <title>DDR Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; max-width: 960px; margin: 0 auto; padding: 24px; }}
        h1 {{ color: white; background: #2c3e50; padding: 20px; border-radius: 8px; margin-bottom: 8px; }}
        h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 6px; margin-top: 32px; }}
        .meta {{ color: #7f8c8d; font-size: 13px; margin-bottom: 24px; }}
        table th {{ background: #34495e; color: white; }}
    </style>
</head>
<body>
    <h1>🏠 Detailed Diagnostic Report (DDR)</h1>
    <p class="meta">Generated on: {date_str} &nbsp;|&nbsp; Powered by AI-based inspection analysis</p>

    <h2>1. Property Issue Summary</h2>
    {summary_html}

    <h2>2. Area-wise Observations</h2>
    {area_html}

    <h2>3. Probable Root Cause</h2>
    {cause_html}

    <h2>4. Severity Assessment</h2>
    {severity_html}

    <h2>5. Recommended Actions</h2>
    {actions_html}

    <h2>6. Additional Notes</h2>
    {notes_html}

    <h2>7. Missing or Unclear Information</h2>
    {missing_html}

    <hr style="margin-top:40px;border:none;border-top:1px solid #eee;"/>
    <p style="color:#aaa;font-size:12px;text-align:center;">This report was auto-generated by the DDR AI System. Please review with a qualified professional.</p>
</body>
</html>"""

    return html
