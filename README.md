# Empa nanotech@surfaces Laboratory - Molecules

App to compute molecular properties.

## Installation

This Jupyter-based app is intended to be run with [AiiDAlab](https://www.materialscloud.org/aiidalab).

Assuming that the app was registered, you can install it directly via the app store in AiiDAlab or on the command line with:
```
aiidalab install aiidalab-empa-molecules
```
Otherwise, you can also install it directly from the repository:
```
aiidalab install aiidalab-empa-molecules@git+https://github.com/nanotech-empa/aiidalab-empa-molecules.git
```

## For maintainers

To create a new release, clone the repository, install development dependencies with `pip install -e '.[dev]'`, and then execute `bumpver update`.
This will:

  1. Create a tagged release with bumped version and push it to the repository.
  2. Trigger a GitHub actions workflow that creates a GitHub release.

Additional notes:

  - Use the `--dry` option to preview the release change.
  - The release tag (e.g. a/b/rc) is determined from the last release.
    Use the `--tag` option to switch the release tag.

## License

MIT

## Contact

## Software attribution and scientific acknowledgements

Please credit [aiidalab-empa-molecules](https://github.com/nanotech-empa/aiidalab-empa-molecules) and its
[contributors](https://github.com/nanotech-empa/aiidalab-empa-molecules/graphs/contributors),
and identify the release or immutable commit used. Existing author,
contributor and funding acknowledgements remain authoritative.

See [CITATION.cff](CITATION.cff) for the software citation and identify the
exact release or commit used.

Preserve the copyright and permission notices in [LICENSE](LICENSE)
when copying or distributing copies or substantial portions of MIT-licensed
code. Separately licensed components retain their own notices. A name or
repository link does not replace the applicable licence notices.

For research using this app, acknowledge the [AiiDA team](https://github.com/nanotech-empa/.github/blob/main/CITATION_GUIDANCE.md#aiida)
and [AiiDAlab team](https://github.com/nanotech-empa/.github/blob/main/CITATION_GUIDANCE.md#aiidalab), and cite the three AiiDA papers
and both AiiDAlab platform papers listed in that guide.

Also credit the workflow plugins, molecular simulation codes and methods actually used.

The [shared credit guide](https://github.com/nanotech-empa/.github/blob/main/CITATION_GUIDANCE.md) keeps software attribution, licence
compliance and scientific citation requests separate. Scientific citation
requests are not additional MIT licence conditions.
