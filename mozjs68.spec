%global major 0
%define libname %mklibname mozjs %major
%define devname %mklibname -d mozjs
%global major 68

# LTO - Enable in Release builds, but consider disabling for development as it increases compile time
%global build_with_lto    1

%if 0%{?build_with_lto}
%global optflags        %{optflags} -flto
%global build_ldflags   %{build_ldflags} -flto
%endif

# Require libatomic for ppc
%ifarch ppc
%global system_libatomic 1
%endif

# Big endian platforms
%ifarch ppc ppc64 s390 s390x
%global big_endian 1
%endif

Name:           mozjs%{major}
Version:        68.5.0
Release:        %mkrel 2
Summary:        SpiderMonkey JavaScript library
Group:          Development/Other
License:        MPLv2.0 and MPLv1.1 and BSD and GPLv2+ and GPLv3+ and LGPLv2+ and AFL and ASL 2.0
URL:            https://developer.mozilla.org/en-US/docs/Mozilla/Projects/SpiderMonkey
Source0:        https://ftp.mozilla.org/pub/firefox/releases/%{version}esr/source/firefox-%{version}esr.source.tar.xz

# Patches from Debian mozjs60, rebased for mozjs68:
Patch01:        fix-soname.patch
Patch02:        copy-headers.patch
Patch03:        tests-increase-timeout.patch
Patch09:        icu_sources_data.py-Decouple-from-Mozilla-build-system.patch
Patch10:        icu_sources_data-Write-command-output-to-our-stderr.patch

# Build fixes - https://hg.mozilla.org/mozilla-central/rev/ca36a6c4f8a4a0ddaa033fdbe20836d87bbfb873
Patch12:        emitter.patch
Patch13:        emitter_test.patch

# Build fixes
Patch14:        init_patch.patch
# TODO: Check with mozilla for cause of these fails and re-enable spidermonkey compile time checks if needed
Patch15:        spidermonkey_checks_disable.patch

# armv7 fixes
Patch16:        rust_armv7.patch
Patch17:        armv7_disable_WASM_EMULATE_ARM_UNALIGNED_FP_ACCESS.patch

# Patches from Fedora firefox package:
Patch26:        build-icu-big-endian.patch

# Support Python 3 in js tests
Patch30:        jstests_python-3.patch

# (tv) don't check for cmov support when running on older CPUs
Patch1000:      bypass-cmov-assert-on-i586.patch
# (tv) fix building i586 with rust
Patch1001:      force-i586-host.patch

BuildRequires:  autoconf2.1
BuildRequires:  cargo
BuildRequires:  clang-devel
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  llvm
BuildRequires:  llvm-devel
BuildRequires:  perl-devel
BuildRequires:  pkgconfig(libffi)
BuildRequires:  pkgconfig(zlib)
# Build requires Python 2, tests are patched to run with Python 3
BuildRequires:  python2-devel
BuildRequires:  python3-devel
BuildRequires:  python3-six
BuildRequires:  readline-devel
BuildRequires:  rust
BuildRequires:  zip
%if 0%{?system_libatomic}
BuildRequires:  libatomic
%endif

%description
SpiderMonkey is the code-name for Mozilla Firefox's C++ implementation of
JavaScript. It is intended to be embedded in other applications
that provide host environments for JavaScript.

%package -n %{libname}
Summary:       JavaScript engine library
Group:         System/Libraries

%description -n %{libname}
JavaScript is the Netscape-developed object scripting languages. This
package has been created for purposes of Sablotron and is suitable for
embedding in applications. See http://www.mozilla.org/js for details
and sources.

%package        -n %devname
Summary:        Development files for %{name}
Requires:       %{libname}%{?_isa} = %{version}-%{release}

%description    -n %devname
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.

%prep
%setup -q -n firefox-%{version}/js/src

pushd ../..
%patch01 -p1
%patch02 -p1
%patch03 -p1
%patch09 -p1
%patch10 -p1

%patch12 -p1
%patch13 -p1
%patch14 -p1
%patch15 -p1

%ifarch armv7hl
# Correct armv7hl rust triple seems to be armv7-unknown-linux-gnueabihf and not armv7-unknown-linux-gnueabi
%patch16 -p1
# Disable WASM_EMULATE_ARM_UNALIGNED_FP_ACCESS as it causes the compilation to fail
# https://bugzilla.mozilla.org/show_bug.cgi?id=1526653
%patch17 -p1
%endif

