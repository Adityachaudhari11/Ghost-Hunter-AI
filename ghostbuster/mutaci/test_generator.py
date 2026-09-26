"""
Test generator — produces semantically meaningful tests for surviving mutants.
Uses Claude to generate tests based on PR intent + mutant description.
"""

import os
from dataclasses import dataclass

import anthropic

from .stryker_runner import Mutant


@dataclass
class GeneratedTest:
    mutant_id: str
    test_code: str
    description: str
    target_file: str


SYSTEM_PROMPT = """You are a TypeScript test engineer. Given a description of a behavioral gap
found by mutation testing, generate a precise, minimal Jest test that would catch the bug.

Rules:
- Import only from the source file being tested
- Use describe/it/expect — no extra libraries
- Test the SPECIFIC BEHAVIOR described, not the code structure
- The test must FAIL if the mutant is applied (that's the point)
- Keep it under 15 lines
- Return ONLY the test code, no explanation, no markdown fences"""


def generate_test_for_mutant(
    mutant: Mutant,
    pr_description: str = "",
    client: anthropic.Anthropic | None = None,
) -> GeneratedTest:
    """Generate a targeted test for a surviving mutant using Claude."""
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        client = anthropic.Anthropic(api_key=api_key) if api_key else None

    file_stem = mutant.file_path.replace("src/", "").replace(".ts", "")
    import_path = f"../src/{file_stem}"

    prompt = f"""Surviving mutant in {mutant.file_path}, line {mutant.line}:

Original code: {mutant.original_code}
Mutated code:  {mutant.mutated_code}
Mutator: {mutant.mutator_name}
Gap description: {mutant.description}

PR context: {pr_description or "Add seasonal discount pricing to cart"}

Generate a Jest test that imports from '{import_path}' and specifically catches this behavioral gap.
"""

    if client:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
        )
        test_code = message.content[0].text.strip()
    else:
        # Fallback demo tests when no API key
        test_code = _demo_test(mutant, import_path)

    return GeneratedTest(
        mutant_id=mutant.id,
        test_code=test_code,
        description=mutant.description,
        target_file=f"tests/{file_stem}.mutaci.test.ts",
    )


def _demo_test(mutant: Mutant, import_path: str) -> str:
    """Hardcoded demo tests matching the demo report mutants."""
    demos = {
        "1": f"""import {{ applyDiscount }} from '{import_path}';

describe('applyDiscount — boundary: 0% discount', () => {{
  it('returns original price unchanged when discount is 0%', () => {{
    expect(applyDiscount(100, {{ type: 'percentage', value: 0 }})).toBe(100);
  }});
}});""",
        "2": f"""import {{ applyDiscount }} from '{import_path}';

describe('applyDiscount — validation: negative discount', () => {{
  it('throws when percentage discount is negative', () => {{
    expect(() =>
      applyDiscount(100, {{ type: 'percentage', value: -10 }})
    ).toThrow('Invalid percentage discount');
  }});
}});""",
        "3": f"""import {{ applyDiscount }} from '{import_path}';

describe('applyDiscount — boundary: 100% discount', () => {{
  it('returns 0 (not negative) when discount is 100%', () => {{
    const result = applyDiscount(50, {{ type: 'percentage', value: 100 }});
    expect(result).toBe(0);
    expect(result).toBeGreaterThanOrEqual(0);
  }});
}});""",
        "4": f"""import {{ calculateSeasonalPrice }} from '{import_path}';

describe('calculateSeasonalPrice — discount stacking order', () => {{
  it('fixed-then-percentage differs from percentage-then-fixed', () => {{
    const fixedFirst = calculateSeasonalPrice(100, 1, [
      {{ type: 'fixed', value: 20 }},
      {{ type: 'percentage', value: 10 }},
    ]);
    const pctFirst = calculateSeasonalPrice(100, 1, [
      {{ type: 'percentage', value: 10 }},
      {{ type: 'fixed', value: 20 }},
    ]);
    // $100 - $20 = $80 * 0.9 = $72  vs  $100 * 0.9 = $90 - $20 = $70
    expect(fixedFirst.discountedPrice).toBe(72);
    expect(pctFirst.discountedPrice).toBe(70);
    expect(fixedFirst.discountedPrice).not.toBe(pctFirst.discountedPrice);
  }});
}});""",
    }
    return demos.get(mutant.id, f"// TODO: test for mutant {mutant.id}\n")


def generate_all_tests(
    mutants: list[Mutant],
    pr_description: str = "",
    client: anthropic.Anthropic | None = None,
) -> list[GeneratedTest]:
    """Generate tests for all surviving mutants."""
    return [generate_test_for_mutant(m, pr_description, client) for m in mutants]
