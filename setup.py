import os
import subprocess
from setuptools import setup, Command


class SimpleCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


class DocCommand(SimpleCommand):
    def run(self):
        subprocess.call(["sphinx-autobuild", "docs", "docs/_build",
                        "--port", "8888", "--open-browser"])


setup(
    cmdclass={
        "doc": DocCommand,
    },
)
