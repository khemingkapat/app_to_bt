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


def setup_module():
    """Runs once before all tests — wipes any real (non-example) JSON outputs."""
    for f in outputs_dir.glob("*.json"):
        if ".example." not in f.name:
            f.unlink()


# ── Tests ──────────────────────────────────────────────────────────────────


def test_landing_page(page: Page):
    page.goto("http://localhost:8501")
    expect(page).to_have_title(re.compile("AXA Health Insurance Application"))
    expect(
        page.get_by_role("heading", name="🏥 AXA Health Insurance Application Portal")
    ).to_be_visible()


def test_pdf_tool_navigation(page: Page):
    page.goto("http://localhost:8501")
    page.get_by_role("button", name="🚀 Launch PDF to BlueTable Tool").click()
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
    page.get_by_test_id("stBaseButton-secondary").first.click()
    page.get_by_role("button", name="⬇️").click()
    page.get_by_role("button", name="⬇️").click()
    page.get_by_role("button", name="⬇️").click()
    page.get_by_role("button", name="✅").click()

    expect(page.get_by_test_id("stJson")).to_contain_text('"name"')

    # Reset
    page.get_by_test_id("stButton").get_by_test_id("stBaseButton-secondary").click()
    expect(page.get_by_text("📋 PDF ➜ BlueTable Auto-Fill")).to_be_visible()

    # Second upload — verify cache restore + manual edit
    page.get_by_test_id("stBaseButton-secondary").click()
    page.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(ACROFORM_PDF)
    page.get_by_text("Field 1 of").wait_for()

    page.get_by_role("textbox", name="Main Insured").dblclick()
    page.get_by_role("textbox", name="Main Insured").fill("name_naja")
    page.get_by_role("textbox", name="Main Insured").press("Enter")
    page.get_by_role("button", name="✅").click()

    expect(page.get_by_test_id("stJson")).to_contain_text('"name_naja"')


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

        expect(page.get_by_role("img")).to_be_visible()
        expect(page.get_by_role("button", name="⬇️")).to_be_visible()
        expect(page.get_by_role("button", name="✅")).to_be_visible()

        # page.get_by_role("button", name="⬇️").click()
        # page.get_by_test_id("stBaseButton-secondary").first.click()
        page.get_by_role("button", name="✅").click()

        expect(
            page.get_by_test_id("stDownloadButton").get_by_test_id(
                "stBaseButton-secondary"
            )
        ).to_be_visible()
        expect(page.get_by_test_id("stJson")).to_contain_text('"p_name"')

    finally:
        context.close()


def test_digital_eform_flow(page: Page):
    page.goto("http://localhost:8501")
    page.get_by_role("button", name="Launch Digital E-Form Portal ➡️").click()

    # Step 1: Health Gate
    expect(page.get_by_text("Step 1: Health Pre-Screening Questionnaire")).to_be_visible()
    page.get_by_role("button", name="Proceed to Plan Sandbox ➡️").click()

    # Step 2: Sandbox
    expect(page.get_by_text("Step 2: Interactive Plan & Premium Sandbox")).to_be_visible()
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
    expect(page.get_by_role("button", name="⬇️ Download BlueTable JSON Row")).to_be_visible()
    expect(page.get_by_role("button", name="⬇️ Download Pre-filled Official PDF")).to_be_visible()

