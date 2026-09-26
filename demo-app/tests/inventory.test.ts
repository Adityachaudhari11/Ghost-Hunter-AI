// INTENTIONALLY THIN TESTS — happy path only
import { reserveStock, releaseReservation, getAvailableStock, needsReorder, deductStock } from "../src/inventory";

const makeEntry = () => ({
  sku: "SKU-001",
  available: 100,
  reserved: 10,
  reorderThreshold: 20,
});

describe("getAvailableStock", () => {
  it("returns available minus reserved", () => {
    expect(getAvailableStock(makeEntry())).toBe(90);
  });
});

describe("reserveStock", () => {
  it("reserves stock successfully", () => {
    const { result } = reserveStock(makeEntry(), 5);
    expect(result.success).toBe(true);
    expect(result.reserved).toBe(5);
  });
});

describe("needsReorder", () => {
  it("returns false when stock is sufficient", () => {
    expect(needsReorder(makeEntry())).toBe(false);
  });
});
