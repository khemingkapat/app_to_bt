const fs = require('fs');
const path = require('path');
const { processPdf } = require('../../src/pdf_processor/engine');

describe('engine.js', () => {

    it('processes a filled AcroForm PDF successfully without existing registry', async () => {
        const pdfPath = path.join(__dirname, '../../resources/FilledApplication.pdf');

        // Skip test if test PDF doesn't exist locally
        if (!fs.existsSync(pdfPath)) {
            console.warn(`Test skipped, ${pdfPath} not found`);
            return;
        }

        const pdfBuffer = fs.readFileSync(pdfPath);

        const result = await processPdf(pdfBuffer);

        expect(result).toHaveProperty('pdf_id');
        expect(result).toHaveProperty('registry_dict');
        expect(result).toHaveProperty('values_dict');

        // It should extract basic values for filled form
        expect(Object.keys(result.values_dict).length).toBeGreaterThan(0);

        // Registry should have entry matching the ID
        expect(result.registry_dict[result.pdf_id]).toBeDefined();

        // Pages should be populated
        expect(result.registry_dict[result.pdf_id].pages.length).toBeGreaterThan(0);

        // Fields should be populated
        expect(result.registry_dict[result.pdf_id].fields.length).toBeGreaterThan(0);

        // Structural hash should be created
        expect(result.registry_dict[result.pdf_id].structural_hash).toBeDefined();
    });

});
