import streamlit as st
import tempfile
import os
from extractor import extract_from_pdf
from ai_processor import generate_DDR
from report_builder import build_html_report

st.set_page_config(page_title="DDR Report Generator", page_icon="🏠", layout="wide")

st.title("🏠 DDR Report Generator")
st.markdown("**Automated Detailed Diagnostic Report from Inspection + Thermal Documents**")
st.markdown("---")

# ── Sidebar: API Key ──
with st.sidebar:
    st.header("⚙️ Configuration")
    groq_api_key = st.text_input(" groq_api_key", type="password", placeholder="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")
    st.markdown("---")
    st.markdown("**How it works:**")
    st.markdown("1. Upload both PDF reports")
    st.markdown("2. AI extracts & merges data")
    st.markdown("3. Download your DDR report")

# ── File Uploads ──
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Inspection Report")
    inspection_file = st.file_uploader("Upload Inspection PDF", type=["pdf"], key="inspection")

with col2:
    st.subheader("🌡️ Thermal Report")
    thermal_file = st.file_uploader("Upload Thermal PDF", type=["pdf"], key="thermal")

st.markdown("---")

# ── Generate Button ──
if st.button("🚀 Generate DDR Report", use_container_width=True, type="primary"):

    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
    elif not inspection_file or not thermal_file:
        st.error("Please upload both PDF files.")
    else:
        with st.spinner("Step 1/3 — Extracting text and images from PDFs..."):
            # Save uploaded files to temp paths
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp1:
                tmp1.write(inspection_file.read())
                inspection_path = tmp1.name

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp2:
                tmp2.write(thermal_file.read())
                thermal_path = tmp2.name

            tmpdir = tempfile.mkdtemp()

            inspection_data = extract_from_pdf(inspection_path, "inspection", output_dir=tmpdir)
            thermal_data = extract_from_pdf(thermal_path, "thermal", output_dir=tmpdir)

        st.success(f"✅ Extracted: {len(inspection_data['images'])} images from Inspection, {len(thermal_data['images'])} from Thermal")

        with st.spinner("Step 2/3 — AI is analyzing and generating the DDR..."):
            try:
                ddr = generate_ddr(
                    inspection_text=inspection_data["text"],
                    thermal_text=thermal_data["text"],
                    api_key=api_key
                )
            except Exception as e:
                st.error(f"AI Error: {e}")
                st.stop()

        with st.spinner("Step 3/3 — Building the final report..."):
            html_report = build_html_report(
                ddr=ddr,
                inspection_images=inspection_data["images"],
                thermal_images=thermal_data["images"]
            )

        st.success("✅ DDR Report Generated!")
        st.markdown("---")

        # ── Preview Key Sections ──
        st.subheader("📋 Report Preview")

        with st.expander("1. Property Issue Summary", expanded=True):
            st.write(ddr.get("property_issue_summary", "Not Available"))

        with st.expander("2. Area-wise Observations"):
            for area in ddr.get("area_wise_observations", []):
                st.markdown(f"**📍 {area.get('area', '')}**")
                for obs in area.get("observations", []):
                    st.markdown(f"- {obs}")
                thermal = area.get("thermal_findings", [])
                if thermal:
                    st.markdown("*Thermal:*")
                    for t in thermal:
                        st.markdown(f"  - {t}")

        with st.expander("4. Severity Assessment"):
            for item in ddr.get("severity_assessment", []):
                sev = item.get("severity", "")
                color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(sev, "⚪")
                st.markdown(f"{color} **{item.get('area','')}** — {sev}: {item.get('reasoning','')}")

        with st.expander("5. Recommended Actions"):
            for item in ddr.get("recommended_actions", []):
                st.markdown(f"- [{item.get('priority','')}] {item.get('action','')}")

        with st.expander("7. Missing or Unclear Information"):
            for m in ddr.get("missing_or_unclear_information", []):
                st.markdown(f"- {m}")

        st.markdown("---")

        # ── Download Button ──
        st.download_button(
            label="⬇️ Download Full DDR Report (HTML)",
            data=html_report,
            file_name="DDR_Report.html",
            mime="text/html",
            use_container_width=True
        )

        st.info("💡 Open the downloaded HTML file in any browser to see the full report with images.")

        # Cleanup temp files
        try:
            os.unlink(inspection_path)
            os.unlink(thermal_path)
        except:
            pass
