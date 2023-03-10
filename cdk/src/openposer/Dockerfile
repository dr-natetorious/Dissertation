# FROM nvidia/cuda:10.0-cudnn7-devel

# #get deps
# RUN apt-get update && \
# DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
# python3-dev python3-pip git g++ wget make libprotobuf-dev protobuf-compiler libopencv-dev \
# libgoogle-glog-dev libboost-all-dev libcaffe-cuda-dev libhdf5-dev libatlas-base-dev

# #for python api
# RUN pip3 install numpy opencv-python 

# #replace cmake as old version has CUDA variable bugs
# RUN wget https://github.com/Kitware/CMake/releases/download/v3.16.0/cmake-3.16.0-Linux-x86_64.tar.gz && \
# tar xzf cmake-3.16.0-Linux-x86_64.tar.gz -C /opt && \
# rm cmake-3.16.0-Linux-x86_64.tar.gz
# ENV PATH="/opt/cmake-3.16.0-Linux-x86_64/bin:${PATH}"

# #get openpose
# WORKDIR /openpose
# RUN git clone https://github.com/CMU-Perceptual-Computing-Lab/openpose.git .

# #build it
# WORKDIR /openpose/build
# RUN cmake -DBUILD_PYTHON=ON .. && make -j `nproc`

FROM cwaffles/openpose as base

#setup pyopenpose
WORKDIR /openpose/build/python/openpose
RUN make install

# setup env
WORKDIR /openpose/build/python/openpose
RUN cp ./pyopenpose.cpython-36m-x86_64-linux-gnu.so /usr/local/lib/python3.6/dist-packages
WORKDIR /usr/local/lib/python3.6/dist-packages
RUN ln -s pyopenpose.cpython-36m-x86_64-linux-gnu.so pyopenpose
ENV LD_LIBRARY_PATH=/openpose/build/python/openpose:${LD_LIBRARY_PATH}

# setup models
WORKDIR /openpose/models
RUN  ./getModels.sh

WORKDIR /usr/local/bin/analyze
COPY requirements.txt .
RUN pip3 install --upgrade pip
RUN pip3 install setuptools
RUN pip3 install -r requirements.txt

######################################################
# DEBUG Layer
######################################################
FROM base as debug

EXPOSE 3000
WORKDIR /usr/local/bin/analyze
RUN pip3 install debugpy

# ######################################################
# # Prod Layer
# ######################################################
FROM base as prod

WORKDIR /usr/local/bin/analyze
COPY . .
CMD [ "/usr/local/bin/analyze/app.py" ]