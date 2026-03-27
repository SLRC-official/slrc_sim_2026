# AprilTag Decoding Guide for Competitors


Each scanned AprilTag value is a 5-digit number in the form `kabcd`:

- `k` = key ID (0 to 4)
- `abcd` = 4-digit payload `P`

After decoding, you will get an intermediate integer `A`, then convert `A` to:

- `order_id` (1 to 14)
- `x_coordinate` (0 to 24)
- `y_coordinate` (0 to 24)

---

## Converting A to Coordinates (Common for All Keys)

Use this for every key after computing `A`:

```text
order_id = floor(A / 625) + 1
remainder = A % 625
x_coordinate = floor(remainder / 25)
y_coordinate = remainder % 25
```

Coordinate limits:

- `A` must be in the range 0 to 8749
- `order_id`: 1 to 14
- `x_coordinate`: 0 to 24
- `y_coordinate`: 0 to 24

---

## Key 0 Decoder

- Key ID: `0`
- Key value: `6180`

### Description

- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `P_rev` is the reverse of the payload. ie. if `P = abcd` then `P_rev = dcba`.
    5. `A = ((P_rev * 7) + 6180) mod 10000`.

### Decoding function

```python
def decode_key_0(payload):
    # P_rev is reverse of payload digits
    p_rev = int(str(payload).zfill(4)[::-1])
    A = ((p_rev * 7) + 6180) % 10000
    return A
```

### Worked example (Tag: 05194)

![AprilTag 05194](Clue1/media/tagStandard52h13-5194.svg)

```text
Tag = 05194
key_id = 0
payload P = 5194

P_rev = reverse("5194") = 4915
A = ((4915 * 7) + 6180) % 10000 = 585

order_id = floor(585 / 625) + 1 = 1
remainder = 585 % 625 = 585
x_coordinate = floor(585 / 25) = 23
y_coordinate = 585 % 25 = 10
```

Final decoded output: `order_id=1, x_coordinate=23, y_coordinate=10` (formatted `012310`)

---

## Key 1 Decoder

- Key ID: `1`
- Key value: `3141`

### Description

- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `P_swap` is formed by swapping the first two digits with the last two digits. ie. if `P = abcd` then `P_swap = cdab`.
    5. `A = ((P_swap * 3) + 3141) mod 8750`.

### Decoding function

```python
def decode_key_1(payload):
    # P_swap = swap first two digits with last two digits
    s = str(payload).zfill(4)
    p_swap = int(s[2:4] + s[0:2])
    A = ((p_swap * 3) + 3141) % 8750
    return A
```

### Worked example (Tag: 18862)

![AprilTag 18862](Clue2/media/tagStandard52h13-18862.svg)

```text
Tag = 18862
key_id = 1
payload P = 8862

P_swap = 6288
A = ((6288 * 3) + 3141) % 8750 = 4505

order_id = floor(4505 / 625) + 1 = 8
remainder = 4505 % 625 = 130
x_coordinate = floor(130 / 25) = 5
y_coordinate = 130 % 25 = 5
```

Final decoded output: `order_id=8, x_coordinate=5, y_coordinate=5` (formatted `080505`)

---

## Key 2 Decoder

- Key ID: `2`
- Key value: `2718`

### Description

- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `P_comp` is the complement of the payload. ie. `P_comp = 9999 - P`.
    5. `A = ((P_comp * 9) + 2718) mod 8750`.

### Decoding function

```python
def decode_key_2(payload):
    # P_comp = 9999 - P
    p_comp = 9999 - payload
    A = ((p_comp * 9) + 2718) % 8750
    return A
```

### Worked example (Tag: 27261)

![AprilTag 27261](Clue3/media/tagStandard52h13-27261.svg)

```text
Tag = 27261
key_id = 2
payload P = 7261

P_comp = 9999 - 7261 = 2738
A = ((2738 * 9) + 2718) % 8750 = 1110

order_id = floor(1110 / 625) + 1 = 2
remainder = 1110 % 625 = 485
x_coordinate = floor(485 / 25) = 19
y_coordinate = 485 % 25 = 10
```

Final decoded output: `order_id=2, x_coordinate=19, y_coordinate=10` (formatted `021910`)

---

## Key 3 Decoder

- Key ID: `3`
- Key value: `8080`

### Description

- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `P_int` is formed by swapping the first and last digits of the payload. ie. if `P = abcd` then `P_int = dbca`.
    5. `A = ((P_int * 11) + 8080) mod 8750`.

### Decoding function

```python
def decode_key_3(payload):
    # P_int = swap first and last payload digits
    s = list(str(payload).zfill(4))
    s[0], s[3] = s[3], s[0]
    p_int = int("".join(s))
    A = ((p_int * 11) + 8080) % 8750
    return A
```

### Worked example (Tag: 32994)

![AprilTag 32994](Clue4/media/tagStandard52h13-32994.svg)

```text
Tag = 32994
key_id = 3
payload P = 2994

P_int = 4992
A = ((4992 * 11) + 8080) % 8750 = 1742

order_id = floor(1742 / 625) + 1 = 3
remainder = 1742 % 625 = 492
x_coordinate = floor(492 / 25) = 19
y_coordinate = 492 % 25 = 17
```

Final decoded output: `order_id=3, x_coordinate=19, y_coordinate=17` (formatted `031917`)

---

## Key 4 Decoder

- Key ID: `4`
- Key value: `4040`

### Description

- Decryption Algorithm
    1. The scanned AprilTag value is a 5-digit number of the form `kabcd`.
    2. The first digit `k` is the key ID.
    3. The remaining 4 digits form the payload `P = abcd`.
    4. `G` is the Gray code of the payload. ie. `G = P XOR floor(P / 2)`.
    5. `A = G XOR 4040`.

### Decoding function

```python
def decode_key_4(payload):
    # G is Gray code of payload
    g = payload ^ (payload >> 1)
    A = g ^ 4040
    return A
```

### Worked example (Tag: 46258)

![AprilTag 46258](Clue5/media/tagStandard52h13-46258.svg)

```text
Tag = 46258
key_id = 4
payload P = 6258

G = 6258 XOR floor(6258 / 2)
G = 6258 XOR 3129 = 5179
A = 5179 XOR 4040 = 7043

order_id = floor(7043 / 625) + 1 = 12
remainder = 7043 % 625 = 168
x_coordinate = floor(168 / 25) = 6
y_coordinate = 168 % 25 = 18
```

Final decoded output: `order_id=12, x_coordinate=6, y_coordinate=18` (formatted `120618`)

---

## Complete Example Python Decoder

```python
def retrieve_coordinates(A_value):
    if A_value < 0 or A_value >= 8750:
        raise ValueError("Invalid A value")

    order = (A_value // 625) + 1
    remainder = A_value % 625
    row = remainder // 25
    col = remainder % 25
    return order, row, col


def decode_tag(tag_value):
    if len(tag_value) != 5:
        raise ValueError("Invalid tag value length")

    key_id = int(tag_value[0])
    payload = int(tag_value[1:])

    if key_id == 0:  # Key 0 = 6180
        p_rev = int(str(payload).zfill(4)[::-1])
        A = ((p_rev * 7) + 6180) % 10000
        return retrieve_coordinates(A)

    elif key_id == 1:  # Key 1 = 3141
        s = str(payload).zfill(4)
        p_swap = int(s[2:4] + s[0:2])
        A = ((p_swap * 3) + 3141) % 8750
        return retrieve_coordinates(A)

    elif key_id == 2:  # Key 2 = 2718
        p_comp = 9999 - payload
        A = ((p_comp * 9) + 2718) % 8750
        return retrieve_coordinates(A)

    elif key_id == 3:  # Key 3 = 8080
        s = list(str(payload).zfill(4))
        s[0], s[3] = s[3], s[0]
        p_int = int("".join(s))
        A = ((p_int * 11) + 8080) % 8750
        return retrieve_coordinates(A)

    elif key_id == 4:  # Key 4 = 4040
        g = payload ^ (payload >> 1)
        A = g ^ 4040
        return retrieve_coordinates(A)

    else:
        raise ValueError("Invalid key ID")
```

## Usage

```python
tag = "18862"
order_id, x_coordinate, y_coordinate = decode_tag(tag)
print(order_id, x_coordinate, y_coordinate)
# Output: 8 5 5
```

For scoreboard or logging, you can format the result as `OOXXYY`:

```python
formatted = f"{order_id:02d}{x_coordinate:02d}{y_coordinate:02d}"
print(formatted)
# Output: 080505
```

## Note

It is guaranteed that all AprilTags used in the arena decode to a valid key (`0` to `4`) and produce a valid coordinate output.