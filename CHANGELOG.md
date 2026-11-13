# Changelog

## Unreleased — alpha

- Phase 0: Python 3.12 package bootstrap, pinned development tools, CI lint,
  formatting, smoke tests and package build checks.
- Documented architecture, safety policies and outstanding hardware verification.
- Phase 1 (gate blocked): aarch64 add-on skeleton, startup mount checks,
  heartbeat healthcheck, graceful shutdown and alpha local-install instructions.
- ARM64 execution and full Supervisor validation remain outstanding.
- Phase 1 gate completed: current add-on schema lint and emulated ARM64 service
  checks pass; added reusable native/emulated container validation and CI checks.
