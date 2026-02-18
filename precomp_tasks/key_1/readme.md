# Pre-Competition Challenge 1 — Decoder Notes

This folder contains the decoding notes and sample tags for **Pre-Competition Challenge 1**.

Refer to the official task document for the base rules, constraints, and how to interpret the scanned AprilTag value. This README only describes how to convert the **payload** into the format used by this challenge and how the puzzle key is applied.

---

## Step 1 — Build the 6-digit value `N` from the payload

Convert the payload `P` into `(order, x, y)` using this structure:

> **P = (order − 1) · 625 + x · 25 + y**

To construct `N`:

1. Recover `order`, `x`, and `y` from `P` (consistent with the equation above).
2. Concatenate them as two digits each to form the **6-digit integer**:
   - `N = OOXXYY`  
     where `OO` is `order` (01–14), `XX` is `x` (00–24), `YY` is `y` (00–24).

Use integer arithmetic only (no floats).

---

## Step 2 — Apply XOR with the obtained key

Solving the puzzle gives you a **key** in decimal form.

For this challenge, the decoding rule is:

> **N XOR KEY = ANSWER**

### Important
- XOR must follow the standard **bitwise XOR** rules.
- Treat both values as integers with the **same bit-width** when performing the XOR.
- Interpret the result back in `OOXXYY` format and ensure it satisfies the constraints defined in the official task document.

This README intentionally does **not** describe how to perform the XOR or how to convert between decimal and bits.

---

## Provided materials in this folder
- Sample AprilTags for testing and their final answers
- This README with the decoding rule
