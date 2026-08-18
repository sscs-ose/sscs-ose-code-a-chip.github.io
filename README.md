## IEEE SSCS Open-Source Ecosystem “Code-a-Chip” Travel Grant Awards for [ISSCC 2027](https://www.isscc.org/)

**The IEEE SSCS Code-a-Chip Travel Grant Award** was created to:
 1. Promote *reproducible* chip design using *open-source* tools and *notebook-driven* design flows,
 2. Enable emerging designers and experienced open-source contributors to attend IEEE SSCS conferences, engage with the chip-design community, and build professional networks,
 3. <span style='color: skyblue;'>Broaden educational value and accessibility within the open-source chip design community, fostering a more inclusive environment for dissemination, learning, and innovation.</span>

## Program Rules
- The program is open to anyone (no restrictions). IEEE Solid-State Circuits Society (SSCS) membership is encouraged but not required.
- Code-a-Chip competitions are conducted for the ISSCC and VLSI Symposium conferences according to their respective submission deadlines.
- Team submissions are encouraged; however, each team must designate one representative to receive the award and attend ISSCC 2027 in person.  
-  Applicants must submit an openly licensed Jupyter notebook demonstrating an innovative circuit-design or educational project developed using open-source tools and, where applicable, open-source process design kits.
-  The notebook should clearly communicate the project’s main ideas, design decisions, methodology, results, and reproducibility instructions. Generating a final circuit layout is encouraged but not required.
-  Eligible submissions may include, but are not limited to:
    -  Innovative circuit-design projects, such as inverters and temperature sensors.
    -  Creative educational uses of Python packages for circuit visualization or animation, including explanations of digital circuits, such as D flip-flops, and analog circuits, such as successive-approximation-register analog-to-digital converters.
    -  Exploration of open-source PDKs and SPICE simulations to demonstrate relevant figures of merit for circuit building blocks, including gain, bandwidth, power consumption, noise, linearity, or other appropriate performance metrics.
- Applicants are encouraged to review submissions from previous Code-a-Chip award recipients for examples of successful projects.
- Each submission must include an appropriate open-source license, such as the Apache License 2.0.
- Award recipients must comply with the applicable IEEE travel and expense reimbursement policies and attend ISSCC 2027 in person to qualify for reimbursement.

## Examples
- Examples:  [inverter](https://developers.google.com/silicon/guides/digital-inverter-openlane), [temperature sensor](https://github.com/idea-fasoc/OpenFASOC/blob/main/docs/source/notebooks/temp-sense-gen/temp_sense_genCollab.ipynb)
- Submissions of previous winners: [VLSI26](VLSI26/README.md), [ISSCC'26](ISSCC26/README.md), [VLSI'25](VLSI25/README.md), [ISSCC'24](ISSCC24/README.md), [ISSCC'23](ISSCC23/README.md), [VLSI'24](VLSI24/README.md) and [VLSI'23](VLSI23/README.md)

## Evaluation
- A jury of technical experts will evaluate all eligible submissions. Up to 10 applicants or teams may be selected to receive travel grants.

## Grant Amount
- Travel grants will be awarded according to the applicant’s category:

|Applicant category|Maximum grant amount|
|----|----|
|Secondary-school student|Up to US$500|
|Undergraduate student|Up to US$2,500|
|Graduate student or other eligible applicant|US$1,000–US$5,000|

- Grants may be used to reimburse eligible airfare, ground transportation and accommodation expenses, subject to IEEE travel and expense policies. Reimbursement will be limited to documented eligible expenses and will not exceed the recipient’s approved grant amount.
- Award recipients are responsible for retaining and submitting all required receipts and supporting documentation. Reimbursement will be processed after the conference upon receipt and approval of the required documentation.

## Program Logistics
- Submissions must be made through a GitHub pull request to the IEEE SSCS Open-Source Ecosystem Code-a-Chip GitHub repository.
1. Fork the official Code-a-Chip repository to your GitHub account:

   [https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io]
2. Create the following directory within your forked repository:

   `ISSCC27/submitted_notebooks/<project_name>/`
3. Place all files associated with your project inside this directory. Do not add, update, or modify files outside your project directory, as doing so may create conflicts when the pull request is reviewed and merged.
4. Add your completed Jupyter notebook, open-source license, and any necessary supporting files to the project directory.
5. Ensure that the notebook follows all requirements described in the “How to Apply” section.
6. Submit a pull request from your forked repository to the official Code-a-Chip repository before the submission deadline.
7. Monitor the pull request for questions or requested revisions from the program organizers.

- Award recipients must attend ISSCC 2027 in person to receive recognition and present a poster describing their projects.
- Reimbursement will be processed after the conference once the required travel and accommodation receipts and supporting documents have been submitted to and approved by the designated conference treasurer.


## Program Schedule
- **October 9, 2026, 11:59 AM Pacific Time**: Notebook submission deadline (GitHub pull request)
- Early November: Announcement of winners
- February 14-18, 2027: Attend the conference


## FAQ
**Who may apply?**
- The program is open to participants worldwide. IEEE SSCS membership is encouraged but not required. Individuals and teams may submit projects.

**Can a team submit a project?**
- Yes. Team submissions are encouraged. Each team must designate one representative who will receive the award and attend ISSCC 2027 in person.

**Is a completed circuit layout required?**
- No. A final circuit layout is encouraged but not required. The notebook should clearly present the project’s concept, methodology, design decisions, simulation or implementation results, and reproducibility instructions.

**Must the submission use an open-source PDK?**
- Applicants are encouraged to use open-source PDKs where appropriate. Educational projects involving circuit visualization, animation, simulation, or other open-source design activities may also be considered.

**Is an open-source license required?**
- Yes. Each submission must include an appropriate open-source license, such as the Apache License 2.0.

**How should a project be submitted?**
- Create a project directory under `ISSCC27/submitted_notebooks/` in a fork of the official repository. Add the notebook and all supporting files to that directory, and then submit a GitHub pull request before the deadline.

**What should I do if OpenLane cannot generate a layout in Google Colab?**
- Run the layout-generation flow in a compatible local environment. Include the resulting layout image, relevant output, and sufficient explanation in the submitted Jupyter notebook.

**What expenses are eligible for reimbursement?**
- Eligible expenses may include airfare, ground transportation and accommodation, subject to the approved grant amount and applicable IEEE travel and expense policies. Recipients must provide the required receipts and supporting documentation.

**When will reimbursement be issued?**
- Reimbursement will be processed after ISSCC 2027 once the recipient has attended the conference and submitted all required receipts and documentation for review and approval.

**Must an award recipient attend ISSCC 2027?**
- Yes. Award recipients must attend ISSCC 2027 in person and present a poster to qualify for recognition and reimbursement.

## Contact
- Akira Tsuchiya (a_tsuchiya@ieee.org)
- Muhammed Luqman Jukaku (Contact@mljukaku.com)
- Mehdi Saligane (mehdi_saligane@brown.edu)
- Boris Murmann (bmurmann@hawaii.edu)
