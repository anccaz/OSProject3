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

---
## Entry 3 – April 29, 2026 | Header & File Management

**Goal:** Implement create, header read/write, and file validation.

- `_build_header(root_id, next_block)` packs a 512-byte block.
- `_read_header(f)` checks magic bytes on open and exits with error if invalid.
- `_open_valid(filename, mode)` centralizes the "file exists + is valid" check
used by every command except `create`.
- For `create`: checked `os.path.exists` first to avoid overwriting files.
- The first block written is a header with `root_id=0, next_block=1`, meaning
the tree is empty and the next node will live at block 1.

---
## Entry 4 – May 3, 2026 | B-Tree Insert

**Goal:** Implement B-Tree insertion with the 3-node memory constraint.

This was the most complex part. The algorithm follows CLRS B-Tree insertion:

1. If tree empty: create root node at next_block.
2. If root is full (19 keys): create new empty root, make old root its child,
   call `_split_child` to split it, then proceed with insert.
3. `_split_child(parent, i)`: splits `parent.children[i]` (which must be full).
   - Load child (node 2 in memory alongside parent = node 1)
   - Allocate new sibling at next_block (node 3)
   - Move keys/values/children t..19 to sibling
   - Promote median key[t-1] to parent
   - Save all three nodes, update header
   - Memory peak: parent + child + new_sib = 3 nodes ✓
4. `_insert_nonfull(node, key, value)`: recursively descend, splitting full
   children proactively on the way down so we never backtrack.

**Memory constraint analysis during a split:**
- In `_split_child`: parent (1) + child (2) + new_sib (3) = 3 nodes in memory.
  After saves, all are written to disk before returning.
- After a split, we reload child from disk before recursing,
  maintaining ≤ 3 nodes in memory at any point.

---