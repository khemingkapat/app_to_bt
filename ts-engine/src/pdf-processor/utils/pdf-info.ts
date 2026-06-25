/**
 * PDF identity and metadata extraction using pdf-lib.
 *
 * Ported from pdf_processor/utils/pdf_info.py
 */
import { PDFDocument, PDFHexString, PDFString } from "pdf-lib";

/**
 * Extract the permanent unique cryptographic /ID from the PDF trailer.
 * Returns hex string of the first ID element, or "UNKNOWN_ID" on failure.
 */
export async function getPdfFileId(pdfBytes: Uint8Array): Promise<string> {
  try {
    const pdf = await PDFDocument.load(pdfBytes, {
      updateMetadata: false,
      ignoreEncryption: true,
    });

    const trailer = pdf.context.trailerInfo;
    const idArray = trailer.ID as any;
    if (idArray && typeof idArray.asArray === "function") {
      const arr = idArray.asArray();
      if (arr.length > 0) {
        const rawId = arr[0];
        if (rawId instanceof PDFHexString) {
          return rawId.asString()
            .split("")
            .map((c) => c.charCodeAt(0).toString(16).padStart(2, "0"))
            .join("");
        }
        if (rawId instanceof PDFString) {
          return rawId
            .asString()
            .split("")
            .map((c) => c.charCodeAt(0).toString(16).padStart(2, "0"))
            .join("");
        }
        return String(rawId);
      }
    }
  } catch {
    // Fall through to UNKNOWN_ID
  }
  return "UNKNOWN_ID";
}

/**
 * Get page dimensions from a PDFDocument.
 * Returns array of { pageNum, pageW, pageH } for each page.
 */
export async function getPageDimensionsList(
  pdfBytes: Uint8Array,
): Promise<Array<{ page_num: number; page_w: number; page_h: number }>> {
  const pdf = await PDFDocument.load(pdfBytes, {
    updateMetadata: false,
    ignoreEncryption: true,
  });
  const pages = pdf.getPages();
  return pages.map((page, idx) => {
    const { width, height } = page.getSize();
    return {
      page_num: idx + 1,
      page_w: Math.round(width * 100) / 100,
      page_h: Math.round(height * 100) / 100,
    };
  });
}
