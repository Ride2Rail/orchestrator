FROM python:3.9

ENV APP_NAME=orchestrator.py

COPY orchestrator.conf /code/orchestrator.conf
COPY "$APP_NAME" /code/"$APP_NAME"

WORKDIR /code

ENV FLASK_APP="$APP_NAME"
ENV FLASK_RUN_HOST=0.0.0.0

RUN pip3 install --no-cache-dir --upgrade pip

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["flask", "run"]