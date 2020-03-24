FROM pythondiscord/snekbox-venv:latest

ENTRYPOINT ["gunicorn"]
CMD ["-c", "config/gunicorn.conf.py", "snekbox.api.app"]

COPY . /snekbox
WORKDIR /snekbox
