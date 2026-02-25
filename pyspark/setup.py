from setuptools import setup, find_packages

setup(
    name="meps-pyspark",
    version="1.0.0",
    description="MEPS Healthcare Analytics - PySpark Migration from SAS",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pyspark>=3.4.0",
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        "scipy>=1.9.0",
        "pyreadstat>=1.2.0",
        "openpyxl>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
)
