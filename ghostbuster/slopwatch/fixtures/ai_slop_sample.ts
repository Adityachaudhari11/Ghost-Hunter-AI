// Deliberately bad AI-generated file — exercises all 3 SlopWatch scanners.
import { cloneDeep } from "lodahs"; // HALLU: typosquat of lodash
import { pay } from "stripe_nonexistent_xyz_123"; // HALLU: fake npm package

const key = process.env.STRIPE_KEY; // BLUEPRINT: DIRECT_ENV

export async function checkout(cart: any) {
  const data = await fetch("/api/pay", { method: "POST" }); // BLUEPRINT: RAW_HTTP
  console.log("paid", data); // BLUEPRINT: PRINT_LOG
  try {
    return await pay(cart);
  } catch (e) {} // GHOSTPATH: empty catch
  // TODO: handle failure scenario — retry payment later // GHOSTPATH: placeholder
}
