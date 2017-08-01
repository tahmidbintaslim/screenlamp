import subprocess


with open('sources/user_guide/tools.md', 'w') as f:
    subprocess.call(['python', 'argparse_to_md.py', '../tools'], stdout=f)

subprocess.call(['python', 'ipynb2markdown.py', '--ipynb',
                 'sources/user_guide/tools-tutorial-1.ipynb'])
