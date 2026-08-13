# Security policy

Please report security issues privately to `asifahamedstudent@gmail.com`. Do not include secrets, personal files, or unrelated logs.

Supported releases are the latest tagged major version. Downloads should come from GitHub Releases and be verified with the accompanying SHA-256 checksum. Signed releases should display **Asif Ahamed** as the Windows publisher.

The downloader accepts HTTPS image URLs only, validates trusted hosts, MIME type, file size, and image decoding, and writes through a temporary file before an atomic rename.

