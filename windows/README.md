

### 1. Install MSYS2
Download and install from https://www.msys2.org/, then open the **MSYS2 MinGW64** shell
(not the plain MSYS2 shell) for the steps below.

### 2. Set PATH inside the MSYS2 shell
```bash
PATH=$PATH:/c/msys64/mingw64/bin:/c/msys64/mingw64/lib
```

### 3. Update packages
```bash
pacman -Syu
```
(You may need to close and reopen the shell if it asks you to restart after a core update.)

### 4. Install the toolchain and dependencies (64-bit)
```bash
pacman -S --needed --noconfirm \
  base-devel mingw-w64-x86_64-toolchain \
  mingw-w64-x86_64-ffmpeg mingw-w64-x86_64-qt5 mingw-w64-x86_64-python-pyqt5 \
  mingw-w64-x86_64-swig mingw-w64-x86_64-cmake mingw-w64-x86_64-doxygen \
  mingw-w64-x86_64-python-pip mingw-w64-x86_64-zeromq mingw-w64-x86_64-python-pyzmq \
  mingw-w64-x86_64-ninja mingw-w64-x86_64-catch \
  mingw-w64-x86_64-python-pyopengl mingw-w64-x86_64-python-pyopengl-accelerate \
  mingw-w64-x86_64-cppzmq mingw-w64-x86_64-imagemagick \
  python python-pip git
```

### 4b. Download the ASIO SDK
Go to https://www.steinberg.net/developers/prorietary-sdk// and find the ASIO SDK download (free, may require creating a free Steinberg developer account). Download and extract the zip. Set "ASIO_ROOT=C:\msys64\home\<username>\ASIOSDK"
Set ASIO_ROOT variable
```bash
export ASIO_ROOT='~/ASIOSDk'
```

### 5. Install Python pip extras
```bash
python -m venv .venv
source .venv/bin/activate
pip3 install httplib2 slacker tinys3 github3.py requests meson PyOpenGL PyOpenGL-accelerate
```

### 6. Clone the source repos
```bash
mkdir openshot.github && cd openshot.github
git clone https://github.com/OpenShot/libopenshot-audio.git
git clone https://github.com/OpenShot/libopenshot.git
git clone https://github.com/<your-fork>/openshot-qt.git
```

### 7. Build libopenshot-audio first (it's a dependency of libopenshot)
```bash
cd libopenshot-audio
rm -rf build
mkdir build && cd build
cmake -G "MinGW Makefiles" -DASIO_ROOT="$ASIO_ROOT" -DCMAKE_INSTALL_PREFIX=/mingw64 ../
mingw32-make
mingw32-make install
```

### 8. Build libopenshot
```bash
cd ~/openshot/libopenshot/build
rm -rf *
cmake -G "MinGW Makefiles" -DCMAKE_INSTALL_PREFIX=/mingw64 \
  -DImageMagick_INCLUDE_DIRS=/mingw64/include/ImageMagick-7 \
  -DImageMagick_Magick++_LIBRARY=/mingw64/lib/libMagick++-7.Q16HDRI.dll.a \
  -DImageMagick_MagickCore_LIBRARY=/mingw64/lib/libMagickCore-7.Q16HDRI.dll.a \
  -DPYTHON_LIBRARY="C:/msys64/mingw64/lib/libpython3.14.dll.a" \
  -DASIO_ROOT="$ASIO_ROOT" \
  ../
mingw32-make
```
Expect to iterate here — missing dependency errors are common on first attempts. Install
whatever package it's missing and re-run `cmake ../` then `mingw32-make`.

Optional: run the C++ unit tests to confirm your changes didn't break the core:
```bash
mingw32-make test
```

