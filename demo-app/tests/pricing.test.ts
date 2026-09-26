// INTENTIONALLY THIN TESTS — happy path only
// This is the demo target for MutaCI to analyze
import { applyDiscount, calculateSeasonalPrice, computeBulkTier, finalPrice } from "../src/pricing";

describe("applyDiscount", () => {
  it("applies percentage discount", () => {
    expect(applyDiscount(100, { type: "percentage", value: 10 })).toBe(90);
  });

  it("applies fixed discount", () => {
    expect(applyDiscount(100, { type: "fixed", value: 15 })).toBe(85);
  });
});

describe("calculateSeasonalPrice", () => {
  it("returns original price when no discounts", () => {
    const result = calculateSeasonalPrice(50, 2, []);
    expect(result.originalPrice).toBe(100);
    expect(result.discountedPrice).toBe(100);
  });

  it("applies a percentage discount", () => {
    const result = calculateSeasonalPrice(100, 1, [
      { type: "percentage", value: 20 },
    ]);
    expect(result.discountedPrice).toBe(80);
  });
});

describe("computeBulkTier", () => {
  it("returns 0 for small quantities", () => {
    expect(computeBulkTier(1)).toBe(0);
  });

  it("returns 5 for quantity 10", () => {
    expect(computeBulkTier(10)).toBe(5);
  });
});

describe("finalPrice", () => {
  it("calculates price with bulk discount", () => {
    // 10 units at $10 each, 5% bulk discount
    expect(finalPrice(10, 10)).toBe(95);
  });
});
