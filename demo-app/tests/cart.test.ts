// INTENTIONALLY THIN TESTS — happy path only
import { addItem, removeItem, summarizeCart, applyCoupon, Cart } from "../src/cart";

const makeCart = (): Cart => ({
  sessionId: "test-session",
  items: [],
});

describe("addItem", () => {
  it("adds a new item to empty cart", () => {
    const cart = addItem(makeCart(), { id: "a", name: "Widget", unitPrice: 10, quantity: 1 });
    expect(cart.items).toHaveLength(1);
  });

  it("increments quantity for existing item", () => {
    let cart = addItem(makeCart(), { id: "a", name: "Widget", unitPrice: 10, quantity: 2 });
    cart = addItem(cart, { id: "a", name: "Widget", unitPrice: 10, quantity: 3 });
    expect(cart.items[0].quantity).toBe(5);
  });
});

describe("removeItem", () => {
  it("removes an item by id", () => {
    let cart = addItem(makeCart(), { id: "a", name: "Widget", unitPrice: 10, quantity: 1 });
    cart = removeItem(cart, "a");
    expect(cart.items).toHaveLength(0);
  });
});

describe("summarizeCart", () => {
  it("returns zeros for empty cart", () => {
    const summary = summarizeCart(makeCart());
    expect(summary.total).toBe(0);
  });
});

describe("applyCoupon", () => {
  it("applies a valid coupon", () => {
    const cart = applyCoupon(makeCart(), "SAVE10");
    expect(cart.couponCode).toBe("SAVE10");
  });

  it("throws for invalid coupon", () => {
    expect(() => applyCoupon(makeCart(), "INVALID")).toThrow();
  });
});
