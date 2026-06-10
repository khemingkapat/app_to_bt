import re
from playwright.sync_api import Page, expect

def test_landing_page(page: Page):
    page.goto("http://localhost:8501")
    expect(page).to_have_title(re.compile("AXA Health Insurance Application"))
    expect(page.get_by_role("heading", name="🏥 AXA Health Insurance Application Portal")).to_be_visible()

def test_pdf_tool_navigation(page: Page):
    page.goto("http://localhost:8501")
    page.get_by_role("button", name="🚀 Launch PDF to BlueTable Tool").click()
    # Wait for the heading in the new page to appear.
    expect(page.get_by_role("heading", name="📋 PDF ➜ BlueTable Auto-Fill")).to_be_visible()
