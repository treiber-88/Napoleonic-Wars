"""
Minimal read-only HFS+ reader, enough to pull an application bundle out of a raw macOS disk image
(e.g. the image inside OpenRA's release .dmg, converted with dmg2img).

Unlike 7-Zip it resolves HFS+ hard links (OpenRA's release hard-links the files its three app bundles
share, so most files of each bundle are link stubs) and it reports each file's Unix mode and symlinks.

    vol = Volume(open(path, "rb"))
    for rel, entry in vol.walk("OpenRA - Red Alert.app"):
        ...            # entry.kind in ("dir", "file", "symlink"); entry.mode; vol.read(entry)
"""
import struct

SECTOR = 512
S_IFMT, S_IFLNK = 0o170000, 0o120000
UF_COMPRESSED = 0x20


class Entry:
    __slots__ = ("cnid", "parent", "name", "kind", "mode", "size", "extents", "total_blocks", "link_inode", "flags", "target")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class Volume:
    def __init__(self, f):
        self.f = f
        self.base = self._find_partition()
        vh = self._read_at(self.base + 1024, 512)
        if vh[:2] not in (b"H+", b"HX"):
            raise ValueError("not an HFS+ volume")
        self.block_size = struct.unpack(">I", vh[40:44])[0]
        self.overflow = self._load_extents_overflow(self._fork(vh, 192))
        cat_size, cat_extents, cat_blocks = self._fork(vh, 272)
        self.catalog = self._read_fork(4, 0, cat_size, cat_extents, cat_blocks)
        self.by_cnid, self.children = {}, {}
        self._load_catalog()
        self.private_dir = next((e.cnid for e in self.children.get(2, []) if e.kind == "dir" and e.name.endswith("HFS+ Private Data")), None)
        self.inodes = {e.name: e for e in self.children.get(self.private_dir, [])} if self.private_dir else {}

    # ---- low level ----
    def _read_at(self, off, n):
        self.f.seek(off)
        return self.f.read(n)

    def _find_partition(self):
        b0 = self._read_at(0, 2)
        if b0 == b"ER":                                    # Apple Partition Map
            for i in range(1, 64):
                p = self._read_at(i * SECTOR, SECTOR)
                if p[:2] != b"PM":
                    break
                if p[48:80].rstrip(b"\0") == b"Apple_HFS":
                    return struct.unpack(">I", p[8:12])[0] * SECTOR
        for off in (0, 1024, 4096, 8192, 20480, 163840, 409600, 1048576):
            if self._read_at(off + 1024, 2) in (b"H+", b"HX"):
                return off
        raise ValueError("no HFS+ partition found")

    @staticmethod
    def _fork(buf, off):
        size = struct.unpack(">Q", buf[off:off + 8])[0]
        total = struct.unpack(">I", buf[off + 12:off + 16])[0]
        extents = [struct.unpack(">II", buf[off + 16 + 8 * i:off + 24 + 8 * i]) for i in range(8)]
        return size, [e for e in extents if e[1]], total

    def _read_extents(self, extents, size):
        out = bytearray()
        for start, count in extents:
            out += self._read_at(self.base + start * self.block_size, count * self.block_size)
            if len(out) >= size:
                break
        return bytes(out[:size])

    def _read_fork(self, cnid, fork_type, size, extents, total_blocks):
        extents = list(extents)
        have = sum(c for _, c in extents)
        while have < total_blocks:                         # continue in the extents overflow file
            more = self.overflow.get((cnid, fork_type, have))
            if not more:
                raise ValueError("fork of CNID %d is fragmented beyond the extents found" % cnid)
            extents += more
            have += sum(c for _, c in more)
        return self._read_extents(extents, size)

    @staticmethod
    def _leaf_records(tree):
        node_size = struct.unpack(">H", tree[32:34])[0]
        node = struct.unpack(">I", tree[24:28])[0]         # firstLeafNode
        while node:
            n = tree[node * node_size:(node + 1) * node_size]
            flink, _, kind, _, count = struct.unpack(">IIbBH", n[:12])
            if kind == -1:
                for i in range(count):
                    off = struct.unpack(">H", n[node_size - 2 * (i + 1):node_size - 2 * i])[0]
                    end = struct.unpack(">H", n[node_size - 2 * (i + 2):node_size - 2 * (i + 1)])[0]
                    yield n[off:end]
            node = flink

    def _load_extents_overflow(self, fork):
        size, extents, _ = fork
        table = {}
        if not size:
            return table
        tree = self._read_extents(extents, size)
        for rec in self._leaf_records(tree):
            key_len = struct.unpack(">H", rec[:2])[0]
            fork_type, _, cnid, start = struct.unpack(">BBII", rec[2:12])
            data = rec[2 + key_len:]
            ext = [struct.unpack(">II", data[8 * i:8 * i + 8]) for i in range(8)]
            table[(cnid, fork_type, start)] = [e for e in ext if e[1]]
        return table

    def _load_catalog(self):
        for rec in self._leaf_records(self.catalog):
            key_len = struct.unpack(">H", rec[:2])[0]
            parent, name_len = struct.unpack(">IH", rec[2:8])
            name = rec[8:8 + 2 * name_len].decode("utf-16-be")
            d = rec[2 + key_len + ((2 + key_len) & 1):]
            rtype = struct.unpack(">h", d[:2])[0]
            if rtype == 1:
                cnid = struct.unpack(">I", d[8:12])[0]
                mode = struct.unpack(">H", d[42:44])[0]
                e = Entry(cnid=cnid, parent=parent, name=name, kind="dir", mode=mode & 0o7777 or 0o755)
            elif rtype == 2:
                cnid = struct.unpack(">I", d[8:12])[0]
                flags = d[41]
                mode, special = struct.unpack(">HI", d[42:48])
                ftype, creator = d[48:52], d[52:56]
                size, extents, total = self._fork(d, 88)
                e = Entry(cnid=cnid, parent=parent, name=name, kind="file", mode=mode & 0o7777, size=size, extents=extents,
                          total_blocks=total, flags=flags)
                if ftype == b"hlnk" and creator == b"hfs+":
                    e.link_inode = "iNode%d" % special
                elif mode & S_IFMT == S_IFLNK:
                    e.kind = "symlink"
            else:
                continue
            self.by_cnid[e.cnid] = e
            self.children.setdefault(parent, []).append(e)

    # ---- public ----
    def resolve(self, entry):
        """Follows a hard link to the file that holds the data."""
        if entry.link_inode:
            target = self.inodes.get(entry.link_inode)
            if target is None:
                raise KeyError("hard link target %s missing" % entry.link_inode)
            return target
        return entry

    def read(self, entry):
        e = self.resolve(entry)
        if e.flags and e.flags & UF_COMPRESSED and not e.size:
            raise ValueError("%s is HFS-compressed (not supported)" % entry.name)
        return self._read_fork(e.cnid, 0, e.size, e.extents, e.total_blocks)

    def find(self, path):
        cur = 2
        entry = None
        for part in [p for p in path.split("/") if p]:
            entry = next((c for c in self.children.get(cur, []) if c.name == part), None)
            if entry is None:
                raise KeyError(path)
            cur = entry.cnid
        return entry

    def walk(self, path):
        """Yields (relative path, entry) for everything below `path`; files are already hard-link resolved for mode/size."""
        root = self.find(path)

        def rec(cnid, prefix):
            for c in sorted(self.children.get(cnid, []), key=lambda e: e.name):
                rel = prefix + c.name
                if c.kind == "dir":
                    yield rel, c
                    yield from rec(c.cnid, rel + "/")
                else:
                    real = self.resolve(c)
                    out = Entry(cnid=real.cnid, parent=c.parent, name=c.name, kind=real.kind if real.kind != "file" else c.kind,
                                mode=real.mode or c.mode, size=real.size, extents=real.extents, total_blocks=real.total_blocks,
                                flags=real.flags, link_inode=None)
                    if c.kind == "symlink" or real.kind == "symlink":
                        out.kind = "symlink"
                    yield rel, out
        yield from rec(root.cnid, "")
