const { getDocument } = require("pdfjs-dist/legacy/build/pdf");

/**
 * Extracts text from a flattened PDF using structural bounding box coordinates.
 * Expects PyPDF-style coordinates (bottom-left origin) but processes via PDF.js.
 */
async function extractTextFromCoords(pdfBuffer, fields, pagesInfo) {
    const data = new Uint8Array(pdfBuffer);
    const loadingTask = getDocument({ data });
    const doc = await loadingTask.promise;

    const pageHeights = {};
    for (const p of pagesInfo) {
        pageHeights[p.page_num] = p.page_h;
    }

    const valuesDict = {};

    for (const field of fields) {
        const name = field.name;
        const kind = field.field_kind || "text";

        let sources = [];
        if (kind === "radio") {
            sources = (field.widgets || []).map((w) => [w.page || 1, w.coords]);
        } else {
            const coords = field.coords;
            const pageNum = field.page || 1;
            if (coords) {
                sources = [[pageNum, coords]];
            }
        }

        if (kind === "radio" || kind === "checkbox") {
            valuesDict[name] = "";
            continue;
        }

        const extractedTexts = [];
        for (const [pageNum, coords] of sources) {
            if (!coords || !pageHeights[pageNum]) {
                continue;
            }
            if ((pageNum - 1) >= doc.numPages) {
                continue;
            }

            const pdfH = pageHeights[pageNum];
            const x0 = coords.x0;
            const x1 = coords.x1;
            // Map pypdf coordinates to standard top-left PDF.js/canvas coordinates
            const y0 = pdfH - coords.y1;
            const y1 = pdfH - coords.y0;

            const page = await doc.getPage(pageNum);
            const textContent = await page.getTextContent();

            // Reconstruct text in bounding box
            const textParts = [];
            for (const item of textContent.items) {
                // PDF.js transform: [scaleX, skewY, skewX, scaleY, tx, ty]
                // ty is bottom-left y coordinate
                const tx = item.transform[4];
                const ty = pdfH - item.transform[5]; // Convert ty to top-left

                const itemW = item.width;
                const itemH = item.height;

                // Simple bounding box intersection
                if (tx >= x0 - 5 && tx <= x1 + 5 && ty >= y0 - 15 && ty <= y1 + 5) {
                    textParts.push(item.str);
                }
            }

            if (textParts.length > 0) {
                extractedTexts.push(textParts.join("").trim());
            }
        }

        valuesDict[name] = extractedTexts.length > 0 ? extractedTexts.join(" ") : "";
    }

    return valuesDict;
}

/**
 * Extracts the topmost text lines from the first page of the PDF.
 * These 'word anchors' can be used to identify a flattened form.
 */
async function getWordAnchors(pdfBuffer, numLines = 3) {
    const data = new Uint8Array(pdfBuffer);
    const loadingTask = getDocument({ data });
    const doc = await loadingTask.promise;

    const page = await doc.getPage(1);
    const textContent = await page.getTextContent();

    // Sort items vertically top-to-bottom
    const items = textContent.items.map(item => ({
        text: item.str,
        y: item.transform[5] // bottom-up y coordinate in pdf.js
    })).sort((a, b) => b.y - a.y);

    const anchors = [];
    for (const item of items) {
        const text = item.text.trim();
        if (text) {
            anchors.push(text);
            if (anchors.length >= numLines) {
                break;
            }
        }
    }

    return anchors.slice(0, numLines);
}

function rectToDict(rect, pageHeight = null) {
    if (!rect || !Array.isArray(rect) || rect.length !== 4) {
        return null;
    }
    try {
        const [x0, y0, x1, y1] = rect.map(Number);
        if (isNaN(x0) || isNaN(y0) || isNaN(x1) || isNaN(y1)) return null;

        const result = {
            x0: Math.round(x0 * 100) / 100,
            y0: Math.round(y0 * 100) / 100,
            x1: Math.round(x1 * 100) / 100,
            y1: Math.round(y1 * 100) / 100,
            width: Math.round((x1 - x0) * 100) / 100,
            height: Math.round((y1 - y0) * 100) / 100,
        };

        if (pageHeight !== null) {
            result.canvas_top = Math.round((pageHeight - y1) * 100) / 100;
            result.canvas_bottom = Math.round((pageHeight - y0) * 100) / 100;
        }
        return result;
    } catch (e) {
        return null;
    }
}

function getPageDimensions(pageInfo) {
    const DEFAULT_WIDTH = 595.27;
    const DEFAULT_HEIGHT = 842.0;

    if (!pageInfo || !pageInfo.mediaBox) {
        return [DEFAULT_WIDTH, DEFAULT_HEIGHT];
    }

    const width = pageInfo.mediaBox[2] - pageInfo.mediaBox[0];
    const height = pageInfo.mediaBox[3] - pageInfo.mediaBox[1];

    return [Math.round(width * 100) / 100, Math.round(height * 100) / 100];
}

module.exports = {
    extractTextFromCoords,
    getWordAnchors,
    rectToDict,
    getPageDimensions
};
