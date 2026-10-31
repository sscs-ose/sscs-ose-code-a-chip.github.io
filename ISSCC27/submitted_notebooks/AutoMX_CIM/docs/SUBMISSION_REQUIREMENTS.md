# Code-a-Chip ISSCC 2027 submission format

Official instructions checked on 30 October 2026:

- [Current program rules and logistics](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/README.md).
- [How to Apply](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/howtoapply.md).
- [GitHub file-size guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

Submit a GitHub pull request from a fork to the official repository. All
changed files belong inside `ISSCC27/submitted_notebooks/AutoMX_CIM/`.
Include the Jupyter `.ipynb`, an open-source license and necessary supporting
sources/data or reproducible dependency acquisition instructions. Spell out
the team at the notebook top; retain references and recommended tool versions.
Explain the design, decisions, method, results and reproduction procedure.
A final layout is encouraged but is not mandatory. The current rules do not
request a separate paper PDF, video, slide deck or Colab version at submission.

The older How to Apply page still mentions ISSCC26; the current program
logistics explicitly name `ISSCC27/submitted_notebooks/<project_name>/`.
This package follows the current ISSCC27 path. One team representative is
required for attendance if selected; the package names the Lead as contact.

Published deadline: 31 October 2026, 11:59 AM Pacific Time, which is
1 November 2026, 01:59 in Vietnam (UTC+7, Pacific daylight time on that date).
Submit before the deadline and follow the organizers' restriction on changes
after it. This local package has not opened a PR or uploaded an asset.

GitHub warns above 50 MiB and blocks ordinary Git files above 100 MiB;
browser upload has a 25 MiB per-file limit. Keep the rendered notebook in
ordinary Git so its saved results remain visible. Runtime PDKs/tools/data
and detailed measurement archives are prepared separately for Releases.
