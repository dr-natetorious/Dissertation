docker build -t analyze .

docker run -it --gpus all --entrypoint bash analyze