mingw-llvm
==========

LLVM based cross toolchain drivers for MinGW targets.

Why
---

GNU binutils has no usable AArch64 PE/COFF support - Fedora's
mingw-binutils-generic 2.46 lists only `pei-i386` and `pei-x86-64` in
`objdump --info`.  There is therefore no ARM64 counterpart to mingw-binutils
or mingw-gcc, and the Windows on ARM64 target has to be driven by clang, lld
and the llvm-* tools instead.

This package provides the `<triplet>-<tool>` drivers which map those names
onto the LLVM tools, in the shape llvm-mingw uses.  Build systems, autotools
configure scripts, the cmake and meson toolchain files, and the
`%{<target>_*}` rpm macros in mingw-filesystem all expect to find tools under
those names, so providing them is what makes the rest of the MinGW packaging
work unchanged.

Packages
--------

| Package | Contents | Requires |
| --- | --- | --- |
| `mingw-llvm-common` | the shared driver | - |
| `ucrtarm64-llvm-tools` | ar, nm, objdump, dlltool, windres, ld, ... | llvm, lld |
| `ucrtarm64-clang` | clang, clang++, cpp, as, cc, c++, gcc, g++ | ucrtarm64-llvm-tools, clang, ucrtarm64-headers, ucrtarm64-crt, ucrtarm64-compiler-rt |
| `mingw32-clang` | clang, clang++, cc | clang, lld, mingw32-headers, mingw32-crt, mingw32-compiler-rt, mingw32-libunwind |
| `mingw64-clang` | clang, clang++, cc | clang, lld, mingw64-headers, mingw64-crt, mingw64-compiler-rt, mingw64-libunwind |

The split mirrors mingw-binutils-generic vs mingw-gcc, and it is not
cosmetic: `ucrtarm64-filesystem` needs the binary utilities in every buildroot
so that the rpm dependency generator and the debuginfo extraction in
mingw-filesystem can read AArch64 PE files, but it has no reason to pull the
compiler drivers in as well.

`as` is in the compiler package rather than the tools one, which is where
binutils would put it, precisely to keep that true: it is a clang driver, so
having it in the tools package would make the tools package require clang,
and every dependency-generating buildroot would install a compiler it never
invokes.

Adding another LLVM driven target is a matter of adding its triplet to
`%llvm_targets` in the spec and adding the matching subpackages.

Supplement targets
------------------

The win32 and win64 targets have a full GNU toolchain, and mingw-gcc and
mingw-binutils own the `<triplet>-*` names in `/usr/bin`.  For those targets
this package ships only the driver names the GNU packages leave unowned -
`cc`, `clang` and `clang++` (`%clang_targets` in the spec) - so both
toolchains install side by side and the GNU one stays the default.  No
`cpp`: mingw-cpp owns `<triplet>-cpp`, and the rpm macros' clang column
preprocesses with `<triplet>-clang -E` instead.  The binary utilities stay
with mingw-binutils, which also supplies the tools LLVM has no counterpart
for (`windmc`).

Like the ARM64 drivers, the supplement drivers select the LLVM runtime stack
(compiler-rt and libunwind); building C++ additionally needs libc++, which is
not yet packaged for these targets.

Tool mapping
------------

| `<triplet>-...` | runs |
| --- | --- |
| `clang`, `cc`, `gcc` | `clang --target=<triplet> --sysroot=<sysroot> -fuse-ld=lld -rtlib=compiler-rt -unwindlib=libunwind` |
| `clang++`, `c++`, `g++` | as above, plus `-stdlib=libc++` |
| `cpp` | `clang ... -E` |
| `as` | `clang ... -c -x assembler` |
| `ld` | `ld.lld -m arm64pe` |
| `dlltool` | `llvm-dlltool -m arm64` |
| `windres` | `llvm-windres --target=<triplet>` |
| `ar`, `ranlib`, `nm`, `objcopy`, `objdump`, `strip`, `strings`, `size`, `addr2line`, `readelf`, `cxxfilt` | `llvm-<tool>` |

