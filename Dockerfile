# syntax=docker/dockerfile:1.7

ARG TARGETPLATFORM=linux/amd64
ARG GEM5_JOBS=0
ARG LLVM_JOBS=0
ARG LLVM_CMAKE_BUILD_TYPE=Debug

FROM --platform=${TARGETPLATFORM} ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV USER=root
ENV PIP_BREAK_SYSTEM_PACKAGES=1
ENV LLVM_BUILD_DIR=/workspace/llvm-build

SHELL ["/bin/bash", "-lc"]

RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lists,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
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
    && /workspace/emulator/scripts/bootstrap-submodules.sh

FROM submodules AS emulator-src

WORKDIR /workspace/emulator

COPY emulator/ /workspace/emulator/

RUN chmod +x \
        /workspace/emulator/build.sh \
        /workspace/emulator/build_gem5.sh \
        /workspace/emulator/build-sim.sh \
        /workspace/emulator/run-sim.sh \
        /workspace/emulator/scripts/bootstrap-submodules.sh

FROM base AS build-base

ENV CC=clang \
    CXX=clang++ \
    CCACHE_DIR=/root/.cache/ccache \
    CCACHE_MAXSIZE=20G \
    CCACHE_NOHASHDIR=true

RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lists,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        autoconf \
        automake \
        bc \
        bison \
        build-essential \
        ccache \
        clang \
        cmake \
        device-tree-compiler \
        flex \
        gtkwave \
        libboost-all-dev \
        libcapstone-dev \
        libfdt-dev \
        libgmp-dev \
        libgoogle-perftools-dev \
        libhdf5-dev \
        libmpc-dev \
        libmpfr-dev \
        libpng-dev \
        libprotobuf-dev \
        libreadline-dev \
        libsdl2-dev \
        libsqlite3-dev \
        libtool \
        libzstd-dev \
        lld \
        m4 \
        mold \
        ninja-build \
        numactl \
        openjdk-21-jdk \
        pkg-config \
        protobuf-compiler \
        python3-dev \
        python3-pip \
        python3-venv \
        scons \
        verilator \
        zlib1g-dev \
    && ln -sf /usr/bin/ccache /usr/local/bin/clang \
    && ln -sf /usr/bin/ccache /usr/local/bin/clang++

FROM build-base AS llvm-builder

ARG LLVM_JOBS=0
ARG LLVM_CMAKE_BUILD_TYPE=Debug

ENV CCACHE_BASEDIR=/workspace/llvm-project \
    CCACHE_COMPILERCHECK=content

WORKDIR /workspace

COPY llvm-project/ /workspace/llvm-project/

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

FROM build-base AS gem5-ready

ARG GEM5_JOBS=0

ENV CCACHE_BASEDIR=/workspace/emulator/gem5 \
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

RUN --mount=type=cache,id=gem5-ccache,target=/root/.cache/ccache,sharing=locked \
    if [ "${GEM5_JOBS}" = "0" ]; then \
        export JOBS="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"; \
    else \
        export JOBS="${GEM5_JOBS}"; \
    fi \
    && ./build_gem5.sh -j "${JOBS}" \
    && ccache --show-stats

FROM build-base AS full

ENV SKIP_ROOT_SUBMODULE_UPDATE=1
ENV PATH=/workspace/emulator/llvm-build/bin:${PATH}

WORKDIR /workspace/emulator

COPY --from=emulator-src /workspace/emulator /workspace/emulator
COPY --from=llvm-builder /workspace/llvm-build /workspace/emulator/llvm-build

RUN ./build.sh \
    && source ./env.sh \
    && ./build-sim.sh

FROM gem5-ready AS final

CMD ["/bin/bash"]
