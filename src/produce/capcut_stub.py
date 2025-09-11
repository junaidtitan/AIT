import os
def assemble(voice_wavs: list[str], assets: list[str], out_path: str) -> str:
    with open(out_path, "wb") as f:
        f.write(b"FAKE_MP4")
    return out_path
