from base64 import b64encode
from tempfile import NamedTemporaryFile

import ase


def render_thumbnail(atoms):
    tmp = NamedTemporaryFile()
    ase.io.write(tmp.name, atoms, format="png")
    raw = open(tmp.name, "rb").read()
    tmp.close()
    return b64encode(raw).decode()
