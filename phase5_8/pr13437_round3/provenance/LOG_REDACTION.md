# YOLO log redaction disclosure

Only the local machine identifier in download-progress lines 71 and 72 of
`raw/yolo/F_r3.log` was replaced with same-length `X` bytes. No other byte,
line ending, timing, numerical result or provenance record was changed.
Agent D independently inspected and approved this exact scope before the edit.
This sanitizes the final payload; the original was already in earlier Git history.

- Original log SHA256: `89ad020a6913bf30d7439d718dfd374537261e9276286f17a595403dde1aa201`
- Published sanitized log SHA256: `6d668973338f03aedf75cca7fbc8a11d4cc814c708324cb6e00e9fc8af84b629`
- Replacements: 2; original and final length: 27612 bytes.
