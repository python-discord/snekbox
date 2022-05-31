workers = 2
bind = "0.0.0.0:8060"
logger_class = "snekbox.utils.gunicorn.GunicornLogger"
access_logformat = "%(m)s %(U)s%(q)s %(s)s %(b)s %(L)ss"
access_logfile = "-"
wsgi_app = "snekbox.api:SnekAPI"
