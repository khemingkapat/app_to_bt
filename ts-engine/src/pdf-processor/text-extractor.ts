/**
 * Text extraction from PDFs using mupdf (WASM).
 *
 * Ported from pdf_processor/utils/helpers.py:
 *   - extract_text_from_coords()  → extractTextFromCoords()
 *   - get_word_anchors()          → getWordAnchors()
 *
 * These are the highest-risk operations in the port because they rely on
 * mupdf.js's structured text API instead of PyMuPDF's clip=rect parameter.
 * The approach: extract full page structured text as JSON, then spatially
 * filter text spans whose bounding boxes overlap the target rectangle.
 */
import * as mupdf from "mupdf";
import type { CoordDict } from "./utils/helpers.js";

/** A structured text block as returned by mupdf's toStructuredText().asJSON() */
interface MuPdfTextChar {
  c: string;
  quad: number[]; // [x0,y0, x1,y1, x2,y2, x3,y3] — 4 corners
  /** origin coordinates */
  origin?: [number, number];
}

interface MuPdfTextSpan {
  font: string;
  size: number;
  chars?: MuPdfTextChar[];
}

interface MuPdfTextLine {
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  spans: MuPdfTextSpan[];
}

interface MuPdfTextBlock {
  type: string;
  bbox: [number, number, number, number];
  lines: MuPdfTextLine[];
}

interface MuPdfStructuredText {
  blocks: MuPdfTextBlock[];
}

/** Page info matching the registry format. */
interface PageInfo {
  page_num: number;
  page_w: number;
  page_h: number;
}

/** Field info subset needed for text extraction. */
interface FieldForExtraction {
  name: string;
  field_kind: string;
  page?: number;
  coords?: CoordDict | null;
  widgets?: Array<{ page?: number; coords?: CoordDict | null }>;
}

/**
 * Check if two axis-aligned rectangles overlap.
 * Both are [x0, y0, x1, y1] format.
 */
function rectsOverlap(
  a: [number, number, number, number],
  b: [number, number, number, number],
): boolean {
  return a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
}

/**
 * Convert structured text {x, y, w, h} bbox to [x0, y0, x1, y1] format.
 */
function parseBbox(bbox: any): [number, number, number, number] {
  if (Array.isArray(bbox)) {
    return [bbox[0], bbox[1], bbox[2], bbox[3]];
  }
  if (bbox && typeof bbox === "object") {
    return [bbox.x, bbox.y, bbox.x + bbox.w, bbox.y + bbox.h];
  }
  return [0, 0, 0, 0];
}

/**
 * Extract text from a PDF page within a specific bounding box.
 *
 * This replaces PyMuPDF's `page.get_text("text", clip=rect)`.
 * Strategy: get structured text JSON, filter lines whose bbox overlaps
 * the target rect, extract character content.
 */
function extractTextFromPage(
  page: mupdf.PDFPage,
  targetRect: [number, number, number, number],
): string {
  const st = page.toStructuredText("preserve-whitespace");
  const json: any = JSON.parse(st.asJSON());

  const matchedTexts: string[] = [];

  for (const block of json.blocks) {
    if (block.type !== "text") continue;
    const blockBox = parseBbox(block.bbox);
    if (!rectsOverlap(blockBox, targetRect)) continue;

    for (const line of block.lines) {
      const lineBox = parseBbox(line.bbox);
      if (!rectsOverlap(lineBox, targetRect)) continue;

      // If characters are not present (or we just want line-level text), check line text
      if (line.text && !line.spans?.some((s: any) => s.chars && s.chars.length > 0)) {
        matchedTexts.push(line.text);
        continue;
      }

      const lineChars: string[] = [];
      for (const span of line.spans || []) {
        if (span.chars && span.chars.length > 0) {
          for (const ch of span.chars) {
            if (ch.quad && ch.quad.length >= 4) {
              const cx = (ch.quad[0] + ch.quad[2]) / 2;
              const cy = (ch.quad[1] + ch.quad[3]) / 2;
              if (
                cx >= targetRect[0] &&
                cx <= targetRect[2] &&
                cy >= targetRect[1] &&
                cy <= targetRect[3]
              ) {
                lineChars.push(ch.c);
              }
            }
          }
        } else if (span.text) {
          lineChars.push(span.text);
        }
      }
      if (lineChars.length > 0) {
        matchedTexts.push(lineChars.join(""));
      }
    }
  }

  return matchedTexts.join("\n").trim();
}

