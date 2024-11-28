# msan.Dockerfile
# this is to create images with MSAN for BB workers
ARG CLANG_VERSION=15

# Marker to make it possible to build a dev msan builder
# from the nightly clang versions as they are in a differently
# name repo
ENV CLANG_DEV_VERSION=20

WORKDIR /tmp/msan

ENV CC=clang
ENV CXX=clang++
ENV NO_MSAN_PATH=/msan-libs/bin
ENV GDB_PATH=$NO_MSAN_PATH/gdb
ENV MSAN_LIBDIR=/msan-libs
ENV MSAN_SYMBOLIZER_PATH=$NO_MSAN_PATH/llvm-symbolizer-msan

ENV PATH=$NO_MSAN_PATH:$PATH

# hadolint ignore=SC2046
RUN . /etc/os-release \
    && chmod a-t /tmp \
    && if [ "${CLANG_VERSION}" -gt 17 ]; then \
        export LLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind"; \
    else \
        export LLVM_ENABLE_RUNTIMES="libcxx;libcxxabi"; fi \
    && mkdir $MSAN_LIBDIR \
    && mkdir $MSAN_LIBDIR/bin \
    && printf "#!/bin/sh\nunset LD_LIBRARY_PATH\nexec llvm-symbolizer-%s \"\$@\"" "${CLANG_VERSION}" > $MSAN_SYMBOLIZER_PATH \
    && printf '#!/bin/sh\nunset LD_LIBRARY_PATH\nexec /usr/bin/gdb "$@"' > $GDB_PATH \
    && printf '#!/bin/sh\nunset LD_LIBRARY_PATH\nexec /usr/bin/ctest "$@"' > "$NO_MSAN_PATH"/ctest \
    && printf '#!/bin/sh\nunset LD_LIBRARY_PATH\nexec /bin/grep "$@"' > "$NO_MSAN_PATH"/grep \
    && curl -sL https://apt.llvm.org/llvm-snapshot.gpg.key | gpg --dearmor -o /usr/share/keyrings/llvm-snapshot.gpg \
    && if [ "${CLANG_VERSION}" -ge "${CLANG_DEV_VERSION}" ]; then \
        export LLVM_DIR="llvm-toolchain-snapshot-${CLANG_VERSION}" ; \
        export LLVM_DEB="${VERSION_CODENAME}" ; \
       else \
        export LLVM_DIR="llvm-toolchain-${CLANG_VERSION}-${CLANG_VERSION}" ; \
        export LLVM_DEB="${VERSION_CODENAME}-${CLANG_VERSION}"; fi \
    && for v in deb deb-src; do \
         echo "$v [signed-by=/usr/share/keyrings/llvm-snapshot.gpg] http://apt.llvm.org/${VERSION_CODENAME}/ llvm-toolchain-${LLVM_DEB} main" >> /etc/apt/sources.list.d/llvm-toolchain.list; done \
    && apt-get update \
    && apt-get -y install --no-install-recommends \
       clang-${CLANG_VERSION} \
       libclang-rt-${CLANG_VERSION}-dev \
       libc++abi-${CLANG_VERSION}-dev \
       libc++-${CLANG_VERSION}-dev \
       llvm-${CLANG_VERSION} \
       automake \
    && if [ "${CLANG_VERSION}" -ge 19 ]; then \
        apt-get -y install --no-install-recommends libclang-${CLANG_VERSION}-dev libllvmlibc-${CLANG_VERSION}-dev; fi \
    && update-alternatives \
        --verbose \
        --install /usr/bin/clang   clang   /usr/bin/clang-"${CLANG_VERSION}" 20 \
        --slave   /usr/bin/clang++ clang++ /usr/bin/clang++-"${CLANG_VERSION}" \
    && apt-get source libc++-${CLANG_VERSION}-dev \
    && mv "$LLVM_DIR"*/* . \
    && mkdir build \
    && cmake \
        -S runtimes \
        -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang-${CLANG_VERSION} \
        -DCMAKE_CXX_COMPILER=clang++-${CLANG_VERSION} \
        -DLLVM_ENABLE_RUNTIMES="${LLVM_ENABLE_RUNTIMES}" \
        $(if [ "${CLANG_VERSION}" -ge 19 ]; then echo "-DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_DOCS=OFF -DLLVM_ENABLE_SPHINX=OFF"; fi) \
        -DLLVM_USE_SANITIZER=MemoryWithOrigins \
    && cmake --build build --parallel "$(nproc)" \
    && cp -aL build/lib/lib*.so* $MSAN_LIBDIR \
    && cp -a build/include/c++/v1 "$MSAN_LIBDIR/include" \
    && rm -rf -- *

ENV CFLAGS="-fno-omit-frame-pointer -O2 -g -fsanitize=memory"
ENV CXXFLAGS="$CFLAGS"
ENV LDFLAGS="-fsanitize=memory"

RUN . /etc/os-release \
    && apt-get source gnutls28 \
    && mv gnutls28-*/* . \
    && mk-build-deps -it 'apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' \
    && aclocal \
    && automake --add-missing \
    && ./configure \
        --with-included-libtasn1 \
        --with-included-unistring \
        --without-p11-kit \
        --disable-hardware-acceleration \
        --disable-guile \
    && make -j "$(nproc)" \
    && cp -aL lib/.libs/libgnutls.so* $MSAN_LIBDIR \
    && rm -rf -- * \
    \
    && apt-get source nettle \
    && mv nettle-*/* . \
    && mk-build-deps -it 'apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' \
    && ./configure \
        --disable-assembler \
    && make -j "$(nproc)" \
    && cp -aL .lib/lib*.so* $MSAN_LIBDIR \
    && rm -rf -- * \
    \
    && apt-get source libidn2 \
    && mv libidn2-*/* . \
    && mk-build-deps -it 'apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' \
    && ./configure \
        --enable-valgrind-tests=no \
    && make -j "$(nproc)" \
    && cp -aL lib/.libs/libidn2.so* $MSAN_LIBDIR \
    && rm -rf -- * \
    \
    && apt-get source gmp \
    && mv gmp-*/* . \
    && mk-build-deps -it 'apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' \
    && if [ "${VERSION_CODENAME}" = "bookworm" ]; then \
        sed -e '/^.*"doc\/Makefile".*/d;s/doc\/Makefile //;' -i.bak configure \
        && sed -e 's/^\(SUBDIRS = .*\) doc$/\1/;' -i.bak Makefile.in; \
    fi \
    && ./configure \
        --disable-assembly \
    && make -j "$(nproc)" \
    && cp -aL .libs/libgmp.so* $MSAN_LIBDIR \
    && rm -rf -- * \
    && apt-get source libxml2 \
    && mv libxml2-*/* . \
    && aclocal \
    && automake --add-missing \
    && ./configure  --without-python --without-docbook --with-icu \
    && make -j "$(nproc)" \
    && cp -aL .libs/libxml2.so* $MSAN_LIBDIR \
    && rm -rf -- * \
    && apt-get source unixodbc-dev \
    && mv unixodbc-*/* . \
    && libtoolize --force \
    && aclocal \
    && autoheader \
    && autoconf \
    && automake --add-missing \
    &&  ./configure --enable-fastvalidate  --with-pth=no --with-included-ltdl=no \
    && make -j "$(nproc)" \
    && mv ./DriverManager/.libs/libodbc.so* $MSAN_LIBDIR \
    && rm -rf -- * \
    && apt-get source libfmt-dev \
    && mv fmtlib-*/* . \
    && mkdir build \
    && cmake -DFMT_DOC=OFF -DFMT_TEST=OFF  -DBUILD_SHARED_LIBS=on  -DFMT_PEDANTIC=on -S . -B build \
    && cmake --build build \
    && mv build/libfmt.so* $MSAN_LIBDIR \
    && rm -rf -- * \
    && apt-get source  libpcre2-dev \
    && mv pcre2-*/* . \
    && cmake -S . -B build/ -DBUILD_SHARED_LIBS=ON -DBUILD_STATIC_LIBS=OFF -DPCRE2_BUILD_TESTS=OFF -DPCRE2_SUPPORT_JIT=ON  -DCMAKE_C_FLAGS="${CFLAGS} -Dregcomp=PCRE2regcomp -Dregexec=PCRE2regexec -Dregerror=PCRE2regerror -Dregfree=PCRE2regfree" \
    && cmake --build build/ \
    && mv ./build/libpcre2*so* $MSAN_LIBDIR \
    && rm -rf -- * \
    && apt-get source libxcrypt \
    && mv libxcrypt-*/* . \
    && ./autogen.sh \
    && ./configure --disable-xcrypt-compat-files --enable-obsolete-api=glibc \
    && make -j "$(nproc)" libcrypt.la \
    && mv .libs/libcrypt.so.* $MSAN_LIBDIR \
    && rm -rf -- * \
    && ls -la $MSAN_LIBDIR

ENV CFLAGS="$CFLAGS -Wno-conversion"
ENV CXXFLAGS="$CFLAGS"

RUN . /etc/os-release \
    && apt-get source cracklib2 \
    && mv cracklib2-*/* . \
    && mk-build-deps -it 'apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends --yes' \
    && if [ "${VERSION_CODENAME}" = "bookworm" ]; then \
        aclocal \
        && automake --add-missing; \
    fi \
    && ./configure \
        --with-default-dict=/usr/share/dict/cracklib-small \
    && make -j "$(nproc)" \
    && make install \
    && create-cracklib-dict ./dicts/cracklib-small \
    && cp -aL lib/.libs/*.so* $MSAN_LIBDIR \
    && rm -rf -- * \
    && rm -rf /tmp/msan \
    && apt-get clean \
    && apt-get -y purge \
       bzip2 \
       libbz2-dev \
       liblz4-dev \
       liblzma-dev \
       liblzo2-dev \
       libsnappy-dev \
    && chmod -R a+x $MSAN_LIBDIR/bin/*

# For convenience of human users of msan image
ENV MSAN_OPTIONS=abort_on_error=1:poison_in_dtor=0

ENV CFLAGS="-fno-omit-frame-pointer -O2 -g -fsanitize=memory"
ENV CXXFLAGS="$CFLAGS"

ENV CMAKE_GENERATOR=Ninja
# rr installation + ninja
RUN . /etc/os-release \
    && if [ "${VERSION_CODENAME}" = "bullseye" ]; then \
         apt-get install --no-install-recommends -y libcapnp-0.7.0 ninja-build; \
       else \
         apt-get install --no-install-recommends -y libcapnp-0.9.2 ninja-build; \
    fi \
    && apt-get clean

# unknown rr
# hadolint ignore=DL3022
COPY --from=rr /tmp/install/usr/ /usr/
