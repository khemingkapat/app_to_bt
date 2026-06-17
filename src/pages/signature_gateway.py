import sys
import os
import secrets
import socket
from io import BytesIO
from datetime import datetime, timezone
import numpy as np
import streamlit as st
from PIL import Image

# Import from local signature_gateway package
import src.signature_gateway.vault as vault
from src.signature_gateway.pdf_stamping import get_network_ip, stamp_signature_on_pdf

# Import app_to_bt modules
from src.pdf_processor.engine import update_pdf_registry
from src.blue_table_tools.cache import load_cache
from src.pdf_processor.inverter import fill_acroform_pdf
from src.blue_table_tools.docx_generator import fill_blue_table_docx





# Page configuration
st.set_page_config(
    page_title="Signature Gateway",
    page_icon="✍️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom premium styling injected via CSS
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap');

/* Main page backdrop styling */
.stApp {
    background: linear-gradient(135deg, #0b132b, #1c2541, #0b132b) !important;
    color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
}

/* Sidebar overrides if visible */
[data-testid="stSidebar"] {
    background-color: #0b132b !important;
}

/* Titles and Headers */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: #ffffff !important;
}

.portal-title {
    background: linear-gradient(135deg, #818cf8, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    text-align: center;
}

.portal-subtitle {
    color: #94a3b8;
    text-align: center;
    margin-bottom: 2rem;
    font-size: 1.1rem;
}

/* Glassmorphism Cards for targeted Columns and Containers */
div[data-testid="stContainer"]:has(.glass-card-trigger), [data-testid="column"]:has(.glass-card-trigger) {
    background: rgba(30, 41, 59, 0.45) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    padding: 28px !important;
    box-shadow: 0 10px 40px 0 rgba(0, 0, 0, 0.4) !important;
    margin-bottom: 24px !important;
    transition: all 0.3s ease !important;
}

div[data-testid="stContainer"]:has(.glass-card-trigger):hover, [data-testid="column"]:has(.glass-card-trigger):hover {
    border-color: rgba(99, 102, 241, 0.25) !important;
    box-shadow: 0 12px 48px 0 rgba(99, 102, 241, 0.15) !important;
}

/* Status Indicator */
.status-pill {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}

.status-pending {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-signed {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

/* Form inputs styling */
.stTextInput>div>div>input {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    padding: 12px !important;
    font-size: 1rem !important;
}

.stTextInput>div>div>input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}

/* Customize Streamlit Buttons */
.stButton>button {
    background: linear-gradient(135deg, #4f46e5, #6366f1) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.3) !important;
    transition: all 0.3s ease !important;
}

.stButton>button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px 0 rgba(79, 70, 229, 0.5) !important;
    background: linear-gradient(135deg, #4338ca, #4f46e5) !important;
}

.stButton>button:active {
    transform: translateY(0) !important;
}

/* Link area styling */
.copyable-link {
    background: rgba(15, 23, 42, 0.8);
    border: 1px dashed rgba(99, 102, 241, 0.4);
    border-radius: 8px;
    padding: 16px;
    font-family: monospace;
    color: #a5b4fc;
    font-size: 0.95rem;
    margin: 12px 0;
    word-break: break-all;
    text-align: center;
}

/* Table styling override */
table {
    color: #e2e8f0 !important;
}

/* Help descriptions */
.desc-text {
    color: #94a3b8;
    font-size: 0.9rem;
    margin-top: 4px;
}
</style>
""",
    unsafe_allow_html=True,
)


# Extract token from query parameter
token_param = st.query_params.get("token")

# ==============================================================================
# PATHWAY B: Mobile Customer Signing Flow
# ==============================================================================
if token_param:
    # Look up the transaction in the vault
    entry = vault.get_entry(token_param)

    if not entry:
        with st.container(border=True):
            st.markdown(
                """
            <span class='glass-card-trigger'></span>
            <div style="text-align: center; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #f87171;">❌ Secure Link Invalid or Expired</h3>
                <p class='desc-text' style="color: #cbd5e1; font-size: 1.05rem;">This secure signing link is single-use, has expired, or is invalid. Please request your sales representative to generate a new signing link.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
        st.stop()

    status = entry["status"]

    if status == "signed":
        with st.container(border=True):
            st.markdown(
                f"""
            <span class='glass-card-trigger'></span>
            <div style="text-align: center; margin: 20px 0;">
                <span class="status-pill status-signed">Signed Successfully</span>
                <h3 style="margin-top: 15px;">✍️ Document Already Signed</h3>
                <p class='desc-text' style="color: #cbd5e1; font-size: 1.05rem;">Thank you, <b>{entry['customer_name']}</b>. Your signature has already been submitted successfully, and the sales representative has been notified. You may close this browser tab.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
        st.stop()

    # Identity Gate Check
    if not st.session_state.get("customer_verified"):
        with st.container(border=True):
            st.markdown(
                f'<span class="glass-card-trigger"></span><h3 style="margin-top: 0; text-align: center;">🔐 Identity Verification</h3>'
                f"<p style='text-align: center; color: #cbd5e1; margin-top: 10px;'>Welcome, <b>{entry['customer_name']}</b>. "
                "For security purposes, please confirm your identity to review and sign your application.</p>",
                unsafe_allow_html=True,
            )

            id_input = st.text_input(
                "Enter your ID / Passport Number",
                type="password",
                key="customer_id_gate",
            )

            col_btn, _ = st.columns([1, 1])
            with col_btn:
                if st.button("Verify & Proceed"):
                    if not id_input:
                        st.error("Please enter your ID number.")
                    elif vault.verify_identity(token_param, id_input):
                        st.session_state.customer_verified = True
                        st.success(
                            "Identity verified! Proceeding to document signing..."
                        )
                        st.rerun()
                    else:
                        st.error(
                            "❌ Identity verification failed. Please enter the correct ID/Passport number as provided to the sales representative."
                        )

            st.markdown(
                '<p class="desc-text" style="font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px; margin-top: 15px; text-align: center;">Disclaimer: This verification check gates access to your filled application. Raw details are encrypted and deleted immediately upon success.</p>',
                unsafe_allow_html=True,
            )
        st.stop()

    # Customer Signature Interface
    with st.container(border=True):
        st.markdown(
            f'<span class="glass-card-trigger"></span><h2 style="margin-top: 0; text-align: center;">✍️ Sign Application</h2>'
            f"<p style='color: #cbd5e1; text-align: center; margin-bottom: 20px;'>Please draw your signature in the box below, then submit to complete the application.</p>",
            unsafe_allow_html=True,
        )

    st.subheader("Draw Your Signature")
    st.markdown(
        "<p class='desc-text'>Draw your signature using your finger, stylus, or mouse pointer in the box below.</p>",
        unsafe_allow_html=True,
    )

    from streamlit_drawable_canvas import st_canvas

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=3,
        stroke_color="#0b132b",
        background_color="#ffffff",
        height=200,
        width=550,
        drawing_mode="freedraw",
        key="canvas",
    )

    col_submit, col_clear = st.columns([2, 1])
    with col_submit:
        if st.button("Submit Secure Signature"):
            # Check if signature was drawn
            if canvas_result.image_data is not None:
                # Count non-white/non-transparent pixels to verify if anything was drawn
                # Since background is #ffffff (white), we check pixels that are not pure white
                img_data = canvas_result.image_data
                # Convert to RGB and count non-white pixels
                non_white = np.any(img_data[:, :, :3] < 240, axis=-1)
                pixels_drawn = np.sum(non_white)

                if pixels_drawn < 50:
                    st.error(
                        "⚠️ Please draw your signature in the box before submitting."
                    )
                else:
                    with st.spinner(
                        "Processing document generation and e-signature stamp..."
                    ):
                        # Convert canvas signature to PIL and remove white background (make it transparent)
                        pil_img = Image.fromarray(img_data.astype(np.uint8)).convert(
                            "RGBA"
                        )
                        datas = pil_img.getdata()
                        newData = []
                        for item in datas:
                            # If pixel is white/near-white (R, G, B > 240), make it transparent (alpha = 0)
                            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                                newData.append((255, 255, 255, 0))
                            else:
                                newData.append(item)
                        pil_img.putdata(newData)

                        sig_io = BytesIO()
                        pil_img.save(sig_io, format="PNG")
                        sig_png_bytes = sig_io.getvalue()

                        # Generate filled files from the stored PDF template bytes
                        bt = entry["bt_data"]
                        pdf_template_bytes = entry["pdf_bytes"]

                        # 1. Fill AcroForm interactive fields
                        filled_pdf_stream = fill_acroform_pdf(
                            BytesIO(pdf_template_bytes), bt
                        )
                        filled_pdf_bytes = filled_pdf_stream.getvalue()

                        # 2. Stamp PNG signature using Text94 coordinate lookup
                        registry_dict = entry.get("registry_dict")
                        final_pdf_bytes = stamp_signature_on_pdf(
                            filled_pdf_bytes,
                            sig_png_bytes,
                            entry.get("pdf_id"),
                            registry_dict,
                        )

                        # 3. Fill the BlueTable docx tracker template
                        filled_docx_stream = fill_blue_table_docx(
                            "resources/BlueTable.docx", bt
                        )
                        final_docx_bytes = filled_docx_stream.getvalue()

                        # 4. Save to vault and flip status to signed
                        vault.save_signed_documents(
                            token_param, final_pdf_bytes, final_docx_bytes
                        )

                    st.success("🎉 Signature submitted successfully!")
                    st.rerun()
            else:
                st.error("Please draw your signature.")

    with col_clear:
        if st.button("Clear Canvas"):
            st.rerun()

    st.markdown(
        "<hr style='border-color: rgba(255,255,255,0.08); margin-top: 25px;'>",
        unsafe_allow_html=True,
    )

    # Read-only Summary Table on the bottom
    st.subheader("📋 Application Details Summary")
    st.markdown(
        "<p class='desc-text' style='margin-bottom: 15px;'>Please review your pre-filled details below for accuracy.</p>",
        unsafe_allow_html=True,
    )

    bt = entry["bt_data"]

    # Premium styled HTML table format
    table_html = f"""
    <table style="width: 100%; border-collapse: collapse; border: 1px solid rgba(255,255,255,0.08); background: rgba(15,23,42,0.3); border-radius: 8px; font-size: 0.95rem; margin-bottom: 15px;">
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.03);">
        <th style="padding: 12px; text-align: left; color: #818cf8; font-weight: 600;">Field Description</th>
        <th style="padding: 12px; text-align: left; color: #818cf8; font-weight: 600;">Pre-filled Information</th>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Main Applicant Name</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('name', '')}</td>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Date of Birth</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('dob', '')}</td>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Nationality</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('nationality', '')}</td>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Email Address</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('email', '')}</td>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Telephone Number</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('tel', '')}</td>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Product Line Selection</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('product_name', '')}</td>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Plan Tier</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('plan', '')}</td>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Deductible Amount</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('deductible', '')}</td>
      </tr>
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Net Premium (THB)</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('premium', '')}</td>
      </tr>
      <tr>
        <td style="padding: 10px; font-weight: 500; color: #cbd5e1;">Coverage Effective Date</td>
        <td style="padding: 10px; color: #ffffff;">{bt.get('effective_date', '')}</td>
      </tr>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)


