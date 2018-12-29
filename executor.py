import sys
import ast


def main():
    code = sys.argv[1]
    tree = ast.parse(code)
    fake_interactive_tree = ast.Interactive()
    fake_interactive_tree.body = tree.body
    exec(compile(fake_interactive_tree, "<input>", "single"), {}, {})

main()