from jinja2 import Environment, FileSystemLoader
import os

loader = FileSystemLoader(os.path.join(os.getcwd(), 'app', 'templates'))
env = Environment(loader=loader)
files = ['client/ticket.html', 'admin/html/support_detail.html']
for f in files:
    try:
        env.get_template(f)
        print('OK', f)
    except Exception as e:
        print('ERROR', f, repr(e))
        raise
