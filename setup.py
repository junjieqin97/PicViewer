from setuptools import find_packages, setup


# NOTE: Deviates from rules.md (Python 3.10+) to support user's Python 3.9 environment.
setup(
    name="picviewer",
    version="0.1.0",
    description="A desktop photo viewer with histogram and waveform.",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    package_data={
        "pic_viewer": [
            "ui/resources/i18n/*.ts",
            "ui/resources/i18n/*.qm",
        ]
    },
    install_requires=[
        "PyQt5>=5.15",
        "opencv-python>=4.7",
        "numpy>=1.23",
        "Pillow>=10.0",
    ],
    extras_require={
        "raw": ["rawpy>=0.17"],
    },
    python_requires=">=3.9",
)
