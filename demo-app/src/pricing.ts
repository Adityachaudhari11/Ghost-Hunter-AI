export interface DiscountRule {
  type: "percentage" | "fixed" | "bogo";
  value: number;
  minQuantity?: number;
  maxUsage?: number;
}

export interface PricingResult {
  originalPrice: number;
  discountedPrice: number;
  discountApplied: number;
  discountBreakdown: string[];
}

export function applyDiscount(basePrice: number, discount: DiscountRule): number {
  if (discount.type === "percentage") {
    if (discount.value < 0 || discount.value > 100) {
      throw new Error(`Invalid percentage discount: ${discount.value}`);
    }
    return Math.max(0, basePrice * (1 - discount.value / 100));
  }
  if (discount.type === "fixed") {
    if (discount.value < 0) {
      throw new Error(`Fixed discount cannot be negative: ${discount.value}`);
    }
    return Math.max(0, basePrice - discount.value);
  }
  return basePrice;
}

export function calculateSeasonalPrice(
  basePrice: number,
  quantity: number,
  discounts: DiscountRule[]
): PricingResult {
  if (basePrice < 0) {
    throw new Error("Base price cannot be negative");
  }
  if (quantity <= 0) {
    throw new Error("Quantity must be positive");
  }

  let price = basePrice;
  const breakdown: string[] = [];

  // Apply discounts in order — ORDER MATTERS for stacking
  for (const discount of discounts) {
    if (discount.minQuantity !== undefined && quantity < discount.minQuantity) {
      continue;
    }
    const before = price;
    price = applyDiscount(price, discount);
    const saved = before - price;
    if (saved > 0) {
      breakdown.push(
        `${discount.type}(${discount.value}): -$${saved.toFixed(2)}`
      );
    }
  }

  const totalPrice = price * quantity;
  return {
    originalPrice: basePrice * quantity,
    discountedPrice: Math.max(0, totalPrice),
    discountApplied: basePrice * quantity - Math.max(0, totalPrice),
    discountBreakdown: breakdown,
  };
}

export function computeBulkTier(quantity: number): number {
  if (quantity >= 100) return 20;
  if (quantity >= 50) return 15;
  if (quantity >= 20) return 10;
  if (quantity >= 10) return 5;
  return 0;
}

export function finalPrice(basePrice: number, quantity: number): number {
  const bulkDiscountPct = computeBulkTier(quantity);
  const discounted = basePrice * (1 - bulkDiscountPct / 100);
  return Math.round(discounted * quantity * 100) / 100;
}
