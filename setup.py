from setuptools import setup, find_packages

setup(
    name="mindmap_etl",
    version="0.1.3",
    keywords=["mindmap", "ETL", 'etl', 'graph'],
    description="使用 .xmmap 思维导图文件构建模型和ETL导入逻辑，转换为图数据库需要的结构。",
    long_description="",
    license="MIT Licence",
    url="https://github.com/tr33oph/mindmap_etl.git",
    author="treeoph",
    author_email="treeoph@gmail.com",

    packages=find_packages(),
    include_package_data=True,
    platforms="any",
    install_requires=["xml2dict",
                        "dpath",
                        "lxml",
                        "pandas"],

    scripts=[],
    zip_safe=False
)
