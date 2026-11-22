# Windows helper protocol

Experimental protocol between a Windows-side capture helper and Draw
running in WSL, for frame capture with trustworthy timestamps — ground
work for a future cursor bridge. Draw consumes it with
`--source tcp://host` + `--helper-token-file`; nothing in the default
path depends on this folder.

- `PROTOCOL.md` — the wire contract: a stream of records (28-byte
  binary header + JPEG payload) over TCP or in a recorded file; the
  consumer cannot tell the two sources apart.
- `windows_helper.py` — the Windows-side sender: DirectShow capture and
  JPEG encoding are implemented and were exercised on a real webcam;
  cursor injection is the untested sketch.
- `../tools/helper_receiver.py` — the WSL-side receiver and recorder
  (`--selfcheck`, `--record`, `--dump`). Uses `draw.infra.safe_io` for
  bounded JPEG decoding.

If the helper is not running, nothing changes on the default path:
Draw captures from the camera as usual (local webcam,
`hvcam+reverse://` with `hvcam-host.exe --reverse`, or a network URL —
see `--source`). An explicit `--source tcp://host` fails with an error
when the helper is not listening — there is no automatic fallback to
another camera.
