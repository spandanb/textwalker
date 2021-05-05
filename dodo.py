"""
doit docs: https://pydoit.org/cmd_run.html
"""
import pdoc
import os
import os.path


def generate_docs(docs_dir: str):
    """
    python callable that creates docs like docs/textwalker.html, docs/patternparser.py
    Args:
        docs_dir: location to output docs to
    """
    if not os.path.exists(docs_dir):
        print(f'{docs_dir} does not exist; creating dir')
        os.mkdir(docs_dir)

    mod_names = ["textwalker", "textwalker.textwalker", "textwalker.pattern_parser", "textwalker.utils"]
    context = pdoc.Context()
    modules = [pdoc.Module(mod, context=context)
               for mod in mod_names]
    pdoc.link_inheritance(context)
    for module in modules:
        if module.name == "textwalker":
            filepath = os.path.join(docs_dir, 'index.html')
        else:
            pkg, modname = module.name.split('.')
            filename = f'{modname}.html'
            filepath = os.path.join(docs_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as fp:
            fp.write(module.html())
        print(f'wrote docs for module {module.name} to {filepath}')


def task_run_tests():
    """
    run tests
    """
    task = {
        'actions': ['pytest textwalker'],
        'verbosity': 2
    }
    return task


def task_run_tests_with_codecov():
    """
    run tests with codecov
    """
    task = {
        'actions': ['pytest --cov=textwalker'],
        'verbosity': 2
    }
    return task


def task_run_flake8():
    """
    calls flake8 linter
    """
    task = {
        'actions': ['flake8 textwalker'],
        'verbosity': 2
    }
    return task


def task_run_black():
    """
    calls black code formatter
    """
    task = {
        'actions': ['black textwalker'],
        'verbosity': 2
    }
    return task


def task_run_pdoc_cli():
    """
    calls pdoc via CLI
    pdoc3 : https://pdoc3.github.io/pdoc/doc/pdoc/#programmatic-usage
    """
    task = {
        'actions': ['pdoc3 --html --force textwalker -o docs'],
        'verbosity': 2
    }
    return task


def task_run_pdoc():
    """
    calls pdoc via python
    pdoc3 : https://pdoc3.github.io/pdoc/doc/pdoc/#programmatic-usage
    """
    task = {
        'actions': [(generate_docs, ('docs',))],
        'verbosity': 2
    }
    return task
