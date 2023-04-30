docker build -t analyze .

@REM docker run -it --gpus all -p 8888:3001 -p 8879:8069 --entrypoint bash analyze
docker run -it --gpus all -v `pwd`:/files -v ~/.aws:/root/.aws -w /files -p 8888:3001 -p 8879:8069 analyze /usr/bin/python3 -m debugpy --listen 0.0.0.0:3001 --wait-for-client /files/app.py