/**
 * Extract text from a flattened PDF using structural bounding box coordinates.
 *
 * Direct port of Python's extract_text_from_coords().
 * Expects coordinates in PDF coordinate system (bottom-left origin).
 */
export function extractTextFromCoords(
  pdfBytes: Uint8Array | Buffer,
  fields: FieldForExtraction[],
  pagesInfo: PageInfo[],
): Record<string, string> {
  const doc = mupdf.Document.openDocument(pdfBytes, "application/pdf") as mupdf.PDFDocument;
  const pageHeights = new Map(pagesInfo.map((p) => [p.page_num, p.page_h]));
  const valuesDict: Record<string, string> = {};
  const pageCount = doc.countPages();

  try {
    for (const field of fields) {
      const name = field.name;
      const kind = field.field_kind ?? "text";

      // Radio/checkbox visual marks aren't meaningful text
      if (kind === "radio" || kind === "checkbox") {
        valuesDict[name] = "";
        continue;
      }

      // Determine source coordinates
      let sources: Array<{ pageNum: number; coords: CoordDict }> = [];
      if (kind === "radio" && field.widgets) {
        sources = field.widgets
          .filter((w) => w.page && w.coords)
          .map((w) => ({ pageNum: w.page!, coords: w.coords! }));
      } else if (field.coords && field.page) {
        sources = [{ pageNum: field.page, coords: field.coords }];
      }

      const extractedTexts: string[] = [];
      for (const { pageNum, coords } of sources) {
        const pdfH = pageHeights.get(pageNum);
        if (!pdfH || pageNum - 1 >= pageCount) continue;

        // Convert from PDF coords (bottom-left origin) to mupdf coords (top-left origin)
        const targetRect: [number, number, number, number] = [
          coords.x0,
          pdfH - coords.y1,
          coords.x1,
          pdfH - coords.y0,
        ];

        const page = doc.loadPage(pageNum - 1) as mupdf.PDFPage;
        const text = extractTextFromPage(page, targetRect);
        if (text) {
          extractedTexts.push(text);
        }
      }

      valuesDict[name] = extractedTexts.length > 0 ? extractedTexts.join(" ") : "";
    }
  } finally {
    doc.destroy();
  }

  return valuesDict;
}

/**
 * Extract the topmost text lines from the first page of a PDF.
 *
 * Direct port of Python's get_word_anchors().
 * These "word anchors" identify a flattened form by its header text.
 */
export function getWordAnchors(
  pdfBytes: Uint8Array | Buffer,
  numLines = 3,
): string[] {
  const doc = mupdf.Document.openDocument(pdfBytes, "application/pdf") as mupdf.PDFDocument;

  try {
    const page = doc.loadPage(0) as mupdf.PDFPage;
    const st = page.toStructuredText("preserve-whitespace");
    const json: MuPdfStructuredText = JSON.parse(st.asJSON());

    // Collect all text blocks and sort by vertical position (top to bottom)
    const textBlocks = (json.blocks as any[])
      .filter((b) => b.type === "text")
      .sort((a, b) => {
        const bboxA = parseBbox(a.bbox);
        const bboxB = parseBbox(b.bbox);
        return bboxA[1] - bboxB[1];
      });

    const anchors: string[] = [];
    for (const block of textBlocks) {
      // Reconstruct text from lines
      const linesTexts: string[] = [];
      for (const line of block.lines || []) {
        if (line.text) {
          linesTexts.push(line.text);
        } else {
          const spansText = (line.spans || [])
            .map((span: any) => {
              if (span.chars && span.chars.length > 0) {
                return span.chars.map((c: any) => c.c).join("");
              }
              return span.text ?? "";
            })
            .join("");
          linesTexts.push(spansText);
        }
      }

      const blockText = linesTexts.join("\n");
      const lines = blockText
        .split("\n")
        .map((l) => l.trim())
        .filter((l) => l.length > 0);

      anchors.push(...lines);
      if (anchors.length >= numLines) break;
    }

    return anchors.slice(0, numLines);
  } finally {
    doc.destroy();
  }
}
