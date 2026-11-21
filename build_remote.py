"""Build with preinstalled Microsoft tools, test, and return evidence in run logs.

No package installs, caches or Actions artifacts are used. Run from an x64
Visual Studio developer command prompt, or via the included public workflow.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import textwrap
import zipfile

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'


def run(command, filename):
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                          errors='replace', timeout=90)
    log = '$ ' + subprocess.list2cmdline(command) + '\n' + proc.stdout + proc.stderr
    (BUILD / filename).write_text(log, encoding='utf-8')
    print(log)
    if proc.returncode:
        raise RuntimeError(f'{command[0]} failed with exit code {proc.returncode}')


def package_results():
    # Return files through normal job logs, not billable artifact storage.
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(BUILD.iterdir()) if p.is_file()}
    (BUILD / 'file_hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(BUILD.iterdir()):
            if path.is_file():
                bundle.writestr(path.name, path.read_bytes())
    data = buffer.getvalue()
    print('SYSPROG_ZIP_SHA256=' + hashlib.sha256(data).hexdigest())
    print('SYSPROG_PAYLOAD_BEGIN')
    for chunk in textwrap.wrap(base64.b64encode(data).decode('ascii'), 120):
        print(chunk)
    print('SYSPROG_PAYLOAD_END')


def main():
    os.chdir(ROOT)
    BUILD.mkdir(exist_ok=True)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
        assert event['repository']['private'] is False, 'Public repository required'
        assert os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted', 'Standard hosted runner required'
        assert os.environ.get('RUNNER_OS') == 'Windows'
    for tool in ['ml64', 'link', 'dumpbin']:
        if not shutil.which(tool):
            raise RuntimeError(f'{tool} is missing; an x64 developer environment is required')
    source_files = ['lab_1.asm', 'lab_2.asm', 'verify.py', 'build_remote.py',
                    '.github/workflows/build.yml']
    metadata = {
        'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
        'python': sys.version, 'repository': os.environ.get('GITHUB_REPOSITORY'),
        'commit': os.environ.get('GITHUB_SHA'), 'run_id': os.environ.get('GITHUB_RUN_ID'),
        'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'runner_os': os.environ.get('RUNNER_OS'),
        'runner_environment': os.environ.get('RUNNER_ENVIRONMENT'),
        'image_os': os.environ.get('ImageOS'), 'image_version': os.environ.get('ImageVersion'),
        'assembler': shutil.which('ml64'), 'linker': shutil.which('link'),
        'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in source_files},
        'delivery': 'Build evidence encoded in ordinary run logs; no artifact upload or cache.'
    }
    (BUILD / 'build_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    try:
        for lab in ['lab_1', 'lab_2']:
            run(['ml64', '/nologo', '/W3', '/WX', '/Sa', '/Flbuild/' + lab + '.lst',
                 '/Fobuild/' + lab + '.obj', '/c', lab + '.asm'], lab + '_assemble.txt')
            libraries = ['kernel32.lib'] + (['shell32.lib'] if lab == 'lab_2' else [])
            run(['link', '/nologo', '/WX', '/MACHINE:X64', '/SUBSYSTEM:CONSOLE',
                 '/ENTRY:WinMain', '/DYNAMICBASE', '/NXCOMPAT',
                 '/OUT:build/' + lab + '.exe', 'build/' + lab + '.obj', *libraries],
                lab + '_link.txt')
        run(['link', '/nologo', '/WX', '/DLL', '/NOENTRY', '/MACHINE:X64',
             '/DYNAMICBASE', '/NXCOMPAT', '/EXPORT:calculate_expression',
             '/OUT:build/lab_2.dll', 'build/lab_2.obj', 'kernel32.lib', 'shell32.lib'],
            'lab_2_dll_link.txt')
        run(['dumpbin', '/nologo', '/headers', '/symbols', 'build/lab_1.obj'],
            'lab_1_object_dump.txt')
        run(['dumpbin', '/nologo', '/disasm', 'build/lab_2.obj'], 'lab_2_disassembly.txt')
        run([sys.executable, 'verify.py'], 'verification.txt')
        metadata['status'] = 'PASS'
    except Exception as error:
        metadata['status'] = 'FAIL'
        metadata['error'] = str(error)
        raise
    finally:
        (BUILD / 'build_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        package_results()


if __name__ == '__main__':
    main()