Install it so other tools (and Python) can find it:
```bash
mingw32-make install
```
This installs binaries/headers under `C:\Program Files\openshot\` and installs the Python
bindings (`openshot` module) into your MSYS2 Python's site-packages.

Verify:
```bash
python3 -c "import openshot; print(openshot.OPENSHOT_VERSION_FULL)"
```

### 9. Run your modified openshot-qt against your freshly built libopenshot
```bash
cd ../../openshot-qt
python3 src/launch.py
```

### Notes and gotchas specific to Windows 11
- **Always use the MSYS2 MinGW64 shell**, not PowerShell/cmd, for the pacman/cmake/mingw32-make
  steps — mixing MSVC and MinGW toolchains is the most common source of link errors.
- If `mingw32-make install` for libopenshot doesn't drop `openshot.pyd`/`_openshot*.pyd` where
  your `python3` (the one running `openshot-qt`) can see it, manually add that install path to
  `PYTHONPATH`, same as step 5 in Path A.
- Windows Defender / antivirus sometimes quarantines freshly built `.dll`/`.pyd` files — if an
  import silently fails, check quarantine history.
- If you only changed the SWIG `.i` interface files or C++ signatures that Python calls into,
  you must rebuild `libopenshot` (Path B, steps 8–9) — Path A's prebuilt bindings won't reflect
  those changes.

---

## Quick sanity checklist before reporting a Windows-specific bug
1. `python -c "import openshot"` succeeds with no DLL errors.
2. `openshot.OPENSHOT_VERSION_FULL` matches the version you expect.
3. `python src\launch.py` opens the OpenShot window without traceback in the console.
4. Your specific changed feature behaves the same as it did on Linux.

If steps 1–3 pass but your feature doesn't work only on Windows, that's a genuine
Windows-specific bug worth filing upstream — otherwise it's almost always an environment/PATH
issue rather than your code.

# Building OpenShot (this fork) as a standalone Windows .exe

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
  mingw-w64-x86_64-imagemagick mingw-w64-x86_64-python-cx-freeze \
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
/mingw64/bin/python3 -m venv --system-site-packages .venv
source .venv/bin/activate
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
git clone https://github.com/OpenShot/libopenshot-audio.git ~/openshot/libopenshot-audio
cd ~/openshot/libopenshot-audio
mkdir build && cd build
cmake -G "MinGW Makefiles" -DASIO_ROOT="$ASIO_ROOT" -DCMAKE_INSTALL_PREFIX=/mingw64 ../
mingw32-make
mingw32-make install
openshot-audio-test-sound
```

`-DCMAKE_INSTALL_PREFIX=/mingw64` avoids needing admin rights (the default
install location is under `C:\Program Files`, which requires elevation) and
also means `libopenshot` will auto-find it later with no extra flags.

---

## Part 3: Build libopenshot (your fork)

```bash
git clone <your-fork-url> ~/openshot/libopenshot
cd ~/openshot/libopenshot
```

### Known source patches needed for current FFmpeg/ImageMagick versions

If you're building against a recent MSYS2 FFmpeg (9.x+) and ImageMagick 7,
you'll likely need these patches — they're not upstream yet as of this
writing:

**1. Missing `<cstdint>` include** (`src/AudioLocation.h`) — triggers
`'int64_t' does not name a type` on newer GCC:
```bash
sed -i '1a #include <cstdint>' src/AudioLocation.h
```

**2. FFmpeg 9.x removed several `AVCodec` struct fields**
(`supported_samplerates`, `ch_layouts`, `sample_fmts`, `pix_fmts`) in favor
of `avcodec_get_supported_config()`. `src/FFmpegWriter.cpp`'s
`add_audio_stream()` and `add_video_stream()` need rewriting to use the new
API guarded by `#if LIBAVCODEC_VERSION_MAJOR >= 61`. See the corresponding
sections in this fork's `FFmpegWriter.cpp` for the exact replacement code —
it's a substantial diff, not reproduced here.

