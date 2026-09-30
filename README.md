# TIA Portal AI Extensions

A collection of installable AI plugins for working with Siemens TIA Portal.
Each plugin has its own package directory and can be installed independently.

## Available plugins

- [TIA Portal Openness Development Kit](openness_development/README.md) —
  32 Agent Skills for TIA Portal Openness.

## Install with GitHub Copilot CLI

Register this repository's marketplace, then install the plugin you need:

```shell
copilot plugin marketplace add siemens/tia-portal-ai-extensions
copilot plugin install tia-portal-openness-development-kit@tia-portal-ai-extensions
```

See the [Openness plugin documentation](openness_development/README.md) for
compatibility details, prerequisites, and the complete skill list.

## Repository layout

- `.github/plugin/marketplace.json` lists the installable plugins.
- Each plugin package, such as `openness_development/`, contains its own
  manifests, documentation, and `skills/` directory.
