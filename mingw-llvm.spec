# The targets driven by LLVM instead of GCC/binutils, and the tools provided
# for each of them.  Adding a target is a matter of adding it here.
%global llvm_targets aarch64-w64-mingw32

# Targets where GCC and binutils exist and own the <triplet>-* names in
# %%{_bindir}.  These get only the driver names neither of them ships: a
# clang toolchain supplementing the GNU one, not replacing it.
%global clang_targets i686-w64-mingw32 x86_64-w64-mingw32

# Tools which take the place of binutils, packaged apart from the compiler.
# No "rc": %%<target>_env would export RC=llvm-rc, which speaks MSVC options,
# not the -i/-o that libtool and autotools expect.  No "as": it is a clang
# driver and belongs in the compiler package.
%global tools_binutils addr2line ar cxxfilt dlltool ld nm objcopy objdump ranlib readelf size strings strip windres

# Tools which are compiler drivers.
%global tools_compiler as c++ cc clang clang++ cpp g++ gcc

# The compiler drivers for %%clang_targets: only the names mingw-gcc and
# mingw-binutils leave unowned.
%global tools_clang cc clang clang++ cpp

# The runtimes the drivers select are built with this toolchain, so they
# cannot exist the first time it is built.  "--with bootstrap" drops the
# runtime Requires; %%dist appends ~bootstrap, which sorts below the full
# build at the same release.
%bcond_with bootstrap

Name:           mingw-llvm
Version:        1
Release:        2%{?dist}
Summary:        LLVM based cross toolchain drivers for MinGW targets

License:        GPL-2.0-or-later
URL:            http://fedoraproject.org/wiki/MinGW
BuildArch:      noarch

Source0:        COPYING
Source1:        mingw-llvm-wrapper
Source2:        README.md

# For %%check only: the drivers are exercised against the real tools.
# The floor is the major the stack is built and verified with; it moves in
# lockstep with mingw-compiler-rt's version lock on the chroot clang.
BuildRequires:  clang >= 22
BuildRequires:  lld >= 22
BuildRequires:  llvm >= 22


%description
GNU binutils has no usable AArch64 PE/COFF support, so MinGW targets for
Windows on ARM are driven by clang, lld and the llvm-* tools instead of by
mingw-gcc and mingw-binutils.

This package provides the <triplet>-<tool> drivers which map those names onto
the LLVM tools, so that build systems and the %%{<target>_*} rpm macros in
mingw-filesystem find what they expect.

This environment is maintained by the Fedora MinGW SIG at:

  http://fedoraproject.org/wiki/SIGs/MinGW


%package common
Summary:        Files shared by the LLVM based MinGW cross toolchains

%description common
This package contains the driver shared by all LLVM based MinGW cross
toolchains.  It is of no use on its own.


%package -n ucrtarm64-llvm-tools
Summary:        LLVM based cross binary utilities for the Windows on ARM64 target
Requires:       %{name}-common = %{version}-%{release}
Requires:       lld >= 22
Requires:       llvm >= 22

%description -n ucrtarm64-llvm-tools
This package contains the binary utilities (ar, nm, objdump, dlltool,
windres, ...) for the aarch64-w64-mingw32 target, implemented on top of the
llvm-* tools because GNU binutils cannot read AArch64 PE/COFF.

It is the AArch64 counterpart of mingw-binutils-generic, and is what
ucrtarm64-filesystem needs in order to generate dependencies and extract
debug info.  Cross compiling also requires ucrtarm64-clang.


%package -n ucrtarm64-clang
Summary:        LLVM based cross compiler for the Windows on ARM64 target
Requires:       ucrtarm64-llvm-tools = %{version}-%{release}
Requires:       clang >= 22
%if %{without bootstrap}
# A compiler which cannot find stdio.h is not a compiler.  mingw64-gcc and
# ucrt64-gcc both require their target's crt and headers outright, and
# nothing else in the chain pulls the headers in: crt only arrives as a
# side effect of ucrtarm64-compiler-rt's own dependencies.
Requires:       ucrtarm64-crt
Requires:       ucrtarm64-headers
Requires:       ucrtarm64-compiler-rt
Recommends:     ucrtarm64-libcxx
%endif

