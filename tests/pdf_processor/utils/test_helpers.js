const { rectToDict, getPageDimensions } = require('../../../src/pdf_processor/utils/helpers');

describe('helpers.js', () => {

    describe('getPageDimensions', () => {
        it('returns standard size when no mediaBox is provided', () => {
            const [width, height] = getPageDimensions(null);
            expect(width).toBe(595.27);
            expect(height).toBe(842.0);
        });

        it('calculates width and height from valid mediaBox', () => {
            const mockPageInfo = { mediaBox: [0, 0, 500, 600] };
            const [width, height] = getPageDimensions(mockPageInfo);
            expect(width).toBe(500.0);
            expect(height).toBe(600.0);
        });

        it('handles non-zero origin mediaBox', () => {
            const mockPageInfo = { mediaBox: [50, 60, 550, 660] };
            const [width, height] = getPageDimensions(mockPageInfo);
            expect(width).toBe(500.0);
            expect(height).toBe(600.0);
        });
    });

    describe('rectToDict', () => {
        it('returns null for empty or invalid array', () => {
            expect(rectToDict(null)).toBeNull();
            expect(rectToDict([10, 20, 100])).toBeNull();
            expect(rectToDict(["a", "b", "c", "d"])).toBeNull();
        });

        it('returns a basic dict of coordinates', () => {
            const rect = [10.5, 20.2, 110.5, 120.2];
            const expected = {
                x0: 10.5,
                y0: 20.2,
                x1: 110.5,
                y1: 120.2,
                width: 100.0,
                height: 100.0,
            };
            expect(rectToDict(rect)).toEqual(expected);
        });

        it('returns a dict with canvas properties when page height is provided', () => {
            const rect = [10.5, 20.2, 110.5, 120.2];
            const expected = {
                x0: 10.5,
                y0: 20.2,
                x1: 110.5,
                y1: 120.2,
                width: 100.0,
                height: 100.0,
                canvas_top: 679.8,
                canvas_bottom: 779.8,
            };
            expect(rectToDict(rect, 800.0)).toEqual(expected);
        });
    });

});