# ==============================================================================
# PATHWAY A: Sales Rep Portal
# ==============================================================================
else:
    st.markdown(
        '<div class="portal-title">AXA Signature Gateway</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="portal-subtitle">Secure, Database-Free Customer Document Signing</div>',
        unsafe_allow_html=True,
    )

    col_input, col_status = st.columns([1, 1])

    with col_input:
        with st.container(border=True):
            st.markdown(
                '<span class="glass-card-trigger"></span><h3 style="margin-top: 0;">📤 Generate Secure Link</h3>'
                '<p class="desc-text">Upload the pre-filled AcroForm PDF application from app-to-bt to create a single-use customer portal link.</p>',
                unsafe_allow_html=True,
            )

            uploaded = st.file_uploader("Select Application PDF File", type=["pdf"])

            if uploaded:
                # Check if this PDF has already been processed in the current session
                # to avoid re-parsing on every UI interaction
                file_bytes = uploaded.getvalue()

                with st.spinner("Extracting template ID and structural fields..."):
                    try:
                        pdf_id, registry_dict, values_dict = update_pdf_registry(
                            BytesIO(file_bytes)
                        )
                        cache_mapping = load_cache(pdf_id)
                    except Exception as e:
                        st.error(f"Error parsing PDF: {e}")
                        st.stop()

                if not cache_mapping:
                    st.markdown(
                        '<hr style="border-color: rgba(255,255,255,0.08);">',
                        unsafe_allow_html=True,
                    )
                    st.warning(
                        "⚠️ **Unknown PDF Template**\n\n"
                        "This PDF template has no saved field mapping yet. "
                        "Please map this template first using the Config Manager or PDF-to-BlueTable admin tools."
                    )
                else:
                    # Extract customer and BlueTable fields using our helper
                    bt_data = vault.extract_bt_data(
                        registry_dict.get(pdf_id, {}).get("fields", []),
                        cache_mapping,
                        values_dict,
                    )
                    bt_data["pdf_id"] = pdf_id

                    customer_name = bt_data.get("name", "").strip()
                    identity_id = bt_data.get("id_card_no", "").strip()

                    if not customer_name:
                        st.warning(
                            "⚠️ Could not extract 'customer_name' (name field) from layout. Please check template mapping."
                        )
                    if not identity_id:
                        st.warning(
                            "⚠️ Could not extract 'identity_id' (id_card_no field) from layout. Please check template mapping."
                        )

                    # Mask identity_id for security display
                    masked_id = identity_id
                    if len(identity_id) > 4:
                        masked_id = "*" * (len(identity_id) - 4) + identity_id[-4:]

                    st.markdown(
                        '<hr style="border-color: rgba(255,255,255,0.08);">',
                        unsafe_allow_html=True,
                    )
                    st.markdown("##### Resolved Customer Details")
                    st.write(
                        f"👤 **Name:** {customer_name if customer_name else 'Unknown'}"
                    )
                    st.write(
                        f"💳 **ID Card / Passport:** `{masked_id if masked_id else 'Not found'}`"
                    )

                    if customer_name and identity_id:
                        if st.button("Generate Secure Customer Link"):
                            # Generate unique token
                            token = secrets.token_hex(16)

                            # Add token entry to vault, storing PDF bytes as well
                            vault.add_entry(
                                token=token,
                                pdf_id=pdf_id,
                                customer_name=customer_name,
                                identity_id=identity_id,
                                bt_data=bt_data,
                                ttl_seconds=900,
                            )
                            # Save the raw PDF bytes specifically in the entry (not displayed/exposed)
                            vault.get_entry(token)["pdf_bytes"] = file_bytes
                            vault.get_entry(token)["registry_dict"] = registry_dict

                            # Save token state to check status
                            st.session_state.active_token = token
                            st.session_state.active_customer = customer_name
                            st.rerun()

    with col_status:
        with st.container(border=True):
            st.markdown(
                '<span class="glass-card-trigger"></span><h3 style="margin-top: 0;">📊 Active Session Status</h3>',
                unsafe_allow_html=True,
            )

            active_token = st.session_state.get("active_token")

            if not active_token:
                st.info(
                    "No active signing link session. Generate a link to start monitoring."
                )
            else:
                entry = vault.get_entry(active_token)

                if not entry:
                    st.warning("⚠️ Session has expired or been cleared.")
                    if st.button("Start New Session"):
                        del st.session_state.active_token
                        st.rerun()
                else:
                    # Browser notification permission requester helper
                    st.markdown(
                        """
                    <div style="margin-bottom: 15px;">
                        <button onclick="requestPermission()" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #cbd5e1; border-radius: 6px; padding: 6px 12px; font-size: 0.8rem; cursor: pointer; width: 100%;">
                            🔔 Enable Desktop Notifications
                        </button>
                        <script>
                        function requestPermission() {
                            if (Notification.permission === 'default') {
                                Notification.requestPermission().then(permission => {
                                    if (permission === 'granted') {
                                        alert('Desktop notifications enabled!');
                                    }
                                });
                            } else if (Notification.permission === 'granted') {
                                alert('Notifications already enabled!');
                            } else {
                                alert('Please reset notification permissions in your browser settings.');
                            }
                        }
                        </script>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    # Construct query parameters link. If PORTAL_BASE_URL is set in environment, use it.
                    # Otherwise, auto-detect from request headers (handling domain DNS names & proxies).
                    base_url = os.environ.get("PORTAL_BASE_URL")
                    if base_url:
                        base_url = base_url.rstrip("/")
                    else:
                        host = st.context.headers.get("x-forwarded-host")
                        if not host:
                            host = st.context.headers.get("host", "localhost:8501")
                        
                        # Resolve to local network IP if localhost/127.0.0.1 is used
                        if "localhost" in host or "127.0.0.1" in host:
                            net_ip = get_network_ip()
                            host = host.replace("localhost", net_ip).replace(
                                "127.0.0.1", net_ip
                            )

                        protocol = (
                            "https"
                            if st.context.headers.get("x-forwarded-proto") == "https"
                            else "http"
                        )
                        base_url = f"{protocol}://{host}"

                    share_link = f"{base_url}/?token={active_token}"

                    st.markdown(f"**Customer:** {entry['customer_name']}")

                    # Link share block with Clipboard copy button
                    st.markdown("**Secure Customer Link:**")
                    copy_html = f"""
                    <div style="margin-bottom: 15px;">
                        <div class="copyable-link">{share_link}</div>
                        <button onclick="(function(txt){{
                            if (navigator.clipboard && window.isSecureContext) {{
                                navigator.clipboard.writeText(txt).then(function() {{
                                    alert('📋 Link copied to clipboard!');
                                }}).catch(function(e) {{
                                    fallback(txt);
                                }});
                            }} else {{
                                fallback(txt);
                            }}
                            function fallback(t) {{
                                var ta = document.createElement('textarea');
                                ta.value = t;
                                ta.style.position = 'fixed';
                                ta.style.top = '0';
                                ta.style.left = '0';
                                document.body.appendChild(ta);
                                ta.focus();
                                ta.select();
                                try {{
                                    var success = document.execCommand('copy');
                                    if (success) {{
                                        alert('📋 Link copied to clipboard!');
                                    }} else {{
                                        alert('❌ Copy failed, please select the link above and copy manually.');
                                    }}
                                }} catch (err) {{
                                    alert('❌ Error copying: ' + err);
                                }}
                                document.body.removeChild(ta);
                            }}
                        }})('{share_link}')" 
                            style="background: linear-gradient(135deg, #4f46e5, #6366f1); color: white; font-weight: 600; border: none; border-radius: 8px; padding: 10px 20px; box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.3); cursor: pointer; width: 100%; transition: all 0.3s ease;">
                            📋 Copy Link to Clipboard
                        </button>
                    </div>
                    """
                    st.markdown(copy_html, unsafe_allow_html=True)

                    st.markdown(
                        "<hr style='border-color: rgba(255,255,255,0.08);'>",
                        unsafe_allow_html=True,
                    )

                    # Active Status Polling Fragment
                    @st.fragment(run_every=3)
                    def check_status_fragment(token):
                        # Reload entry from vault
                        e = vault.get_entry(token)
                        if not e:
                            st.warning("Session expired.")
                            return

                        # Expiry TTL progress/countdown
                        elapsed = (
                            datetime.now(timezone.utc) - e["created_at"]
                        ).total_seconds()
                        remaining = int(e["ttl_seconds"] - elapsed)

                        if remaining <= 0:
                            st.error("⏳ Secure Link Expired")
                            vault.remove_entry(token)
                            st.rerun()
                        else:
                            mins = remaining // 60
                            secs = remaining % 60
                            st.info(f"⏳ Link expires in **{mins:02d}:{secs:02d}**")

                        status = e["status"]

                        if status == "pending":
                            st.markdown(
                                """
                            <div style="text-align: center; margin: 15px 0;">
                                <span class="status-pill status-pending">Pending Signature</span>
                                <p class="desc-text">Waiting for customer to verify and sign...</p>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                        elif status == "signed":
                            st.markdown(
                                """
                            <div style="text-align: center; margin: 15px 0;">
                                <span class="status-pill status-signed">Signed Successfully</span>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            # Fire desktop browser notification (once only)
                            if not st.session_state.get(f"notified_{token}"):
                                st.markdown(
                                    f"""
                                <script>
                                if (Notification.permission === 'granted') {{
                                    new Notification("AXA Signature Gateway", {{
                                        body: "The customer {e['customer_name']} has signed the application!",
                                        icon: "https://img.icons8.com/color/96/signature.png"
                                    }});
                                }}
                                </script>
                                """,
                                    unsafe_allow_html=True,
                                )
                                st.session_state[f"notified_{token}"] = True

                            st.markdown("#### 📥 Download Completed Documents")

                            col_pdf, col_docx = st.columns(2)
                            with col_pdf:
                                st.download_button(
                                    label="📄 Download PDF",
                                    data=e["signed_pdf_bytes"],
                                    file_name=f"Signed_{e['customer_name'].replace(' ', '_')}.pdf",
                                    mime="application/pdf",
                                )
                            with col_docx:
                                st.download_button(
                                    label="📝 Download DOCX",
                                    data=e["signed_docx_bytes"],
                                    file_name=f"BlueTable_{e['customer_name'].replace(' ', '_')}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                )

                            # Complete transaction / Clear vault button for compliance
                            st.markdown(
                                "<hr style='border-color: rgba(255,255,255,0.08);'>",
                                unsafe_allow_html=True,
                            )
                            if st.button(
                                "🧹 Clear Transaction & PII (Compliance Complete)"
                            ):
                                vault.remove_entry(token)
                                del st.session_state.active_token
                                if f"notified_{token}" in st.session_state:
                                    del st.session_state[f"notified_{token}"]
                                st.success(
                                    "Vault entry and document bytes successfully purged."
                                )
                                st.rerun()

                    check_status_fragment(active_token)
