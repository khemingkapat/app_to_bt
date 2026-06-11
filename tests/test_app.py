import re
import sys
from pathlib import Path
from playwright.sync_api import Page, expect
import pytest

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

# Fixture to clear outputs before each test for complete isolation
@pytest.fixture(autouse=True)
def clean_outputs():
    # Make sure we clean everything in outputs that's not an example file
    outputs_dir = repo_root / "outputs"
    for f in outputs_dir.glob("*.json"):
        if ".example." not in f.name:
            f.unlink()
    yield
    # Clean up after as well
    for f in outputs_dir.glob("*.json"):
        if ".example." not in f.name:
            f.unlink()

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
    pdf_path = str(repo_root / "resources" / "FilledApplication.pdf")

    page.goto("http://localhost:8501/pdf_to_blue_table")
    expect(page.get_by_label("📋 PDF ➜ BlueTable Auto-Fill")).to_contain_text(
        "📋 PDF ➜ BlueTable Auto-Fill"
    )
    expect(page.get_by_test_id("stBaseButton-secondary")).to_be_visible()

    page.get_by_test_id("stBaseButton-secondary").click()
    page.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(pdf_path)

    expect(page.get_by_role("img")).to_be_visible()
    expect(
        page.get_by_text("Main InsuredMain InsuredAssignClear")
    ).to_be_visible()
    expect(page.get_by_label("🔵 BlueTable")).to_contain_text("🔵 BlueTable")
    expect(page.get_by_role("button", name="⬇️")).to_be_visible()
    expect(page.get_by_role("button", name="✅")).to_be_visible()

    # Clicking sequences
    page.get_by_role("button", name="⬇️").click()
    page.get_by_test_id("stBaseButton-secondary").first.click()
    page.get_by_test_id("stBaseButton-secondary").nth(2).click()
    page.get_by_test_id("stBaseButton-secondary").nth(2).click()
    page.get_by_test_id("stBaseButton-secondary").nth(2).click()
    page.get_by_role("button", name="⬇️").click()
    page.get_by_role("button", name="⬇️").click()
    page.get_by_role("button", name="⬇️").click()
    page.get_by_role("button", name="Assign").nth(3).click()
    page.get_by_role("button", name="⬆️").click()
    page.get_by_role("button", name="⬆️").click()
    page.get_by_role("button", name="Assign").nth(4).click()
    page.get_by_role("button", name="⬇️").click()
    page.get_by_role("textbox", name="Main Insured").click()
    page.get_by_role("textbox", name="Main Insured").fill("name_naja")
    page.get_by_role("textbox", name="Main Insured").press("Enter")
    page.get_by_role("button", name="✅").click()

    expect(page.get_by_test_id("stJson")).to_contain_text('"name_naja"')
    expect(page.get_by_test_id("stJson")).to_contain_text('"nationality"')

    expect(
        page.get_by_test_id("stDownloadButton").get_by_test_id("stBaseButton-secondary")
    ).to_be_visible()
    expect(
        page.get_by_test_id("stButton").get_by_test_id("stBaseButton-secondary")
    ).to_be_visible()
    expect(page.get_by_label("Assignment Log")).to_contain_text("Assignment Log")

    page.get_by_test_id("stButton").get_by_test_id("stBaseButton-secondary").click()
    expect(page.get_by_label("📋 PDF ➜ BlueTable Auto-Fill")).to_contain_text(
        "📋 PDF ➜ BlueTable Auto-Fill"
    )

def test_flatten_pdf_flow(page: Page):
    acroform_pdf_path = str(repo_root / "resources" / "FilledApplication.pdf")
    flatten_pdf_path = str(repo_root / "resources" / "PrintedApplication.pdf")

    # Seed the registry with AcroForm PDF so the flattened one can match
    from src.pdf_processor.engine import update_pdf_registry
    update_pdf_registry(acroform_pdf_path)

    # 1. Start the flow
    page.goto("http://localhost:8501/pdf_to_blue_table")
    expect(page.get_by_label("📋 PDF ➜ BlueTable Auto-Fill")).to_contain_text(
        "📋 PDF ➜ BlueTable Auto-Fill"
    )
    expect(page.get_by_test_id("stBaseButton-secondary")).to_be_visible()

    # 2. Upload the flattened file
    page.get_by_test_id("stBaseButton-secondary").click()
    page.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(flatten_pdf_path)

    # 3. Form Interactions & UI validation
    expect(page.get_by_role("img")).to_be_visible()
    expect(
        page.get_by_text("Main InsuredMain InsuredAssignClear")
    ).to_be_visible()
    expect(page.get_by_label("🔵 BlueTable")).to_contain_text("🔵 BlueTable")
    expect(page.get_by_role("button", name="⬇️")).to_be_visible()
    expect(page.get_by_role("button", name="✅")).to_be_visible()

    # Clicking sequences
    page.get_by_role("button", name="⬇️").click()
    page.get_by_test_id("stBaseButton-secondary").first.click()
    page.get_by_role("button", name="✅").click()

    expect(
        page.get_by_test_id("stDownloadButton").get_by_test_id("stBaseButton-secondary")
    ).to_be_visible()

    expect(page.get_by_test_id("stJson")).to_contain_text('"name"')
