# Building OpenShot-CCMagic as a standalone Windows .exe

This documents the full MSYS2/MinGW64 build process used to compile this fork
— including custom `libopenshot` changes and the custom "AI Tools" workflow
system — into a self-contained Windows executable that end users can run
without installing any of this toolchain themselves.

**Time estimate:** 3–5 hours the first time. Once your environment is set
up, rebuilding after code changes takes a few minutes.

---

## Overview: what gets built

1. **libopenshot-audio** — C++ audio library (JUCE-based)
2. **libopenshot** — C++ core video library (your fork, includes custom
   FFmpeg-9-compatibility patches and ImageMagick 7 linking fixes)
3. **Python bindings** (`openshot.py` + `_openshot.pyd`) — SWIG-generated,
   produced as part of the libopenshot build
4. **openshot-qt** — the Python/PyQt5 GUI application (your fork)
5. **Frozen .exe** — cx_Freeze packages steps 3+4 plus every runtime
   dependency into a standalone folder, runnable with zero installed
   prerequisites

---

## Part 1: Environment setup

### Install MSYS2
Download from https://www.msys2.org/ and install.

**Critical:** all commands below run inside the **MSYS2 MinGW64** shell
specifically — not "MSYS2 MSYS", not "MSYS2 UCRT64". Launch it by name from
the Start Menu. Verify you're in the right one:

```bash
echo $MSYSTEM
# must print: MINGW64
```

Mixing shells is the single most common source of confusing errors in this
process — wrong Python, wrong toolchain, path translation failures. If
anything behaves strangely, check this first.

### Update packages and install the toolchain

```bash
pacman -Syu
# close/reopen the shell if prompted after a core update, then:

pacman -S --needed --noconfirm \
  base-devel mingw-w64-x86_64-toolchain \
  mingw-w64-x86_64-ffmpeg mingw-w64-x86_64-qt5 mingw-w64-x86_64-python-pyqt5 \
  mingw-w64-x86_64-swig mingw-w64-x86_64-cmake mingw-w64-x86_64-doxygen \
  mingw-w64-x86_64-python-pip mingw-w64-x86_64-zeromq mingw-w64-x86_64-python-pyzmq \
  mingw-w64-x86_64-ninja mingw-w64-x86_64-catch \
  mingw-w64-x86_64-python-pyopengl mingw-w64-x86_64-python-pyopengl-accelerate \
  mingw-w64-x86_64-imagemagick mingw-w64-x86_64-python-cx-freeze mingw-w64-x86_64-cppzmq \
  git
```

**Do not** use `pacman -S python` (bare, no `mingw-w64-x86_64-` prefix) —
that installs a separate MSYS-layer Python with a different ABI than the
MinGW one everything else here is built against. If you accidentally end up
with the wrong Python on your `PATH`, check with:

```bash
which python
python -c "import sys; print(sys.base_prefix)"
# should print something ending in /mingw64, NOT /usr
```

### Get the ASIO SDK
`libopenshot-audio` requires it at build time even if you don't need
ASIO-class low-latency audio drivers — it's a JUCE compile-time requirement.

1. Register (free) and download from https://www.steinberg.net/developers/
2. Extract somewhere permanent, e.g. `~/ASIOSDK`
3. Set it in your shell (add to `~/.bashrc` in MSYS2 to persist):
   ```bash
   export ASIO_ROOT=~/ASIOSDK
   ```

### Create your Python virtual environment

```bash
cd ~
/mingw64/bin/python3 -m venv --system-site-packages .venv_freeze
source .venv_freeze/bin/activate
```

`--system-site-packages` is required — it lets your venv see the
system-installed PyQt5, pyzmq, cx_Freeze, etc. from the pacman packages
above, instead of needing (and often failing) to `pip install` them
separately. Several packages this project needs (`PyQt5`, `cx_Freeze`, `lief`
via cx_Freeze) don't have prebuilt wheels for MSYS2's Python platform tag, so
pip-installing them from scratch fails — system packages avoid that.

---

## Part 2: Build libopenshot-audio

```bash
mkdir ~/openshot_ccmagic && cd ~/openshot_ccmagic
git clone https://github.com/ccmagic-io/libopenshot-audio.git
cd ~/openshot_ccmagic/libopenshot-audio
rm -rf build
mkdir build && cd build
cmake -G "MinGW Makefiles" -DASIO_ROOT="$ASIO_ROOT" -DCMAKE_INSTALL_PREFIX=/mingw64 ../
mingw32-make
mingw32-make install
```

`-DCMAKE_INSTALL_PREFIX=/mingw64` avoids needing admin rights (the default
install location is under `C:\Program Files`, which requires elevation) and
also means `libopenshot` will auto-find it later with no extra flags.

---

## Part 3: Build libopenshot (your fork)

