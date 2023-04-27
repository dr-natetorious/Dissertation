FROM python:3.9

WORKDIR /usr/local/collection
COPY . .
RUN pip3 install -r requirements.txt
RUN chmod a+x ./app.py
ENTRYPOINT ["/usr/local/collection/app.py"]