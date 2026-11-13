# Third-party notices

The bootstrap has no runtime Python dependencies. Development/build tooling:
setuptools (MIT), pytest (MIT), Ruff (MIT), build (MIT), and their transitive
dependencies retain their upstream license terms. They are not application code.
GitHub Actions checkout/setup-python use MIT-licensed upstream actions.

Before distributing an add-on image, inventory its base OS, Python, FFmpeg build
configuration and licenses. FFmpeg licensing depends on enabled components;
project MIT licensing does not replace any bundled dependency obligations.
