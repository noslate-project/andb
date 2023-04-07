# docker build -t andb-dev -f dockerfile .

FROM centos:7

RUN yum clean all && \
    yum makecache && \
    yum install -y centos-release-scl && \
    yum makecache && \
    yum install -y wget curl psmisc dstat vim git tmux net-tools make cmake libtool gcc-c++ automake autoconf texinfo libevent python-devel python3-devel && \
    yum install -y llvm-toolset-7.0-lldb-devel llvm-toolset-7.0-python-lldb llvm-toolset-7.0-clang llvm-toolset-7.0-build && \
    yum clean all

WORKDIR /root
RUN git clone https://github.com/noslate-project/andb.git && \
    git clone https://github.com/noslate-project/andb-gdb.git && \
    echo $'source /opt/rh/llvm-toolset-7.0/enable \n\
cd andb-gdb && source env.sh && cd .. \n\
cd andb && source env.sh && cd ..' > /root/env.sh
