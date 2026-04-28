# syntax=docker/dockerfile:1.7

ARG TARGETPLATFORM=linux/amd64
ARG XIANGSHAN_JOBS=0
ARG LLVM_JOBS=0
ARG LLVM_CMAKE_BUILD_TYPE=Debug
ARG LLVM_REPO_URL=https://github.com/cheolwanpark/llvm-project-vplan-experiment.git
ARG LLVM_REPO_REF=vplans-measure
ARG MILL_VERSION=0.12.3
ARG TEMURIN_JRE_URL=https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jre/hotspot/normal/eclipse

FROM --platform=${TARGETPLATFORM} ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV USER=root
ENV PIP_BREAK_SYSTEM_PACKAGES=1
ENV LLVM_BUILD_DIR=/workspace/llvm-build

SHELL ["/bin/bash", "-lc"]

# Retry apt downloads because the Ubuntu mirror intermittently resets long fetches.
RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lists,target=/var/lib/apt/lists,sharing=locked \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Dpkg::Use-Pty=0 update \
    && apt-get install -y --no-install-recommends \
        -o Acquire::Retries=5 \
        -o Acquire::http::Timeout=30 \
        -o Acquire::https::Timeout=30 \
        -o Dpkg::Use-Pty=0 \
        bash \
        ca-certificates \
        curl \
        git \
        python3 \
        wget

FROM base AS submodules

WORKDIR /workspace/emulator

COPY emulator/scripts/bootstrap-submodules.sh /workspace/emulator/scripts/bootstrap-submodules.sh

RUN chmod +x /workspace/emulator/scripts/bootstrap-submodules.sh \
    && BOOTSTRAP_PROFILE=emulate /workspace/emulator/scripts/bootstrap-submodules.sh

FROM submodules AS emulator-src

WORKDIR /workspace/emulator

COPY emulator/ /workspace/emulator/

RUN chmod +x \
        /workspace/emulator/build.sh \
        /workspace/emulator/build-sim.sh \
        /workspace/emulator/run-sim.sh \
        /workspace/emulator/scripts/bootstrap-submodules.sh

FROM base AS build-base

ARG TEMURIN_JRE_URL

ENV CC=clang \
    CXX=clang++ \
    CCACHE_DIR=/root/.cache/ccache \
    CCACHE_MAXSIZE=20G \
    CCACHE_NOHASHDIR=true \
    JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:${PATH}

# Keep the Docker image focused on the headless LLVM + emulator toolchain.
RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lists,target=/var/lib/apt/lists,sharing=locked \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Dpkg::Use-Pty=0 update \
    && apt-get install -y --no-install-recommends \
        -o Acquire::Retries=5 \
        -o Acquire::http::Timeout=30 \
        -o Acquire::https::Timeout=30 \
        -o Dpkg::Use-Pty=0 \
        build-essential \
        ccache \
        clang \
        cmake \
        flex \
        bison \
        bc \
        lld \
        gcc-riscv64-linux-gnu \
        libc6-dev-riscv64-cross \
        linux-libc-dev-riscv64-cross \
        libsqlite3-dev \
        libzstd-dev \
        mold \
        ninja-build \
        numactl \
        pkg-config \
        python3-yaml \
        python3-dev \
        python3-pip \
        python3-venv \
        scons \
        linux-tools-common \
        linux-tools-generic \
        time \
        verilator \
        zlib1g-dev \
    && ln -sf /usr/bin/ccache /usr/local/bin/clang \
    && ln -sf /usr/bin/ccache /usr/local/bin/clang++ \
    && mkdir -p "${JAVA_HOME}" \
    && curl -fsSL "${TEMURIN_JRE_URL}" -o /tmp/temurin-jre.tar.gz \
    && tar -xzf /tmp/temurin-jre.tar.gz -C "${JAVA_HOME}" --strip-components=1 \
    && rm /tmp/temurin-jre.tar.gz

FROM build-base AS llvm-builder

ARG LLVM_JOBS=0
ARG LLVM_CMAKE_BUILD_TYPE=Debug
ARG LLVM_REPO_URL
ARG LLVM_REPO_REF

ENV CCACHE_BASEDIR=/workspace/llvm-project \
    CCACHE_COMPILERCHECK=content

WORKDIR /workspace

COPY llvm-project/ /workspace/llvm-project/

RUN if [ -f /workspace/llvm-project/llvm/CMakeLists.txt ]; then \
        exit 0; \
    fi \
    && rm -rf /workspace/llvm-project \
    && git clone --depth 1 --branch "${LLVM_REPO_REF}" "${LLVM_REPO_URL}" /workspace/llvm-project \
    && test -f /workspace/llvm-project/llvm/CMakeLists.txt

