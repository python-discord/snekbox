import sys
from io import StringIO

def execute(snippet):
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    try:
        exec(snippet)
    except:
        raise
    finally:
        sys.stdout = old_stdout

    return redirected_output.getvalue()


code = """
i = [0,1,2]
for j in i:
    print(j)
"""
