/**
 * AcroForm field walker using pdf-lib.
 *
 * Ported from pdf_processor/core/walker.py
 *
 * pdf-lib's form API abstracts the recursive /Fields tree walk that the
 * Python version does manually. We use getForm().getFields() to get a flat
 * list and then enrich each entry with coordinate and type metadata.
 */
import {
  PDFDocument,
  PDFTextField,
  PDFCheckBox,
  PDFRadioGroup,
  PDFDropdown,
  PDFOptionList,
  PDFSignature,
  PDFField,
  PDFWidgetAnnotation,
} from "pdf-lib";
import { type CoordDict, rectToCoords } from "./utils/helpers.js";

/** The kind of form field — matches the Python walker's field_kind values. */
export type FieldKind = "text" | "checkbox" | "radio" | "choice" | "signature";

/** A single radio/checkbox widget with its own page and coordinates. */
export interface WidgetInfo {
  page: number | null;
  choice_value?: string;
  coords: CoordDict | null;
}

/** A parsed form field with structural metadata. */
export interface FieldInfo {
  field_kind: FieldKind;
  name: string;
  value: string;
  page: number | null;
  coords?: CoordDict | null;
  states?: string[];
  widgets?: WidgetInfo[];
}

/**
 * Walk all AcroForm fields in a PDF and extract structural info.
 *
 * Returns an array of FieldInfo objects matching the Python walker's output
 * format, including field kind, name, value, page number, and coordinates.
 */
export async function walkFields(pdfBytes: Uint8Array): Promise<FieldInfo[]> {
  const pdf = await PDFDocument.load(pdfBytes, {
    updateMetadata: false,
    ignoreEncryption: true,
  });

  const pages = pdf.getPages();
  const pageHeights = pages.map((p) => p.getSize().height);

  // Build a map from widget annotation ref → page index for page resolution
  const widgetToPage = new Map<string, number>();
  for (let i = 0; i < pages.length; i++) {
    const annots = pages[i].node.Annots();
    if (!annots) continue;
    const arr = annots.asArray();
    for (const ref of arr) {
      // Use the object's string representation as key for matching
      widgetToPage.set(String(ref), i);
    }
  }

  let form;
  try {
    form = pdf.getForm();
  } catch {
    // PDF has no AcroForm
    return [];
  }

  const pdfFields = form.getFields();
  const results: FieldInfo[] = [];

  for (const field of pdfFields) {
    const name = field.getName();

    if (field instanceof PDFRadioGroup) {
      const selected = field.getSelected() ?? "";
      const options = field.getOptions();
      const widgets = field.acroField.getWidgets();

      const widgetInfos: WidgetInfo[] = widgets.map((widget) => {
        const { pageIndex, pageHeight } = resolveWidgetPage(widget, widgetToPage, pageHeights);
        const rect = widget.getRectangle();
        const coords = rectToCoords(
          [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height],
          pageHeight,
        );

        // Extract choice value from the widget's appearance state
        const choiceValue = getWidgetAppearanceState(widget) ?? "";

        return {
          page: pageIndex !== null ? pageIndex + 1 : null,
          choice_value: choiceValue,
          coords,
        };
      });

      results.push({
        field_kind: "radio",
        name,
        value: selected ? `/${selected}` : "",
        page: widgetInfos[0]?.page ?? null,
        states: options.map((o) => `/${o}`),
        widgets: widgetInfos,
      });
    } else if (field instanceof PDFCheckBox) {
      const checked = field.isChecked();
      const widget = field.acroField.getWidgets()[0];
      const { pageIndex, pageHeight } = resolveWidgetPage(
        widget,
        widgetToPage,
        pageHeights,
      );
      const rect = widget?.getRectangle();
      const coords = rect
        ? rectToCoords(
            [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height],
            pageHeight,
          )
        : null;

      results.push({
        field_kind: "checkbox",
        name,
        value: checked ? "/Yes" : "/Off",
        page: pageIndex !== null ? pageIndex + 1 : null,
        coords,
      });
    } else if (field instanceof PDFTextField) {
      const value = field.getText() ?? "";
      const widget = field.acroField.getWidgets()[0];
      const { pageIndex, pageHeight } = resolveWidgetPage(
        widget,
        widgetToPage,
        pageHeights,
      );
      const rect = widget?.getRectangle();
      const coords = rect
        ? rectToCoords(
            [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height],
            pageHeight,
          )
        : null;

      results.push({
        field_kind: "text",
        name,
        value,
        page: pageIndex !== null ? pageIndex + 1 : null,
        coords,
      });
    } else if (field instanceof PDFDropdown || field instanceof PDFOptionList) {
      const selected = field.getSelected();
      const value = selected.length > 0 ? selected[0] : "";
      const widget = field.acroField.getWidgets()[0];
      const { pageIndex, pageHeight } = resolveWidgetPage(
        widget,
        widgetToPage,
        pageHeights,
      );
      const rect = widget?.getRectangle();
      const coords = rect
        ? rectToCoords(
            [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height],
            pageHeight,
          )
        : null;

      results.push({
        field_kind: "choice",
        name,
        value,
        page: pageIndex !== null ? pageIndex + 1 : null,
        coords,
      });
    } else if (field instanceof PDFSignature) {
      const widget = field.acroField.getWidgets()[0];
      const { pageIndex, pageHeight } = resolveWidgetPage(
        widget,
        widgetToPage,
        pageHeights,
      );
      const rect = widget?.getRectangle();
      const coords = rect
        ? rectToCoords(
            [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height],
            pageHeight,
          )
        : null;

      results.push({
        field_kind: "signature",
        name,
        value: "",
        page: pageIndex !== null ? pageIndex + 1 : null,
        coords,
      });
    } else {
      // Unknown field type — treat as text
      const widget = (field as PDFField).acroField.getWidgets()[0];
      const { pageIndex, pageHeight } = resolveWidgetPage(
        widget,
        widgetToPage,
        pageHeights,
      );
      const rect = widget?.getRectangle();
      const coords = rect
        ? rectToCoords(
            [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height],
            pageHeight,
          )
        : null;

      results.push({
        field_kind: "text",
        name,
        value: "",
        page: pageIndex !== null ? pageIndex + 1 : null,
        coords,
      });
    }
  }

  return results;
}

