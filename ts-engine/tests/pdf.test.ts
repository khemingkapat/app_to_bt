import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { walkFields } from "../src/pdf-processor/walker.js";
import { extractTextFromCoords } from "../src/pdf-processor/text-extractor.js";
import { getPdfFileId, getPageDimensionsList } from "../src/pdf-processor/utils/pdf-info.js";

describe("PDF processing integration tests", () => {
  const resourcesDir = path.resolve(__dirname, "../../resources");
  const annotatedPdfPath = path.join(resourcesDir, "AnnotatedApplicationExample.pdf");
  const originalPdfPath = path.join(resourcesDir, "OriginalApplication.pdf");

  it("should extract PDF identity and basic info", async () => {
    const pdfBytes = fs.readFileSync(annotatedPdfPath);
    const id = await getPdfFileId(pdfBytes);
    const dims = await getPageDimensionsList(pdfBytes);
    
    expect(id).toBeDefined();
    expect(typeof id).toBe("string");
    expect(id.length).toBeGreaterThan(0);
    expect(dims.length).toBeGreaterThan(0);
    expect(dims.length).toBe(5);
  });

  it("should walk fields in an AcroForm PDF", async () => {
    // AnnotatedApplicationExample.pdf is an AcroForm PDF
    const pdfBytes = fs.readFileSync(annotatedPdfPath);
    const fields = await walkFields(pdfBytes);

    expect(fields).toBeDefined();
    expect(fields.length).toBeGreaterThan(0);
    
    // Check structure of a sample field
    const field = fields[0];
    expect(field).toHaveProperty("name");
    expect(field).toHaveProperty("field_kind");
    expect(field).toHaveProperty("value");
    expect(field).toHaveProperty("page");
  });

  it("should initialize mupdf and perform text extraction from coords", async () => {
    const pdfBytes = fs.readFileSync(originalPdfPath);
    
    // Try to extract text at a sample location.
    const text = await extractTextFromCoords(
      pdfBytes,
      [
        {
          name: "SampleField",
          field_kind: "text",
          page: 1,
          coords: { x0: 0, y0: 0, x1: 1000, y1: 1000 }
        }
      ],
      [
        { page_num: 1, page_w: 1000, page_h: 1000 }
      ]
    );
    
    expect(text).toBeDefined();
    expect(typeof text.SampleField).toBe("string");
  });

  it("should extract text from flattened PrintedApplication.pdf using mupdf", async () => {
    const pdfBytes = fs.readFileSync(path.join(resourcesDir, "PrintedApplication.pdf"));
    
    // Parse dimensions first to get heights
    const dims = await getPageDimensionsList(pdfBytes);
    expect(dims.length).toBeGreaterThan(0);
    
    // Extract text from the entire first page using a large bounding box
    const text = await extractTextFromCoords(
      pdfBytes,
      [
        {
          name: "full_page_1",
          field_kind: "text",
          page: 1,
          coords: { x0: 0, y0: 0, x1: dims[0].page_w, y1: dims[0].page_h }
        }
      ],
      dims
    );

    expect(text).toBeDefined();
    expect(typeof text.full_page_1).toBe("string");
    // Verify that we actually extracted readable text characters from the flattened page
    expect(text.full_page_1.length).toBeGreaterThan(0);
  });
});
