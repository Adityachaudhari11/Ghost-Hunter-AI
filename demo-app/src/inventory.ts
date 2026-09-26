export interface StockEntry {
  sku: string;
  available: number;
  reserved: number;
  reorderThreshold: number;
}

export interface ReservationResult {
  success: boolean;
  reserved: number;
  message: string;
}

export function getAvailableStock(entry: StockEntry): number {
  return entry.available - entry.reserved;
}

export function reserveStock(
  entry: StockEntry,
  quantity: number
): { entry: StockEntry; result: ReservationResult } {
  if (quantity <= 0) {
    throw new Error("Quantity must be positive");
  }

  const available = getAvailableStock(entry);

  if (available < quantity) {
    return {
      entry,
      result: {
        success: false,
        reserved: 0,
        message: `Insufficient stock: ${available} available, ${quantity} requested`,
      },
    };
  }

  const updated: StockEntry = {
    ...entry,
    reserved: entry.reserved + quantity,
  };

  return {
    entry: updated,
    result: {
      success: true,
      reserved: quantity,
      message: `Reserved ${quantity} units`,
    },
  };
}

export function releaseReservation(
  entry: StockEntry,
  quantity: number
): StockEntry {
  const newReserved = Math.max(0, entry.reserved - quantity);
  return { ...entry, reserved: newReserved };
}

export function needsReorder(entry: StockEntry): boolean {
  return getAvailableStock(entry) <= entry.reorderThreshold;
}

export function deductStock(entry: StockEntry, quantity: number): StockEntry {
  if (quantity > entry.available) {
    throw new Error(`Cannot deduct ${quantity}: only ${entry.available} in stock`);
  }
  return {
    ...entry,
    available: entry.available - quantity,
    reserved: Math.max(0, entry.reserved - quantity),
  };
}