```bash
cd ~/openshot_ccmagic
git clone https://github.com/ccmagic-io/libopenshot.git
cd ~/openshot_ccmagic/libopenshot
rm -rf build
mkdir build && cd build
cmake -G "MinGW Makefiles" -DCMAKE_INSTALL_PREFIX=/mingw64 \
  -DImageMagick_INCLUDE_DIRS=/mingw64/include/ImageMagick-7 \
  -DImageMagick_Magick++_LIBRARY=/mingw64/lib/libMagick++-7.Q16HDRI.dll.a \
  -DImageMagick_MagickCore_LIBRARY=/mingw64/lib/libMagickCore-7.Q16HDRI.dll.a \
  -DPYTHON_LIBRARY="C:/msys64/mingw64/lib/libpython3.14.dll.a" \
  -DASIO_ROOT="$ASIO_ROOT" \
  ../
```

Adjust `libpython3.14.dll.a` to match your actual installed version — check
with `ls /mingw64/lib | grep libpython`.

Build **only the Python bindings target** (skips the unit test suite, which
has an unrelated pre-existing bug referencing a missing `InvalidJSON`
exception class as of this writing):

```bash
mingw32-make pyopenshot
```

If you want the full `mingw32-make install` (registers `libopenshot.dll` etc.
system-wide in `/mingw64`), that's fine too, just be aware `mingw32-make`
(no target) or `mingw32-make install` alone will also try to build the
broken tests unless that's fixed upstream by the time you read this.

### Get the bindings and core DLL where Python + Windows can find them

```bash
cp ~/openshot_ccmagic/libopenshot/build/bindings/python/openshot.py \
   ~/openshot_ccmagic/libopenshot/build/bindings/python/_openshot.pyd \
   ~/.venv_freeze/lib/python3.14/site-packages/

cp ~/openshot_ccmagic/libopenshot/build/src/libopenshot.dll /mingw64/bin/
```

(The second copy matters — `_openshot.pyd` depends on `libopenshot.dll` at
import time, and `mingw32-make pyopenshot` alone doesn't install it anywhere
on the search path.)

Verify:
```bash
python -c "import openshot; print(openshot.OPENSHOT_VERSION_FULL)"
```

---

## Part 4: Run openshot-qt from source (sanity check before freezing)

```bash
cd ~/openshot_ccmagic
git clone https://github.com/ccmagic-io/openshot-qt.git
pip install requests distro defusedxml sentry-sdk certifi chardet urllib3
python src/launch.py
```

If this opens the app with your changes visible, you're ready to freeze it
into a distributable `.exe`.

---

## Part 5: Freeze into a standalone .exe

`openshot-qt` ships its own `freeze.py` (cx_Freeze-based) for this. It needs
a few patches to work with current cx_Freeze (8.6.4) — the version in this
project's comments/history targets an older cx_Freeze API.

### Run the freeze

```bash
rm -rf openshot_qt build   # clean slate — stale state causes confusing errors
python freeze.py build
```

If `rm -rf build` ever fails with "Device or resource busy", a previous run
of the frozen `.exe` is still holding a file lock — close any Windows `cmd`
window that ran it (and check no Explorer window/antivirus scan has that
folder open) before retrying.

### Output

```
build/exe.mingw_x86_64_msvcrt_gnu-3.14/
├── openshot-qt-cli.exe    # console-attached, useful for debugging (shows logs/tracebacks)
├── launch.exe             # windowed, no console
└── lib/                   # bundled Python + all dependencies
```

Test with the console version first — silent failures in `openshot-qt-cli.exe`
show tracebacks that `launch.exe` (no console) would hide entirely.

```bash
cd "build/exe.mingw_x86_64_msvcrt_gnu-3.14"
./openshot-qt-cli.exe
```
(or double-click it / run from `cmd` on the Windows side)

---

## Distributing to end users

The entire `build/exe.mingw_x86_64_msvcrt_gnu-3.14/` folder is
self-contained — no MSYS2, no Python, no Qt install required on the
recipient's machine. Zip it up, or wrap it with an installer tool like [Inno
Setup](https://jrsoftware.org/isinfo.php) for a proper `Setup.exe` with
Start Menu shortcuts.

---

## Troubleshooting quick-reference

| Symptom | Cause |
|---|---|
| `ModuleNotFoundError` for a stdlib module deep in a vendored package's import chain | The vendored package was copied as data files, not traced as real Python by cx_Freeze — add it to `python_packages` and ensure it's importable via `sys.path` at freeze time |
| Dialog/window opens but is empty, no errors in log | Silent failure in a `try/except` block combined with a resource cx_Freeze didn't bundle (dynamically-discovered plugins, `pkgutil.iter_modules()`, resource folders not in `include_files`) |
| `FileNotFoundError` for a `_default.*` or similar config file at a `lib\<folder>\...` path | That resource folder isn't in `freeze.py`'s `src_files`/`include_files` — see the `resource_dirs` loop above |
| `cannot remove ... Device or resource busy` on `rm -rf build` | A previous frozen `.exe` run is still holding a file lock — close it first |
| `NameError: name 'PATH' is not defined` when editing `freeze.py` | Inserted code that references `PATH` before the line that actually defines it — move the insertion later in the file |
| Any command with a `/home/...` or `/mingw64/...` path silently fails or says file not found, but `ls`/bash sees it fine | You're passing an MSYS-mount-style path to a native Windows tool (`cmake`, `mingw32-make`) that doesn't understand MSYS path translation — use the real `C:/msys64/...` path instead |

