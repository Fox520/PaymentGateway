FROM python:3-alpine

RUN python -m pip install --upgrade pip

WORKDIR /app
COPY . /app
RUN pip3 --no-cache-dir install -r requirements.txt
EXPOSE 6001

ENTRYPOINT ["python3"]
CMD ["run.py"]