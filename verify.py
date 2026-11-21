"""Independent checks for the two MASM labs; runs on the Windows build runner."""
from __future__ import annotations
import csv
import ctypes
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
LOW, HIGH = -(1 << 63), (1 << 63) - 1
VALUES = [('x_plus_n', 8354 + 1), ('x_minus_n', 8354 - 1),
          ('neg_x_minus_n', -8354 - 1), ('neg_x_plus_n', -8354 + 1),
          ('y_plus_n', 101 + 1), ('y_minus_n', 101 - 1),
          ('neg_y_minus_n', -101 - 1), ('neg_y_plus_n', -101 + 1)]
TYPES = [('byte', 8, False), ('shortint', 8, True), ('word', 16, False),
         ('integer', 16, True), ('longword', 32, False), ('longint', 32, True)]


def fits(value, width, signed):
    return -(1 << (width - 1)) <= value < (1 << (width - 1)) if signed else 0 <= value < (1 << width)


def read_coff(path):
    """Read native AMD64 COFF sections/symbols without trusting listing text."""
    data = path.read_bytes()
    machine, count, _, sym_start, sym_count, opt_size, _ = struct.unpack_from('<HHIIIHH', data)
    assert machine == 0x8664, 'Expected AMD64 object file'
    sections = []
    for i in range(count):
        base = 20 + opt_size + i * 40
        name = data[base:base + 8].split(b'\0')[0].decode('ascii')
        size, offset = struct.unpack_from('<II', data, base + 16)
        sections.append((name, data[offset:offset + size]))
    strings = sym_start + sym_count * 18
    symbols = {}
    i = 0
    while i < sym_count:
        base = sym_start + i * 18
        raw_name = data[base:base + 8]
        if raw_name[:4] == b'\0' * 4:
            start = strings + struct.unpack_from('<I', raw_name, 4)[0]
            name = data[start:data.index(b'\0', start)].decode('ascii')
        else:
            name = raw_name.split(b'\0')[0].decode('ascii')
        value, section, _, _, aux = struct.unpack_from('<IhHBB', data, base + 8)
        symbols[name] = (section, value)
        i += 1 + aux
    return sections, symbols


