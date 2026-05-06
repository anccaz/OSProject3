# CS4348 Project 3 – B-Tree Index File Manager

## Author
Annie Li  
CS4348-003 – Operating Systems Concepts  
Spring 2026

---

## Overview

This program creates and manages binary index files that store a B-Tree
with minimal degree **t = 10** (max 19 keys, 20 child pointers per node).
All data is stored in 512-byte blocks using big-endian 8-byte integers.
Implemented in Python 3.

---

## Requirements

- Python 3.8 or higher
- No third-party libraries required (uses only `sys`, `os`, `struct`, `csv`)

---

## How to Run

```bash
python3 project3.py <command> [arguments]
```

---

## Commands

### `create`
Create a new index file. Fails if the file already exists.
```bash
python3 project3.py create test.idx
```

### `insert`
Insert a key/value pair. Both must be integers.
```bash
python3 project3.py insert test.idx 15 100
```

### `search`
Search for a key. Prints the pair if found, otherwise prints an error.
```bash
python3 project3.py search test.idx 15
```

### `load`
Load key/value pairs from a CSV file into the index.
```bash
python3 project3.py load test.idx input.csv
```

### `print`
Print all key/value pairs in sorted order to stdout.
```bash
python3 project3.py print test.idx
```

### `extract`
Save all key/value pairs to a new CSV file. Fails if the output file already exists.
```bash
python3 project3.py extract test.idx output.csv
```

---

## File Format

### Header — Block 0 (512 bytes)

| Offset | Size | Content                        |
|--------|------|--------------------------------|
| 0      | 8    | Magic number: `4348PRJ3`       |
| 8      | 8    | Root block ID (0 = empty tree) |
| 16     | 8    | Next available block ID        |
| 24     | 488  | Unused                         |

### Node Block (512 bytes)

| Offset | Size | Content                        |
|--------|------|--------------------------------|
| 0      | 8    | This node's block ID           |
| 8      | 8    | Parent block ID (0 = root)     |
| 16     | 8    | Number of keys currently stored|
| 24     | 152  | 19 × 8-byte keys               |
| 176    | 152  | 19 × 8-byte values             |
| 328    | 160  | 20 × 8-byte child block IDs    |
| 488    | 24   | Unused                         |

All integers are stored in **big-endian** byte order.

---

## Design Notes

- **Memory constraint:** At most 3 nodes are held in memory at any time.
  During a split this is parent + child + new sibling — then all are
  written to disk before any further loads occur.
- **Leaf detection:** A node is a leaf if all 20 child pointers equal zero.
- **Block allocation:** Block 0 is always the header. New nodes are
  appended starting at block 1. The next available block ID is tracked
  in the header and updated on every insert.
- **No deletion:** The spec does not require a delete operation so none
  is implemented.
- **Traversal:** In-order traversal is used for both `print` and `extract`
  to return keys in sorted ascending order.

---

## Example Workflow

```bash
python3 project3.py create mydb.idx
python3 project3.py insert mydb.idx 10 1000
python3 project3.py insert mydb.idx 5 500
python3 project3.py insert mydb.idx 20 2000
python3 project3.py search mydb.idx 5
# Found: key=5, value=500
python3 project3.py print mydb.idx
# 5,500
# 10,1000
# 20,2000
python3 project3.py extract mydb.idx output.csv
```

---

## How to Run

```bash