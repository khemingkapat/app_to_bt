import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { stampSignature } from "../src/signature/pdf-stamping.js";
import { fillBlueTableDocx } from "../src/blue-table/docx-generator.js";

describe("Signature Stamping & DOCX Generation Tests", () => {
  const resourcesDir = path.resolve(__dirname, "../../resources");
  
  it("should stamp signature on a PDF without throwing errors", async () => {
    const pdfBytes = fs.readFileSync(path.join(resourcesDir, "OriginalApplication.pdf"));
    
    // Create a 1x1 pixel transparent PNG buffer for testing the stamp process
    const dummyPngBytes = new Uint8Array([
      137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 1,
      0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0, 0, 13, 73, 68, 65, 84,
      120, 156, 99, 96, 0, 0, 0, 2, 0, 1, 73, 175, 167, 104, 0, 0, 0, 0, 73,
      69, 78, 68, 174, 66, 96, 130
    ]);
    
    const outputPdf = await stampSignature(
      pdfBytes,
      dummyPngBytes,
      "dummy-id",
      {
        "dummy-id": {
          fields: [
            {
              name: "Text94",
              page: 1,
              coords: {
                x0: 100,
                y0: 100,
                x1: 200,
                y1: 200,
                canvas_top: 100,
                canvas_bottom: 200
              }
            }
          ]
        }
      },
      {
        "Text94": "signature"
      }
    );
    
    expect(outputPdf).toBeDefined();
    expect(outputPdf.length).toBeGreaterThan(0);
  });

  it("should parse and fill a basic Word template using docxtemplater", () => {
    const templateBytes = fs.readFileSync(path.join(resourcesDir, "BlueTable.docx"));
    
    // Test filling docx
    const outputDocx = fillBlueTableDocx(
      templateBytes,
      {
        "main_name": "Test Customer",
        "plan": "premium-plan"
      },
      {
        plans: {
          "premium-plan": {
            name: "Premium Health & Accident Protection Plan",
            premium: "1250.00"
          }
        }
      }
    );
    
    expect(outputDocx).toBeDefined();
    expect(outputDocx.length).toBeGreaterThan(0);
  });
});
