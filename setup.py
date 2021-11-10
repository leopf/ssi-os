from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

requirements = [
    "paramiko",
    "inquirer"
]

setup(
    name="ssiOS Installer",
    version="0.0.1",
    author="",
    author_email="",
    description="",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="",
    packages=[ "ssiosinstaller" ],
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.7",
    ],
    scripts=['bin/ssiosinstall.py']
)