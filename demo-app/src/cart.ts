import { calculateSeasonalPrice, finalPrice, DiscountRule } from "./pricing";

export interface CartItem {
  id: string;
  name: string;
  unitPrice: number;
  quantity: number;
}

export interface Cart {
  items: CartItem[];
  couponCode?: string;
  sessionId: string;
}

export interface CartSummary {
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
  itemCount: number;
}

const TAX_RATE = 0.08;
const COUPON_DISCOUNTS: Record<string, DiscountRule> = {
  SAVE10: { type: "percentage", value: 10 },
  SAVE20: { type: "percentage", value: 20, minQuantity: 5 },
  FLAT5: { type: "fixed", value: 5 },
};

export function addItem(cart: Cart, item: CartItem): Cart {
  const existing = cart.items.find((i) => i.id === item.id);
  if (existing) {
    return {
      ...cart,
      items: cart.items.map((i) =>
        i.id === item.id
          ? { ...i, quantity: i.quantity + item.quantity }
          : i
      ),
    };
  }
  return { ...cart, items: [...cart.items, item] };
}

export function removeItem(cart: Cart, itemId: string): Cart {
  return { ...cart, items: cart.items.filter((i) => i.id !== itemId) };
}

export function updateQuantity(
  cart: Cart,
  itemId: string,
  quantity: number
): Cart {
  if (quantity <= 0) {
    return removeItem(cart, itemId);
  }
  return {
    ...cart,
    items: cart.items.map((i) =>
      i.id === itemId ? { ...i, quantity } : i
    ),
  };
}

export function summarizeCart(cart: Cart): CartSummary {
  if (cart.items.length === 0) {
    return { subtotal: 0, discount: 0, tax: 0, total: 0, itemCount: 0 };
  }

  const totalQuantity = cart.items.reduce((sum, i) => sum + i.quantity, 0);
  const discounts: DiscountRule[] = [];

  if (cart.couponCode && COUPON_DISCOUNTS[cart.couponCode]) {
    discounts.push(COUPON_DISCOUNTS[cart.couponCode]);
  }

  let subtotal = 0;
  let discountTotal = 0;

  for (const item of cart.items) {
    const result = calculateSeasonalPrice(item.unitPrice, item.quantity, discounts);
    subtotal += result.originalPrice;
    discountTotal += result.discountApplied;
  }

  // Apply bulk tier on total quantity
  const bulkSubtotal = cart.items.reduce(
    (sum, item) => sum + finalPrice(item.unitPrice, totalQuantity),
    0
  );

  const effectiveSubtotal = discounts.length > 0 ? subtotal - discountTotal : bulkSubtotal;
  const tax = Math.round(effectiveSubtotal * TAX_RATE * 100) / 100;
  const total = Math.round((effectiveSubtotal + tax) * 100) / 100;

  return {
    subtotal,
    discount: discountTotal,
    tax,
    total,
    itemCount: totalQuantity,
  };
}

export function applyCoupon(cart: Cart, code: string): Cart {
  if (!COUPON_DISCOUNTS[code]) {
    throw new Error(`Invalid coupon code: ${code}`);
  }
  return { ...cart, couponCode: code };
}

export function clearCart(cart: Cart): Cart {
  return { ...cart, items: [], couponCode: undefined };
}
