# Dev Log – CS4348 Project 3

## Entry 1 – April 23, 2026 | Project Setup & File Format Design

**Goal:** Understand the spec and plan the file layout.

Read through the project description carefully. Key constraints:

- 512-byte blocks, big-endian 8-byte integers everywhere
- Header at block 0: magic `4348PRJ3`, root block ID, next block ID
- Each B-Tree node = one block with: block_id, parent_id, n_keys,
  19 keys (152 bytes), 19 values (152 bytes), 20 child pointers (160 bytes)
- Minimal degree t=10 → max 19 keys, max 20 children
- **Critical constraint: never more than 3 nodes in memory at once**

---

## Entry 2 – April 28, 2026 | BNode Class & Serialization

**Goal:** Implement reliable node serialization/deserialization.

- Built the `BNode` dataclass with `serialize()` and `deserialize()` methods.
- Used `struct.pack_into('>Q', ...)` for fixed-offset writes into a 512-byte `bytearray`.

