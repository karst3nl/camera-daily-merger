# Third-party notices

The bootstrap has no runtime Python dependencies. Development/build tooling:
setuptools (MIT), pytest (MIT), Ruff (MIT), build (MIT), and their transitive
dependencies retain their upstream license terms. They are not application code.
GitHub Actions checkout/setup-python use MIT-licensed upstream actions.

Before distributing an add-on image, inventory its base OS, Python, FFmpeg build
configuration and licenses. FFmpeg licensing depends on enabled components;
project MIT licensing does not replace any bundled dependency obligations.

## Phase 3 container

The image adds Alpine 3.22 FFmpeg 6.1.2-r2 and its runtime libraries. The inspected
AMD64 build enables GPL and version3, so treat the FFmpeg binary distribution as
GPL-3.0-or-later; Python orchestration remains MIT. Dependencies include x264,
x265, libav*, and other Alpine codec/media libraries with their own licenses.
Inspect the exact image with `apk info -v`, `apk info --license` and
`ffmpeg -version`; preserve notices and corresponding-source obligations when
redistributing an image. Source package/build recipes are available from Alpine
aports branch 3.22-stable (community/ffmpeg) and the upstream projects referenced
by those recipes. No distributable release image is published by this work.
Image dependency inventory and source/notice bundle must be finalized before a
release; project MIT does not license these binaries.
