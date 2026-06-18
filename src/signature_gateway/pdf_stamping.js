const { PDFDocument } = require('pdf-lib');

/**
 * Stamps the PNG signature image onto the PDF page matching the mapped signature field (defaults to Text94) or last page as fallback.
 * Emulates the fitz (PyMuPDF) logic using pdf-lib.
 */
async function stampSignatureOnPdf(pdfBytes, sigImgBytes, pdfId = null, registryDict = null, cacheMapping = null) {
    const pdfDoc = await PDFDocument.load(pdfBytes);

    let pageIdx = null;
    let rectObj = null;

    // Resolve signature field name from cache mapping, defaulting to "Text94"
    let sigFieldName = "Text94";
    if (cacheMapping) {
        for (const [fieldName, mappedKey] of Object.entries(cacheMapping)) {
            if (mappedKey === "signature") {
                sigFieldName = fieldName;
                break;
            }
        }
    }

    if (registryDict && pdfId) {
        const entry = registryDict[pdfId] || {};
        const fields = entry.fields || [];
        for (const field of fields) {
            if (field.name === sigFieldName) {
                const coords = field.coords || {};
                const pageNum = field.page || 5;
                const canvasTop = coords.canvas_top;
                const canvasBottom = coords.canvas_bottom;
                const x0 = coords.x0;
                const x1 = coords.x1;

                if (canvasTop != null && canvasBottom != null && x0 != null && x1 != null) {
                    pageIdx = pageNum - 1;
                    if (pageIdx >= 0 && pageIdx < pdfDoc.getPageCount()) {
                        // Scale down by 25% and shift up by 10% of the canvas height
                        const h = canvasBottom - canvasTop;
                        rectObj = {
                            x: x0 + 19,
                            // PyMuPDF y coordinates are from the top down. pdf-lib uses bottom-left origin.
                            // We use the canvas_top (which is distance from bottom)
                            y: canvasTop - 11 - (0.10 * h),
                            width: (x1 - 19) - (x0 + 19),
                            height: (canvasBottom + 21 - (0.10 * h)) - (canvasTop - 11 - (0.10 * h))
                        };
                        break;
                    } else {
                        pageIdx = null;
                    }
                }
            }
        }
    }

    if (pageIdx === null || rectObj === null) {
        pageIdx = pdfDoc.getPageCount() - 1;
        const page = pdfDoc.getPage(pageIdx);
        const { width, height } = page.getSize();

        // PyMuPDF logic:
        // x0 = width * 0.58, y0 = height * 0.76
        // x1 = width * 0.88, y1 = height * 0.86
        // pdf-lib origin is bottom-left, so we must invert y

        rectObj = {
            x: width * 0.58,
            y: height - (height * 0.86), // invert Y
            width: (width * 0.88) - (width * 0.58),
            height: (height * 0.86) - (height * 0.76)
        };
    }

    const page = pdfDoc.getPage(pageIdx);
    const pngImage = await pdfDoc.embedPng(sigImgBytes);

    page.drawImage(pngImage, {
        x: rectObj.x,
        y: rectObj.y,
        width: rectObj.width,
        height: rectObj.height
    });

    return await pdfDoc.save();
}

module.exports = {
    stampSignatureOnPdf
};