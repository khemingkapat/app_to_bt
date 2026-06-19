import re
import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page, Browser, expect

repo_root = Path(__file__).resolve().parent.parent
outputs_dir = repo_root / "outputs"
sys.path.insert(0, str(repo_root))

ACROFORM_PDF = str(repo_root / "resources" / "FilledApplication.pdf")
FLATTEN_PDF = str(repo_root / "resources" / "PrintedApplication.pdf")


# ── Module-level setup ─────────────────────────────────────────────────────

import shutil

backup_dir = outputs_dir / "backup_test_temp"
backup_files = {}


def setup_module():
    """Runs once before all tests — backs up and wipes any real (non-example) JSON outputs."""
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    for f in outputs_dir.glob("*.json"):
        if ".example." not in f.name:
            shutil.copy(f, backup_dir / f.name)
            backup_files[f.name] = True
            f.unlink()


def teardown_module():
    """Runs once after all tests — restores backed-up files, or copies from example files if they don't exist."""
    # 1. Restore from backup
    for f_name in backup_files:
        backup_file = backup_dir / f_name
        if backup_file.exists():
            shutil.copy(backup_file, outputs_dir / f_name)
            
    # 2. Cleanup backup folder
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
        
    # 3. For any missing non-example json files, copy from .example.json
    for f in outputs_dir.glob("*.example.json"):
        real_name = f.name.replace(".example.json", ".json")
        real_path = outputs_dir / real_name
        if not real_path.exists():
            shutil.copy(f, real_path)


# ── Tests ──────────────────────────────────────────────────────────────────


def test_landing_page(page: Page):
    page.goto("http://localhost:8501")
    expect(page).to_have_title(re.compile("AXA Application Tools Portal"))
    expect(
        page.get_by_role("heading", name="🏥 AXA Application Tools Portal")
    ).to_be_visible()


def test_pdf_tool_navigation(page: Page):
    page.goto("http://localhost:8501")
    page.get_by_role("button", name="Launch PDF to BlueTable Tool ➡️").click()
    expect(
        page.get_by_role("heading", name="📋 PDF ➜ BlueTable Auto-Fill")
    ).to_be_visible()


def test_acroform_pdf_flow(page: Page):
    page.goto("http://localhost:8501/pdf_to_blue_table")
    expect(page.get_by_text("📋 PDF ➜ BlueTable Auto-Fill")).to_be_visible()
    expect(page.get_by_test_id("stBaseButton-secondary")).to_be_visible()

    page.get_by_test_id("stBaseButton-secondary").click()
    page.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(ACROFORM_PDF)
    page.get_by_text("Field 1 of").wait_for()

    expect(page.get_by_role("button", name="⬇️")).to_be_visible()
    expect(page.get_by_role("button", name="✅")).to_be_visible()

    page.get_by_role("button", name="⬇️").click()
    page.wait_for_timeout(500)
    page.get_by_text("✍️ Fields & Signature").click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="Assign").first.click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="⬇️").click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="⬇️").click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="⬇️").click()
    page.wait_for_timeout(500)
    page.get_by_role("button", name="✅").click()
    page.wait_for_timeout(1000)

    expect(page.locator("table")).to_contain_text("name")

    # Reset
    page.get_by_test_id("stButton").get_by_test_id("stBaseButton-secondary").click()
    page.wait_for_timeout(500)
    expect(page.get_by_text("📋 PDF ➜ BlueTable Auto-Fill")).to_be_visible()

    # Second upload — verify cache restore + manual edit
    page.get_by_test_id("stBaseButton-secondary").click()
    page.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(ACROFORM_PDF)
    page.get_by_text("Field 1 of").wait_for()
    page.get_by_text("✍️ Fields & Signature").click()
    page.wait_for_timeout(500)

    page.get_by_role("textbox", name="Main Insured").dblclick()
    page.get_by_role("textbox", name="Main Insured").fill("name_naja")
    page.get_by_role("textbox", name="Main Insured").press("Enter")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="✅").click()
    page.wait_for_timeout(1000)

    expect(page.locator("table")).to_contain_text("name_naja")


def test_flatten_pdf_flow(browser: Browser):
    """
    Uses a fresh browser context to avoid stale Streamlit session state
    left over from test_acroform_pdf_flow.
    Seeds the registry directly via the engine before uploading the flatten PDF.
    """
    from src.pdf_processor.engine import update_pdf_registry

    update_pdf_registry(ACROFORM_PDF)

    context = browser.new_context()
    page = context.new_page()

    try:
        page.goto("http://localhost:8501/pdf_to_blue_table")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("📋 PDF ➜ BlueTable Auto-Fill")).to_be_visible()
        expect(page.get_by_test_id("stBaseButton-secondary")).to_be_visible()

        page.get_by_test_id("stBaseButton-secondary").click()
        page.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(FLATTEN_PDF)
        page.get_by_text("Field 1 of").wait_for()

        expect(page.locator("img")).to_be_visible()
        expect(page.get_by_role("button", name="⬇️")).to_be_visible()
        expect(page.get_by_role("button", name="✅")).to_be_visible()

        # page.get_by_role("button", name="⬇️").click()
        # page.get_by_test_id("stBaseButton-secondary").first.click()
        page.get_by_role("button", name="✅").click()

        if (repo_root / "resources" / "BlueTable.docx").exists():
            expect(
                page.get_by_test_id("stDownloadButton").get_by_test_id(
                    "stBaseButton-primary"
                )
            ).to_be_visible()
        expect(page.locator("table")).to_contain_text("name")

    finally:
        context.close()


