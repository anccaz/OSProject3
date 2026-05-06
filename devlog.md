# Dev Log – CS4348 Project 3

## Entry 1 – April 23, 2026 | Project Setup & File Format Design

**Goal:** Understand the spec and plan the binary file layout.

Read through the project description carefully. Key constraints:

- 512-byte blocks, big-endian 8-byte integers everywhere
- Header at block 0: magic `4348PRJ3`, root block ID, next block ID
- Each B-Tree node = one block with: block_id, parent_id, n_keys,
  19 keys (152 bytes), 19 values (152 bytes), 20 child pointers (160 bytes)
- Minimal degree t=10 → max 19 keys, max 20 children
- **Critical constraint: never more than 3 nodes in memory at once**

Decided to implement in Python since the spec calls out `int.to_bytes(8, 'big')` directly.

Planned modules and functions:
- `_pack8` / `_unpack8`: endian-safe integer I/O
- `_read_block` / `_write_block`: raw 512-byte I/O
- `BNode` class: serialize/deserialize node to/from bytes
- Header helpers: `_read_header`, `_write_header`
- B-Tree logic: `btree_insert`, `btree_search`, `btree_all_pairs`
- Command handlers: one per command

---

## Entry 2 – April 28, 2026 | BNode Class & Serialization

**Goal:** Implement reliable node serialization/deserialization.

Built the `BNode` class with `serialize()` and `deserialize()` methods.
Used `struct.pack_into('>Q', ...)` for fixed-offset writes into a 512-byte `bytearray`.

Key byte offsets:
NODE_ID_OFF     = 0
NODE_PARENT_OFF = 8
NODE_NKEYS_OFF  = 16
NODE_KEYS_OFF   = 24     (19 keys × 8 = 152 bytes)
NODE_VALS_OFF   = 176    (19 values × 8 = 152 bytes)
NODE_CHLD_OFF   = 328    (20 children × 8 = 160 bytes)


Total used: 488 bytes → 24 bytes unused per node, which is fine per spec.

Added `is_leaf` property: a node is a leaf if all 20 child pointers are zero.
Tested serialization round-trip — create a BNode, serialize, deserialize,
compare all fields. Everything matched.

---

## Entry 3 – April 29, 2026 | Header & File Management

**Goal:** Implement create, header read/write, and file validation.

- `_build_header(root_id, next_block)` packs the full 512-byte header block.
- `_read_header(f)` validates the magic bytes on open and exits with an error if invalid.
- `_open_valid(filename, mode)` centralizes the "file exists + is valid" check
  used by every command except `create`.
- For `create`: used `os.path.exists` first to avoid overwriting existing files.
- First block written is a header with `root_id=0, next_block=1` — tree starts
  empty and the first node will be placed at block 1.

---

## Entry 4 – May 3, 2026 | B-Tree Insert

**Goal:** Implement B-Tree insertion while respecting the 3-node memory constraint.

This was the most complex part of the project. Followed the CLRS B-Tree insertion algorithm:

1. If tree is empty: create root node at next_block.
2. If root is full (19 keys): create a new empty root, make the old root its
   first child, call `_split_child`, then proceed with the insert.
3. `_split_child(parent, i)`: splits `parent.children[i]`, which must be full.
   - Load the full child (node 2, alongside parent = node 1)
   - Allocate a new sibling at next_block (node 3)
   - Move keys/values/children from index t onward into the sibling
   - Promote the median key at index t-1 up into the parent
   - Save all three nodes and update the header
   - Memory peak: parent + child + new_sib = exactly 3 nodes ✓
4. `_insert_nonfull(node, key, value)`: descends the tree, splitting any full
   child proactively on the way down so we never need to backtrack.

Memory stays at or below 3 nodes throughout because all nodes are written to
disk before the next load occurs.

---

## Entry 5 – May 4, 2026 | Bug Fix – Grandchild Parent Pointers

**Goal:** Fix incorrect `parent_id` fields after splitting a non-leaf node.

Found a bug: when a non-leaf node was split, the children that moved into the
new sibling still had their `parent_id` pointing to the original node. Fixed
by adding a loop after the split that loads each affected grandchild, updates
its `parent_id` to the new sibling's block ID, and immediately saves it back.
Only one grandchild is held in memory at a time during this loop, so the
working set stays at or below 3 nodes.

Verified the fix by inserting 50 sequential keys and inspecting the file with
a hex dump — all parent pointers were consistent.

---

## Entry 6 – May 5, 2026 | Search & Traversal

**Goal:** Implement key search and in-order traversal.

`btree_search(f, key)` — iterative descent:
- Scan each node's keys left to right
- If `key == keys[i]` → return `(key, values[i])`
- If `key < keys[i]` → follow `children[i]`
- If key is larger than all keys → follow `children[n]`
- Only one node in memory at a time ✓

`_traverse(f, block_id, pairs)` — recursive in-order walk:
- For each node, interleave left child → key[i] → right child
- One node loaded per stack frame; used for both `print` and `extract`

---

## Entry 7 – May 5, 2026 | Remaining Commands & Error Handling

**Goal:** Implement `load`, `print`, `extract` and finalize all error paths.

- `load`: reads a CSV with `csv.reader`, parses each row as `(int, int)`,
  calls `btree_insert` for each. Skips and warns on malformed rows.
- `print`: calls `btree_all_pairs` and prints each pair as `key,value` to stdout.
- `extract`: same as print but writes to a new CSV file. Exits if the output
  file already exists, leaving it untouched.

Error handling summary:

| Scenario | Behavior |
|---|---|
| `create` on existing file | Exit with message, file untouched |
| Command on missing index file | Exit with message |
| File exists but bad magic number | Exit with message |
| Non-integer key or value | Exit with message |
| `extract` to existing output file | Exit with message, file untouched |
| Malformed row during `load` | Print warning, skip row, continue |
| Search for missing key | Print not found message |
| Unknown command | Print usage and exit |

---

## Entry 8 – May 6, 2026 | Final Testing & Cleanup

**Goal:** Full end-to-end test pass before submission.

**Test 1 – Basic insert & search**
Inserted keys 1, 5, 10, 15, 20. Searched for key 5 → found correctly.
Searched for key 99 → not found message printed correctly.

**Test 2 – Print in sorted order**
`print` returned all keys in ascending order via in-order traversal. ✓

**Test 3 – Load from CSV**
Created `input.csv` with 50 entries. Loaded cleanly. Verified with `print`
that all 50 keys appeared in sorted order. ✓

**Test 4 – Extract and reload**
Extracted to `out.csv`, created a fresh index, loaded `out.csv` back in,
printed it — output matched the original exactly. ✓

**Test 5 – Root split stress test**
Inserted 50 sequential keys to trigger multiple node splits including a root
split. All 50 keys were retrievable via `search` after insertion.
File structure confirmed correct via hex dump. ✓

**Test 6 – Error conditions**
- Double `create` → error, original file unchanged ✓
- `insert` into non-existent file → error ✓
- `extract` to existing output file → error, file unchanged ✓

Cleaned up all print statements, verified all commands are lowercase per spec.
Ready to submit.