# Patch for big endian platforms only
%if 0%{?big_endian}
%patch26 -p1 -b .icu
%endif

# Execute tests with Python 3
%patch30 -p1

%patch1000 -p1
%patch1001 -p0

# make sure we don't ever accidentally link against bundled security libs
rm -rf security/
popd

# Remove zlib directory (to be sure using system version)
rm -rf ../../modules/zlib

%build
# Prefer GCC, because clang doesn't support -fstack-clash-protection yet
export CC=gcc
export CXX=g++

%if 0%{?build_with_lto}
export AR=%{_bindir}/gcc-ar
export RANLIB=%{_bindir}/gcc-ranlib
export NM=%{_bindir}/gcc-nm
%endif

export CFLAGS="%{optflags}"
export CXXFLAGS="$CFLAGS"
export LINKFLAGS="%{?__global_ldflags}"
export PYTHON="%{__python2}"

autoconf-2.13
%configure \
  --without-system-icu \
  --enable-posix-nspr-emulation \
  --with-system-zlib \
  --disable-tests \
  --disable-strip \
  --with-intl-api \
  --enable-readline \
  --enable-shared-js \
  --disable-optimize \
  --enable-pie \
  --disable-jemalloc \
  --enable-unaligned-private-values

%if 0%{?big_endian}
echo "Generate big endian version of config/external/icu/data/icud58l.dat"
pushd ../..
  ./mach python intl/icu_sources_data.py .
  ls -l config/external/icu/data
  rm -f config/external/icu/data/icudt*l.dat
popd
%endif

%make_build

%install
%make_install

# Fix permissions
chmod -x %{buildroot}%{_libdir}/pkgconfig/*.pc

# Avoid multilib conflicts
case `uname -i` in
  i386 | ppc | s390 | sparc )
    wordsize="32"
    ;;
  x86_64 | ppc64 | s390x | sparc64 )
    wordsize="64"
    ;;
  *)
    wordsize=""
    ;;
esac

if test -n "$wordsize"
then
  mv %{buildroot}%{_includedir}/mozjs-%{major}/js-config.h \
     %{buildroot}%{_includedir}/mozjs-%{major}/js-config-$wordsize.h

  cat >%{buildroot}%{_includedir}/mozjs-%{major}/js-config.h <<EOF
#ifndef JS_CONFIG_H_MULTILIB
#define JS_CONFIG_H_MULTILIB

#include <bits/wordsize.h>

#if __WORDSIZE == 32
# include "js-config-32.h"
#elif __WORDSIZE == 64
# include "js-config-64.h"
#else
# error "unexpected value for __WORDSIZE macro"
#endif

#endif
EOF

fi

# Remove unneeded files
rm %{buildroot}%{_bindir}/js%{major}-config
rm %{buildroot}%{_libdir}/libjs_static.ajs

# Rename library and create symlinks, following fix-soname.patch
mv %{buildroot}%{_libdir}/libmozjs-%{major}.so \
   %{buildroot}%{_libdir}/libmozjs-%{major}.so.0.0.0
ln -s libmozjs-%{major}.so.0.0.0 %{buildroot}%{_libdir}/libmozjs-%{major}.so.0
ln -s libmozjs-%{major}.so.0 %{buildroot}%{_libdir}/libmozjs-%{major}.so

%check
# Run SpiderMonkey tests
PYTHONPATH=tests/lib %{__python3} tests/jstests.py -d -s -t 1800 --no-progress --wpt=disabled ../../js/src/dist/bin/js%{major} \
%ifnarch %{ix86} x86_64 %{arm} aarch64 ppc ppc64le
;
%else
|| :
%endif

# Run basic JIT tests
PYTHONPATH=tests/lib %{__python3} jit-test/jit_test.py -s -t 1800 --no-progress ../../js/src/dist/bin/js%{major} basic \
%ifnarch %{ix86} x86_64 %{arm} aarch64 ppc ppc64le
;
%else
|| :
%endif

%files -n %libname
%doc README.html
%{_libdir}/libmozjs-%{major}.so.0*

%files -n %devname
%{_bindir}/js%{major}
%{_libdir}/libmozjs-%{major}.so
%{_libdir}/pkgconfig/*.pc
%{_includedir}/mozjs-%{major}/
