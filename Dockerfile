FROM python:slim

RUN useradd app

WORKDIR /home/app

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN apt-get update && apt-get install -y nano python3-pip python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
RUN pip install weasyprint
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn openpyxl weasyprint

COPY app app
COPY files files
#COPY migrations migrations
COPY main.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP main.py

RUN chown -R app:app ./
USER app

#EXPOSE 8080
ENTRYPOINT ["./boot.sh"]