`ld` gets the PE emulation because bare `ld.lld` is the ELF driver.  libtool
decides whether shared libraries are possible at all by grepping `$LD --help`
for `auto-import`; with the ELF help text it answers no and builds no DLLs.

`<triplet>-rc` is deliberately absent.  binutils ships `windres` and no `rc`,
so an `rc` driver only serves to make `%<target>_env` point `RC` at
`llvm-rc`, whose MSVC style options (`/fo out.res`) are not what libtool's
`--tag=RC` and every autotools project pass.

`<triplet>-pkg-config` is deliberately absent too: it is a pkgconf symlink
owned by mingw-filesystem, like it is for the other targets.

Overriding the driver's flags
-----------------------------

Every flag the driver adds is emitted **before** the caller's arguments, and
clang takes the last occurrence of an option.  Overriding is therefore done
the ordinary way, by passing the opposite flag on the command line:

    aarch64-w64-mingw32-clang -nostdlib -nodefaultlibs ...
    aarch64-w64-mingw32-clang -rtlib=libgcc ...
    aarch64-w64-mingw32-clang++ -nostdlib++ ...

There is no environment variable and no bootstrap mode in the wrapper.  A
build that cannot link against the runtimes because it *is* the runtimes -
compiler-rt, libunwind, libc++ - passes `-nostdlib`/`-nodefaultlibs` in its
own `CFLAGS`/`LDFLAGS`, exactly as it would with any other compiler.  A cmake
based runtime build will also want
`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`, since the compiler check
cannot link until the runtimes exist.

### Under libtool, spell the override with two dashes

clang accepts `-rtlib=`, `-unwindlib=` and `-stdlib=` with either one dash or
two, and so the two spellings are interchangeable when the driver is invoked
directly.  They are **not** interchangeable under libtool.

`ltmain.sh` classifies every argument it is given and passes only a
whitelisted set through to the link line.  The whitelist carries the two-dash
forms; a one-dash `-unwindlib=none` matches nothing in it, so libtool drops
it silently, links with the driver's own `-unwindlib=libunwind` still in
force, and the failure surfaces much later as unresolved unwinder symbols
rather than as a rejected option.  Write it as:

    ./configure ... LDFLAGS="--unwindlib=none"

An autotools package that overrides the unwinder, the runtime library or the
C++ standard library therefore has to use `--unwindlib=`, `--rtlib=` and
`--stdlib=`.  Anything that drives the compiler itself - cmake, meson, a
plain Makefile, the command line - takes either.

Runtime stack
-------------

There is no libgcc or libstdc++ for these targets, so the drivers select
compiler-rt, libunwind and libc++.

The runtimes are built *with* this toolchain, so they cannot exist the first
time it is built.  A build with `--with bootstrap` drops the
`ucrtarm64-compiler-rt` requirement and the `ucrtarm64-libcxx`
recommendation from `ucrtarm64-clang`, and the `compiler-rt`/`libunwind`
requirements from the supplement packages; the drivers themselves are
identical.  `%dist` appends `~bootstrap` to such a build, so the regular
build supersedes it at the same release number.

The stack is brought up in this order:

    mingw-llvm (bootstrap) -> mingw-headers -> mingw-crt
      -> mingw-compiler-rt -> mingw-libcxx + mingw-winpthreads
        -> mingw-llvm (full)

Status
------

Verified with Fedora's clang/lld/llvm 22:

- `--target=aarch64-w64-mingw32` normalises to `aarch64-w64-windows-gnu`
- the drivers produce `coff-arm64` objects, archives, import libraries and DLLs
- `ar`, `nm`, `objdump`, `dlltool` and `windres` work through the wrappers
- mingw-filesystem's `mingw.req` generates correct `ucrtarm64(*.dll)`
  dependencies from a linked ARM64 DLL

Two LLVM incompatibilities were found and handled in mingw-filesystem:

- `llvm-nm --format=sysv` leaves the Type column empty, so the debuginfo
  helper uses `--format=posix`
- `llvm-objcopy --keep-symbols` is not implemented for COFF, so the helper
  falls back to stripping without it
