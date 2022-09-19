FROM snakepacker/python:all AS builder
RUN python3.10 -m venv /usr/share/python3/app
RUN /usr/share/python3/app/bin/pip install -U pip
COPY requirements.txt /mnt/
RUN /usr/share/python3/app/bin/pip install -Ur /mnt/requirements.txt
COPY dist/ /mnt/dist/
RUN /usr/share/python3/app/bin/pip install /mnt/dist/* \
    && /usr/share/python3/app/bin/pip check
FROM snakepacker/python:3.10 as api
COPY --from=builder /usr/share/python3/app /usr/share/python3/app
COPY config.yml /usr/share/python3/app/lib/python3.10/site-packages/
RUN ln -snf /usr/share/python3/app/bin/app-bot /usr/local/bin/
RUN ln -snf /usr/share/python3/app/bin/app-db /usr/local/bin/
RUN ln -snf /usr/share/python3/app/bin/app-tg /usr/local/bin/
COPY alembic.ini/ /usr/share/python3/app/lib/python3.10/site-packages/
COPY alembic/ /usr/share/python3/app/lib/python3.10/site-packages/alembic
