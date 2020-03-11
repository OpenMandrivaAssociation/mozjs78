%global pre_release %{nil}
%define pkgname mozjs
%define api 68
%define major 68
%define majorlib 0
%define libmozjs %mklibname %{pkgname} %{api} %{major}
%define libmozjs_devel %mklibname %{pkgname} %{api} -d

# (tpg) optimize a bit
%global optflags %{optflags} -O3

# Big endian platforms
%ifarch ppc ppc64 s390 s390x
%global big_endian 1
%endif

Summary:	JavaScript interpreter and libraries
Name:		mozjs60
Version:	68.5.0
Release:	2
License:	MPLv2.0 and BSD and GPLv2+ and GPLv3+ and LGPLv2.1 and LGPLv2.1+
URL:		https://developer.mozilla.org/en-US/docs/Mozilla/Projects/SpiderMonkey/Releases/%{major}
Source0:        https://ftp.mozilla.org/pub/firefox/releases/%{version}esr/source/firefox-%{version}esr.source.tar.xz
Source10:	http://ftp.gnu.org/gnu/autoconf/autoconf-2.13.tar.gz
# Patches from Debian mozjs52_52.3.1-4.debian.tar.xz:
Patch0001:      fix-soname.patch
Patch0002:      copy-headers.patch
Patch0003:      tests-increase-timeout.patch
#Patch0008:      Always-use-the-equivalent-year-to-determine-the-time-zone.patch
#Patch0009:      icu_sources_data.py-Decouple-from-Mozilla-build-system.patch
Patch0010:      icu_sources_data-Write-command-output-to-our-stderr.patch
Patch0011:      tests-For-tests-that-are-skipped-on-64-bit-mips64-is-also.patch

# Build fixes - https://hg.mozilla.org/mozilla-central/rev/ca36a6c4f8a4a0ddaa033fdbe20836d87bbfb873
Patch12:        emitter.patch
Patch13:        emitter_test.patch
Patch14:        init_patch.patch

# Patches from Fedora firefox package:
Patch26:        build-icu-big-endian.patch

# aarch64 fixes for -O2
Patch30:        Save-x28-before-clobbering-it-in-the-regex-compiler.patch
Patch31:        Save-and-restore-non-volatile-x28-on-ARM64-for-generated-unboxed-object-constructor.patch
Patch32:	firefox-60.2.2-add-riscv64.patch
Patch33:	mozjs-52.8.1-fix-crash-on-startup.patch

#BuildRequires:  autoconf
BuildRequires:	pkgconfig(icu-i18n)
BuildRequires:	pkgconfig(nspr)
BuildRequires:	pkgconfig(libffi)
BuildRequires:	pkgconfig(zlib)
BuildRequires:	pkgconfig(python2)
BuildRequires:	readline-devel
BuildRequires:	zip
BuildRequires:	python

%description
JavaScript is the Netscape-developed object scripting language used in millions
of web pages and server applications worldwide. Netscape's JavaScript is a
super set of the ECMA-262 Edition 3 (ECMAScript) standard scripting language,
with only mild differences from the published standard.

%package -n %{libmozjs}
Provides:	mozjs%{major} = %{EVRD}
Summary:	JavaScript engine library

%description -n %{libmozjs}
JavaScript is the Netscape-developed object scripting language used in millions
of web pages and server applications worldwide. Netscape's JavaScript is a
super set of the ECMA-262 Edition 3 (ECMAScript) standard scripting language,
with only mild differences from the published standard.

%package -n %{libmozjs_devel}
Summary:	Header files, libraries and development documentation for %{name}
Provides:	mozjs%{major}-devel = %{EVRD}
Requires:	%{libmozjs} = %{EVRD}

%description -n %{libmozjs_devel}
This package contains the header files, static libraries and development
documentation for %{name}. If you like to develop programs using %{name},
you will need to install %{name}-devel.

%prep
%setup -q -n firefox-%{version}/js/src -a 10

pushd ../..
%config_update
%patch0001 -p1
%patch0002 -p1
%patch0003 -p1
#patch0008 -p1
#patch0009 -p1
%patch0010 -p1
%patch0011 -p1

%patch12 -p1
%patch13 -p1
%patch14 -p1

# Patch for big endian platforms only
%if 0%{?big_endian}
%patch26 -p1 -b .icu
%endif

# aarch64 -O2 fixes
%ifarch aarch64
%patch30 -p1
%patch31 -p1
%endif
%patch32 -p1
%patch33 -p1

# make sure we don't ever accidentally link against bundled security libs
rm -rf security/
popd

# Remove zlib directory (to be sure using system version)
rm -rf ../../modules/zlib

#rm -rf nsprpub
#cd config/external/
#for i in freetype2 icu nspr nss sqlite zlib; do
#	rm -rf $i
#	mkdir $i
#	touch $i/moz.build
#done
#cd ../..

TOP="$(pwd)"
cd autoconf-2.13
./configure --prefix=$TOP/ac213bin
%make_build
%make install

%build
%setup_compile_flags
# Need -fpermissive due to some macros using nullptr as bool false
export AUTOCONF="`pwd`"/ac213bin/bin/autoconf
export CFLAGS="%{optflags} -fuse-ld=bfd"
export CXXFLAGS="$CFLAGS"
export LDFLAGS="$CFLAGS"
export CC=gcc
export CXX=g++
export LD=ld.bfd

%configure \
  --without-system-icu \
  --enable-posix-nspr-emulation \
  --with-system-zlib \
  --enable-tests \
  --disable-strip \
  --with-intl-api \
  --enable-readline \
  --enable-optimize="-O3" \
  --enable-shared-js \
  --disable-optimize \
  --enable-pie \
  --disable-jemalloc \

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

# Remove unneeded files
rm %{buildroot}%{_bindir}/js%{major}-config
rm %{buildroot}%{_libdir}/libjs_static.ajs

# Rename library and create symlinks, following fix-soname.patch
mv %{buildroot}%{_libdir}/libmozjs-%{major}.so \
   %{buildroot}%{_libdir}/libmozjs-%{major}.so.0.0.0
ln -s libmozjs-%{major}.so.0.0.0 %{buildroot}%{_libdir}/libmozjs-%{major}.so.0
ln -s libmozjs-%{major}.so.0 %{buildroot}%{_libdir}/libmozjs-%{major}.so

%check
# Some tests will fail
tests/jstests.py -d -s --no-progress ../../js/src/js/src/shell/js || :

%files
%{_bindir}/js60

%files -n %{libmozjs}
%{_libdir}/libmozjs-60.so.%{majorlib}*

%files -n %{libmozjs_devel}
%{_libdir}/libmozjs-60.so
%{_libdir}/pkgconfig/*.pc
%{_includedir}/mozjs-%{major}
