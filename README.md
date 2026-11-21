# System Programming - 1

Two UzhNU laboratory works, both variant 1. The programs use Microsoft x64 MASM.

- `lab_1.asm` declares all representable 8-, 16- and 32-bit versions of the eight
  integers derived from X=8354, Y=101 and N=1. The genuine assembler listing is
  checked against the object file's data bytes and symbol offsets.
- `lab_2.asm` calculates `(2*c - d - 23) / (a/4 - 1)` using signed 64-bit integers.
  The calculation, decimal input parsing and console output are all in assembly.

## Build and test

The public GitHub Actions workflow uses the standard `windows-2022` hosted
runner and its preinstalled Microsoft assembler/linker. Standard hosted runner
usage is free in public repositories. The workflow has a public-repository guard,
a 10-minute timeout and read-only repository permissions. It does not use paid
runner labels, Actions caches, artifact uploads, external cloud services or paid
dependencies. Compiled files and test evidence are returned in the normal job log
as a SHA-256-checked ZIP payload.

To reproduce with an existing x64 Visual Studio developer prompt:

```text
python build_remote.py
```

No build tools need to be installed on the local machine when using the workflow.
The reports are generated locally using the document runtime already available.

## Run Lab 2

```text
lab_2.exe 12 30 5
lab_2.exe -7 30 5
lab_2.exe --help
```

The three arguments are `a c d`, in that order. Both divisions truncate toward
zero. The output gives numerator, denominator, quotient and remainder.

Exit codes: 0 success/help; 2 invalid arguments; 3 zero denominator; 4 arithmetic
overflow. Checks apply after each numerator operation in the order `2*c`,
subtract `d`, subtract `23`; cancellation in a later operation does not repair an
earlier overflow. The calculation routine returns status 0, 1 or 2 to its caller
and leaves the result buffer unchanged on failure.

## Reports and review

Each lab has its own PDF report, source and assembler listing. The reports cover
the required workings, implementation, verification and control questions.
`build/` contains the downloaded remote binaries, listings, logs and test records.
The Moodle assignments accept up to five files of 5 MB each. Submission packages
will be prepared for review; no Moodle submission is made by the build workflow.

References:
- [Course](https://moodle.uzhnu.edu.ua/course/view.php?id=1870)
- [Lab 1](https://moodle.uzhnu.edu.ua/mod/assign/view.php?id=25852)
- [Lab 2](https://moodle.uzhnu.edu.ua/mod/assign/view.php?id=25853)
- [GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [ML64 options](https://learn.microsoft.com/en-us/cpp/assembler/masm/ml-and-ml64-command-line-reference)
- [Windows x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention)
