FROM alpine:3.8

ENV GUNICORN_WORKER_AMOUNT 4
ENV GUNICORN_TIMEOUT 300
ENV GUNICORN_RELOAD ""

RUN apk add python3 python3-dev build-base && rm -rf /var/cache/apk/*

COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt

RUN python3 -c "import nltk; nltk.download('punkt', '/usr/share/nltk_data')"

RUN pip3 install gunicorn

WORKDIR /app

COPY src ./src
COPY language-resources ./language-resources
COPY run.py ./

RUN mkdir logs

RUN chgrp -R 0 /app \
 && chmod -R g+rwX /app

EXPOSE 5000

USER 9008

COPY run /run.sh

ENTRYPOINT [ "/run.sh" ]
