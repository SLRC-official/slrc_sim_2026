# Clue 3: Key 2 Decoder Guide

![Clue 3](media/Clue3.png)

This clue uses:

- Key ID: `2`
- Key `(K)`: `Solve the Puzzle to find the Key!!!`
- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `P_comp` is the complement of the payload. ie. `P_comp = 9999 - P`
    5. `A = ((P_comp * 9) + K) mod 8750`

- Then convert `A` into coordinates:

```text
order = floor(A / 625) + 1
remainder = A % 625
x = floor(remainder / 25)
y = remainder % 25
```

- Valid coordinate output range:

    - `order`: 1 to 14
    - `x`: 0 to 24
    - `y`: 0 to 24

## Worked Example 1

- Tag: `27261`
- Key ID: `2`
- Payload: `7261`
- AprilTag image:
![AprilTag 27261](media/tagStandard52h13-27261.svg)
- Final decoded result `(OOXXYY)` : `021910`

## Worked Example 2

- Tag: `24599`
- Key ID: `2`
- Payload: `4599`
- AprilTag image:
![AprilTag 24599](media/tagStandard52h13-24599.svg)
- Final decoded result `(OOXXYY)` : `130218`
