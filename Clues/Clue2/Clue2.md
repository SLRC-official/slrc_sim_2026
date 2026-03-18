# Clue 2: Key 1 Decoder Guide

![Clue 2](media/Clue2.png)

This clue uses:

- Key ID: `1`
- Key `(K)`: `Solve the Puzzle to find the Key!!!`
- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `P_swap` is formed by swapping the first two digits with the last two digits. ie. if `P = abcd` then `P_swap = cdab`
    5. `A = ((P_swap * 3) + K) mod 8750`

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

- Tag: `18862`
- Key ID: `1`
- Payload: `8862`
- AprilTag image:
![AprilTag 18862](media/tagStandard52h13-18862.svg)
- Final decoded result `(OOXXYY)` : `080505`

## Worked Example 2

- Tag: `16722`
- Key ID: `1`
- Payload: `6722`
- AprilTag image:
![AprilTag 16722](media/tagStandard52h13-16722.svg)
- Final decoded result `(OOXXYY)` : `022217`
