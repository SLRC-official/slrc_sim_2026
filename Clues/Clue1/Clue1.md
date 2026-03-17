# Clue 1: Key 0 Decoder Guide

![Clue 1](media/Clue1.png)

This clue uses:

- Key ID: `0`
- Key `(K)`: `Solve the Puzzle to find the Key!!!`
- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `P_rev` is the reverse of the payload. ie. `P_rev = dcba`
    5. `A = ((P_rev * 7) + K) mod 10000`

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

- Tag: `05194`
- Key ID: `0`
- Payload: `5194`
- AprilTag image:
![AprilTag 05194](media/tagStandard52h13-5194.svg)
- Final decoded result `(OOXXYY)` : `012310`

## Worked Example 2

- Tag: `02893`
- Key ID: `0`
- Payload: `2893`
- AprilTag image:
![AprilTag 02893](media/tagStandard52h13-2893.svg)
- Final decoded result `(OOXXYY)` : `071204`