%description -n ucrtarm64-clang
This package contains the C and C++ cross compiler, the preprocessor and the
assembler for the aarch64-w64-mingw32 target, implemented as clang drivers.

It is the AArch64 counterpart of mingw-gcc.  Note that it selects the LLVM
runtime stack (compiler-rt, libunwind, libc++), as there is no libgcc or
libstdc++ for this target.


%package -n mingw32-clang
Summary:        LLVM based cross compiler for the win32 target
Requires:       %{name}-common = %{version}-%{release}
Requires:       clang >= 22
Requires:       lld >= 22
Requires:       mingw32-crt
Requires:       mingw32-headers
%if %{without bootstrap}
Requires:       mingw32-compiler-rt
Requires:       mingw32-libunwind
%endif

%description -n mingw32-clang
This package contains clang drivers for the i686-w64-mingw32 target,
supplementing the GCC toolchain: only the driver names mingw32-gcc and
mingw32-binutils do not own (cc, clang, clang++, cpp) are provided.

The drivers select the LLVM runtime stack (compiler-rt, libunwind).  C++
additionally needs libc++, which is not yet packaged for this target.


%package -n mingw64-clang
Summary:        LLVM based cross compiler for the win64 target
Requires:       %{name}-common = %{version}-%{release}
Requires:       clang >= 22
Requires:       lld >= 22
Requires:       mingw64-crt
Requires:       mingw64-headers
%if %{without bootstrap}
Requires:       mingw64-compiler-rt
Requires:       mingw64-libunwind
%endif

%description -n mingw64-clang
This package contains clang drivers for the x86_64-w64-mingw32 target,
supplementing the GCC toolchain: only the driver names mingw64-gcc and
mingw64-binutils do not own (cc, clang, clang++, cpp) are provided.

The drivers select the LLVM runtime stack (compiler-rt, libunwind).  C++
additionally needs libc++, which is not yet packaged for this target.


%prep
%setup -q -c -T
cp %{SOURCE0} COPYING
cp %{SOURCE2} README.md


%build
# nothing


%install
mkdir -p %{buildroot}%{_libexecdir}
install -m 755 %{SOURCE1} %{buildroot}%{_libexecdir}/mingw-llvm-wrapper

topdir=$(pwd)
mkdir -p %{buildroot}%{_bindir}
pushd %{buildroot}%{_bindir}
for triplet in %{llvm_targets}; do
  for tool in %{tools_binutils}; do
    ln -s %{_libexecdir}/mingw-llvm-wrapper $triplet-$tool
    echo "%{_bindir}/$triplet-$tool" >> $topdir/filelist-$triplet-tools
  done
  for tool in %{tools_compiler}; do
    ln -s %{_libexecdir}/mingw-llvm-wrapper $triplet-$tool
    echo "%{_bindir}/$triplet-$tool" >> $topdir/filelist-$triplet-compiler
  done
done
for triplet in %{clang_targets}; do
  for tool in %{tools_clang}; do
    ln -s %{_libexecdir}/mingw-llvm-wrapper $triplet-$tool
    echo "%{_bindir}/$triplet-$tool" >> $topdir/filelist-$triplet-compiler
  done
done
popd


%check
# The installed drivers are symlinks to %%{_libexecdir}/mingw-llvm-wrapper,
# which does not exist on the build host until the package is installed, so
# lay the same tree out in the build directory and exercise that.
rm -rf check-bin
mkdir -p check-bin
install -m 755 %{SOURCE1} check-bin/mingw-llvm-wrapper
for triplet in %{llvm_targets}; do
  for tool in %{tools_binutils} %{tools_compiler}; do
    ln -s mingw-llvm-wrapper check-bin/$triplet-$tool
  done
done
for triplet in %{clang_targets}; do
  for tool in %{tools_clang}; do
    ln -s mingw-llvm-wrapper check-bin/$triplet-$tool
  done
done
PATH="$(pwd)/check-bin:$PATH"
export PATH

rc=0

# 1. Every driver is there and runs.
for triplet in %{llvm_targets}; do
  for tool in %{tools_binutils} %{tools_compiler}; do
    case $tool in
      # llvm-dlltool has neither --version nor a successful --help, unlike
      # the binutils one.  It is exercised for real just below instead.
      dlltool) continue ;;
    esac
    if out=$($triplet-$tool --version 2>&1); then
      echo "check: ok    $triplet-$tool --version"
    else
      echo "check: FAIL  $triplet-$tool --version: $out"
      rc=1
    fi
  done
  test -x check-bin/$triplet-dlltool || { echo "check: FAIL  no $triplet-dlltool"; rc=1; }
