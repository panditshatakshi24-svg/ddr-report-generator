import streamlit as st
import fitz  # PyMuPDF
import base64
import json
import tempfile
import os
from datetime import datetime
from groq import Groq

# ─────────────────────────────────────────
# 1. PDF EXTRACTOR
# ─────────────────────────────────────────

def extract_from_pdf(pdf_path: str, label: str) -> dict:
    doc = fitz.open(pdf_path)
    full_text = ""
    images = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        full_text += f"\n--- Page {page_num + 1} ---\n"
        full_text += page.get_text()

        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            images.append({
                "base64": b64,
                "ext": ext,
                "page": page_num + 1,
                "label": label,
                "caption": f"{label.capitalize()} Report – Page {page_num+1}, Image {img_index+1}"
            })

    doc.close()
    return {"text": full_text, "images": images}


# ─────────────────────────────────────────
# 2. AI PROCESSOR (GROQ)
# ─────────────────────────────────────────

DDR_PROMPT = """
You are an expert building diagnostics report writer.

You are given raw text from two documents:
1. INSPECTION REPORT - site observations and issue descriptions
2. THERMAL REPORT - temperature readings and thermal findings

Generate a DDR (Detailed Diagnostic Report) as a JSON object.

STRICT RULES:
- Do NOT invent facts not present in the documents
- If information is missing → write "Not Available"
- If information conflicts between reports → mention the conflict clearly
- Use simple, client-friendly language
- No duplicate observations
- Merge related points logically

Return ONLY a valid JSON object with this exact structure:
{
  "property_issue_summary": "Overall summary of all issues found...",
  "area_wise_observations": [
    {
      "area": "Area name (e.g. Roof, Bathroom, Living Room)",
      "observations": ["observation 1", "observation 2"],
      "thermal_findings": ["thermal finding 1 if any, else Not Available"],
      "image_tag": "inspection or thermal or none"
    }
  ],
  "probable_root_cause": [
    {
      "issue": "Issue name",
      "cause": "Probable cause explanation"
    }
  ],
  "severity_assessment": [
    {
      "area": "Area name",
      "severity": "High or Medium or Low",
      "reasoning": "Why this severity level was assigned"
    }
  ],
  "recommended_actions": [
    {
      "action": "Action description",
      "priority": "Immediate or Short-term or Long-term"
    }
  ],
  "additional_notes": "Any extra observations. Write Not Available if none.",
  "missing_or_unclear_information": ["missing item 1", "missing item 2"]
}
"""

