/**
 * PDF form filling (inverter) using pdf-lib.
 *
 * Ported from pdf_processor/inverter.py
 *
 * Takes customer data + config + field mappings and fills an AcroForm PDF.
 */
import {
  PDFDocument,
  PDFTextField,
  PDFCheckBox,
  PDFRadioGroup,
  PDFDropdown,
} from "pdf-lib";

/**
 * Parse a date string (YYYY-MM-DD or DD/MM/YYYY) and return the requested part.
 * Part can be "DD", "MM", or "YYYY".
 */
export function parseDatePart(dateStr: string, part: "DD" | "MM" | "YYYY"): string {
  if (!dateStr) return "";

  let day = "";
  let month = "";
  let year = "";

  if (dateStr.includes("-")) {
    const parts = dateStr.split("-");
    if (parts[0].length === 4) {
      // YYYY-MM-DD
      [year, month, day] = parts;
    } else {
      // DD-MM-YYYY
      [day, month, year] = parts;
    }
  } else if (dateStr.includes("/")) {
    const parts = dateStr.split("/");
    if (parts[2].length === 4) {
      // DD/MM/YYYY
      [day, month, year] = parts;
    } else {
      // YYYY/MM/DD
      [year, month, day] = parts;
    }
  } else {
    return dateStr;
  }

  switch (part) {
    case "DD":
      return day.padStart(2, "0");
    case "MM":
      return month.padStart(2, "0");
    case "YYYY":
      return year;
  }
}

/** Field mapping entry from the assignment cache / config. */
interface FieldMapping {
  bt_key?: string;
  label?: string;
}

/**
 * Map standard customer data fields to physical PDF AcroForm field values.
 * Handles split fields like DOB (day/month/year in separate fields).
 */
export function mapCustomerDataToPdf(
  customerData: Record<string, string>,
  _config: Record<string, unknown>,
  fieldMappings: Record<string, string | FieldMapping>,
): Record<string, string> {
  const pdfValues: Record<string, string> = {};

  for (const [pdfField, mapping] of Object.entries(fieldMappings)) {
    let btKey: string | undefined;
    let label = "";

    if (typeof mapping === "object" && mapping !== null) {
      btKey = mapping.bt_key;
      label = (mapping.label ?? "").toUpperCase();
    } else {
      btKey = mapping;
    }

    if (!btKey || !(btKey in customerData)) continue;

    const value = customerData[btKey] ?? "";

    // Handle date parts for DOB fields
    if (btKey.includes("dob") || btKey.includes("date")) {
      const dateStr = String(value);
      let part: "DD" | "MM" | "YYYY" | null = null;

      if (label.includes("DAY") || label.includes("(DD)")) {
        part = "DD";
      } else if (label.includes("MONTH") || label.includes("(MM)")) {
        part = "MM";
      } else if (label.includes("YEAR") || label.includes("(YYYY)")) {
        part = "YYYY";
      } else {
        // Fallback: check if multiple fields map to same bt_key
        const siblingFields = Object.entries(fieldMappings)
          .filter(([, m]) => {
            const k = typeof m === "object" ? m.bt_key : m;
            return k === btKey;
          })
          .map(([f]) => f)
          .sort((a, b) => {
            const aNum = parseInt(a.match(/\d+/)?.[0] ?? "0");
            const bNum = parseInt(b.match(/\d+/)?.[0] ?? "0");
            return aNum - bNum;
          });

        if (siblingFields.length > 1) {
          const idx = siblingFields.indexOf(pdfField);
          if (idx === 0) part = "DD";
          else if (idx === 1) part = "MM";
          else if (idx === 2) part = "YYYY";
        }
      }

      if (part) {
        pdfValues[pdfField] = parseDatePart(dateStr, part);
      } else {
        pdfValues[pdfField] = dateStr;
      }
    } else {
      pdfValues[pdfField] = String(value);
    }
  }

  return pdfValues;
}

/**
 * Fill an AcroForm PDF with customer data using config and field mappings.
 *
 * Returns the filled PDF as a Uint8Array.
 */
export async function fillAcroformPdf(
  pdfBytes: Uint8Array,
  customerData: Record<string, string>,
  config: Record<string, unknown>,
  fieldMappings: Record<string, string | FieldMapping>,
): Promise<Uint8Array> {
  const pdfValues = mapCustomerDataToPdf(customerData, config, fieldMappings);

  const pdf = await PDFDocument.load(pdfBytes, {
    ignoreEncryption: true,
  });

  const form = pdf.getForm();

  for (const [fieldName, value] of Object.entries(pdfValues)) {
    try {
      const field = form.getField(fieldName);

      if (field instanceof PDFTextField) {
        field.setText(value);
      } else if (field instanceof PDFCheckBox) {
        if (value === "/Yes" || value === "Yes" || value === "true") {
          field.check();
        } else {
          field.uncheck();
        }
      } else if (field instanceof PDFRadioGroup) {
        // Strip leading "/" for pdf-lib's select method
        const option = value.startsWith("/") ? value.slice(1) : value;
        if (option) {
          field.select(option);
        }
      } else if (field instanceof PDFDropdown) {
        if (value) {
          field.select(value);
        }
      }
    } catch {
      // Field not found or incompatible — skip silently
      // This matches the Python behavior which uses writer.update_page_form_field_values
      // which also silently ignores missing fields
    }
  }

  return pdf.save();
}
