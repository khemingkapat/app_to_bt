const crypto = require('crypto');
const { PDFDocument } = require('pdf-lib');
const stringify = require('json-stable-stringify');
const { getWordAnchors, extractTextFromCoords, getPageDimensions } = require('./utils/helpers');
const { walkFields } = require('./core/walker');

/**
 * Extracts the permanent unique cryptographic ID from the PDF trailer.
 */
function getPdfFileId(pdfDoc) {
    try {
        const idArray = pdfDoc.context.lookup(pdfDoc.context.trailerInfo.ID);
        if (idArray && idArray.size() > 0) {
            const rawId = idArray.get(0);
            if (rawId && rawId.value) {
                // Buffer to hex
                return Buffer.from(rawId.value, 'binary').toString('hex');
            }
        }
    } catch (e) {
        // Fallback
    }
    return "UNKNOWN_ID";
}

/**
 * Parses a PDF file and extracts its structure and values statelessly.
 * Accepts a Buffer object instead of a file path.
 *
 * Returns:
 *   { pdf_id, registry_dict, values_dict }
 */
async function processPdf(pdfBuffer, existingRegistry = null) {
    const pdfDoc = await PDFDocument.load(pdfBuffer);
    const pdf_id = getPdfFileId(pdfDoc);

    const pagesList = [];
    const pages = pdfDoc.getPages();
    for (let i = 0; i < pages.length; i++) {
        const page = pages[i];
        // Mock pageInfo to match what helpers expect or calculate directly
        const { width, height } = page.getSize();
        pagesList.push({
            page_num: i + 1,
            page_w: Math.round(width * 100) / 100,
            page_h: Math.round(height * 100) / 100
        });
    }

    let rawFields = [];
    try {
        rawFields = walkFields(pdfDoc);
    } catch (e) {
        console.warn("Failed to walk fields:", e);
    }

    const wordAnchors = await getWordAnchors(pdfBuffer);
    let valuesDict = {};
    let cleanStructuralFields = [];
    let registryDict = {};

    if (rawFields && rawFields.length > 0) {
        // Normal AcroForm PDF
        for (const field of rawFields) {
            const name = field.name;
            valuesDict[name] = field.value || "";

            // Clone to remove value
            const structField = JSON.parse(JSON.stringify(field));
            delete structField.value;

            // Preserve choices_map from existing registry if present
            if (existingRegistry && existingRegistry[pdf_id]) {
                const existingFields = existingRegistry[pdf_id].fields || [];
                for (const ef of existingFields) {
                    if (ef.name === name && ef.choices_map) {
                        structField.choices_map = ef.choices_map;
                        break;
                    }
                }
            }
            cleanStructuralFields.push(structField);
        }

        const structuralData = { pages: pagesList, fields: cleanStructuralFields };
        const structuralJson = stringify(structuralData);
        const structuralHash = crypto.createHash('sha256').update(structuralJson, 'utf-8').digest('hex');

        let matchedId = pdf_id;
        if (existingRegistry) {
            for (const [existingId, existingData] of Object.entries(existingRegistry)) {
                if (existingData.structural_hash === structuralHash) {
                    matchedId = existingId;
                    break;
                }
            }
        }

        registryDict[matchedId] = {
            pages: pagesList,
            fields: cleanStructuralFields,
            structural_hash: structuralHash,
            word_anchors: wordAnchors
        };

        return { pdf_id: matchedId, registry_dict: registryDict, values_dict: valuesDict };

    } else {
        // Flattened PDF
        let matched = false;
        let matchedId = pdf_id;
        let structuralHash = null;

        if (existingRegistry) {
            for (const [existingId, existingData] of Object.entries(existingRegistry)) {
                const existingAnchors = existingData.word_anchors || [];

                if (existingAnchors.length > 0 && wordAnchors.length > 0) {
                    let hasMatch = false;
                    for (const anchor of wordAnchors) {
                        for (const existingAnchor of existingAnchors) {
                            if (anchor.includes(existingAnchor) || existingAnchor.includes(anchor)) {
                                hasMatch = true;
                                break;
                            }
                        }
                        if (hasMatch) break;
                    }

                    if (hasMatch) {
                        matchedId = existingId;
                        cleanStructuralFields = existingData.fields || [];
                        structuralHash = existingData.structural_hash;
                        matched = true;
                        break;
                    }
                }
            }
        }

        if (matched && cleanStructuralFields.length > 0) {
            valuesDict = await extractTextFromCoords(pdfBuffer, cleanStructuralFields, pagesList);
        }

        registryDict[matchedId] = {
            pages: pagesList,
            fields: cleanStructuralFields,
            structural_hash: structuralHash,
            word_anchors: wordAnchors
        };

        return { pdf_id: matchedId, registry_dict: registryDict, values_dict: valuesDict };
    }
}

module.exports = {
    getPdfFileId,
    processPdf
};
