const request = require('supertest');
const path = require('path');
const fs = require('fs');
const app = require('../server'); // Fix path

describe('POST /api/process-pdf', () => {

    it('should return 400 if no file is uploaded', async () => {
        const response = await request(app).post('/api/process-pdf');
        expect(response.status).toBe(400);
        expect(response.body.error).toBe('No PDF file provided.');
    });

    it('should process a valid PDF statelessly', async () => {
        const pdfPath = path.join(__dirname, '../resources/FilledApplication.pdf');

        // Skip test if test PDF doesn't exist locally
        if (!fs.existsSync(pdfPath)) {
            console.warn(`Test skipped, ${pdfPath} not found`);
            return;
        }

        const response = await request(app)
            .post('/api/process-pdf')
            .attach('pdf', pdfPath);

        expect(response.status).toBe(200);
        expect(response.body.success).toBe(true);
        expect(response.body).toHaveProperty('pdf_id');
        expect(response.body.fieldsExtracted).toBeGreaterThan(0);
        expect(Object.keys(response.body.values).length).toBeGreaterThan(0);
        expect(response.body).toHaveProperty('registry');
    });
});
