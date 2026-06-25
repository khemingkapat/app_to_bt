/**
 * Coordinate and geometry utilities for PDF processing.
 *
 * These are pure-math helpers ported from the Python worker's
 * pdf_processor/utils/helpers.py — no library dependencies.
 */

/** Bounding box coordinates as stored in the registry. */
export interface CoordDict {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  width: number;
  height: number;
  canvas_top?: number;
  canvas_bottom?: number;
}

/** Convert a raw PDF /Rect array [x0, y0, x1, y1] to a CoordDict. */
export function rectToCoords(
  rect: [number, number, number, number],
  pageHeight?: number,
): CoordDict | null {
  try {
    const [x0, y0, x1, y1] = rect;
    const result: CoordDict = {
      x0: round(x0),
      y0: round(y0),
      x1: round(x1),
      y1: round(y1),
      width: round(x1 - x0),
      height: round(y1 - y0),
    };
    if (pageHeight !== undefined) {
      result.canvas_top = round(pageHeight - y1);
      result.canvas_bottom = round(pageHeight - y0);
    }
    return result;
  } catch {
    return null;
  }
}

/** Calculate the center point of a coordinate dictionary. */
export function calculateCenter(coords: CoordDict): [number, number] {
  return [(coords.x0 + coords.x1) / 2, (coords.y0 + coords.y1) / 2];
}

/** Euclidean distance between two points. */
export function dist(
  p1: [number, number],
  p2: [number, number],
): number {
  return Math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2);
}

/** Round to 2 decimal places (matches Python's round(x, 2)). */
export function round(value: number, decimals = 2): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}
