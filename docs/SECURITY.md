# Security and privacy model

The add-on performs local processing only; it does not upload recordings or need
cloud runtime services. Treat NAS names and metadata as untrusted. Source opens
are read-only, descriptor-relative, regular-file-only and reject symlink traversal.
New media files are confined to explicitly designated output/staging directories;
publication never overwrites existing files. NAS ACLs should provide additional
protection because the HA media mount is writable for exports.

The web listener has no host-port mapping, host networking, privileged mode or
Supervisor API permissions. It trusts the internal Supervisor peer resolved by
HA DNS, delegates authentication to ingress and rejects direct peers regardless
of forwarding headers. Administrative POSTs require a CSRF token. APIs expose
camera/date/status but no raw manifests or source paths. Outputs are addressed by
camera/date and verified managed filenames, never arbitrary request paths.

The loopback development mode is explicit and must remain disabled in HA. Do not
publish the listener through an extra reverse proxy/port mapping. Actual ingress
and NAS access controls remain unverified until the Phase 7 device protocol passes.
This alpha has not undergone an independent security audit. Before release, review
pinned image/dependency vulnerabilities and complete third-party source/notices.

Please report suspected vulnerabilities privately to the repository owner through
an available private GitHub security reporting channel; if unavailable, contact
the owner without publishing exploit details or private recording metadata.

Authenticated discovery diagnostics may include up to three offending recording
basenames per diagnostic group to support local troubleshooting. They never
include source directories and are not logged or uploaded. Treat those names and
the SQLite state as private. The frontend renders names as text; HTML-looking
filenames cannot inject markup. Unauthorized HTTP peers cannot retrieve them.