done
for triplet in %{clang_targets}; do
  for tool in %{tools_clang}; do
    if out=$($triplet-$tool --version 2>&1); then
      echo "check: ok    $triplet-$tool --version"
    else
      echo "check: FAIL  $triplet-$tool --version: $out"
      rc=1
    fi
  done
done

# 1b. dlltool, for real: an import library is what it exists to produce, and
#     ar and nm have to be able to read the AArch64 COFF it produced.
printf 'LIBRARY test.dll\nEXPORTS\ntestfunc\n' > test.def
if aarch64-w64-mingw32-dlltool -d test.def -l libtest.dll.a &&
   aarch64-w64-mingw32-ranlib libtest.dll.a &&
   aarch64-w64-mingw32-ar t libtest.dll.a &&
   aarch64-w64-mingw32-nm --format=posix --defined-only libtest.dll.a; then
  echo "check: ok    dlltool builds an import library ar, ranlib and nm read"
else
  echo "check: FAIL  dlltool/ar/ranlib/nm cannot handle an AArch64 import library"
  rc=1
fi

# 2. libtool decides whether shared libraries are possible by grepping
#    "$LD --help" for auto-import.  ld.lld without -m arm64pe answers with the
#    ELF driver's help, libtool concludes no, and the build quietly produces
#    no DLLs at all.  This is the regression that check exists for.
if aarch64-w64-mingw32-ld --help 2>&1 | grep -e --enable-auto-import; then
  echo "check: ok    ld --help advertises auto-import"
else
  echo "check: FAIL  ld --help does not advertise auto-import"
  rc=1
fi

# 3. The compiler driver targets the right triple.  Linking is impossible
#    until the sysroot exists, so stop at -c, and at -### so nothing runs.
#    Match the "Target:" line exactly: a looser pattern is satisfied by the
#    --sysroot path the wrapper always emits, and asserts nothing.
out=$(aarch64-w64-mingw32-clang -### -c -x c /dev/null 2>&1)
case "$out" in
  *"Target: aarch64-w64-windows-gnu"*)
    echo "check: ok    clang -### targets aarch64-w64-windows-gnu" ;;
  *)
    echo "check: FAIL  clang -### does not target aarch64: $out"
    rc=1 ;;
esac

# 3b. Same for the supplement targets, against the normalised triples clang
#     reports.
for pair in "i686-w64-mingw32 i686-w64-windows-gnu" \
            "x86_64-w64-mingw32 x86_64-w64-windows-gnu"; do
  triplet=$(echo "$pair" | cut -d' ' -f1)
  normalized=$(echo "$pair" | cut -d' ' -f2)
  out=$($triplet-clang -### -c -x c /dev/null 2>&1)
  case "$out" in
    *"Target: $normalized"*)
      echo "check: ok    $triplet-clang -### targets $normalized" ;;
    *)
      echo "check: FAIL  $triplet-clang -### does not target $normalized: $out"
      rc=1 ;;
  esac
done

# 4. The runtime flags are emitted, and emitted before the caller's arguments
#    so that the caller can override them by passing the opposite flag.
trace=$(sh -x check-bin/aarch64-w64-mingw32-clang --version 2>&1 | grep 'exec clang ')
case "$trace" in
  *-rtlib=compiler-rt*-unwindlib=libunwind*--version*)
    echo "check: ok    clang driver flags precede the caller's" ;;
  *)
    echo "check: FAIL  clang driver flags wrong: $trace"
    rc=1 ;;
esac

trace=$(sh -x check-bin/aarch64-w64-mingw32-clang++ --version 2>&1 | grep 'exec clang++ ')
case "$trace" in
  *-rtlib=compiler-rt*-stdlib=libc++*--version*)
    echo "check: ok    clang++ driver flags precede the caller's" ;;
  *)
    echo "check: FAIL  clang++ driver flags wrong: $trace"
    rc=1 ;;
esac

