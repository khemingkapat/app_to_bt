const { PDFDocument } = require('pdf-lib');
const { rectToDict } = require('../utils/helpers');

/**
 * Parses a loaded pdf-lib PDFDocument to extract fields.
 */
function walkFields(pdfDoc) {
    const results = [];
    const form = pdfDoc.getForm();
    const fields = form.getFields();

    for (const field of fields) {
        const name = field.getName();
        const type = field.constructor.name; // e.g. PDFTextField, PDFCheckBox

        // Get the widgets to extract coordinates and pages
        const widgets = field.acroField.getWidgets();

        if (type === 'PDFRadioGroup') {
            const radioField = field;
            const options = radioField.getOptions();
            let value = "";
            try {
                value = radioField.getSelected() || "";
            } catch (e) {
                // Ignore parsing errors for empty radio
            }

            const kidWidgets = widgets.map((widget, idx) => {
                const rect = widget.getRectangle();
                const pageRef = widget.P();

                let pageNum = 1;
                if (pageRef) {
                     // find page index
                    const pages = pdfDoc.getPages();
                    for (let i = 0; i < pages.length; i++) {
                         if (pages[i].ref === pageRef) {
                             pageNum = i + 1;
                             break;
                         }
                    }
                }

                let pageHeight = 842.0;
                if (pageNum <= pdfDoc.getPageCount()) {
                    pageHeight = pdfDoc.getPage(pageNum - 1).getHeight();
                }

                // Try to infer choice value from options
                let choiceValue = options[idx] || "";

                return {
                    page: pageNum,
                    choice_value: choiceValue,
                    coords: rectToDict([rect.x, rect.y, rect.x + rect.width, rect.y + rect.height], pageHeight)
                };
            });

            // Need to get the first page for the root property
            const firstPageNum = kidWidgets.length > 0 ? kidWidgets[0].page : 1;

            results.push({
                field_kind: "radio",
                name: name || "UNNAMED",
                value: value,
                page: firstPageNum,
                states: options,
                widgets: kidWidgets
            });

        } else {
            let kind = "text";
            let value = "";

            if (type === 'PDFCheckBox') {
                kind = "checkbox";
                try { value = field.isChecked() ? "Yes" : "Off"; } catch(e){}
            } else if (type === 'PDFDropdown' || type === 'PDFOptionList') {
                kind = "choice";
                try { value = field.getSelected() || ""; } catch(e){}
            } else if (type === 'PDFSignature') {
                kind = "signature";
            } else if (type === 'PDFTextField') {
                try { value = field.getText() || ""; } catch(e){}
            }

            // Get coords for the first widget (most fields have 1 widget)
            let pageNum = 1;
            let pageHeight = 842.0;
            let coords = null;

            if (widgets.length > 0) {
                const widget = widgets[0];
                const rect = widget.getRectangle();
                const pageRef = widget.P();

                if (pageRef) {
                    const pages = pdfDoc.getPages();
                    for (let i = 0; i < pages.length; i++) {
                         if (pages[i].ref === pageRef) {
                             pageNum = i + 1;
                             break;
                         }
                    }
                }
                if (pageNum <= pdfDoc.getPageCount()) {
                    pageHeight = pdfDoc.getPage(pageNum - 1).getHeight();
                }
                coords = rectToDict([rect.x, rect.y, rect.x + rect.width, rect.y + rect.height], pageHeight);
            }

            results.push({
                field_kind: kind,
                name: name || "UNNAMED",
                value: value,
                page: pageNum,
                coords: coords
            });
        }
    }

    return results;
}

module.exports = {
    walkFields
};
