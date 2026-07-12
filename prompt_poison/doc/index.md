# PyRIT

Welcome to the Python Risk Identification Tool for generative AI (PyRIT)! PyRIT is designed to be a flexible and extensible tool that can be used to assess the security and safety issues of generative AI systems in a variety of ways.

Before starting with AI Red Teaming, we recommend reading about planning red teaming for large language models (LLMs) and their applications.

Generative AI systems introduce many categories of risk, which can be difficult to mitigate even with a red teaming
plan in place. To quote the article above, "with LLMs, both benign and adversarial usage can produce
potentially harmful outputs, which can take many forms, including harmful content such as hate speech,
incitement or glorification of violence, or sexual content." Additionally, a variety of security risks
can be introduced by the deployment of an AI system.

## Installation Guide

PyRIT offers flexible installation options to suit different needs. Choose the path that best fits your use case:

```{important}
**Version Compatibility:**
- **User installations** (Docker, Pip/Conda) install the **latest stable release** from PyPI
- **Contributor installations** (DevContainers, Local Development) use the **latest development code** from the `main` branch
- Always match your notebooks to your PyRIT version - download from the corresponding release branch if using a stable release
```

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} 🐋 Docker Installation
:link: setup/1b_install_docker
:shadow: md
:class-header: bg-light
:link-type: doc

**For Users - Quick Start** ⭐

^^^

Get started immediately with a pre-configured environment:

- ✅ All dependencies included
- ✅ No Python setup needed
- ✅ JupyterLab built-in
- ✅ Works on all platforms

+++

**Best for:** First-time users who want to start quickly without environment setup.

:::

:::{grid-item-card} 🐍 Local Pip/uv Installation
:link: setup/1a_install_uv
:shadow: md
:class-header: bg-light
:link-type: doc

**For Users - Custom Setup**

^^^

Install PyRIT directly on your machine:

- ✅ Full Python environment control
- ✅ Lighter weight installation
- ✅ Easy integration with existing workflows
- ✅ Direct system access

+++

**Best for:** Users comfortable with Python environments or integrating PyRIT into existing projects.

:::

:::{grid-item-card} 🐋 DevContainers in VS Code
:link: contributing/1b_install_devcontainers
:shadow: md
:class-header: bg-light
:link-type: doc

**For Contributors** ⭐

^^^

Standardized development environment:

- ✅ Pre-configured VS Code setup
- ✅ Consistent across all contributors
- ✅ All extensions pre-installed
- ✅ Zero configuration needed

+++

**Best for:** Contributors using VS Code who want a ready-to-go development environment.

:::

:::{grid-item-card} 🐍 Local uv Development
:link: contributing/1a_install_uv
:shadow: md
:class-header: bg-light
:link-type: doc

**For Contributors - Custom Dev Setup**

^^^

Install from source in editable mode:

- ✅ Full development control
- ✅ Use any IDE or editor
- ✅ Customize environment
- ✅ Advanced configuration options

+++

**Best for:** Contributors who prefer custom development setups or don't use VS Code.

:::

::::

## Recommended Docs Reading Order

There is no single way to read the documentation, and it's perfectly fine to jump around. However, here is a recommended reading order. Note that in many sections there are numbered documentation pages. If there is no number attached, it is supplemental and the recommended reading order would be to skip it on a first pass.

::::{grid} 1
:gutter: 2

:::{grid-item-card} 1️⃣ Cookbooks
:link: cookbooks/README
:shadow: md
:class-header: bg-light
:link-type: doc

This provides an overview of PyRIT in action. A great place to see practical examples and get started quickly.

:::

:::{grid-item-card} 2️⃣ Architecture
:link: code/architecture
:shadow: md
:class-header: bg-light
:link-type: doc

High-level overview of all PyRIT components. Understanding any single component is easier with knowledge of the others.

:::

:::{grid-item-card} 3️⃣ Attacks
:link: code/executor/0_executor
:shadow: md
:class-header: bg-light
:link-type: doc

Top-level components implementing end-to-end attack techniques. Shows how all PyRIT components fit together.

:::

:::{grid-item-card} 4️⃣ Datasets
:link: code/datasets/0_dataset
:shadow: md
:class-header: bg-light
:link-type: doc

Building attacks using seed prompts and fetching datasets. The foundation for creating test scenarios.

:::

:::{grid-item-card} 5️⃣ Targets
:link: code/targets/0_prompt_targets
:shadow: md
:class-header: bg-light
:link-type: doc

Endpoints that PyRIT sends prompts to. Essential for nearly any PyRIT scenario - learn what targets are available.

:::

:::{grid-item-card} 6️⃣ Converters
:link: code/converters/0_converters
:shadow: md
:class-header: bg-light
:link-type: doc

Transform prompts from one format to another. One of the most powerful capabilities within PyRIT.

:::

:::{grid-item-card} 7️⃣ Scorers
:link: code/scoring/0_scoring
:shadow: md
:class-header: bg-light
:link-type: doc

How PyRIT makes decisions and records output. Essential for evaluating AI system responses.

:::

:::{grid-item-card} 8️⃣ Memory
:link: code/memory/0_memory
:shadow: md
:class-header: bg-light
:link-type: doc

How PyRIT components communicate state information. Understand the data flow and storage mechanisms.

:::

:::{grid-item-card} 9️⃣ Auxiliary Attacks (Optional)
:link: code/auxiliary_attacks/0_auxiliary_attacks
:shadow: md
:class-header: bg-light
:link-type: doc

Attacks and techniques that don't fit into core PyRIT functionality. Advanced and specialized methods.

:::

::::

### Additional Resources

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} 🚀 Deployment
:link: deployment/README
:shadow: md
:class-header: bg-light
:link-type: doc

Code to download, deploy, and score open-source models (such as Hugging Face) on Azure.

:::

:::{grid-item-card} 📰 Blog
:link: blog/README
:shadow: md
:class-header: bg-light
:link-type: doc

Notable new changes and updates. Stay current with the latest PyRIT developments.

:::

::::
