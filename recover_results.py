"""Recover verified build files from GitHub's downloaded log archive."""
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent


def recover(archive):
    with zipfile.ZipFile(archive) as logs:
        texts = [logs.read(name).decode('utf-8-sig') for name in logs.namelist()
                 if name.endswith('.txt')]
    text = next(t for t in texts if 'SYSPROG_PAYLOAD_BEGIN' in t)
    expected_zip_hash = re.search(r'SYSPROG_ZIP_SHA256=([0-9a-f]{64})', text)[1]
    payload = text.split('SYSPROG_PAYLOAD_BEGIN', 1)[1].split('SYSPROG_PAYLOAD_END', 1)[0]
    chunks = []
    for line in payload.splitlines():
        line = re.sub(r'^\d{4}-\d\d-\d\dT\S+Z\s*', '', line).strip()
        if line:
            assert re.fullmatch(r'[A-Za-z0-9+/=]+', line), 'Unexpected log content'
            chunks.append(line)
    data = base64.b64decode(''.join(chunks), validate=True)
    assert hashlib.sha256(data).hexdigest() == expected_zip_hash, 'ZIP hash mismatch'
    with zipfile.ZipFile(io.BytesIO(data)) as bundle:
        files = {name: bundle.read(name) for name in bundle.namelist()}
    for name in files:
        assert Path(name).name == name and not name.startswith('.'), 'Unsafe archive path'
    hashes = json.loads(files['file_hashes.json'])
    assert set(files) == set(hashes) | {'file_hashes.json'}
    for name, expected in hashes.items():
        assert hashlib.sha256(files[name]).hexdigest() == expected, name
    metadata = json.loads(files['build_metadata.json'])
    assert metadata['status'] == 'PASS', metadata
    for name, expected in metadata['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    output = ROOT / 'build'
    output.mkdir(exist_ok=True)
    for name, content in files.items():
        (output / name).write_bytes(content)
    verification = ROOT / 'verification'
    verification.mkdir(exist_ok=True)
    (verification / 'remote_run_logs.zip').write_bytes(Path(archive).read_bytes())
    (verification / 'downloaded_build.zip').write_bytes(data)
    print('Recovered', len(files), 'files; ZIP and individual SHA-256 checks passed.')
    print('Remote build commit:', metadata['commit'])


if __name__ == '__main__':
    recover(Path(sys.argv[1]))