def check_lab1():
    sections, symbols = read_coff(BUILD / 'lab_1.obj')
    declarations = []
    offset = 0
    expected_bytes = bytearray()
    for kind, width, signed in TYPES:
        for expr, number in VALUES:
            label = kind + '_' + expr
            if not fits(number, width, signed):
                assert label not in symbols, 'Out-of-range declaration: ' + label
                continue
            section, location = symbols[label]
            assert section > 0 and sections[section - 1][0] == '.data'
            assert location == offset, (label, location, offset)
            encoded = number.to_bytes(width // 8, 'little', signed=signed)
            actual = sections[section - 1][1][location:location + width // 8]
            assert actual == encoded, (label, actual.hex(), encoded.hex())
            encoded_value = number % (1 << width)
            declarations.append({'label': label, 'value': number, 'bits': width,
                                 'signed': signed, 'offset': offset,
                                 'hex': f'{encoded_value:0{width // 4}X}',
                                 'binary': f'{encoded_value:0{width}b}',
                                 'memory_bytes': encoded.hex(' ').upper()})
            offset += width // 8
            expected_bytes.extend(encoded)
    begin_sec, begin = symbols['data_begin']
    end_sec, end = symbols['data_end']
    assert begin_sec == end_sec and begin == 0 and end == offset == 78
    assert len(declarations) == 30
    assert sections[begin_sec - 1][1][:offset] == expected_bytes
    listing = (BUILD / 'lab_1.lst').read_text(encoding='utf-8', errors='replace')
    for declaration in declarations:
        assert declaration['label'] in listing
    proc = subprocess.run([str(BUILD / 'lab_1.exe')], capture_output=True, timeout=5)
    assert proc.returncode == 0
    return {'status': 'PASS', 'declarations_checked': len(declarations),
            'data_bytes_checked': offset, 'invalid_formats_excluded': 18,
            'executable_exit_code': proc.returncode, 'declarations': declarations}


def trunc_div(n, d):
    q = abs(n) // abs(d)
    return -q if (n < 0) != (d < 0) else q


def reference(a, c, d):
    # Explicit policy: signed 64-bit checks after 2*c, then subtract d, then 23.
    n = c * 2
    if not LOW <= n <= HIGH:
        return 2, None
    n -= d
    if not LOW <= n <= HIGH:
        return 2, None
    n -= 23
    if not LOW <= n <= HIGH:
        return 2, None
    denominator = trunc_div(a, 4) - 1
    if denominator == 0:
        return 1, None
    q = trunc_div(n, denominator)
    if not LOW <= q <= HIGH:
        return 2, None
    return 0, (q, n - q * denominator, n, denominator)


NAMED_CASES = [
    ('positive exact', 12, 30, 5), ('positive remainder', 20, 30, 4),
    ('negative numerator', 12, 5, 0), ('negative denominator', -8, 30, 5),
    ('both negative', -8, 5, 0), ('negative a not divisible by four', -7, 30, 5),
    ('negative a near zero', -1, 30, 5), ('zero numerator', 12, 12, 1),
    ('zero a', 0, 30, 5), ('zero denominator lower', 4, 30, 5),
    ('zero denominator upper', 7, 30, 5), ('multiply overflow', 12, HIGH, 0),
    ('subtract d overflow', 12, 0, LOW), ('subtract 23 underflow', 12, LOW // 2, 0),
    ('minimum numerator valid', 12, (LOW + 24) // 2, 1),
    ('minimum divided by minus one', 0, (LOW + 24) // 2, 1),
    ('largest sequential numerator', 12, HIGH // 2, -1),
    ('maximum quotient', 0, (LOW + 24) // 2, 0),
    ('minimum a', LOW, 30, 5), ('maximum a', HIGH, 30, 5),
    ('minimum input accepted with safe numerator', 12, LOW // 2, -23),
]


def check_lab2():
    dll = ctypes.WinDLL(str(BUILD / 'lab_2.dll'))
    calc = dll.calculate_expression
    calc.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_int64,
                     ctypes.POINTER(ctypes.c_int64)]
    calc.restype = ctypes.c_int
    totals = {'success': 0, 'zero_denominator': 0, 'overflow': 0}
    digest = hashlib.sha256()
    total = 0

    def check(a, c, d):
        nonlocal total
        assert all(LOW <= value <= HIGH for value in [a, c, d])
        expected_status, expected = reference(a, c, d)
        # Guard both ends of the output and verify atomic failure behaviour.
        sentinel = 43210987654321
        storage = (ctypes.c_int64 * 6)(*[sentinel] * 6)
        ptr = ctypes.cast(ctypes.byref(storage, 8), ctypes.POINTER(ctypes.c_int64))
        status = calc(a, c, d, ptr)
        actual = tuple(storage[1:5])
        assert status == expected_status, (a, c, d, status, expected_status)
        assert storage[0] == storage[5] == sentinel, 'Output overrun'
        if status == 0:
            assert actual == expected, (a, c, d, actual, expected)
            q, r, n, denominator = actual
            assert n == q * denominator + r and abs(r) < abs(denominator)
            assert r == 0 or (r < 0) == (n < 0)
        else:
            assert actual == (sentinel,) * 4, 'Failure modified output'
        totals[['success', 'zero_denominator', 'overflow'][status]] += 1
        total += 1
        digest.update(json.dumps([a, c, d, status, actual], separators=(',', ':')).encode())
        return {'a': a, 'c': c, 'd': d, 'status': status,
                'result': list(actual) if status == 0 else None}

    named = [{'name': name, **check(a, c, d)} for name, a, c, d in NAMED_CASES]
    for a, c, d in itertools.product(range(-20, 21), range(-4, 5), range(-4, 5)):
        check(a, c, d)
    edges = [LOW, LOW + 1, LOW // 2 - 1, LOW // 2, -8, -7, -4, -1, 0,
             1, 3, 4, 7, 8, HIGH // 2, HIGH // 2 + 1, HIGH - 1, HIGH]
    for a, c, d in itertools.product(edges, repeat=3):
        check(a, c, d)
    rng = random.Random(20261121)
    for _ in range(10000):
        check(*(rng.randint(-1000000, 1000000) for _ in range(3)))
    for _ in range(10000):
        check(*(rng.randint(LOW, HIGH) for _ in range(3)))

    cli_results = []
    exe = str(BUILD / 'lab_2.exe')

    def run_cli(name, args, code, required):
        proc = subprocess.run([exe, *args], capture_output=True, text=True,
                              encoding='utf-8', timeout=5)
        assert proc.returncode == code, (name, proc.returncode, proc.stdout, proc.stderr)
        assert not proc.stderr, (name, proc.stderr)
        for part in required:
            assert part in proc.stdout, (name, part, proc.stdout)
        cli_results.append({'name': name, 'arguments': args, 'exit_code': code,
                            'output': proc.stdout, 'status': 'PASS'})

    for name, a, c, d in NAMED_CASES:
        status, result = reference(a, c, d)
        required = ([f'Numerator: {result[2]}', f'Denominator: {result[3]}',
                     f'Quotient: {result[0]}', f'Remainder: {result[1]}'] if result
                    else ['denominator' if status == 1 else 'overflow'])
        run_cli(name, list(map(str, [a, c, d])), {0: 0, 1: 3, 2: 4}[status], required)
    run_cli('help', ['--help'], 0, ['Usage: lab_2.exe a c d'])
    run_cli('leading plus and zeros', ['+0012', '0030', '+0005'], 0, ['Quotient: 16'])
    run_cli('negative zero', ['-0', '30', '5'], 0, ['Quotient: -32'])
    invalid = [[], ['12'], ['12', '30'], ['12', '30', '5', '6'], ['', '30', '5'],
               ['+', '30', '5'], ['--1', '30', '5'], ['1x', '30', '5'],
               ['1.5', '30', '5'], [' 12', '30', '5'], ['12 ', '30', '5'],
               [str(HIGH + 1), '30', '5'], [str(LOW - 1), '30', '5'],
               ['12', str(HIGH + 1), '5'], ['12', '30', str(LOW - 1)],
               ['１２', '30', '5'], ['12', '30', '5\n'], ['--help', '1', '2']]
    for i, args in enumerate(invalid, 1):
        run_cli(f'invalid input {i}', args, 2, ['Error:', 'Usage:'])
    return {'status': 'PASS', 'arithmetic_cases': total, 'seed': 20261121,
            'outcomes': totals, 'case_digest_sha256': digest.hexdigest(),
            'named_cases': named, 'cli_cases': len(cli_results), 'cli_results': cli_results}


def main():
    assert os.name == 'nt', 'These execution checks require the Windows runner.'
    result = {'lab1': check_lab1(), 'lab2': check_lab2()}
    (BUILD / 'test_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (BUILD / 'lab1_data.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result['lab1']['declarations'][0]))
        writer.writeheader()
        writer.writerows(result['lab1']['declarations'])
    print('PASS: Lab 1:', result['lab1']['declarations_checked'], 'declarations, 78 bytes.')
    print('PASS: Lab 2:', result['lab2']['arithmetic_cases'], 'arithmetic cases and',
          result['lab2']['cli_cases'], 'command-line cases.')


if __name__ == '__main__':
    main()
