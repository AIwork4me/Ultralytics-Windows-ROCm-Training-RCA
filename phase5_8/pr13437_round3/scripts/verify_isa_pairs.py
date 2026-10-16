"""Recheck the retained ten ELF .text pairs without ROCm or third-party packages.

Usage: python scripts/verify_isa_pairs.py [--root /path/to/evidence/package]
Reads original bytes; SQLite is opened only after copying cache snapshots into a
TemporaryDirectory, so recovery/checkpointing cannot alter archived sidecars.
This verifies retained artifacts, not historical source-to-artifact attestation,
whole-program performance, or reconstruction of the missing BN cache option sets.
"""
import argparse
import bz2
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import struct
import tempfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def elf_sections(data):
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected ELF64 little-endian')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    if header[2] != 224:
        raise ValueError('Expected EM_AMDGPU')
    offset, size, count, strings_index = header[6], header[11], header[12], header[13]
    if size < 64 or not count or strings_index >= count:
        raise ValueError('Unsupported/invalid section table')
    if offset + size * count > len(data):
        raise ValueError('Section table outside file')
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings_header = headers[strings_index]
    strings = data[strings_header[4]:strings_header[4] + strings_header[5]]
    result = {}
    for entry in headers:
        name = strings[entry[0]:].split(b'\0', 1)[0].decode('ascii')
        if entry[1] == 8:  # SHT_NOBITS has no file payload.
            continue
        start, length = entry[4], entry[5]
        if start + length > len(data) or name in result:
            raise ValueError('Invalid section extent/name: ' + name)
        result[name] = data[start:start + length]
    if not result.get('.text'):
        raise ValueError('Missing/empty .text')
    return result


def verify(root):
    perf = root / 'raw/perf'
    pairs = []
    for name in ['kth_fp32', 'kth_fp16', 'kth_bf16'] + ['bnx' + str(i) for i in range(7)]:
        adata = (perf / (name + '_A.elf')).read_bytes()
        bdata = (perf / (name + '_B.elf')).read_bytes()
        a, b = elf_sections(adata), elf_sections(bdata)
        if a['.text'] != b['.text'] or a.get('.note') != b.get('.note'):
            raise ValueError(name + ': .text/.note mismatch')
        pair = {'pair': name, 'text_bytes': len(a['.text']), 'text_sha256': sha(a['.text']),
                'elf_A_sha256': sha(adata), 'elf_B_sha256': sha(bdata),
                'text_equal': True, 'note_equal': True,
                'differing_sections': sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))}
        if name.startswith('bnx'):
            ia = (perf / (name + '_A.isa')).read_bytes()
            ib = (perf / (name + '_B.isa')).read_bytes()
            if ia != ib:
                raise ValueError(name + ': archived ISA body mismatch')
            pair['isa_body_equal'] = True
            pair['isa_instruction_lines'] = len(ia.splitlines())
        pairs.append(pair)
    caches = []
    with tempfile.TemporaryDirectory(prefix='pr13437_readonly_isa_') as temp:
        for label in 'AB':
            source = perf / ('kern_cache_' + label)
            copy = Path(temp) / label
            shutil.copytree(source, copy)
            for db in sorted(copy.rglob('*.ukdb')):
                con = sqlite3.connect(db.as_uri() + '?mode=ro', uri=True)
                try:
                    rows = con.execute('SELECT kernel_name, kernel_args, kernel_blob, uncompressed_size FROM kern_db').fetchall()
                    records = []
                    for name, args, blob, uncompressed_size in sorted(rows):
                        data = bz2.decompress(blob)
                        if len(data) != uncompressed_size:
                            raise ValueError('Cache size metadata mismatch')
                        dtype = ('fp32' if '-DMIOPEN_USE_FP32=1' in args else
                                 'fp16' if '-DMIOPEN_USE_FP16=1' in args else 'bf16')
                        artifact = perf / ('kth_' + dtype + '_' + label + '.elf')
                        matches = name == 'MIOpenKthvalue.cpp.obj' and artifact.read_bytes() == data
                        if not matches:
                            raise ValueError('Cache row does not match retained kth ELF: ' + name)
                        records.append({'kernel_name': name, 'args': args,
                                        'blob_sha256': sha(blob), 'elf_sha256': sha(data),
                                        'retained_elf': artifact.relative_to(root).as_posix(), 'exact_elf_match': True})
                    caches.append({'label': label, 'path': db.relative_to(copy).as_posix(),
                                   'db_sha256': sha(db.read_bytes()), 'rows': records})
                finally:
                    con.close()
    return {'result': 'PASS', 'scope': 'ten retained paired ELF .text sections; kth cache-to-ELF link only',
            'pairs': pairs, 'cache_snapshots': caches,
            'limitations': ['Archived caches contain three kthvalue rows per label, not BatchNorm rows.',
                           'BatchNorm historical source/option-set mapping is not independently reconstructed.',
                           'Machine-code equality does not establish whole-program timing equivalence.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve()), indent=2))


if __name__ == '__main__':
    main()