RUN --mount=type=cache,id=llvm-ccache,target=/root/.cache/ccache,sharing=locked \
    if [ "${LLVM_JOBS}" = "0" ]; then \
        export JOBS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"; \
    else \
        export JOBS="${LLVM_JOBS}"; \
    fi \
    && cmake -S /workspace/llvm-project/llvm -B "${LLVM_BUILD_DIR}" -G Ninja \
        -DCMAKE_BUILD_TYPE="${LLVM_CMAKE_BUILD_TYPE}" \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_C_COMPILER_LAUNCHER=ccache \
        -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
        -DLLVM_ENABLE_ASSERTIONS=ON \
        -DLLVM_ENABLE_DUMP=ON \
        -DLLVM_ENABLE_PROJECTS="clang;lld" \
        -DLLVM_TARGETS_TO_BUILD="RISCV;X86" \
        -DLLVM_INCLUDE_BENCHMARKS=OFF \
        -DLLVM_INCLUDE_EXAMPLES=OFF \
        -DLLVM_INCLUDE_TESTS=OFF \
        -DLLVM_BUILD_TESTS=OFF \
        -DLLVM_INCLUDE_UTILS=OFF \
    && cmake --build "${LLVM_BUILD_DIR}" --target \
        clang \
        lld \
        llc \
        llvm-ar \
        llvm-as \
        llvm-extract \
        llvm-link \
        llvm-nm \
        llvm-objcopy \
        llvm-objdump \
        llvm-ranlib \
        llvm-readelf \
        opt \
        -j "${JOBS}" \
    && ccache --show-stats

FROM build-base AS emulator-ready

ARG XIANGSHAN_JOBS=0
ARG MILL_VERSION

ENV CCACHE_BASEDIR=/workspace/emulator/XiangShan \
    CCACHE_COMPILERCHECK=content \
    PATH=/workspace/llvm-build/bin:${PATH}

WORKDIR /workspace/emulator

COPY --from=emulator-src /workspace/emulator /workspace/emulator
COPY --from=llvm-builder /workspace/llvm-build /workspace/llvm-build

RUN ln -sf "${LLVM_BUILD_DIR}/bin/opt" /usr/local/bin/opt-vplan \
    && ln -sf "${LLVM_BUILD_DIR}/bin/clang" /usr/local/bin/clang-vplan \
    && ln -sf "${LLVM_BUILD_DIR}/bin/clang++" /usr/local/bin/clang++-vplan \
    && ln -sf "${LLVM_BUILD_DIR}/bin/llvm-extract" /usr/local/bin/llvm-extract \
    && ln -sf "${LLVM_BUILD_DIR}/bin/llvm-extract" /usr/local/bin/llvm-extract-vplan \
    && ln -sf "${LLVM_BUILD_DIR}/bin/llc" /usr/local/bin/llc-vplan \
    && printf '\nalias opt-vplan=\"%s/bin/opt\"\n' "${LLVM_BUILD_DIR}" >> /etc/bash.bashrc \
    && printf 'alias clang-vplan=\"%s/bin/clang\"\n' "${LLVM_BUILD_DIR}" >> /etc/bash.bashrc \
    && printf 'alias clang++-vplan=\"%s/bin/clang++\"\n' "${LLVM_BUILD_DIR}" >> /etc/bash.bashrc \
    && printf 'alias llvm-extract-vplan=\"%s/bin/llvm-extract\"\n' "${LLVM_BUILD_DIR}" >> /etc/bash.bashrc \
    && printf 'alias llc-vplan=\"%s/bin/llc\"\n' "${LLVM_BUILD_DIR}" >> /etc/bash.bashrc

RUN --mount=type=cache,id=xiangshan-ccache,target=/root/.cache/ccache,sharing=locked \
    if [ "${XIANGSHAN_JOBS}" = "0" ]; then \
        export JOBS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"; \
    else \
        export JOBS="${XIANGSHAN_JOBS}"; \
    fi \
    && curl -fsSL "https://repo1.maven.org/maven2/com/lihaoyi/mill-dist/${MILL_VERSION}/mill-dist-${MILL_VERSION}.jar" -o /usr/local/bin/mill \
    && chmod +x /usr/local/bin/mill \
    && git -C /workspace/emulator/XiangShan submodule update --init --recursive -- difftest \
    && ln -sfn ../build /workspace/emulator/XiangShan/difftest/build \
    && (git -C /workspace/emulator/XiangShan/difftest apply --check /workspace/emulator/patches/xiangshan-difftest.patch 2>/dev/null \
        && git -C /workspace/emulator/XiangShan/difftest apply /workspace/emulator/patches/xiangshan-difftest.patch \
        || true) \
    && export NEMU_HOME=/workspace/emulator/third-party/NEMU \
    && export AM_HOME=/workspace/emulator/third-party/nexus-am \
    && if [ ! -f /workspace/emulator/third-party/NEMU/build/riscv64-nemu-interpreter-so ]; then \
        cd /workspace/emulator/third-party/NEMU \
        && make CCACHE= CC=gcc CXX=g++ riscv64-xs-kunminghu-v3-ref_defconfig \
        && make CCACHE= CC=gcc CXX=g++ -j "${JOBS}"; \
    fi \
    && cd /workspace/emulator \
    && ./build-sim.sh gem5 xiangshan.KunminghuV2Config -j "${JOBS}" \
    && ccache --show-stats

FROM emulator-ready AS final

CMD ["/bin/bash"]
