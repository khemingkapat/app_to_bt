/**
 * Signature stamping onto PDF using pdf-lib.
 *
 * Ported from signature_gateway/pdf_stamping.py
 *
 * Stamps a PNG signature image onto a PDF page at the coordinates
 * resolved from the registry and cache mapping.
 */
import { PDFDocument } from "pdf-lib";
import type { CoordDict } from "../pdf-processor/utils/helpers.js";

/** Registry entry for a PDF template. */
interface RegistryEntry {
  fields: Array<{
    name: string;
    page?: number;
    coords?: CoordDict;
  }>;
}

/**
 * Stamp a PNG signature image onto a PDF at the mapped signature field coordinates.
 *
 * Falls back to bottom-right of the last page if no signature field is found.
 * Returns the stamped PDF as Uint8Array.
 */
export async function stampSignature(
  pdfBytes: Uint8Array,
  sigImageBytes: Uint8Array,
  pdfId?: string,
  registryDict?: Record<string, RegistryEntry>,
  cacheMapping?: Record<string, string>,
): Promise<Uint8Array> {
  const pdf = await PDFDocument.load(pdfBytes, { ignoreEncryption: true });
  const sigImage = await pdf.embedPng(sigImageBytes);

  let pageIdx: number | null = null;
  let x = 0;
  let y = 0;
  let width = 0;
  let height = 0;

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

  // Find the signature field coordinates in the registry
  if (registryDict && pdfId) {
    const entry = registryDict[pdfId];
    if (entry) {
      for (const field of entry.fields) {
        if (field.name === sigFieldName && field.coords) {
          const coords = field.coords;
          const pageNum = field.page ?? 5;
          const canvasTop = coords.canvas_top;
          const canvasBottom = coords.canvas_bottom;

          if (
            canvasTop !== undefined &&
            canvasBottom !== undefined &&
            pageNum - 1 >= 0 &&
            pageNum - 1 < pdf.getPageCount()
          ) {
            pageIdx = pageNum - 1;
            const h = canvasBottom - canvasTop;

            // Match the Python scaling: shrink by 25% and shift up by 10%
            x = coords.x0 + 19;
            const adjustedTop = canvasTop - 11 - 0.1 * h;
            const adjustedBottom = canvasBottom + 21 - 0.1 * h;
            width = coords.x1 - 19 - x;
            // pdf-lib uses bottom-left origin, so we need to convert from canvas (top-left)
            // The page height is needed for this conversion
            const page = pdf.getPage(pageIdx);
            const pageHeight = page.getSize().height;
            y = pageHeight - adjustedBottom;
            height = adjustedBottom - adjustedTop;
            break;
          }
        }
      }
    }
  }

  // Fallback: bottom-right area of the last page
  if (pageIdx === null) {
    pageIdx = pdf.getPageCount() - 1;
    const page = pdf.getPage(pageIdx);
    const pageWidth = page.getSize().width;
    const pageHeight = page.getSize().height;
    x = pageWidth * 0.58;
    y = pageHeight * (1 - 0.86); // Convert from top-origin to bottom-origin
    width = pageWidth * (0.88 - 0.58);
    height = pageHeight * (0.86 - 0.76);
  }

  const page = pdf.getPage(pageIdx);
  page.drawImage(sigImage, {
    x,
    y,
    width,
    height,
  });

  return pdf.save();
}
