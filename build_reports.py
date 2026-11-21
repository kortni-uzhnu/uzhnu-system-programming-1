"""Create both lab reports from the verified remote build evidence."""
from __future__ import annotations
from datetime import datetime
import hashlib
import json
from pathlib import Path
import textwrap
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                               Table, TableStyle, Preformatted, KeepTogether)
from verify import VALUES, TYPES, fits

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
REPORTS = ROOT / 'reports'
REPORTS.mkdir(exist_ok=True)
META = json.loads((BUILD / 'build_metadata.json').read_text(encoding='utf-8'))
TEST = json.loads((BUILD / 'test_results.json').read_text(encoding='utf-8'))
assert META['status'] == TEST['lab1']['status'] == TEST['lab2']['status'] == 'PASS'
for name, expected in META['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
HASHES = json.loads((BUILD / 'file_hashes.json').read_text(encoding='utf-8'))
for name, expected in HASHES.items():
    assert hashlib.sha256((BUILD / name).read_bytes()).hexdigest() == expected, name

FONT = Path('C:/Windows/Fonts')
for name, file in [('Body', 'times.ttf'), ('Bold', 'timesbd.ttf'),
                   ('Italic', 'timesi.ttf'), ('Code', 'consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT / file)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Bold', italic='Italic')
INK = colors.HexColor('#183c53')
GREY = colors.HexColor('#e9eff3')
styles = {
    'body': ParagraphStyle('body', fontName='Body', fontSize=11, leading=14,
                           spaceAfter=8),
    'small': ParagraphStyle('small', fontName='Body', fontSize=9, leading=11.5,
                            spaceAfter=7),
    'title': ParagraphStyle('title', fontName='Bold', fontSize=21, leading=26,
                            alignment=TA_CENTER, spaceAfter=16, textColor=INK),
    'center': ParagraphStyle('center', fontName='Body', fontSize=12, leading=17,
                             alignment=TA_CENTER, spaceAfter=12),
    'h1': ParagraphStyle('h1', fontName='Bold', fontSize=15, leading=19,
                         spaceAfter=12, textColor=INK, keepWithNext=True),
    'h2': ParagraphStyle('h2', fontName='Bold', fontSize=11, leading=14,
                         spaceBefore=8, spaceAfter=8, keepWithNext=True),
    'cell': ParagraphStyle('cell', fontName='Body', fontSize=9, leading=11),
    'cellsmall': ParagraphStyle('cellsmall', fontName='Body', fontSize=8, leading=10),
    'code': ParagraphStyle('code', fontName='Code', fontSize=8.0, leading=10.3,
                           spaceAfter=8),
    'listing': ParagraphStyle('listing', fontName='Code', fontSize=6.5, leading=8.3),
}


def p(story, text, style='body'):
    story.append(Paragraph(text, styles[style]))


def heading(story, text, level=1):
    p(story, text, 'h1' if level == 1 else 'h2')


def table(story, headers, rows, widths=None, small=False):
    style = styles['cellsmall' if small else 'cell']
    cells = [[Paragraph('<b>' + escape(str(v)) + '</b>', style) for v in headers]]
    cells += [[Paragraph(escape(str(v)).replace('\n', '<br/>'), style) for v in row]
              for row in rows]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GREY),
        ('LINEBELOW', (0, 0), (-1, 0), .7, INK),
        ('LINEBELOW', (0, 1), (-1, -1), .25, colors.HexColor('#c5d0d7')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([t, Spacer(1, 9)])


def code(story, value, listing=False):
    lines = []
    for line in value.expandtabs(4).splitlines():
        lines.extend(textwrap.wrap(line, 115 if listing else 88, replace_whitespace=False,
                                   drop_whitespace=False, break_long_words=True,
                                   break_on_hyphens=False) or [''])
    story.append(Preformatted('\n'.join(lines), styles['listing' if listing else 'code']))


def page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFont('Body', 8)
    canvas.setFillColor(INK)
    if doc.page > 1:
        canvas.drawString(20 * mm, height - 13 * mm, 'System Programming - 1 | Variant 1')
        canvas.setStrokeColor(colors.HexColor('#c5d0d7'))
        canvas.line(20 * mm, height - 15 * mm, width - 20 * mm, height - 15 * mm)
    canvas.drawString(20 * mm, 12 * mm, 'Kortni Shields Scully | UzhNU | 2026')
    canvas.drawRightString(width - 20 * mm, 12 * mm, str(doc.page))
    canvas.restoreState()


def cover(story, number, title):
    story.append(Spacer(1, 17 * mm))
    p(story, 'MINISTRY OF EDUCATION AND SCIENCE OF UKRAINE', 'center')
    p(story, 'UZHHOROD NATIONAL UNIVERSITY', 'center')
    p(story, 'Faculty of Engineering and Technology<br/>'
             'Department of Computer Systems and Networks', 'center')
    story.append(Spacer(1, 30 * mm))
    p(story, 'SYSTEM PROGRAMMING - 1', 'center')
    p(story, f'LABORATORY REPORT {number}', 'title')
    p(story, title, 'title')
    p(story, 'Variant 1', 'center')
    story.append(Spacer(1, 24 * mm))
    p(story, 'Student: Kortni Shields Scully', 'center')
    story.append(Spacer(1, 28 * mm))
    p(story, 'Uzhhorod - 2026', 'center')
    story.append(PageBreak())


def bin_groups(value, width):
    raw = f'{value % (1 << width):0{width}b}'
    return ' '.join(raw[i:i+4] for i in range(0, len(raw), 4))


def listing_appendix(story, lab):
    text = (BUILD / (lab + '.lst')).read_text(encoding='utf-8', errors='replace')
    # Keep the original listing alongside the PDF; this copy wraps long lines.
    text = text.replace('\f', '\n').expandtabs(4)
    lines = []
    for line in text.splitlines():
        lines.extend(textwrap.wrap(line, 115, replace_whitespace=False,
                                   drop_whitespace=False, break_long_words=True,
                                   break_on_hyphens=False) or [''])
    for i in range(0, len(lines), 69):
        story.append(PageBreak())
        heading(story, 'Appendix. Microsoft assembler listing' +
                (f' (continued {i // 69})' if i else ''))
        if i == 0:
            p(story, 'Generated by the actual remote ML64 assembly. Source, offsets, '
                     'machine encodings and the symbol table are reproduced below. '
                     'Long lines wrap for readability; the companion .lst file is unchanged.', 'small')
        story.append(Preformatted('\n'.join(lines[i:i+69]), styles['listing']))


def verification(story, lab_number):
    heading(story, 'Build and verification')
    p(story, 'The source was assembled and linked on a standard GitHub-hosted '
             'Windows Server 2022 x64 runner. Microsoft Macro Assembler 14.44.35230.0 '
             'generated the listing. The build used /W3 /WX, and linking used /WX. '
             'Both executables use Windows system libraries and require no separate '
             'C++ runtime or MASM support package.')
    table(story, ['Item', 'Recorded result'], [
        ('Remote run', '44929971317, attempt 1 - passed'),
        ('Build time (UTC)', META['utc'].split('.')[0].replace('T', ' ')),
        ('Runner image', META['image_os'] + ' / ' + META['image_version']),
        ('Target', 'AMD64 / Windows console executable'),
        ('Source commit', META['commit']),
    ], [37 * mm, 133 * mm])
    if lab_number == 1:
        p(story, '<b>Observed result:</b> all 30 declarations and all 78 data bytes '
                 'matched the independent expected values. All 18 out-of-range formats '
                 'were excluded. The linked executable exited successfully with code 0.')
        p(story, 'Verification reads the COFF section and symbol tables from lab_1.obj. '
                 'It compares each symbol offset and each little-endian byte sequence '
                 'with values calculated independently in Python. It also checks the '
                 'data_begin/data_end span and that every declaration appears in the '
                 'assembler listing. This checks assembled data rather than trusting '
                 'the source comments or a handwritten listing.')
    else:
        t = TEST['lab2']
        p(story, f'<b>Observed result:</b> {t["arithmetic_cases"]:,} arithmetic calls '
                 f'and {t["cli_cases"]} executable command-line cases passed. '
                 'The same lab_2.obj was linked into the console executable and a test DLL.')
        table(story, ['Arithmetic outcome', 'Cases'], [
            ('Successful quotient and remainder', t['outcomes']['success']),
            ('Zero denominator correctly rejected', t['outcomes']['zero_denominator']),
            ('Overflow correctly rejected', t['outcomes']['overflow']),
        ], [125 * mm, 45 * mm])
        p(story, 'The independent reference uses Python arbitrary-precision integers '
                 'with explicit truncation toward zero and int64 range checks. Each '
                 'successful call checks the quotient, remainder, numerator and '
                 'denominator. It also checks N = Q*D + R, |R| &lt; |D| and the '
                 'remainder sign. Guard values detect writes outside the output buffer; '
                 'error cases must leave all four output fields unchanged.')
    p(story, 'The downloaded ZIP and every contained file were checked with SHA-256. '
             'The source hashes recorded on the runner match the local files used for '
             'this report. Detailed evidence is saved in build/test_results.json, '
             'build/build_metadata.json and the original remote run logs.', 'small')
    code(story, f'lab_{lab_number}.asm SHA-256:\n' + META['source_sha256'][f'lab_{lab_number}.asm'])
    p(story, 'Run: https://github.com/kortni-uzhnu/uzhnu-system-programming-1/'
             'actions/runs/44929971317', 'small')


def lab1():
    s = []
    cover(s, 1, 'Internal Representation<br/>of Integer Data')
    heading(s, '1. Task and initial values')
    p(s, 'Convert the eight variant values from decimal to binary and hexadecimal. '
         'Show their machine representation in every signed or unsigned type whose '
         'range contains the value. Declare the numbers in lab_1.asm, generate '
         'lab_1.lst with Microsoft ML64, and check the translation.')
    p(s, '<b>Initial values:</b> X = 8354, Y = 101, N = 1.')
    names = ['X+N', 'X-N', '-X-N', '-X+N', 'Y+N', 'Y-N', '-Y-N', '-Y+N']
    table(s, ['Expression', 'Substitution', 'Decimal result'], [
        (names[i], ['8354+1', '8354-1', '-8354-1', '-8354+1',
                    '101+1', '101-1', '-101-1', '-101+1'][i], value)
        for i, (_, value) in enumerate(VALUES)
    ], [40 * mm, 65 * mm, 65 * mm])
    heading(s, '2. Types and representation ranges')
    p(s, 'The widths follow the laboratory handout and its DB/DW/DD listing: '
         'Byte and ShortInt are 8 bits; Word and Integer are 16 bits; '
         'LongWord and LongInt are 32 bits. These are the handout\'s names, '
         'not assumptions about the size of a modern C++ int or long.')
    table(s, ['Type', 'Bits', 'Range', 'Directive'], [
        ('Byte', 8, '0 to 255', 'DB'), ('ShortInt', 8, '-128 to 127', 'DB'),
        ('Word', 16, '0 to 65,535', 'DW'), ('Integer', 16, '-32,768 to 32,767', 'DW'),
        ('LongWord', 32, '0 to 4,294,967,295', 'DD'),
        ('LongInt', 32, '-2,147,483,648 to 2,147,483,647', 'DD'),
    ], [27 * mm, 15 * mm, 108 * mm, 20 * mm])
    s.append(PageBreak())
    heading(s, '3. Applicable formats')
    table(s, ['Value', 'Byte', 'ShortInt', 'Word', 'Integer', 'LongWord', 'LongInt'], [
        [value] + [('Yes' if fits(value, w, signed) else 'No') for _, w, signed in TYPES]
        for _, value in VALUES
    ], [23 * mm] + [24.5 * mm] * 6, small=True)
    p(s, 'All four X-based values need at least a signed 16-bit format. The '
         'positive Y-based values fit all six types; the negative Y-based values '
         'fit the three signed types. Negative values have no unsigned representation '
         'as the same mathematical number, so they are not declared in unsigned groups.')
    heading(s, '4. Decimal-to-binary conversion method')
    p(s, 'Repeatedly divide the positive magnitude by two, recording the quotient '
         'and remainder. Read the remainders from bottom to top to obtain the binary '
         'magnitude. Group binary digits in fours to obtain hexadecimal digits.')
    p(s, 'For a negative number, first pad the positive magnitude to the selected '
         'width, invert every bit, then add one. This forms the two\'s-complement '
         'machine encoding. The sign-and-magnitude-looking value, for example '
         '-10000010100011b, describes the mathematical number and is not the '
         'stored two\'s-complement bit pattern.')
    p(s, 'The next four pages give the division protocol for each distinct magnitude '
         'and the complete signed conversion for its corresponding negative value. '
         'Together they cover all eight variant values.')
    for positive, pos_expr, neg_expr in [(8355, 'X+N', '-X-N'), (8353, 'X-N', '-X+N'),
                                         (102, 'Y+N', '-Y-N'), (100, 'Y-N', '-Y+N')]:
        s.append(PageBreak())
        heading(s, f'Conversion protocol: {positive} and {-positive}')
        p(s, f'<b>{pos_expr} = {positive}; {neg_expr} = {-positive}.</b>')
        rows = []
        current = positive
        while current:
            quotient, remainder = divmod(current, 2)
            rows.append((current, 2, quotient, remainder))
            current = quotient
        table(s, ['Dividend', 'Divisor', 'Quotient', 'Remainder'], rows,
              [48 * mm, 27 * mm, 48 * mm, 47 * mm])
        p(s, f'Reading upward gives {positive}d = {positive:b}b = {positive:X}h.')
        heading(s, f'Two\'s complement for {-positive}', 2)
        for width in ([16, 32] if positive > 127 else [8, 16, 32]):
            inverted = ((1 << width) - 1) ^ positive
            code(s, f'{width}-bit magnitude: {bin_groups(positive, width)}\n'
                    f'Bit inversion:     {bin_groups(inverted, width)}\n'
                    f'Add one:           {bin_groups(-positive, width)}'
                    f' = {(-positive) % (1 << width):0{width // 4}X}h')
    s.append(PageBreak())
    heading(s, '5. Machine representations')
    p(s, 'The tables show the numeric bit pattern and hexadecimal encoding. '
         'A positive value has the same bits in signed and unsigned formats of '
         'the same width when it fits both. Byte order applies only when these '
         'multi-byte values are stored in memory.')
    for width in [8, 16, 32]:
        if width == 32:
            s.append(PageBreak())
            heading(s, '5. Machine representations (continued)')
        heading(s, f'{width}-bit formats', 2)
        valid = [(n, v) for n, v in VALUES if fits(v, width, True) or fits(v, width, False)]
        rows = []
        for _, value in valid:
            encoded = value % (1 << width)
            rows.append((value, bin_groups(value, width), f'{encoded:0{width // 4}X}',
                         encoded.to_bytes(width // 8, 'little').hex(' ').upper()))
        table(s, ['Decimal', 'Binary', 'Hex', 'Memory bytes'], rows,
              [22 * mm, 87 * mm, 26 * mm, 35 * mm], small=True)
    p(s, 'For example, -8355 in 16 bits is DF5Dh, stored as bytes 5D DF. '
         'In 32 bits it is FFFFDF5Dh, stored as 5D DF FF FF. The high bits '
         'are extended with ones for a negative signed value.')
    p(s, 'The source groups declarations by the six required types. There are '
         '2 Byte, 4 ShortInt, 4 Word, 8 Integer, 4 LongWord and 8 LongInt '
         'declarations: 30 in total, occupying 78 bytes. The PUBLIC labels '
         'allow each declaration to be checked independently in the object file.')
    s.append(PageBreak())
    heading(s, '6. Assembly and verification')
    code(s, 'ml64 /nologo /W3 /WX /Sa /Flbuild/lab_1.lst '
            '/Fobuild/lab_1.obj /c lab_1.asm\n'
            'link /nologo /WX /MACHINE:X64 /SUBSYSTEM:CONSOLE '
            '/ENTRY:WinMain /DYNAMICBASE /NXCOMPAT '
            '/OUT:build/lab_1.exe build/lab_1.obj kernel32.lib')
    verification(s, 1)
    s.append(PageBreak())
    heading(s, '7. Control questions')
    heading(s, 'Integer data types', 2)
    p(s, 'An integer type fixes the number of bits and whether the bit pattern '
         'is interpreted as signed or unsigned. Unsigned values use all bits for '
         'magnitude. In two\'s complement, the most significant bit has negative '
         'weight. The same 8-bit pattern 9Ah therefore represents unsigned 154 '
         'or signed -102.')
    heading(s, 'Representation ranges', 2)
    p(s, 'For w bits, an unsigned type covers 0 through 2^w - 1; a signed '
         'two\'s-complement type covers -2^(w-1) through 2^(w-1) - 1. '
         'A value outside this range must use a wider type. Truncating -8355 '
         'to one byte would change its mathematical value and would not satisfy '
         'the task.')
    heading(s, 'Data declarations in assembly', 2)
    p(s, 'DB reserves and initializes one byte per item; DW uses two bytes; '
         'DD uses four bytes. Signed decimal initializers are encoded in two\'s '
         'complement. Labels identify addresses rather than introducing a '
         'runtime signedness tag. Arithmetic instructions and operand widths '
         'determine how the stored bits are interpreted. Windows x64 stores '
         'multi-byte integers in little-endian order.')
    heading(s, '8. Conclusion')
    p(s, 'All eight variant values were converted, and every applicable format '
         'was declared. The generated ML64 listing and object-file bytes confirm '
         'the expected encodings. The executable smoke test passed.')
    heading(s, 'References', 2)
    references(s, 1)
    listing_appendix(s, 'lab_1')
    return s


def references(s, number):
    p(s, f'1. UzhNU. System Programming - 1, laboratory {number} task handout. '
         f'https://moodle.uzhnu.edu.ua/mod/assign/view.php?id={25851 + number}', 'small')
    p(s, '2. Microsoft. ML and ML64 command-line reference. '
         'https://learn.microsoft.com/en-us/cpp/assembler/masm/'
         'ml-and-ml64-command-line-reference', 'small')
    p(s, '3. Microsoft. x64 calling convention. '
         'https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention', 'small')
    p(s, '4. Intel. Intel 64 and IA-32 Architectures Software Developer\'s Manual, '
         'Volume 1, data types; instruction reference entries for SAL/SAR, SUB, '
         'CQO and IDIV. Course manual folder: '
         'https://moodle.uzhnu.edu.ua/mod/folder/view.php?id=25849', 'small')


def lab2():
    s = []
    cover(s, 2, 'Calculation of Integer<br/>Arithmetic Expressions')
    heading(s, '1. Task and arithmetic model')
    p(s, 'Implement variant 1 in x64 assembly:')
    code(s, 'Q = (2*c - d - 23) / (a/4 - 1)')
    p(s, 'Inputs a, c and d are signed 64-bit decimal integers. Define the '
         'numerator N = 2*c - d - 23 and denominator D = trunc(a/4) - 1. '
         'Both divisions truncate toward zero. The program prints N, D, '
         'the quotient Q and remainder R. A remainder follows the sign of N.')
    p(s, 'The numerator is evaluated in the stated order. Each intermediate '
         'must fit a signed 64-bit integer. A later cancellation does not repair '
         'an earlier overflow. The program rejects D = 0 and the exceptional '
         'division INT64_MIN / -1. It reports an error instead of allowing a '
         'processor divide exception or returning a wrapped result.')
    table(s, ['Condition', 'Calculation status', 'Executable exit code'], [
        ('Successful calculation', '0', '0'),
        ('Invalid input / argument count', 'Not called', '2'),
        ('Zero denominator', '1', '3'),
        ('Signed arithmetic overflow', '2', '4'),
        ('Help requested', 'Not called', '0'),
    ], [85 * mm, 45 * mm, 40 * mm])
    heading(s, '2. Algorithm')
    p(s, '1. Parse exactly three signed decimal arguments.<br/>'
         '2. Form 2*c with a one-bit arithmetic left shift and check overflow.<br/>'
         '3. Subtract d, then 23, checking overflow after each subtraction.<br/>'
         '4. Divide a by four with the signed rounding correction, then subtract one.<br/>'
         '5. Reject zero D and INT64_MIN / -1.<br/>'
         '6. Sign-extend N, divide by D, and output the quotient and remainder.')
    s.append(PageBreak())
    heading(s, '3. Instructions and implementation')
    table(s, ['Instruction / mechanism', 'Purpose in this variant'], [
        ('SAL RAX, 1 and JO', 'Multiply c by two; reject signed overflow.'),
        ('SUB and JO', 'Evaluate the two numerator subtractions with range checks.'),
        ('TEST / JNS, ADD 3, SAR 2', 'Divide a by four with truncation toward zero.'),
        ('DEC', 'Subtract one to obtain the denominator.'),
        ('CMP / TEST and conditional jumps', 'Reject invalid division before IDIV.'),
        ('CQO', 'Sign-extend the signed numerator from RAX into RDX:RAX.'),
        ('IDIV R11', 'Signed division: quotient in RAX, remainder in RDX.'),
    ], [61 * mm, 109 * mm])
    p(s, '<b>Why the negative bias matters.</b> SAR alone rounds negative values '
         'toward minus infinity. For a = -7, SAR by two alone yields -2, while '
         'signed integer division requires -1. Adding 3 only when a is negative '
         'makes the shift produce truncation toward zero. Adding 3 is safe for '
         'every negative int64 value. The following decrement cannot overflow '
         'because a/4 is strictly inside the int64 endpoints.')
    p(s, '<b>Register interface.</b> calculate_expression receives a in RCX, c in '
         'RDX, d in R8 and the result-buffer pointer in R9. It returns the status '
         'in EAX. The four result fields are quotient, remainder, numerator and '
         'denominator, each eight bytes. It is a leaf procedure and uses only '
         'volatile registers. No output field is written until a successful IDIV.')
    p(s, 'The executable gets UTF-16 command-line arguments using Windows APIs, '
         'checks decimal syntax and int64 limits, calls the assembly calculation, '
         'and prints decimal results with WriteFile. All input, arithmetic and '
         'output code is in lab_2.asm. CommandLineToArgvW and Windows API calls '
         'use the required x64 shadow space and aligned stack.')
    p(s, 'The input parser accumulates an unsigned magnitude, admitting a final '
         'digit of 8 only for a negative INT64_MIN input. Output formatting also '
         'uses unsigned magnitude division, so INT64_MIN can be printed correctly.')
    s.append(PageBreak())
    heading(s, '4. Build and use')
    code(s, 'ml64 /nologo /W3 /WX /Sa /Flbuild/lab_2.lst '
            '/Fobuild/lab_2.obj /c lab_2.asm\n'
            'link /nologo /WX /MACHINE:X64 /SUBSYSTEM:CONSOLE '
            '/ENTRY:WinMain /DYNAMICBASE /NXCOMPAT '
            '/OUT:build/lab_2.exe build/lab_2.obj kernel32.lib shell32.lib')
    p(s, 'Arguments are given in the order a c d. Optional leading + or - signs '
         'and leading zeros are accepted. Empty strings, embedded whitespace, '
         'decimal points, non-ASCII digits, trailing characters and values '
         'outside the signed 64-bit range are rejected.')
    for selected in ['positive exact', 'positive remainder', 'negative numerator',
                     'negative a not divisible by four', 'zero denominator lower']:
        record = next(r for r in TEST['lab2']['cli_results'] if r['name'] == selected)
        heading(s, selected.capitalize(), 2)
        code(s, '> lab_2.exe ' + ' '.join(record['arguments']) + '\n' + record['output'].rstrip()
             + '\nExit code: ' + str(record['exit_code']))
    s.append(PageBreak())
    heading(s, '5. Test cases and observed results')
    p(s, 'The following cases were executed against the assembled function; '
         'each was also checked through the console executable. The complete '
         'record, including console output, is in test_results.json.')
    rows = []
    for record in TEST['lab2']['named_cases'][:14]:
        result = record['result']
        rows.append((record['name'], f'{record["a"]}, {record["c"]}, {record["d"]}',
                     f'Q={result[0]}, R={result[1]}' if result else
                     ('Zero denominator' if record['status'] == 1 else 'Overflow')))
    table(s, ['Case', 'a, c, d', 'Expected = observed'], rows,
          [54 * mm, 66 * mm, 50 * mm], small=True)
    p(s, 'The two division-by-zero examples use a = 4 and a = 7. Every integer '
         'a from 4 through 7 produces trunc(a/4) = 1, so D = 0. Negative '
         'inputs must still use truncation toward zero rather than floor division.')
    s.append(PageBreak())
    heading(s, '5. Test cases (continued)')
    rows = []
    for record in TEST['lab2']['named_cases'][14:]:
        result = record['result']
        rows.append((record['name'], '\n'.join(f'{k}={record[k]}' for k in ['a', 'c', 'd']),
                     f'Q={result[0]}\nR={result[1]}' if result else 'Overflow'))
    table(s, ['Boundary case', 'Inputs', 'Expected = observed'], rows,
          [46 * mm, 67 * mm, 57 * mm], small=True)
    p(s, 'The automated coverage includes all combinations a=-20..20 and '
         'c,d=-4..4 (3,321 cases), all combinations of 18 boundary values '
         '(5,832 cases), 10,000 reproducible random cases in a moderate range '
         'and 10,000 random cases over the full int64 domain, plus 21 named '
         'examples. The random seed is 20261121.')
    p(s, 'The 42 executable tests cover the 21 named cases, help, leading plus '
         'and zeros, negative zero and 18 malformed or out-of-range argument '
         'sets. Exact outputs and process exit codes were checked. No test '
         'was performed by substituting a high-level implementation for the assembly.')
    s.append(PageBreak())
    heading(s, '6. Verification evidence')
    verification(s, 2)
    s.append(PageBreak())
    heading(s, '7. Control question: arithmetic instruction behaviour')
    p(s, 'SAL by one moves bits left, inserts zero at the right and sets OF '
         'when signed multiplication by two is not representable. SUB sets OF '
         'when the signed subtraction overflows. JO branches before an invalid '
         'intermediate is used. SAR copies the sign bit; the negative bias '
         'adapts its rounding to the required signed division rule.')
    p(s, 'IDIV interprets RDX:RAX as a signed dividend. CQO fills RDX with '
         'the sign extension of RAX. The quotient truncates toward zero and '
         'the remainder has the dividend\'s sign. Division by zero or a '
         'nonrepresentable quotient raises a processor divide exception unless '
         'checked first. Both conditions are checked here.')
    p(s, 'CBW and CWD in the task\'s instruction list are the corresponding '
         'smaller-width sign-extension operations. CQO is appropriate for '
         'this 64-bit implementation. ADC/SBB are useful for multiword carry '
         'or borrow; this variant fits the selected single-register arithmetic '
         'model and uses checked SAL and SUB.')
    heading(s, '8. Conclusion')
    p(s, 'The variant expression was implemented entirely in x64 assembly. '
         'Signed rounding, remainder semantics and the exceptional arithmetic '
         'cases were verified against an independent reference. All remote '
         'build, data and executable checks passed.')
    heading(s, 'References', 2)
    references(s, 2)
    listing_appendix(s, 'lab_2')
    return s


def main():
    for number, factory in [(1, lab1), (2, lab2)]:
        path = REPORTS / f'Lab_{number}_Report.pdf'
        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=20 * mm,
                                leftMargin=20 * mm, topMargin=22 * mm,
                                bottomMargin=20 * mm,
                                title=f'System Programming - 1, Lab {number}, Variant 1',
                                author='Kortni Shields Scully')
        doc.build(factory(), onFirstPage=page, onLaterPages=page)
        print(path.name, path.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
