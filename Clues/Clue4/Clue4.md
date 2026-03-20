# Clue 4: Key 3 Decoder Guide

![Clue 4](media/Clue4.png)

This clue uses:

- Key ID: `3`
- Key `(K)`: `Solve the puzzle to find the Key!!!`
- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `P_int` is formed by swapping the first and last digits of the payload. ie. if `P = abcd` then `P_int = dbca`
    5. `A = ((P_int * 11) + K) mod 8750`

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

- Tag: `32994`
- Key ID: `3`
- Payload: `2994`
- AprilTag image:
![AprilTag 32994](media/tagStandard52h13-32994.svg)
- Final decoded result `(OOXXYY)` : `031917`

## Worked Example 2

- Tag: `33861`
- Key ID: `3`
- Payload: `3861`
- AprilTag image:
![AprilTag 33861](media/tagStandard52h13-33861.svg)
- Final decoded result `(OOXXYY)` : `041723`
