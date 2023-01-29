FROM cwaffles/openpose

WORKDIR /openpose/build/python/openpose
RUN make install

WORKDIR /openpose/build/python/openpose
RUN cp ./pyopenpose.cpython-36m-x86_64-linux-gnu.so /usr/local/lib/python3.6/dist-packages
WORKDIR /usr/local/lib/python3.6/dist-packages
RUN ln -s pyopenpose.cpython-36m-x86_64-linux-gnu.so pyopenpose
ENV LD_LIBRARY_PATH=/openpose/build/python/openpose

WORKDIR /openpose/models
RUN chmod a+x getModels.sh && ./getModels.sh

# FROM python:3.9 as build

# RUN apt-get -y update && \
#   && apt-get -y install cmake linux-headers-5.10.0-21-common

# # Install NVDIA support
# WORKDIR /usr/local/cuda/
# RUN wget https://developer.download.nvidia.com/compute/cuda/repos/debian10/x86_64/cuda-keyring_1.0-1_all.deb && \
#   dpkg -i cuda-keyring_1.0-1_all.deb && \
#   add-apt-repository contrib && \
#   apt-get update && \
#   apt-get -y install cuda

# WORKDIR /usr/local/src/
# RUN git clone https://github.com/CMU-Perceptual-Computing-Lab/openpose && \
#   cd openpose && \
#   git submodule update --init --recursive --remote

# #RUN pip3 install -r requirements.txt