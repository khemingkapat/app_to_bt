/**
 * Tests for pure utility functions — no PDF files needed.
 *
 * These validate the geometry helpers and date parsing that are
 * ported directly from Python. They must produce identical output.
 */
import { describe, it, expect } from "vitest";
import { rectToCoords, calculateCenter, dist, round } from "../src/pdf-processor/utils/helpers.js";
import { parseDatePart } from "../src/pdf-processor/inverter.js";

describe("rectToCoords", () => {
  it("converts a raw rect array to a CoordDict", () => {
    const result = rectToCoords([77.24, 654.03, 322.69, 668.43], 841.89);
    expect(result).not.toBeNull();
    expect(result!.x0).toBe(77.24);
    expect(result!.y0).toBe(654.03);
    expect(result!.x1).toBe(322.69);
    expect(result!.y1).toBe(668.43);
    expect(result!.width).toBe(245.45);
    expect(result!.height).toBe(14.4);
    expect(result!.canvas_top).toBe(173.46);
    expect(result!.canvas_bottom).toBe(187.86);
  });

  it("works without pageHeight (no canvas coords)", () => {
    const result = rectToCoords([10, 20, 30, 40]);
    expect(result).not.toBeNull();
    expect(result!.canvas_top).toBeUndefined();
    expect(result!.canvas_bottom).toBeUndefined();
    expect(result!.width).toBe(20);
    expect(result!.height).toBe(20);
  });

  it("returns null for invalid input", () => {
    // @ts-expect-error testing invalid input
    const result = rectToCoords(null);
    expect(result).toBeNull();
  });
});

describe("calculateCenter", () => {
  it("returns the center of a coordinate dict", () => {
    const coords = { x0: 0, y0: 0, x1: 10, y1: 20, width: 10, height: 20 };
    const [cx, cy] = calculateCenter(coords);
    expect(cx).toBe(5);
    expect(cy).toBe(10);
  });
});

describe("dist", () => {
  it("calculates Euclidean distance", () => {
    expect(dist([0, 0], [3, 4])).toBe(5);
    expect(dist([1, 1], [1, 1])).toBe(0);
  });
});

describe("round", () => {
  it("rounds to 2 decimal places by default", () => {
    expect(round(3.14159)).toBe(3.14);
    expect(round(2.005)).toBe(2.01); // IEEE 754 edge case handled correctly
  });
});

describe("parseDatePart", () => {
  it("parses YYYY-MM-DD format", () => {
    expect(parseDatePart("1990-03-15", "DD")).toBe("15");
    expect(parseDatePart("1990-03-15", "MM")).toBe("03");
    expect(parseDatePart("1990-03-15", "YYYY")).toBe("1990");
  });

  it("parses DD/MM/YYYY format", () => {
    expect(parseDatePart("15/03/1990", "DD")).toBe("15");
    expect(parseDatePart("15/03/1990", "MM")).toBe("03");
    expect(parseDatePart("15/03/1990", "YYYY")).toBe("1990");
  });

  it("pads single-digit day and month", () => {
    expect(parseDatePart("1990-3-5", "DD")).toBe("05");
    expect(parseDatePart("1990-3-5", "MM")).toBe("03");
  });

  it("returns empty string for empty input", () => {
    expect(parseDatePart("", "DD")).toBe("");
  });

  it("returns the string as-is if unparseable", () => {
    expect(parseDatePart("unknown", "DD")).toBe("unknown");
  });
});