/** Resolve which page a widget annotation belongs to. */
function resolveWidgetPage(
  widget: PDFWidgetAnnotation | undefined,
  widgetToPage: Map<string, number>,
  pageHeights: number[],
): { pageIndex: number | null; pageHeight: number } {
  const DEFAULT_HEIGHT = 842.0;
  if (!widget) return { pageIndex: null, pageHeight: DEFAULT_HEIGHT };

  // Check the /P reference first
  const pRef = widget.P();
  if (pRef) {
    const refStr = String(pRef);
    const idx = widgetToPage.get(refStr);
    if (idx !== undefined) {
      return { pageIndex: idx, pageHeight: pageHeights[idx] ?? DEFAULT_HEIGHT };
    }
  }

  // Fallback: scan the widgetToPage map for this widget's ref
  const widgetRef = String((widget as any).ref);
  for (const [refStr, idx] of widgetToPage.entries()) {
    if (refStr.includes(widgetRef)) {
      return { pageIndex: idx, pageHeight: pageHeights[idx] ?? DEFAULT_HEIGHT };
    }
  }

  return { pageIndex: null, pageHeight: DEFAULT_HEIGHT };
}

/** Extract the non-/Off appearance state key from a widget annotation. */
function getWidgetAppearanceState(widget: PDFWidgetAnnotation): string | null {
  try {
    const as = widget.getAppearanceState();
    if (as && String(as) !== "/Off") {
      const str = String(as);
      return str.startsWith("/") ? str : `/${str}`;
    }
  } catch {
    // ignore
  }
  return null;
}
