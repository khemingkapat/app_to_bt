/**
 * Application-to-BlueTable Engine — Public API
 *
 * This is the main entry point for all PDF/DOCX processing operations.
 * Import from here in the Lovable React app.
 */

// PDF Processing
export { walkFields } from "./pdf-processor/walker.js";
export type { FieldInfo, FieldKind, WidgetInfo } from "./pdf-processor/walker.js";

export { extractTextFromCoords, getWordAnchors } from "./pdf-processor/text-extractor.js";

export { getPdfFileId, getPageDimensionsList } from "./pdf-processor/utils/pdf-info.js";

export {
  fillAcroformPdf,
  mapCustomerDataToPdf,
  parseDatePart,
} from "./pdf-processor/inverter.js";

// Geometry Utilities
export {
  rectToCoords,
  calculateCenter,
  dist,
} from "./pdf-processor/utils/helpers.js";
export type { CoordDict } from "./pdf-processor/utils/helpers.js";

// Signature
export { stampSignature } from "./signature/pdf-stamping.js";

// DOCX Generation
export { fillBlueTableDocx } from "./blue-table/docx-generator.js";
