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

describe('Config Manager API Endpoints', () => {
    let mockPdfId = 'test_pdf_123';

    it('GET /api/registry should return the in-memory registry or fallback empty object', async () => {
        const response = await request(app).get('/api/registry');
        expect(response.status).toBe(200);
        expect(typeof response.body).toBe('object');
    });

    it('POST /api/config should fail without required params', async () => {
        const response = await request(app)
            .post('/api/config')
            .send({ pdf_id: mockPdfId });
        expect(response.status).toBe(400);
        expect(response.body.error).toBe('Missing required parameters: pdf_id, filename, or config_body');
    });

    it('POST /api/config should save config and update cache', async () => {
        const configBody = { product_name: "Test Insurance", pricing: { factor: 1.5 } };
        const response = await request(app)
            .post('/api/config')
            .send({
                pdf_id: mockPdfId,
                filename: 'test_insurance.json',
                config_body: configBody
            });

        expect(response.status).toBe(200);
        expect(response.body.success).toBe(true);

        // Verify files were actually created
        const configPath = path.join(__dirname, '../config', 'test_insurance.json');
        const cachePath = path.join(__dirname, '../outputs', 'assignment_cache.json');

        expect(fs.existsSync(configPath)).toBe(true);
        expect(fs.existsSync(cachePath)).toBe(true);

        const savedConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
        expect(savedConfig.pdf_id).toBe(mockPdfId);
        expect(savedConfig.product_name).toBe("Test Insurance");

        const cache = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));
        expect(cache[mockPdfId].product_config).toBe('test_insurance.json');
        expect(typeof cache[mockPdfId].field_mappings).toBe('object');

        // Clean up mock files created during test
        fs.unlinkSync(configPath);
    });
});