**3. ImageMagick 7's CMake detection is broken for MinGW.** CMake's bundled
`FindImageMagick` module can't locate the versioned library names
(`libMagick++-7.Q16HDRI.dll.a` etc.) and only wires `Magick++` into the link
line, missing `MagickCore`/`MagickWand` (needed for symbols like
`ExportImagePixels`, `AcquireExceptionInfo`). Fix in `src/CMakeLists.txt`,
line ~254 — change:
```cmake
target_link_libraries(openshot PUBLIC ImageMagick::Magick++)
```
to (using your actual `/mingw64/lib/...` paths, found via `ls /mingw64/lib |
grep -i magick`):
```cmake
target_link_libraries(openshot PUBLIC ImageMagick::Magick++
    C:/msys64/mingw64/lib/libMagickWand-7.Q16HDRI.dll.a
    C:/msys64/mingw64/lib/libMagickCore-7.Q16HDRI.dll.a)
```
Use full `C:/msys64/...` Windows-style paths here, not `/mingw64/...`
MSYS-shorthand — `mingw32-make` is a native tool and won't resolve MSYS path
mounts.

### Configure and build

```bash
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
cp ~/openshot/libopenshot/build/bindings/python/openshot.py \
   ~/openshot/libopenshot/build/bindings/python/_openshot.pyd \
   ~/.venv/lib/python3.14/site-packages/

cp ~/openshot/libopenshot/build/src/libopenshot.dll /mingw64/bin/
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
git clone <your-openshot-qt-fork-url> ~/openshot/openshot-qt
cd ~/openshot/openshot-qt
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

### Patches needed to freeze.py

**1. cx_Freeze 8.x renamed several `Executable()` kwargs to snake_case, and
removed `target_name` entirely:**
```bash
sed -i \
  -e 's/shortcutName=/shortcut_name=/' \
  -e 's/shortcutDir=/shortcut_dir=/' \
  -e '/targetName=exe_name,/d' \
  freeze.py

# In the second Executable() call (for extra executables), targetName was
# just renamed, not removed:
sed -i "s/targetName=extra_exe\['name'\]/target_name=extra_exe['name']/" freeze.py
```

**2. The Windows GUI base changed name from `Win32GUI` to `gui`:**
```bash
sed -i 's/base = "Win32GUI"/base = "gui"/' freeze.py
```
(There are two `Executable()` calls with `base=...` — check both use the
same variable, or find/replace each occurrence if hardcoded twice.)

**3. Bundle non-Python resource folders.** `freeze.py` as shipped doesn't
know to copy `settings/`, `profiles/`, or other data-only directories under
`src/` — only Python packages get picked up by cx_Freeze's automatic module
tracing. Add this block right after `version_info = {}` (unindented, top
level, so it runs regardless of platform):
```python
resource_dirs = ["blender", "colors", "comfyui", "effects", "emojis",
                  "images", "presets", "profiles", "resources", "settings",
                  "titles", "transitions", "vendor"]
for resource_dir in resource_dirs:
    resource_src = os.path.join(PATH, "src", resource_dir)
    if os.path.isdir(resource_src):
        src_files.append((resource_src, os.path.join("lib", resource_dir)))
```
(`classes`, `windows`, `themes`, `language` are Python packages and get
traced automatically — no action needed for those.)

**4. Force-bundle dynamically-discovered plugin packages.** If your fork
uses `pkgutil.iter_modules()` or similar runtime plugin discovery (this
fork's AI Tools module system does), cx_Freeze's static import scanner can't
see those files — it only bundles what's reachable via literal `import`
statements. Add the package explicitly to `python_packages` (defined near
the top of `freeze.py`, around line 84):
```python
python_packages = ["classes.ai_modules",
                   "os",
                   # ...
```

**5. Vendored third-party packages under `src/vendor/`** (e.g. this fork
bundles its own copy of `yt_dlp`) need the same treatment — cx_Freeze must
be able to *import* them at freeze time to trace their dependencies, not
just copy them as data. Near the top of `freeze.py`, right after `PATH` is
defined:
```python
sys.path.insert(0, os.path.join(PATH, "src", "vendor"))
```
And add the package name to `python_packages` alongside `classes.ai_modules`:
```python
python_packages = ["classes.ai_modules",
                   "yt_dlp",
                   "os",
                   # ...
```
Without this, runtime-only `sys.path` hacks inside your module code (e.g.
`sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
'vendor'))`) don't help — that code runs when the *app* starts, but
`freeze.py` is a separate process that never executes your app code, so it
has no way to find `vendor/`-based imports unless told directly.

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

