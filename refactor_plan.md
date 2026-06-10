# Refactoring Plan

1. **Memory over Disk for PDFs (Remove `temp_upload.pdf`)**
   - Update `src/pdf_processor/engine.py` (`process_pdf`) to support `io.BytesIO` streams in addition to file paths.
   - Pass the uploaded file bytes directly using Streamlit's `session_state` and `io.BytesIO` instead of saving to the filesystem.

2. **Decouple Logic from Streamlit UI**
   - Create a new module `src/bluetable_tools.py` containing utility functions that operate on standard Python dictionaries and lists.
   - Move `BLUETABLE_FIELDS` schema, data formatting logic, and cache loading/saving mechanisms out of the UI module.
   - Extract the `do_assign` and `do_clear` logic into modular functions that take pure data dictionaries and lists as inputs. This ensures the mapping logic can function without Streamlit.

3. **Streamlit Multi-page Structure (Landing Page)**
   - Create a `pages/` directory. Move the main UI functionality currently in `app.py` into `pages/1_PDF_to_BlueTable.py`.
   - Rewrite `app.py` as a landing page portal containing a header "AXA health insurance application" and a navigation button pointing to the "PDF to BlueTable" tool.

4. **Update Package Description**
   - Modify the `description` field in `pyproject.toml` to clearly describe the final version of the code and its isolated tools structure.

5. **Complete Pre-commit Steps**
   - Ensure proper testing, verifications, reviews, and reflections are done. Run any required checks to confirm that the existing functions are not broken and the logic functions correctly.

6. **Submit Code**
   - Commit and push the branch.
