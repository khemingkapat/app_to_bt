# WP2-7: Align Active Field Index on Page Navigation

## Overview
Currently, when the user navigates between PDF pages using the "Next Page" or "Previous Page" buttons, the `activeFieldIndex` does not update to match. This causes confusing UX when clicking "Skip", as it jumps back to the previous page's field.

## Changes
- Modified `nextPage()` and `prevPage()` in `gateway/public/index.html`.
- Added logic to search `allFields` for the first field present on the newly navigated page.
- If a field is found:
    - `activeFieldIndex` is updated to that field's index.
    - `activeWidgetIndex` is reset to 0.
    - `displayField(activeFieldIndex)` is called to highlight the field and update the UI.
- If no field is found on the page, the system falls back to `renderPDFPage(currentPageNum, null)`, which simply renders the page without any field highlight.

## Impact
This change ensures that the active field state is always synchronized with the page the user is currently viewing, providing a more intuitive mapping experience.