def generate_ddr(inspection_text: str, thermal_text: str, api_key: str) -> dict:
    client = Groq(api_key=api_key)

    user_message = f"""
INSPECTION REPORT TEXT:
{inspection_text[:6000]}

---

THERMAL REPORT TEXT:
{thermal_text[:6000]}

---

Now generate the DDR JSON as instructed.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": DDR_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


# ─────────────────────────────────────────
# 3. REPORT BUILDER (HTML)
# ─────────────────────────────────────────

def severity_badge(s):
    colors = {"High": "#e74c3c", "Medium": "#f39c12", "Low": "#27ae60"}
    c = colors.get(s, "#888")
    return f'<span style="background:{c};color:white;padding:3px 12px;border-radius:12px;font-size:13px;font-weight:bold;">{s}</span>'

def priority_badge(p):
    colors = {"Immediate": "#e74c3c", "Short-term": "#f39c12", "Long-term": "#2980b9"}
    c = colors.get(p, "#888")
    return f'<span style="background:{c};color:white;padding:3px 12px;border-radius:12px;font-size:13px;">{p}</span>'

def get_images_html(images, tag):
    filtered = [i for i in images if i["label"] == tag]
    if not filtered:
        return '<p style="color:#999;font-style:italic;font-size:13px;">📷 Image Not Available</p>'
    html = '<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px;">'
    for img in filtered[:2]:
        src = f"data:image/{img['ext']};base64,{img['base64']}"
        html += f'''<figure style="margin:0;text-align:center;">
            <img src="{src}" style="max-width:280px;max-height:200px;border:1px solid #ddd;border-radius:6px;"/>
            <figcaption style="font-size:11px;color:#888;margin-top:4px;">{img["caption"]}</figcaption>
        </figure>'''
    html += '</div>'
    return html

def build_html_report(ddr, inspection_images, thermal_images):
    all_images = inspection_images + thermal_images
    date_str = datetime.now().strftime("%B %d, %Y")

    # Section 2: Area-wise
    area_html = ""
    for a in ddr.get("area_wise_observations", []):
        obs = "".join(f"<li>{o}</li>" for o in a.get("observations", ["Not Available"]))
        thermal = "".join(f"<li>{t}</li>" for t in a.get("thermal_findings", ["Not Available"]))
        tag = a.get("image_tag", "none")
        imgs = inspection_images if tag == "inspection" else (thermal_images if tag == "thermal" else [])
        area_html += f"""
        <div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;margin-bottom:14px;background:#fafafa;">
            <h3 style="color:#2c3e50;margin-top:0;">📍 {a.get("area","")}</h3>
            <p><strong>Observations:</strong></p><ul>{obs}</ul>
            <p><strong>Thermal Findings:</strong></p><ul>{thermal}</ul>
            {get_images_html(imgs, tag)}
        </div>"""

    # Section 3: Root Cause
    cause_html = ""
    for c in ddr.get("probable_root_cause", []):
        cause_html += f'<div style="margin-bottom:10px;padding:12px;background:#fff8e1;border-left:4px solid #f39c12;border-radius:4px;"><strong>{c.get("issue","")}</strong><br/>{c.get("cause","Not Available")}</div>'

    # Section 4: Severity Table
    sev_rows = ""
    for s in ddr.get("severity_assessment", []):
        sev_rows += f'<tr style="border-bottom:1px solid #eee;"><td style="padding:10px;">{s.get("area","")}</td><td style="padding:10px;text-align:center;">{severity_badge(s.get("severity",""))}</td><td style="padding:10px;">{s.get("reasoning","")}</td></tr>'

    # Section 5: Actions
    actions_html = ""
    for a in ddr.get("recommended_actions", []):
        actions_html += f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;padding:12px;border:1px solid #eee;border-radius:6px;">{priority_badge(a.get("priority",""))} <span>{a.get("action","")}</span></div>'

    # Section 7: Missing info
    missing = ddr.get("missing_or_unclear_information", [])
    missing_html = "".join(f"<li>{m}</li>" for m in missing) if missing else "<li>Not Available</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>DDR Report</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;color:#2c3e50;max-width:960px;margin:0 auto;padding:30px;}}
  h1{{color:white;background:linear-gradient(135deg,#2c3e50,#3498db);padding:24px;border-radius:10px;}}
  h2{{color:#2c3e50;border-bottom:2px solid #3498db;padding-bottom:6px;margin-top:36px;}}
  .meta{{color:#7f8c8d;font-size:13px;margin-bottom:28px;}}
  table{{width:100%;border-collapse:collapse;}}
  th{{background:#34495e;color:white;padding:12px;text-align:left;}}
</style>
</head>
<body>
<h1>🏠 Detailed Diagnostic Report (DDR)</h1>
<p class="meta">📅 Generated: {date_str} &nbsp;|&nbsp; 🤖 AI-Powered Inspection Analysis</p>

<h2>1. Property Issue Summary</h2>
<p>{ddr.get("property_issue_summary","Not Available")}</p>

<h2>2. Area-wise Observations</h2>
{area_html or "<p>Not Available</p>"}

<h2>3. Probable Root Cause</h2>
{cause_html or "<p>Not Available</p>"}

<h2>4. Severity Assessment</h2>
<table><tr><th>Area</th><th style="text-align:center;">Severity</th><th>Reasoning</th></tr>{sev_rows}</table>

<h2>5. Recommended Actions</h2>
{actions_html or "<p>Not Available</p>"}

<h2>6. Additional Notes</h2>
<p>{ddr.get("additional_notes","Not Available")}</p>

<h2>7. Missing or Unclear Information</h2>
<ul>{missing_html}</ul>

<hr style="margin-top:40px;border:none;border-top:1px solid #eee;"/>
<p style="color:#aaa;font-size:12px;text-align:center;">Auto-generated by DDR AI System. Review with a qualified professional before taking action.</p>
</body>
</html>"""


