# python setup.py bdist_wheel
# twine upload dist/~.whl

from setuptools import setup, find_packages

setup(
    name="quantrading",
    version='0.1.35',
    url="https://github.com/quantrading/quantrading",
    license="MIT",
    author="Jang Woo Jae",
    author_email="dnwogo@naver.com",
    description="backtest utils",
    install_requires=[
        'empyrical',
        'openpyxl',
        'xlsxwriter',
        'plotly',
    ],
    packages=find_packages(exclude=['tests', 'docs']),
    python_requires='>=3',
    long_description=open('README.md', encoding='UTF8').read(),
    long_description_content_type="text/markdown",
    package_data={},
    zip_safe=False,
)
