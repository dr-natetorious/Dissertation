FROM python:3

WORKDIR /usr/local/collection
COPY . .
RUN chmod a+x ./app.py
ENTRYPOINT ["app.py"]