# ─────────────────────────────────────────
# 4. STREAMLIT UI
# ─────────────────────────────────────────

st.set_page_config(page_title="DDR Report Generator", page_icon="🏠", layout="wide")

st.title("🏠 DDR Report Generator")
st.markdown("Upload your **Inspection Report** and **Thermal Report** PDFs to generate a professional Detailed Diagnostic Report.")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.markdown("---")
    st.markdown("**Steps:**")
    st.markdown("1. Enter your Groq API key")
    st.markdown("2. Upload both PDF reports")
    st.markdown("3. Click Generate")
    st.markdown("4. Download your DDR report")
    st.markdown("---")
    st.markdown("🔑 Get free key at [console.groq.com](https://console.groq.com)")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Inspection Report")
    inspection_file = st.file_uploader("Upload Inspection PDF", type=["pdf"], key="inspection")
with col2:
    st.subheader("🌡️ Thermal Report")
    thermal_file = st.file_uploader("Upload Thermal PDF", type=["pdf"], key="thermal")

st.markdown("---")

if st.button("🚀 Generate DDR Report", use_container_width=True, type="primary"):
    if not api_key:
        st.error("⚠️ Please enter your Groq API key in the sidebar.")
    elif not inspection_file or not thermal_file:
        st.error("⚠️ Please upload both PDF files.")
    else:
        with st.spinner("📄 Step 1/3 — Extracting text and images from PDFs..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t1:
                t1.write(inspection_file.read())
                p1 = t1.name
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t2:
                t2.write(thermal_file.read())
                p2 = t2.name

            insp = extract_from_pdf(p1, "inspection")
            therm = extract_from_pdf(p2, "thermal")

        st.success(f"✅ Extracted {len(insp['images'])} images from Inspection, {len(therm['images'])} from Thermal")

        with st.spinner("🤖 Step 2/3 — AI is analyzing both reports..."):
            try:
                ddr = generate_ddr(insp["text"], therm["text"], api_key)
            except Exception as e:
                st.error(f"❌ AI Error: {e}")
                st.stop()

        with st.spinner("📝 Step 3/3 — Building final report..."):
            html = build_html_report(ddr, insp["images"], therm["images"])

        st.success("✅ DDR Report Ready!")
        st.markdown("---")

        # Preview
        st.subheader("📋 Report Preview")

        with st.expander("1. 📌 Property Issue Summary", expanded=True):
            st.write(ddr.get("property_issue_summary", "Not Available"))

        with st.expander("2. 📍 Area-wise Observations"):
            for area in ddr.get("area_wise_observations", []):
                st.markdown(f"**📍 {area.get('area','')}**")
                for obs in area.get("observations", []):
                    st.markdown(f"- {obs}")
                for t in area.get("thermal_findings", []):
                    st.markdown(f"  🌡️ {t}")

        with st.expander("3. 🔍 Probable Root Cause"):
            for c in ddr.get("probable_root_cause", []):
                st.markdown(f"**{c.get('issue','')}** — {c.get('cause','')}")

        with st.expander("4. ⚠️ Severity Assessment"):
            for s in ddr.get("severity_assessment", []):
                icon = {"High":"🔴","Medium":"🟡","Low":"🟢"}.get(s.get("severity",""),"⚪")
                st.markdown(f"{icon} **{s.get('area','')}** — {s.get('severity','')}: {s.get('reasoning','')}")

        with st.expander("5. ✅ Recommended Actions"):
            for a in ddr.get("recommended_actions", []):
                st.markdown(f"- **[{a.get('priority','')}]** {a.get('action','')}")

        with st.expander("6. 📝 Additional Notes"):
            st.write(ddr.get("additional_notes", "Not Available"))

        with st.expander("7. ❓ Missing or Unclear Information"):
            for m in ddr.get("missing_or_unclear_information", []):
                st.markdown(f"- {m}")

        st.markdown("---")
        st.download_button(
            label="⬇️ Download Full DDR Report (HTML)",
            data=html,
            file_name="DDR_Report.html",
            mime="text/html",
            use_container_width=True
        )
        st.info("💡 Open the downloaded file in any browser to view the full report with images.")

        try:
            os.unlink(p1)
            os.unlink(p2)
        except:
            pass
