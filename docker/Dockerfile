ARG IMAGE_TAG=latest
FROM ghcr.io/python-discord/snekbox-base:$IMAGE_TAG

ENTRYPOINT ["gunicorn"]
CMD ["-c", "config/gunicorn.conf.py", "snekbox.api.app"]

COPY . /snekbox
WORKDIR /snekbox