# 4b. The supplement targets select the same LLVM runtime stack: they exist
#     to build against compiler-rt/libunwind, not against libgcc.
for triplet in %{clang_targets}; do
  trace=$(sh -x check-bin/$triplet-clang --version 2>&1 | grep 'exec clang ')
  case "$trace" in
    *-rtlib=compiler-rt*-unwindlib=libunwind*--version*)
      echo "check: ok    $triplet-clang driver flags precede the caller's" ;;
    *)
      echo "check: FAIL  $triplet-clang driver flags wrong: $trace"
      rc=1 ;;
  esac
done

# 5. No <triplet>-rc: it would point RC at llvm-rc, whose MSVC style options
#    libtool's --tag=RC does not speak.
if test -e check-bin/aarch64-w64-mingw32-rc; then
  echo "check: FAIL  an rc driver was installed"
  rc=1
else
  echo "check: ok    no rc driver"
fi

# 6. Package attribution: "as" runs clang, so it belongs to the compiler
#    package.  If it lands in the tools package instead, that package needs
#    clang too, and every buildroot which only wants the dependency
#    generators drags the compiler in with it.
if grep -qxF "%{_bindir}/aarch64-w64-mingw32-as" filelist-aarch64-w64-mingw32-compiler &&
   ! grep -qxF "%{_bindir}/aarch64-w64-mingw32-as" filelist-aarch64-w64-mingw32-tools; then
  echo "check: ok    as is packaged with the compiler drivers"
else
  echo "check: FAIL  as is packaged in the wrong subpackage"
  rc=1
fi

# 7. The tools package must stay pure llvm/lld: no compiler driver may land
#    in its file list.  Test the generated filelist, not the spec against
#    itself.
bad=0
for tool in %{tools_compiler}; do
  if grep -qxF "%{_bindir}/aarch64-w64-mingw32-$tool" filelist-aarch64-w64-mingw32-tools; then
    echo "check: FAIL  $tool is a compiler driver and is in the tools filelist"
    bad=1
    rc=1
  fi
done
if [ "$bad" = 0 ]; then
  echo "check: ok    the tools filelist contains no compiler drivers"
fi

# 8. The supplement targets may only ship names mingw-gcc and mingw-binutils
#    leave unowned; anything else is a file conflict with the GNU toolchain
#    packages.  Test the generated filelists against the allowlist.
for triplet in %{clang_targets}; do
  bad=0
  while read -r path; do
    tool=$(basename "$path" | sed "s/^$triplet-//")
    case " %{tools_clang} " in
      *" $tool "*) ;;
      *)
        echo "check: FAIL  $triplet-$tool conflicts with the GNU toolchain"
        bad=1
        rc=1
        ;;
    esac
  done < filelist-$triplet-compiler
  if [ "$bad" = 0 ]; then
    echo "check: ok    $triplet ships only unowned driver names"
  fi
done

exit $rc


%files common
%license COPYING
%doc README.md
%{_libexecdir}/mingw-llvm-wrapper

%files -n ucrtarm64-llvm-tools -f filelist-aarch64-w64-mingw32-tools

%files -n ucrtarm64-clang -f filelist-aarch64-w64-mingw32-compiler

%files -n mingw32-clang -f filelist-i686-w64-mingw32-compiler

%files -n mingw64-clang -f filelist-x86_64-w64-mingw32-compiler


%changelog
* Mon Aug 24 2026 Erik Berg <fedora@slipsprogrammor.no> - 1-2
- Add mingw32-clang and mingw64-clang: clang drivers supplementing the GNU
  toolchain for the win32 and win64 targets, shipping only the driver names
  mingw-gcc and mingw-binutils leave unowned (cc, clang, clang++, cpp)
- The supplement drivers select compiler-rt and libunwind, like ucrtarm64;
  the bootstrap pass drops those Requires until the runtimes exist

* Thu Aug 06 2026 Erik Berg <fedora@slipsprogrammor.no> - 1-1
- Initial package: aarch64-w64-mingw32 toolchain drivers on clang, lld and
  the llvm-* tools, split into ucrtarm64-llvm-tools and ucrtarm64-clang
- Build with "--with bootstrap" to reproduce the stack bring-up pass, which
  drops the runtime Requires; %%dist appends ~bootstrap, so the full build
  supersedes it at the same release
