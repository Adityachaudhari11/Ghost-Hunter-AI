#!/usr/bin/env python3
"""
GhostBuster — Laya AI Domain Fine-Tuning Script
================================================
Fine-tunes the released convaiinnovations/laya checkpoint on GhostBuster-specific
training data: flaky-test root cause classification, mutation severity scoring,
and PII detection in code context.

Usage
-----
  # Full fine-tune (requires ~8-10 GB VRAM, ~2-4 hrs on A10G):
  python ghostbuster/laya_finetune/train.py

  # LoRA fine-tune (fits in 8 GB VRAM, ~30-45 min on T4):
  python ghostbuster/laya_finetune/train.py --lora

  # Dry run (1 record, no GPU required):
  python ghostbuster/laya_finetune/train.py --dry-run

Prerequisites
-------------
  pip install torch transformers safetensors numpy huggingface_hub peft

  # Laya model weights must be downloaded:
  python -c "
  from huggingface_hub import snapshot_download
  snapshot_download('convaiinnovations/laya', local_dir='laya_model', ignore_patterns=['*.md'])
  "

Output
------
  laya_model/model_ghostbuster.safetensors   ← fine-tuned weights
  ghostbuster/laya_finetune/val_results.json ← per-task accuracy on held-out split

To use the fine-tuned weights in production:
  Edit ghostbuster/shared/laya_client.py and change "model.safetensors" to
  "model_ghostbuster.safetensors".
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent
LAYA_MODEL_DIR = ROOT / "laya_model"
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_WEIGHTS = LAYA_MODEL_DIR / "model_ghostbuster.safetensors"
VAL_RESULTS = Path(__file__).parent / "val_results.json"

# ── Hyperparameters ───────────────────────────────────────────────────────────
LR = 2e-5
WARMUP_STEPS = 75
EPOCHS = 3
BATCH_SIZE = 1          # gradient-accumulation friendly for single GPU
GRAD_CLIP = 1.0
WEIGHT_DECAY = 0.01
VAL_SPLIT = 0.1         # 10% held-out for validation
SEED = 42

# LoRA config (applied to ModernBERT encoder only)
LORA_RANK = 16
LORA_ALPHA = 32
LORA_TARGET_MODULES = ["query", "key", "value"]


def parse_args():
    p = argparse.ArgumentParser(description="Fine-tune Laya on GhostBuster domain data")
    p.add_argument("--lora", action="store_true",
                   help="Use LoRA for the encoder (saves VRAM; ~30-45 min on T4 instead of 2-4 h on A10G)")
    p.add_argument("--dry-run", action="store_true",
                   help="Run one record, no GPU required — validates the script end-to-end")
    p.add_argument("--epochs", type=int, default=EPOCHS)
    p.add_argument("--lr", type=float, default=LR)
    p.add_argument("--data", type=str, default=str(DATA_DIR / "ghostbuster_train.jsonl"),
                   help="Path to training JSONL file")
    p.add_argument("--output", type=str, default=str(OUTPUT_WEIGHTS),
                   help="Path to write fine-tuned weights")
    return p.parse_args()


def load_data(path: str, rng: random.Random) -> tuple[list, list]:
    """Load JSONL records and split into train / validation."""
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    rng.shuffle(records)
    split = max(1, int(len(records) * VAL_SPLIT))
    return records[split:], records[:split]


def setup_lora(model):
    """Wrap the encoder in LoRA adapters using PEFT."""
    try:
        from peft import get_peft_model, LoraConfig, TaskType
    except ImportError:
        raise ImportError(
            "peft is required for LoRA fine-tuning.\n"
            "Install with: pip install peft"
        )
    config = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=LORA_TARGET_MODULES,
        lora_dropout=0.05,
        bias="none",
    )
    # Only wrap the encoder sub-module; keep the decision head fully trainable
    model.encoder = get_peft_model(model.encoder, config)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"[LoRA] Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")
    return model


def evaluate(model, val_records, tok, cfg, rng, device) -> dict:
    """
    Run validation on held-out records.
    Returns per-task accuracy / mean absolute error.
    """
    from rl_common import encode_record, collate_items, proper_reward

    model.eval()
    task_correct = {"choice": 0, "score": 0, "noul": 0}
    task_total = {"choice": 0, "score": 0, "noul": 0}

    import torch
    with torch.no_grad():
        for rec in val_records:
            items = encode_record(rec, tok, cfg, rng, train=False)
            if not items:
                continue
            batch = collate_items([items], tok.pad_token_id)
            if batch is None:
                continue
            logits, _ = model(
                batch["input_ids"].to(device),
                batch["attention_mask"].to(device),
                batch["marker_pos"].to(device),
                batch["marker_mask"].to(device),
                batch["qtype"].to(device),
            )
            for q in rec.get("qs", []):
                t = q["t"]
                task_total[t] = task_total.get(t, 0) + 1
                # For choice/noul: check argmax equals y
                if t in ("choice", "noul"):
                    pred = logits.argmax(-1).item()
                    if pred == q["y"]:
                        task_correct[t] = task_correct.get(t, 0) + 1
                elif t == "score":
                    # Mean absolute error for score tasks
                    pred_level = logits.argmax(-1).item()
                    task_correct[t] = task_correct.get(t, 0) + abs(pred_level - q["y"])

    results = {}
    for t in ("choice", "score", "noul"):
        if task_total.get(t, 0) > 0:
            if t == "score":
                results[t] = {"mae": task_correct[t] / task_total[t], "n": task_total[t]}
            else:
                acc = task_correct[t] / task_total[t]
                results[t] = {"accuracy": round(acc, 3), "n": task_total[t]}
    return results


def main():
    args = parse_args()
    rng = random.Random(SEED)

    # ── Check model weights ──────────────────────────────────────────────────
    weights_path = LAYA_MODEL_DIR / "model.safetensors"
    if not weights_path.exists():
        print(
            f"[ERROR] Model weights not found at {weights_path}\n"
            "Download them first:\n"
            "  python -c \"\n"
            "  from huggingface_hub import snapshot_download\n"
            "  snapshot_download('convaiinnovations/laya', local_dir='laya_model', ignore_patterns=['*.md'])\n"
            "  \""
        )
        sys.exit(1)

    # ── Load training data ───────────────────────────────────────────────────
    data_path = args.data
    if not os.path.exists(data_path):
        print(f"[ERROR] Training data not found at {data_path}")
        print("Create ghostbuster/laya_finetune/data/ghostbuster_train.jsonl first.")
        print("See ghostbuster/laya_finetune/data/README.md for the data format.")
        sys.exit(1)

    train_records, val_records = load_data(data_path, rng)
    if args.dry_run:
        train_records = train_records[:1]
        val_records = val_records[:1] if val_records else train_records[:1]
        print(f"[DRY RUN] Using 1 training record.")

    print(f"[Data] Train: {len(train_records)} records | Val: {len(val_records)} records")

    # ── Import Laya internals ────────────────────────────────────────────────
    model_dir = str(LAYA_MODEL_DIR)
    if model_dir not in sys.path:
        sys.path.insert(0, model_dir)

    try:
        import torch
        from safetensors.torch import load_file, save_file
        from transformers import AutoTokenizer
        from rl_common import build_model, encode_record, collate_items, proper_reward, load_cfg
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Install with: pip install torch transformers safetensors numpy")
        sys.exit(1)

    # ── Load model ───────────────────────────────────────────────────────────
    device = "cuda" if (torch.cuda.is_available() and not args.dry_run) else "cpu"
    print(f"[Device] {device}" + (f" ({torch.cuda.get_device_name(0)})" if device == "cuda" else " (CPU — dry run only)"))

    cfg = load_cfg(str(LAYA_MODEL_DIR / "rl_agent_config.json"))
    tok = AutoTokenizer.from_pretrained(str(LAYA_MODEL_DIR))
    model = build_model(cfg, encoder_dir=str(LAYA_MODEL_DIR))
    model.load_state_dict(load_file(str(weights_path)), strict=True)
    model = model.to(device)

    if args.lora:
        print("[LoRA] Applying LoRA adapters to ModernBERT encoder...")
        model = setup_lora(model)

    model.train()

    # ── Optimizer with warmup ────────────────────────────────────────────────
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.lr,
        weight_decay=WEIGHT_DECAY,
    )

    total_steps = args.epochs * len(train_records)
    warmup = min(WARMUP_STEPS, total_steps // 10)

    def lr_lambda(step):
        if step < warmup:
            return step / max(1, warmup)
        return max(0.1, 1.0 - (step - warmup) / max(1, total_steps - warmup))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # ── Training loop ────────────────────────────────────────────────────────
    best_val_loss = float("inf")
    global_step = 0

    for epoch in range(args.epochs):
        rng.shuffle(train_records)
        epoch_loss = 0.0
        epoch_steps = 0

        for rec in train_records:
            items = encode_record(rec, tok, cfg, rng, train=True)
            if not items:
                continue
            batch = collate_items([items], tok.pad_token_id)
            if batch is None:
                continue

            logits, act = model(
                batch["input_ids"].to(device),
                batch["attention_mask"].to(device),
                batch["marker_pos"].to(device),
                batch["marker_mask"].to(device),
                batch["qtype"].to(device),
            )

            p = torch.softmax(logits / 1.0, dim=-1)
            reward = proper_reward(
                p.unsqueeze(0),
                batch["target"].to(device),
                batch["qtype"].to(device),
                batch["marker_mask"].to(device),
            )
            loss = -reward.mean()

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            epoch_loss += loss.item()
            epoch_steps += 1
            global_step += 1

            if global_step % 50 == 0:
                print(f"  step {global_step}/{total_steps} | loss {loss.item():.4f} | lr {scheduler.get_last_lr()[0]:.2e}")

        avg_loss = epoch_loss / max(1, epoch_steps)
        print(f"\n[Epoch {epoch+1}/{args.epochs}] avg_loss={avg_loss:.4f}")

        # Validation
        if val_records:
            val_results = evaluate(model, val_records, tok, cfg, rng, device)
            print(f"  Validation: {json.dumps(val_results, indent=2)}")
            model.train()

        if args.dry_run:
            print("[DRY RUN] Stopping after 1 epoch.")
            break

    # ── Save fine-tuned weights ──────────────────────────────────────────────
    # Merge LoRA adapters back into the base weights before saving
    if args.lora:
        try:
            model.encoder = model.encoder.merge_and_unload()
        except Exception as e:
            print(f"[Warning] Could not merge LoRA weights: {e}. Saving with adapters.")

    output_path = args.output
    save_file(model.state_dict(), output_path)
    print(f"\n[Done] Fine-tuned weights saved to: {output_path}")

    # Save final validation results
    if val_records:
        val_results = evaluate(model, val_records, tok, cfg, rng, device)
        with open(VAL_RESULTS, "w") as f:
            json.dump(val_results, f, indent=2)
        print(f"[Done] Validation results saved to: {VAL_RESULTS}")

    print("\nNext steps:")
    print("  1. Re-calibrate temperature: edit laya_model/rl_agent_config.json")
    print("     temperature_by_options — reduce 'score:3-5' from 1.25 to 0.8")
    print("  2. Update laya_client.py to load 'model_ghostbuster.safetensors'")
    print("  3. Run: python -m ghostbuster.run_platform --demo")
    print("     Verify FlakeHunter classifies 'environment' (not 'ordering')")
    print("     Verify MutaCI scores payment mutants 7-9 (not 3-5)")


if __name__ == "__main__":
    main()
