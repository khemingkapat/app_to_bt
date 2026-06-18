const { PDFDocument } = require('pdf-lib');
const fs = require('fs');
const path = require('path');
const { getPdfFileId } = require('./engine');

function parseDatePart(dateStr, part) {
    if (!dateStr) return "";

    let day, month, year;
    let parts = [];
    if (dateStr.includes("-")) {
        parts = dateStr.split("-");
        if (parts[0].length === 4) {
            year = parts[0]; month = parts[1]; day = parts[2];
        } else {
            day = parts[0]; month = parts[1]; year = parts[2];
        }
    } else if (dateStr.includes("/")) {
        parts = dateStr.split("/");
        if (parts[2].length === 4) {
            day = parts[0]; month = parts[1]; year = parts[2];
        } else {
            year = parts[0]; month = parts[1]; day = parts[2];
        }
    } else {
        return dateStr;
    }

    if (part === "DD") return day.padStart(2, '0');
    if (part === "MM") return month.padStart(2, '0');
    if (part === "YYYY") return year;
    return dateStr;
}

function mapCustomerDataToPdf(customerData, config, fieldMappings = null) {
    const pdfValues = {};
    if (!fieldMappings) {
        fieldMappings = config.field_mappings || {};
    }

    for (const [pdfField, mapping] of Object.entries(fieldMappings)) {
        let btKey = "";
        let label = "";

        if (typeof mapping === 'object' && mapping !== null) {
            btKey = mapping.bt_key;
            label = (mapping.label || "").toUpperCase();
        } else {
            btKey = mapping;
        }

        if (!btKey || !customerData.hasOwnProperty(btKey)) {
            continue;
        }

        let value = customerData[btKey];
        if (value === null || value === undefined) value = "";

        if (btKey.includes("dob") || btKey.includes("date")) {
            const dateStr = String(value);
            let part = null;
            if (label.includes("DAY") || label.includes("(DD)")) part = "DD";
            else if (label.includes("MONTH") || label.includes("(MM)")) part = "MM";
            else if (label.includes("YEAR") || label.includes("(YYYY)")) part = "YYYY";
            else {
                let siblingFields = [];
                for (const [f, m] of Object.entries(fieldMappings)) {
                    const k = (typeof m === 'object' && m !== null) ? m.bt_key : m;
                    if (k === btKey) siblingFields.push(f);
                }

                if (siblingFields.length > 1) {
                    siblingFields.sort((a, b) => {
                        const numA = parseInt(a.match(/\d+/)?.[0] || "0", 10);
                        const numB = parseInt(b.match(/\d+/)?.[0] || "0", 10);
                        return numA - numB;
                    });
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

async function fillAcroformPdf(pdfBuffer, customerData) {
    const pdfDoc = await PDFDocument.load(pdfBuffer);
    const pdfId = getPdfFileId(pdfDoc);

    const cachePath = path.join(__dirname, '../../outputs', 'assignment_cache.json');
    let configName = 'health_and_accident_insurance.json';
    let fieldMappings = {};

    if (fs.existsSync(cachePath)) {
        try {
            const cache = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));
            if (cache[pdfId]) {
                if (cache[pdfId].product_config) configName = cache[pdfId].product_config;
                if (cache[pdfId].field_mappings) fieldMappings = cache[pdfId].field_mappings;
            }
        } catch (e) {
            console.warn("Could not load assignment cache:", e);
        }
    }

    const configPath = path.join(__dirname, '../../config', configName);
    let config = {};
    if (fs.existsSync(configPath)) {
        try {
            config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
        } catch (e) {
            console.warn("Could not load config:", e);
        }
    }

    const pdfValues = mapCustomerDataToPdf(customerData, config, fieldMappings);

    const form = pdfDoc.getForm();
    for (const [fieldName, val] of Object.entries(pdfValues)) {
        try {
            const field = form.getField(fieldName);
            if (!field) continue;

            const type = field.constructor.name;
            if (type === 'PDFTextField') {
                field.setText(val);
            } else if (type === 'PDFCheckBox') {
                if (val && val.toLowerCase() !== 'off') {
                    field.check();
                } else {
                    field.uncheck();
                }
            } else if (type === 'PDFRadioGroup') {
                // Determine option matching the mapped value
                const options = field.getOptions();
                if (options.includes(val)) {
                    field.select(val);
                } else if (val.startsWith('/') && options.includes(val.substring(1))) {
                     field.select(val.substring(1));
                }
            } else if (type === 'PDFDropdown' || type === 'PDFOptionList') {
                field.select(val);
            }
        } catch (e) {
            // Field not found or failed to set, skip
        }
    }

    return await pdfDoc.save();
}

module.exports = {
    mapCustomerDataToPdf,
    fillAcroformPdf
};
