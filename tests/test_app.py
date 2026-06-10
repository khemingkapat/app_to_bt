import re
import os
from playwright.sync_api import Page, expect


def test_landing_page(page: Page):
    page.goto("http://localhost:8501")
    expect(page).to_have_title(re.compile("AXA Health Insurance Application"))
    expect(
        page.get_by_role("heading", name="🏥 AXA Health Insurance Application Portal")
    ).to_be_visible()


def test_pdf_tool_navigation(page: Page):
    page.goto("http://localhost:8501")
    page.get_by_role("button", name="🚀 Launch PDF to BlueTable Tool").click()
    # Wait for the heading in the new page to appear.
    expect(
        page.get_by_role("heading", name="📋 PDF ➜ BlueTable Auto-Fill")
    ).to_be_visible()


def test_pdf_to_bluetable_flow(page: Page):
    # Find the sample PDF file relative to the project root folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.abspath(
        os.path.join(current_dir, "../sources/FilledApplication.pdf")
    )

    # 1. Start the flow
    page.goto("http://localhost:8501/pdf_to_blue_table")
    expect(page.get_by_label("📋 PDF ➜ BlueTable Auto-Fill")).to_contain_text(
        "📋 PDF ➜ BlueTable Auto-Fill"
    )
    expect(page.get_by_test_id("stBaseButton-secondary")).to_be_visible()

    # 2. Upload the file
    page.get_by_test_id("stBaseButton-secondary").click()
    page.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(pdf_path)
    # 3. Form Interactions & UI validation
    expect(page.get_by_role("img")).to_be_visible()
    expect(
        page.get_by_text("Main InsuredMain InsuredAssignClearDate of BirthDate of")
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
    expect(page.get_by_text('[0:{"field_name":"Text2""')).to_be_visible()
    expect(page.get_by_text('0:{"field_name":"Text2""')).to_be_visible()
    expect(page.get_by_test_id("stJson")).to_contain_text('"name_naja"')
    expect(page.get_by_test_id("stJson")).to_contain_text('"nationality"')

    expect(
        page.get_by_test_id("stDownloadButton").get_by_test_id("stBaseButton-secondary")
    ).to_be_visible()
    expect(
        page.get_by_test_id("stButton").get_by_test_id("stBaseButton-secondary")
    ).to_be_visible()
    expect(page.get_by_label("Assignment Log")).to_contain_text("Assignment Log")

    # Reset/Clear test
    page.get_by_test_id("stButton").get_by_test_id("stBaseButton-secondary").click()
    expect(page.get_by_label("📋 PDF ➜ BlueTable Auto-Fill")).to_contain_text(
        "📋 PDF ➜ BlueTable Auto-Fill"
    )
