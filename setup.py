from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mo-git",
    version="0.1.0",
    author="Kyle Lahnakoski",
    description="Enhanced git workflow utilities with smart conflict resolution and branch management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/klahnakoski/mo-git",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        "mo-files>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "hit=mo_git.cli:main",
        ],
    },
)