def test_digital_eform_flow(page: Page):
    page.goto("http://localhost:8501")
    page.get_by_role("button", name="Launch Digital E-Form Portal ➡️").click()

    # Step 1: Health Gate
    expect(
        page.get_by_text("Step 1: Health Pre-Screening Questionnaire")
    ).to_be_visible()
    page.get_by_role("button", name="Proceed to Plan Sandbox ➡️").click()

    # Step 2: Sandbox
    expect(
        page.get_by_text("Step 2: Interactive Plan & Premium Sandbox")
    ).to_be_visible()
    page.get_by_role("button", name="Proceed to Details Intake ➡️").click()

    # Step 3: Details Intake
    expect(page.get_by_text("Step 3: Progressive Personal Info Blocks")).to_be_visible()
    page.get_by_role("textbox", name="Full Name *").fill("Alex Mercer")
    page.get_by_role("textbox", name="Date of Birth *").fill("31/10/1990")
    page.get_by_role("textbox", name="ID Card / Passport No. *").fill("1234567890123")
    page.get_by_role("textbox", name="Telephone No. *").fill("0812345678")

    page.get_by_role("button", name="Submit Application ✅").click()

    # Step 4: Verification
    expect(page.get_by_text("Application Submitted Successfully!")).to_be_visible()
    if (repo_root / "resources" / "BlueTable.docx").exists():
        expect(page.get_by_role("button", name="⬇️ Download Filled BlueTable DOCX")).to_be_visible()
    expect(
        page.get_by_role("button", name="⬇️ Download Pre-filled Official PDF")
    ).to_be_visible()


def test_internal_eform_flow(page: Page):
    page.goto("http://localhost:8501")
    page.get_by_role("button", name="Launch Internal E-Form ➡️").click()

    expect(page.get_by_text("AXA Internal Fast-Entry E-Form Portal")).to_be_visible()
    
    # Fill Policy Details
    page.get_by_role("textbox", name="Agent CODE/Name *").fill("AGENT001")
    page.get_by_role("textbox", name="Agent CODE/Name *").press("Enter")
    page.wait_for_timeout(800)

    # Fill Main Insured Details
    page.get_by_role("textbox", name="Full Name *").fill("Alex Mercer")
    page.get_by_role("textbox", name="Full Name *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="Date of Birth *").fill("31/10/1990")
    page.get_by_role("textbox", name="Date of Birth *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="ID Card / Passport No. *").fill("1234567890123")
    page.get_by_role("textbox", name="ID Card / Passport No. *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="Personal / Present Address *").fill("123 BlueTable Boulevard, Bangkok, Thailand")
    page.get_by_role("textbox", name="Personal / Present Address *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="Telephone No. *").fill("0812345678")
    page.get_by_role("textbox", name="Telephone No. *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="Email Address *").fill("alex@mercer.com")
    page.get_by_role("textbox", name="Email Address *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="Beneficiary Name *").fill("John Mercer")
    page.get_by_role("textbox", name="Beneficiary Name *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="Relation to Beneficiary *").fill("Spouse")
    page.get_by_role("textbox", name="Relation to Beneficiary *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="Occupation *").fill("Engineer")
    page.get_by_role("textbox", name="Occupation *").press("Enter")
    page.wait_for_timeout(800)
    
    # Fill Family config
    page.get_by_role("textbox", name="Cover Spouse? (y/n) *").fill("no")
    page.get_by_role("textbox", name="Cover Spouse? (y/n) *").press("Enter")
    page.wait_for_timeout(800)
    page.get_by_role("textbox", name="Number of Children (0-3) *").fill("0")
    page.get_by_role("textbox", name="Number of Children (0-3) *").press("Enter")
    page.wait_for_timeout(1000)

    page.get_by_role("button", name="Generate Deliverables (Alt + S) 🚀").click()

    # Verification
    expect(page.get_by_text("Verification & Deliverables Generation")).to_be_visible()
    if (repo_root / "resources" / "BlueTable.docx").exists():
        expect(page.get_by_role("button", name="⬇️ Download Filled BlueTable DOCX")).to_be_visible()
    expect(
        page.get_by_role("button", name="⬇️ Download Pre-filled Official PDF")
    ).to_be_visible()
