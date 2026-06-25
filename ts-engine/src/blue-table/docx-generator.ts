/**
 * BlueTable DOCX generation using docxtemplater.
 *
 * Ported from blue_table_tools/docx_generator.py
 *
 * The Python version does raw XML table cell manipulation via python-docx.
 * This TypeScript version uses docxtemplater with {placeholder} tags,
 * which requires the BlueTable DOCX template to be redesigned with
 * tags like {main_name}, {main_dob}, {sp_name}, etc.
 *
 * The visual output of the generated document stays identical — only
 * the data injection mechanism changes.
 */
import Docxtemplater from "docxtemplater";
import PizZip from "pizzip";

/**
 * Fill a BlueTable DOCX template with customer data.
 *
 * The template should contain {placeholder} tags in table cells.
 * Returns the filled DOCX as a Uint8Array.
 *
 * @param templateBytes - The DOCX template file as bytes
 * @param data - Key-value pairs matching the template placeholders
 * @param config - Product configuration (used for plan/premium lookups)
 */
export function fillBlueTableDocx(
  templateBytes: Uint8Array | Buffer,
  data: Record<string, string>,
  config?: Record<string, unknown>,
): Uint8Array {
  const zip = new PizZip(templateBytes);

  const doc = new Docxtemplater(zip, {
    paragraphLoop: true,
    linebreaks: true,
    // Don't throw on missing tags — just leave them empty
    nullGetter: () => "",
  });

  // Build the template data object
  // This maps BlueTable field keys to their values
  const templateData: Record<string, string> = {};

  // Direct data passthrough
  for (const [key, value] of Object.entries(data)) {
    templateData[key] = value ?? "";
  }

  // If config has plan information, resolve plan names and premiums
  if (config) {
    const plans = config["plans"] as Record<string, unknown> | undefined;
    if (plans && data["plan"]) {
      const planInfo = plans[data["plan"]] as Record<string, string> | undefined;
      if (planInfo) {
        templateData["plan_name"] = planInfo["name"] ?? data["plan"];
        templateData["plan_premium"] = planInfo["premium"] ?? "";
      }
    }
  }

  doc.render(templateData);

  const output = doc.getZip().generate({
    type: "uint8array",
    compression: "DEFLATE",
  });

  return output as Uint8Array;
}
